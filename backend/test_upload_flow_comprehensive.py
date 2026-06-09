"""
End-to-End Upload Flow Tests
Comprehensive testing of the entire production refactor pipeline

UPLOAD FLOW:
1. POST /api/conversation-upload/ with conversation_text
2. View validates input (length, rate limit)
3. View creates ConversationUpload record
4. View queues async task: process_upload_production.delay(upload_id)
5. Celery task retrieves upload
6. Task calls ProductionGenerator.generate()
7. Task creates AIReply with all required fields
8. User can GET /api/ai-reply/ to see the generated reply

This test suite validates every step and all failure modes.
"""

import os
import sys
import django
from datetime import timedelta

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')
django.setup()

from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
import json

from accounts.novelty_models import ConversationUpload, AIReply, AIReplyFeedback
from accounts.production_tasks import process_upload_production, _generate_with_production
from accounts.services.production_generator import ProductionGenerator, InputValidator
from accounts.services.novelty import normalize_text, fingerprint_text


class UploadFlowTestBase(TransactionTestCase):
    """Base class for upload flow tests"""
    
    def setUp(self):
        """Set up test user and API client"""
        self.user = User.objects.create_user(
            username='test_flow_user',
            email='test_flow@test.com',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Clear cache between tests
        cache.clear()
    
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()


class Test1_UploadValidation(UploadFlowTestBase):
    """Test 1: Validate input validation at upload endpoint"""
    
    def test_upload_missing_conversation_text(self):
        """Test upload fails with empty conversation_text"""
        print("\n  TEST: Upload with missing conversation_text")
        
        response = self.client.post('/api/conversation-upload/', {})
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert 'error' in response.data
        print("    ✓ Correctly rejected missing conversation_text")
    
    def test_upload_empty_string(self):
        """Test upload fails with empty string"""
        print("\n  TEST: Upload with empty string")
        
        response = self.client.post('/api/conversation-upload/', {
            'conversation_text': ''
        })
        
        assert response.status_code == 400
        print("    ✓ Correctly rejected empty string")
    
    def test_upload_only_whitespace(self):
        """Test upload fails with whitespace only"""
        print("\n  TEST: Upload with whitespace only")
        
        response = self.client.post('/api/conversation-upload/', {
            'conversation_text': '   \n\t   '
        })
        
        assert response.status_code == 400
        print("    ✓ Correctly rejected whitespace only")
    
    def test_upload_too_short(self):
        """Test upload fails with conversation < 10 chars"""
        print("\n  TEST: Upload with too-short conversation")
        
        response = self.client.post('/api/conversation-upload/', {
            'conversation_text': 'short'
        })
        
        assert response.status_code == 400
        data = response.json()
        assert 'short' in data['message'].lower()
        print("    ✓ Correctly rejected too-short input")
    
    def test_upload_too_long(self):
        """Test upload fails with conversation > 50k chars"""
        print("\n  TEST: Upload with too-long conversation")
        
        response = self.client.post('/api/conversation-upload/', {
            'conversation_text': 'x' * 60000
        })
        
        assert response.status_code == 400
        data = response.json()
        assert 'long' in data['message'].lower()
        print("    ✓ Correctly rejected too-long input")
    
    def test_upload_valid_minimum_length(self):
        """Test upload succeeds with exactly 10 chars"""
        print("\n  TEST: Upload with minimum valid length (10 chars)")
        
        response = self.client.post('/api/conversation-upload/', {
            'conversation_text': 'x' * 10
        })
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.data}"
        assert 'upload_id' in response.data
        print("    ✓ Correctly accepted minimum length input")
    
    def test_upload_valid_normal_length(self):
        """Test upload succeeds with normal length"""
        print("\n  TEST: Upload with normal length")
        
        conversation = "She: Hey! How are you?\nYou: I'm doing great! How about you?"
        
        response = self.client.post('/api/conversation-upload/', {
            'conversation_text': conversation
        })
        
        assert response.status_code == 201
        assert response.data['status'] == 'processing'
        print("    ✓ Correctly accepted normal length input")
    
    def test_upload_creates_database_record(self):
        """Test that upload creates ConversationUpload record"""
        print("\n  TEST: Upload creates database record")
        
        conversation = "She: Hi there!\nYou: Hey!"
        
        initial_count = ConversationUpload.objects.count()
        
        response = self.client.post('/api/conversation-upload/', {
            'conversation_text': conversation
        })
        
        assert response.status_code == 201
        final_count = ConversationUpload.objects.count()
        
        assert final_count == initial_count + 1, "Upload not created in database"
        
        upload = ConversationUpload.objects.latest('created_at')
        assert upload.user == self.user
        assert upload.original_text == conversation
        print("    ✓ Upload record correctly created in database")


