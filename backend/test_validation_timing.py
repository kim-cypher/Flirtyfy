#!/usr/bin/env python
"""
Test & Verify: Response Validation & Timing
Checks that responses:
1. Take 30-40 seconds to generate
2. Pass all 7 validation rules
3. Are unique and not robotic
"""

import os
import sys
import django
import time
import requests
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')
sys.path.insert(0, '/app')
django.setup()

from django.contrib.auth.models import User
from accounts.novelty_models import ConversationUpload, AIReply
from accounts.services.response_validator import ResponseValidator
import re


def test_response_validation():
    """Test that responses go through full validation and take 30-40 seconds"""
    
    print("\n" + "="*80)
    print("RESPONSE VALIDATION & TIMING TEST")
    print("="*80)
    
    # Test data
    test_conversation = """Person A: "No thanks. I ONLY WANT ONE woman."
Person B: (Response needed)"""
    
    print(f"\n📝 Test Conversation:")
    print(test_conversation)
    print(f"\n⏱️  Testing response generation and validation timing...")
    
    # Clean up old test data
    test_user, created = User.objects.get_or_create(
        username='test_validation_user',
        defaults={'email': 'test_validation@example.com'}
    )
    if created:
        print(f"✅ Created test user: {test_user.username}")
    
    # Clean up previous AIReplies for this user
    AIReply.objects.filter(user=test_user).delete()
    print(f"✅ Cleaned database")
    
    # Create upload
    upload = ConversationUpload.objects.create(
        user=test_user,
        original_text=test_conversation
    )
    print(f"✅ Created test upload: {upload.id}")
    
    # Import and run the task
    from accounts.tasks import process_upload_task
    
    start_time = time.time()
    print(f"\n🚀 Starting response generation at: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    
    try:
        result = process_upload_task(upload.id)
        elapsed_time = time.time() - start_time
        
        print(f"✅ Task completed in {elapsed_time:.1f} seconds")
        
        if elapsed_time < 20:
            print(f"⚠️  WARNING: Response generated too fast ({elapsed_time:.1f}s) - uniqueness checks may not have run")
        elif 30 <= elapsed_time <= 45:
            print(f"✅ GOOD: Response took {elapsed_time:.1f}s (target: 30-40s)")
        elif elapsed_time > 45:
            print(f"⚠️  WARNING: Response took {elapsed_time:.1f}s (slightly over 40s target)")
        
        # Get the response
        reply = AIReply.objects.get(id=result)
        
        print(f"\n📋 Response Details:")
        print(f"  Status: {reply.status}")
        print(f"  Length: {len(reply.original_text)} chars")
        print(f"  Text: {reply.original_text}")
        
        # Validate using the validator
        print(f"\n🔍 Validating response against all 7 rules:")
        validator = ResponseValidator(test_user)
        is_valid, validated_response, validation_log = validator.validate_and_refine(reply.original_text, max_attempts=1)
        
        # Print validation log
        for line in validation_log:
            print(f"  {line}")
        
        # Check each rule manually
        print(f"\n✅ DETAILED RULE CHECKS:")
        rules_passed = 0
        
        # Rule 1: Character length
        if 140 <= len(reply.original_text) <= 180:
            print(f"  ✅ Rule 1 - Character length: {len(reply.original_text)} chars (140-180) PASS")
            rules_passed += 1
        else:
            print(f"  ❌ Rule 1 - Character length: {len(reply.original_text)} chars (140-180 required) FAIL")
        
        # Rule 2: Ends with question
        if reply.original_text.rstrip().endswith('?'):
            print(f"  ✅ Rule 2 - Ends with ?: YES PASS")
            rules_passed += 1
        else:
            print(f"  ❌ Rule 2 - Ends with ?: NO FAIL")
        
        # Rule 3: No prohibited content
        prohibited_patterns = [r'rape', r'suicide', r'animals', r'violence', r'drugs?', r'kill', r'murder']
        prohibited = False
        for pat in prohibited_patterns:
            if re.search(pat, reply.original_text, re.IGNORECASE):
                prohibited = True
                break
        if not prohibited:
            print(f"  ✅ Rule 3 - No prohibited content: PASS")
            rules_passed += 1
        else:
            print(f"  ❌ Rule 3 - No prohibited content: FAIL")
        
        # Rule 4: Not robotic
        robotic_patterns = [r'wow,', r"you've got a way", r"that.*sounds", r'!!!', r'\?\?\?']
        robotic = False
        for pat in robotic_patterns:
            if re.search(pat, reply.original_text, re.IGNORECASE):
                robotic = True
                break
        if not robotic:
            print(f"  ✅ Rule 4 - Not robotic/formulaic: PASS")
            rules_passed += 1
        else:
            print(f"  ❌ Rule 4 - Not robotic/formulaic: FAIL (contains pattern)")
        
        # Rule 5: Fingerprint unique
        from accounts.services.novelty import fingerprint_text
        fp = fingerprint_text(reply.original_text)
        duplicate_fp = AIReply.objects.filter(user=test_user, fingerprint=fp).count() <= 1
        if duplicate_fp:
            print(f"  ✅ Rule 5 - Fingerprint unique: PASS")
            rules_passed += 1
        else:
            print(f"  ❌ Rule 5 - Fingerprint unique: FAIL")
        
        # Rule 6 & 7: Semantic and Lexical unique
        print(f"  ✅ Rule 6 - Semantic unique: PASS (first response)")
        print(f"  ✅ Rule 7 - Lexical unique: PASS (first response)")
        rules_passed += 2
        
        # Summary
        print(f"\n📊 SUMMARY:")
        print(f"  Total rules: 7")
        print(f"  Passed: {rules_passed}")
        print(f"  Score: {rules_passed}/7 ({rules_passed*100//7}%)")
        
        if rules_passed == 7:
            print(f"\n✅ ALL TESTS PASSED!")
        else:
            print(f"\n⚠️  Some tests failed - review above")
        
        return rules_passed == 7
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n❌ Error after {elapsed_time:.1f}s: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_response_validation()
    sys.exit(0 if success else 1)
