"""
Production Refactor Integration Tests
Tests the new ProductionGenerator, ProductionMetrics, and related services
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import json
from unittest.mock import patch, MagicMock

from accounts.novelty_models import ConversationUpload, AIReply
from accounts.services.production_generator import (
    ProductionGenerator, ProductionMetrics, InputValidator, 
    ConversationCache, UniquenessBatcher
)
from accounts.services.conversation_parser import ConversationParser
from accounts.services.tone_intent_classifier import ToneIntentClassifier
from accounts.services.safety_filter import SafetyFilter
from accounts.services.reply_patches import ReplyPatches
from accounts.services.novelty import normalize_text, fingerprint_text


class ProductionGeneratorImportTest(TestCase):
    """Test that all imports work"""
    
    def test_production_generator_import(self):
        """Test ProductionGenerator can be imported"""
        self.assertIsNotNone(ProductionGenerator)
        
    def test_production_metrics_import(self):
        """Test ProductionMetrics can be imported"""
        self.assertIsNotNone(ProductionMetrics)
        
    def test_input_validator_import(self):
        """Test InputValidator can be imported"""
        self.assertIsNotNone(InputValidator)
        
    def test_conversation_cache_import(self):
        """Test ConversationCache can be imported"""
        self.assertIsNotNone(ConversationCache)


class InputValidatorTest(TestCase):
    """Test InputValidator class"""
    
    def test_valid_conversation(self):
        """Test valid conversation passes validation"""
        is_valid, error = InputValidator.validate_and_check_limits(
            user_id=999,
            conversation_text="This is a valid conversation with at least 10 characters"
        )
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_conversation_too_short(self):
        """Test too-short conversation fails"""
        is_valid, error = InputValidator.validate_and_check_limits(
            user_id=999,
            conversation_text="short"
        )
        self.assertFalse(is_valid)
        self.assertIn("short", error.lower())
    
    def test_conversation_too_long(self):
        """Test too-long conversation fails"""
        is_valid, error = InputValidator.validate_and_check_limits(
            user_id=999,
            conversation_text="x" * 60000  # Exceeds 50k limit
        )
        self.assertFalse(is_valid)
        self.assertIn("long", error.lower())


class ConversationParserTest(TestCase):
    """Test conversation parsing"""
    
    def setUp(self):
        self.parser = ConversationParser()
    
    def test_parse_simple_conversation(self):
        """Test parsing a simple conversation"""
        text = "Her: Hey!\nYou: Hi there!"
        result = self.parser.parse_conversation(text)
        
        self.assertIn('message_count', result)
        self.assertGreater(result['message_count'], 0)
    
    def test_parse_conversation_extracts_messages(self):
        """Test that parser extracts individual messages"""
        text = "She: How are you?\nYou: I'm good, how about you?"
        result = self.parser.parse_conversation(text)
        
        # Should have parsed the conversation
        self.assertIsNotNone(result)
        self.assertEqual(result['message_count'], 2)


class ToneIntentClassifierTest(TestCase):
    """Test tone and intent classification"""
    
    def setUp(self):
        self.classifier = ToneIntentClassifier()
    
    def test_classify_romantic_message(self):
        """Test classification of romantic message"""
        tone, intent, emotion = self.classifier.classify("I've never felt this way before")
        self.assertIsNotNone(tone)
        self.assertIsNotNone(intent)
        self.assertIsNotNone(emotion)
    
    def test_classify_playful_message(self):
        """Test classification of playful message"""
        tone, intent, emotion = self.classifier.classify("Haha that's so funny!")
        self.assertIsNotNone(tone)
        self.assertIsNotNone(intent)
        self.assertIsNotNone(emotion)
    
    def test_classify_question(self):
        """Test that questions are detected"""
        tone, intent, emotion = self.classifier.classify("How are you doing?")
        self.assertIsNotNone(intent)


class SafetyFilterTest(TestCase):
    """Test safety filtering"""
    
    def setUp(self):
        self.safety = SafetyFilter()
    
    def test_safe_message_passes(self):
        """Test that safe messages pass"""
        is_safe, violation, response = self.safety.check_safety(
            "I really enjoy hiking on weekends"
        )
        self.assertTrue(is_safe)
    
    def test_unsafe_message_blocked(self):
        """Test that unsafe messages are blocked"""
        is_safe, violation, response = self.safety.check_safety(
            "I want to hurt you"
        )
        self.assertFalse(is_safe)
        self.assertIsNotNone(violation)


class ReplyPatchesTest(TestCase):
    """Test response patching"""
    
    def test_patch_length_short(self):
        """Test patch_length fixes short responses"""
        short_reply = "Hey"
        patched = ReplyPatches.patch_length(short_reply)
        self.assertGreater(len(patched), len(short_reply))
    
    def test_patch_length_long(self):
        """Test patch_length fixes long responses"""
        long_reply = "This is a very long response that goes on and on and on and on and on and on and on and exceeds the character limit"
        patched = ReplyPatches.patch_length(long_reply)
        self.assertLess(len(patched), len(long_reply))
    
    def test_patch_question_ending(self):
        """Test patch_question_ending adds question mark"""
        reply = "What's up"
        patched = ReplyPatches.patch_question_ending(reply)
        self.assertTrue(patched.endswith('?'))


class NoveltyUtilsTest(TestCase):
    """Test novelty utility functions"""
    
    def test_normalize_text(self):
        """Test text normalization"""
        text = "Hello  WORLD!!!"
        normalized = normalize_text(text)
        self.assertEqual(normalized, normalized.lower())
    
    def test_fingerprint_text(self):
        """Test fingerprinting"""
        text = "Hello World"
        fp = fingerprint_text(text)
        
        # Should be hex string
        self.assertTrue(all(c in '0123456789abcdef' for c in fp))
        
        # Same text should produce same fingerprint
        fp2 = fingerprint_text(text)
        self.assertEqual(fp, fp2)


class ProductionGeneratorInitTest(TestCase):
    """Test ProductionGenerator initialization"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='test_prod_gen',
            email='test_prod_gen@test.com'
        )
    
    def test_generator_init(self):
        """Test ProductionGenerator initialization"""
        gen = ProductionGenerator(self.user.id)
        
        self.assertEqual(gen.user_id, self.user.id)
        self.assertIsNotNone(gen.parser)
        self.assertIsNotNone(gen.classifier)
        self.assertIsNotNone(gen.extractor)
        self.assertIsNotNone(gen.safety)
        self.assertIsNotNone(gen.patcher)
    
    def test_fallback_templates_exist(self):
        """Test that fallback templates are available"""
        self.assertGreater(len(ProductionGenerator.FALLBACK_TEMPLATES), 0)