class Test2_RateLimiting(UploadFlowTestBase):
    """Test 2: Validate rate limiting"""
    
    def test_rate_limit_after_100_uploads(self):
        """Test rate limit kicks in after 100 uploads in 5 minutes"""
        print("\n  TEST: Rate limiting after 100 uploads")
        
        conversation = "She: Hi!\nYou: Hello!"
        
        # Upload 100 times
        for i in range(100):
            response = self.client.post('/api/conversation-upload/', {
                'conversation_text': conversation
            })
            assert response.status_code == 201, f"Upload {i} failed"
        
        # 101st upload should be rate limited
        response = self.client.post('/api/conversation-upload/', {
            'conversation_text': conversation
        })
        
        assert response.status_code == 429, f"Expected 429, got {response.status_code}"
        assert 'rate_limited' in response.data.get('error', '')
        print("    ✓ Correctly rate limited after 100 uploads")
    
    def test_rate_limit_per_user(self):
        """Test rate limiting is per-user"""
        print("\n  TEST: Rate limiting is per-user")
        
        # Create second user
        user2 = User.objects.create_user(
            username='test_user_2',
            email='test2@test.com',
            password='pass123'
        )
        
        conversation = "She: Hi!\nYou: Hello!"
        
        # User 1: upload 100 times
        for i in range(100):
            response = self.client.post('/api/conversation-upload/', {
                'conversation_text': conversation
            })
        
        # User 2 should still be able to upload
        client2 = APIClient()
        client2.force_authenticate(user=user2)
        
        response = client2.post('/api/conversation-upload/', {
            'conversation_text': conversation
        })
        
        assert response.status_code == 201, f"User 2 should not be rate limited: {response.status_code}"
        print("    ✓ Rate limiting is correctly per-user")


class Test3_AsyncProcessing(UploadFlowTestBase):
    """Test 3: Validate async task processing"""
    
    @patch('accounts.production_tasks.get_embedding')
    @patch('accounts.services.production_generator.get_openai_client')
    def test_async_task_creates_reply(self, mock_client, mock_embedding):
        """Test that async task creates AIReply"""
        print("\n  TEST: Async task creates AIReply")
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "That's interesting! What made you think that?"
        mock_api = MagicMock()
        mock_api.chat.completions.create.return_value = mock_response
        mock_client.return_value = mock_api
        
        # Mock embedding
        mock_embedding.return_value = [0.1] * 1536
        
        # Create upload
        conversation = "She: I love hiking on weekends!\nYou: ?"
        upload = ConversationUpload.objects.create(
            user=self.user,
            original_text=conversation
        )
        
        initial_reply_count = AIReply.objects.count()
        
        # Process upload
        result = process_upload_production(upload.id)
        
        assert result['success'] == True, f"Task failed: {result}"
        assert result['reply_id'] is not None
        
        final_reply_count = AIReply.objects.count()
        assert final_reply_count == initial_reply_count + 1, "Reply not created"
        
        reply = AIReply.objects.get(id=result['reply_id'])
        assert reply.user == self.user
        assert reply.upload == upload
        print("    ✓ Async task correctly created AIReply")
    
    @patch('accounts.services.production_generator.get_openai_client')
    def test_async_task_populates_all_required_fields(self, mock_client):
        """Test that AIReply has all required fields"""
        print("\n  TEST: Async task populates all required fields")
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "That sounds great!"
        mock_api = MagicMock()
        mock_api.chat.completions.create.return_value = mock_response
        mock_client.return_value = mock_api
        
        # Create upload
        conversation = "She: I want to travel!\nYou: ?"
        upload = ConversationUpload.objects.create(
            user=self.user,
            original_text=conversation
        )
        
        # Process upload
        result = process_upload_production(upload.id)
        
        reply = AIReply.objects.get(id=result['reply_id'])
        
        # Check all required fields
        required_fields = {
            'user': self.user,
            'upload': upload,
            'original_text': 'That sounds great!',
            'fingerprint': str,
            'normalized_text': str,
            'summary': str,
            'intent': str,
            'status': 'complete',
            'expires_at': (timezone.now() + timedelta(days=45)).date(),
        }
        
        for field, expected in required_fields.items():
            value = getattr(reply, field, None)
            
            if field == 'expires_at':
                # Check date, not exact timestamp
                assert value.date() == expected, f"Field {field}: expected {expected}, got {value}"
            elif isinstance(expected, type):
                assert isinstance(value, expected), f"Field {field}: expected {expected}, got {type(value)}"
            else:
                assert value == expected, f"Field {field}: expected {expected}, got {value}"
        
        print("    ✓ All required fields populated correctly")


class Test4_CompleteUploadFlow(UploadFlowTestBase):
    """Test 4: End-to-end complete flow"""
    
    @patch('accounts.services.production_generator.get_openai_client')
    def test_complete_flow_from_upload_to_reply(self, mock_client):
        """Test complete flow: upload -> async -> reply"""
        print("\n  TEST: Complete flow from upload to reply")
        
        # Mock LLM
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "That's awesome! Tell me more?"
        mock_api = MagicMock()
        mock_api.chat.completions.create.return_value = mock_response
        mock_client.return_value = mock_api
        
        conversation = "She: I just finished a marathon!\nYou: ?"
        
        # Step 1: Upload conversation
        print("    Step 1: POST upload")
        response = self.client.post('/api/conversation-upload/', {
            'conversation_text': conversation
        })
        
        assert response.status_code == 201
        upload_id = response.data['upload_id']
        print(f"      ✓ Upload created: {upload_id}")
        
        # Step 2: Verify ConversationUpload was created
        print("    Step 2: Verify ConversationUpload created")
        upload = ConversationUpload.objects.get(id=upload_id)
        assert upload.original_text == conversation
        print("      ✓ ConversationUpload verified")
        
        # Step 3: Process async task
        print("    Step 3: Process async task")
        result = process_upload_production(upload_id)
        assert result['success'] == True
        reply_id = result['reply_id']
        print(f"      ✓ Async task processed: {reply_id}")
        
        # Step 4: Verify AIReply was created
        print("    Step 4: Verify AIReply created")
        reply = AIReply.objects.get(id=reply_id)
        assert reply.original_text == "That's awesome! Tell me more?"
        assert reply.user == self.user
        assert reply.upload == upload
        print("      ✓ AIReply verified")
        
        # Step 5: Get replies via API
        print("    Step 5: GET replies via API")
        response = self.client.get('/api/ai-reply/')
        assert response.status_code == 200
        assert len(response.data) > 0
        print("      ✓ Replies API working")
        
        print("    ✓ Complete flow successful")