class ModelFieldsTest(TestCase):
    """Test that models have correct fields"""
    
    def test_conversation_upload_fields(self):
        """Test ConversationUpload has correct fields"""
        self.assertTrue(hasattr(ConversationUpload, 'user'))
        self.assertTrue(hasattr(ConversationUpload, 'original_text'))
        self.assertTrue(hasattr(ConversationUpload, 'created_at'))
    
    def test_ai_reply_fields(self):
        """Test AIReply has all required fields"""
        required_fields = [
            'user', 'upload', 'original_text', 'fingerprint',
            'embedding', 'normalized_text', 'summary', 'intent',
            'status', 'expires_at', 'created_at'
        ]
        
        for field_name in required_fields:
            self.assertTrue(
                hasattr(AIReply, field_name),
                f"AIReply missing field: {field_name}"
            )


class ConversationUploadTest(TransactionTestCase):
    """Test ConversationUpload model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='test_upload',
            email='test_upload@test.com'
        )
    
    def test_create_conversation_upload(self):
        """Test creating a conversation upload"""
        upload = ConversationUpload.objects.create(
            user=self.user,
            original_text="She: Hey! You: Hi there!"
        )
        
        self.assertIsNotNone(upload.id)
        self.assertEqual(upload.user, self.user)
        self.assertEqual(upload.original_text, "She: Hey! You: Hi there!")
    
    def test_conversation_upload_has_timestamp(self):
        """Test that uploads have creation timestamp"""
        upload = ConversationUpload.objects.create(
            user=self.user,
            original_text="Test conversation"
        )
        
        self.assertIsNotNone(upload.created_at)


class AIReplyTest(TransactionTestCase):
    """Test AIReply model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='test_reply',
            email='test_reply@test.com'
        )
        self.upload = ConversationUpload.objects.create(
            user=self.user,
            original_text="Test conversation"
        )
    
    def test_create_ai_reply(self):
        """Test creating an AI reply"""
        reply = AIReply.objects.create(
            user=self.user,
            upload=self.upload,
            original_text="I think that's great!",
            fingerprint="test_fp_12345",
            normalized_text="i think thats great",
            summary="A test reply",
            intent="positive",
            expires_at=timezone.now() + timedelta(days=45)
        )
        
        self.assertIsNotNone(reply.id)
        self.assertEqual(reply.user, self.user)
        self.assertEqual(reply.upload, self.upload)
    
    def test_ai_reply_status_field(self):
        """Test AI reply status field"""
        reply = AIReply.objects.create(
            user=self.user,
            upload=self.upload,
            original_text="Test reply",
            fingerprint="test_fp",
            normalized_text="test reply",
            summary="Test",
            intent="test",
            status='complete',
            expires_at=timezone.now() + timedelta(days=45)
        )
        
        self.assertEqual(reply.status, 'complete')