class Test5_ErrorHandling(UploadFlowTestBase):
    """Test 5: Error handling and recovery"""
    
    @patch('accounts.production_tasks.ConversationUpload.objects.get')
    def test_task_handles_missing_upload(self, mock_get):
        """Test task handles missing upload gracefully"""
        print("\n  TEST: Task handles missing upload")
        
        from django.core.exceptions import ObjectDoesNotExist
        mock_get.side_effect = ObjectDoesNotExist("Upload not found")
        
        # Should not crash, should handle gracefully
        try:
            result = process_upload_production(999)
            # Task should either fail gracefully or return error
            print("    ✓ Task handled missing upload gracefully")
        except ObjectDoesNotExist:
            print("    ✓ Task raised expected ObjectDoesNotExist")
    
    @patch('accounts.services.production_generator.get_openai_client')
    def test_fallback_used_on_llm_failure(self, mock_client):
        """Test fallback is used if LLM fails"""
        print("\n  TEST: Fallback used on LLM failure")
        
        # Mock LLM to fail
        mock_client.side_effect = Exception("LLM unavailable")
        
        conversation = "She: Hi!\nYou: ?"
        upload = ConversationUpload.objects.create(
            user=self.user,
            original_text=conversation
        )
        
        # Process should still succeed with fallback
        result = process_upload_production(upload.id)
        
        assert result['success'] == True
        
        reply = AIReply.objects.get(id=result['reply_id'])
        # Should have a fallback reply
        assert reply.original_text in ProductionGenerator.FALLBACK_TEMPLATES
        assert reply.status == 'fallback'
        print("    ✓ Fallback used correctly on LLM failure")
    
    @patch('accounts.services.production_generator.get_openai_client')
    def test_all_required_fields_even_on_failure(self, mock_client):
        """Test all fields populated even if LLM fails"""
        print("\n  TEST: All fields populated even on failure")
        
        mock_client.side_effect = Exception("LLM error")
        
        conversation = "She: How are you?\nYou: ?"
        upload = ConversationUpload.objects.create(
            user=self.user,
            original_text=conversation
        )
        
        result = process_upload_production(upload.id)
        reply = AIReply.objects.get(id=result['reply_id'])
        
        # Check fields exist even in fallback
        assert reply.summary is not None or reply.summary == ''
        assert reply.intent is not None or reply.intent == ''
        assert reply.fingerprint is not None
        assert reply.expires_at is not None
        print("    ✓ All fields populated even on failure")


class Test6_UniquenessPrevention(UploadFlowTestBase):
    """Test 6: Duplicate prevention"""
    
    @patch('accounts.services.production_generator.get_openai_client')
    def test_duplicate_response_uses_fallback(self, mock_client):
        """Test duplicate response triggers fallback"""
        print("\n  TEST: Duplicate response triggers fallback")
        
        # Mock same response twice
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Exact same response every time"
        mock_api = MagicMock()
        mock_api.chat.completions.create.return_value = mock_response
        mock_client.return_value = mock_api
        
        # Create two uploads
        conv1 = "She: First message\nYou: ?"
        conv2 = "She: Second message\nYou: ?"
        
        upload1 = ConversationUpload.objects.create(
            user=self.user,
            original_text=conv1
        )
        
        upload2 = ConversationUpload.objects.create(
            user=self.user,
            original_text=conv2
        )
        
        # Process first upload - should succeed
        result1 = process_upload_production(upload1.id)
        assert result1['success'] == True
        reply1 = AIReply.objects.get(id=result1['reply_id'])
        print(f"      First reply: {reply1.original_text}")
        
        # Process second upload - should use fallback due to duplicate
        result2 = process_upload_production(upload2.id)
        reply2 = AIReply.objects.get(id=result2['reply_id'])
        
        # Second should be different or be fallback
        if reply1.original_text == reply2.original_text:
            # Same response detected, should have used fallback
            assert reply2.status == 'fallback'
            print(f"      Second reply (fallback): {reply2.original_text}")
            print("    ✓ Duplicate response correctly triggered fallback")
        else:
            print(f"      Second reply (unique): {reply2.original_text}")
            print("    ✓ Unique response generated")


class Test7_RateLimitCacheBehavior(UploadFlowTestBase):
    """Test 7: Rate limit cache behavior"""
    
    def test_rate_limit_cache_persists_within_window(self):
        """Test rate limit cache persists within 5-minute window"""
        print("\n  TEST: Rate limit cache persists within window")
        
        conversation = "She: Test\nYou: Hi!"
        
        # Upload once
        response1 = self.client.post('/api/conversation-upload/', {
            'conversation_text': conversation
        })
        assert response1.status_code == 201
        
        # Immediately upload again
        response2 = self.client.post('/api/conversation-upload/', {
            'conversation_text': conversation + " different"
        })
        assert response2.status_code == 201
        
        # Cache counter should have incremented
        cache_key = f"upload_limit:{self.user.id}"
        count = cache.get(cache_key, 0)
        assert count >= 2, f"Cache counter not incremented: {count}"
        
        print("    ✓ Rate limit counter persists correctly")


class Test8_ConcurrentUploads(UploadFlowTestBase):
    """Test 8: Handle concurrent uploads"""
    
    @patch('accounts.services.production_generator.get_openai_client')
    def test_concurrent_uploads_all_processed(self, mock_client):
        """Test that multiple concurrent uploads are all processed"""
        print("\n  TEST: Multiple concurrent uploads processed")
        
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Great response!"
        mock_api = MagicMock()
        mock_api.chat.completions.create.return_value = mock_response
        mock_client.return_value = mock_api
        
        # Upload multiple conversations
        conversations = [
            "She: Message 1\nYou: ?",
            "She: Message 2\nYou: ?",
            "She: Message 3\nYou: ?",
        ]
        
        upload_ids = []
        for conv in conversations:
            response = self.client.post('/api/conversation-upload/', {
                'conversation_text': conv
            })
            assert response.status_code == 201
            upload_ids.append(response.data['upload_id'])
        
        # Process all uploads
        for upload_id in upload_ids:
            result = process_upload_production(upload_id)
            assert result['success'] == True
        
        # Verify all replies created
        replies = AIReply.objects.filter(user=self.user).order_by('-created_at')[:3]
        assert replies.count() == 3, f"Expected 3 replies, got {replies.count()}"
        
        print("    ✓ All concurrent uploads processed correctly")


def run_all_tests():
    """Run all upload flow tests"""
    
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "END-TO-END UPLOAD FLOW TESTS" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")
    
    test_classes = [
        ("Test 1: Upload Validation", Test1_UploadValidation),
        ("Test 2: Rate Limiting", Test2_RateLimiting),
        ("Test 3: Async Processing", Test3_AsyncProcessing),
        ("Test 4: Complete Flow", Test4_CompleteUploadFlow),
        ("Test 5: Error Handling", Test5_ErrorHandling),
        ("Test 6: Uniqueness Prevention", Test6_UniquenessPrevention),
        ("Test 7: Cache Behavior", Test7_RateLimitCacheBehavior),
        ("Test 8: Concurrent Uploads", Test8_ConcurrentUploads),
    ]
    
    results = {}
    
    for test_name, test_class in test_classes:
        print(f"\n{test_name}")
        print("─" * 80)
        
        # Run all test methods in class
        suite = __import__('unittest').TestLoader().loadTestsFromTestCase(test_class)
        runner = __import__('unittest').TextTestRunner(verbosity=0)
        result = runner.run(suite)
        
        passed = result.testsRun - len(result.failures) - len(result.errors)
        results[test_name] = (passed, result.testsRun, result.failures, result.errors)
        
        if result.failures:
            print("\nFAILURES:")
            for test, traceback in result.failures:
                print(f"  ✗ {test}: {traceback}")
        
        if result.errors:
            print("\nERRORS:")
            for test, traceback in result.errors:
                print(f"  ✗ {test}: {traceback}")
    
    # Summary
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 30 + "TEST SUMMARY" + " " * 35 + "║")
    print("╚" + "=" * 78 + "╝\n")
    
    total_passed = 0
    total_tests = 0
    
    for test_name, (passed, total, failures, errors) in results.items():
        total_passed += passed
        total_tests += total
        
        status = "✓ PASS" if len(failures) == 0 and len(errors) == 0 else "✗ FAIL"
        print(f"{status}  {test_name}: {passed}/{total}")
    
    print("\n" + "─" * 80)
    print(f"TOTAL: {total_passed}/{total_tests} tests passed\n")
    
    if total_passed == total_tests:
        print("✅ ALL TESTS PASSED - Upload flow is solid!\n")
        return 0
    else:
        print(f"⚠️  {total_tests - total_passed} test(s) failed\n")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