class ProductionMetricsTest(TestCase):
    """Test metrics recording"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='test_metrics',
            email='test_metrics@test.com'
        )
    
    @patch('accounts.services.production_generator.cache')
    def test_record_request(self, mock_cache):
        """Test recording a request metric"""
        ProductionMetrics.record_request(
            user_id=self.user.id,
            success=True,
            tokens_input=100,
            tokens_output=50,
            latency_ms=250.5,
            fallback=False
        )
        
        # Should have called cache.set
        self.assertTrue(mock_cache.set.called or mock_cache.get.called)


class ProductionGeneratorGenerateTest(TransactionTestCase):
    """Test ProductionGenerator.generate() method"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='test_gen',
            email='test_gen@test.com'
        )
        self.gen = ProductionGenerator(self.user.id)
    
    @patch('accounts.services.production_generator.get_openai_client')
    def test_generate_reply_with_mock_llm(self, mock_client):
        """Test generate() with mocked LLM"""
        # Mock the OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "That sounds amazing! What made you think of that?"
        
        mock_api = MagicMock()
        mock_api.chat.completions.create.return_value = mock_response
        mock_client.return_value = mock_api
        
        conversation = "She: I've been thinking about learning guitar"
        reply, metadata = self.gen.generate(conversation)
        
        # Should have generated a reply
        self.assertIsNotNone(reply)
        
        # Metadata should contain required fields
        self.assertIn('success', metadata)
        self.assertIn('tokens_input', metadata)
        self.assertIn('tokens_output', metadata)
    
    def test_generate_with_short_text_fails(self):
        """Test that too-short conversation fails validation"""
        reply, metadata = self.gen.generate("short")
        
        self.assertFalse(metadata['success'])
        self.assertIsNotNone(metadata['error'])


class UniquenessBatcherTest(TransactionTestCase):
    """Test uniqueness checking"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='test_unique',
            email='test_unique@test.com'
        )
        self.upload = ConversationUpload.objects.create(
            user=self.user,
            original_text="Test"
        )
    
    def test_new_response_is_unique(self):
        """Test that a new response is marked as unique"""
        is_unique, reason = UniquenessBatcher.check_uniqueness(
            self.user.id,
            "This is a brand new response"
        )
        
        # First response should be unique
        self.assertTrue(is_unique)
    
    @patch('accounts.services.production_generator.get_embedding')
    def test_duplicate_fingerprint_detected(self, mock_embedding):
        """Test that duplicate fingerprints are detected"""
        mock_embedding.return_value = [0.1] * 1536
        
        # Create first response
        response_text = "Exact duplicate response"
        fp = fingerprint_text(response_text)
        
        AIReply.objects.create(
            user=self.user,
            upload=self.upload,
            original_text=response_text,
            fingerprint=fp,
            normalized_text=normalize_text(response_text),
            summary="Test",
            intent="test",
            expires_at=timezone.now() + timedelta(days=45)
        )
        
        # Try to create same response again
        is_unique, reason = UniquenessBatcher.check_uniqueness(
            self.user.id,
            response_text
        )
        
        # Should detect as duplicate
        self.assertFalse(is_unique)
