"""
Test Location and Meeting Rules Refinement
Validates that:
1. General location questions are ALLOWED
2. Specific address/work requests are DIVERTED  
3. Meeting requests are DIVERTED with contextual anchoring
4. Vacation/hotel contexts work properly
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')
django.setup()

from accounts.services.response_validator import ResponseValidator
from django.contrib.auth.models import User
import json

def test_location_rules():
    """Test location rule refinements"""
    print("\n" + "="*80)
    print("TESTING LOCATION RULES")
    print("="*80)
    
    # Create test user
    test_user = User.objects.create_user(
        username='test_location_user',
        email='test_location@test.com',
        password='testpass123'
    )
    
    validator = ResponseValidator(test_user)
    
    # TEST 1: General location question - SHOULD ALLOW
    print("\n✅ TEST 1: General location questions (SHOULD NOT DIVERT)")
    test_cases_allow = [
        "where do you live?",
        "where are you from?",
        "what city are you in?",
        "what country are you from?",
        "are you in the US?",
        "what state do you live in?",
    ]
    
    for msg in test_cases_allow:
        result = validator.check_conversation_rules(msg)
        status = "✅ PASS (allowed)" if result['action'] == 'allow' else f"❌ FAIL (diverted: {result.get('reason')})"
        print(f"  {msg:40} → {status}")
    
    # TEST 2: Specific address requests - SHOULD DIVERT
    print("\n❌ TEST 2: Specific address requests (SHOULD DIVERT)")
    test_cases_divert = [
        "what's your exact address?",
        "send me your address",
        "what street do you live on?",
        "what's your house number?",
        "where specifically do you work?",
        "what company do you work for?",
        "what's the name of your workplace?",
        "what office do you go to?",
    ]
    
    for msg in test_cases_divert:
        result = validator.check_conversation_rules(msg)
        status = "✅ DIVERT" if result['action'] == 'divert' else f"❌ FAIL (allowed)"
        reason = result.get('reason', '')
        print(f"  {msg:40} → {status}")
        if result['action'] == 'divert':
            print(f"     Response: {result['response']}")
    
    # TEST 3: Work-specific questions - SHOULD DIVERT
    print("\n❌ TEST 3: Work-specific questions (SHOULD DIVERT)")
    work_questions = [
        "where do you work specifically?",
        "what's your office location?",
        "which company?",
        "what business are you in exactly?",
    ]
    
    for msg in work_questions:
        result = validator.check_conversation_rules(msg)
        status = "✅ DIVERT" if result['action'] == 'divert' else f"❌ FAIL (allowed)"
        print(f"  {msg:40} → {status}")
    
    test_user.delete()
    print("\n✅ Location tests complete\n")


def test_meeting_rules():
    """Test meeting rule refinements and contextual anchoring"""
    print("\n" + "="*80)
    print("TESTING MEETING RULES & CONTEXTUAL ANCHORING")
    print("="*80)
    
    # Create test user
    test_user = User.objects.create_user(
        username='test_meeting_user',
        email='test_meeting@test.com',
        password='testpass123'
    )
    
    validator = ResponseValidator(test_user)
    
    # TEST 1: Specific meeting requests - SHOULD DIVERT
    print("\n❌ TEST 1: Meeting requests (SHOULD DIVERT with contextual anchoring)")
    test_cases_meeting = [
        ("let's meet soon", "Generic meeting request"),
        ("when can we meet?", "When question"),
        ("let's get coffee", "Specific activity"),
        ("can I come see you?", "Visit request"),
        ("should we meet tomorrow?", "Time-specific"),
        ("where can we meet?", "Location question"),
    ]
    
    for msg, description in test_cases_meeting:
        result = validator.check_conversation_rules(msg)
        status = "✅ DIVERT" if result['action'] == 'divert' else f"❌ FAIL (allowed)"
        print(f"\n  {description:30} | {msg}")
        print(f"  Status: {status}")
        if result['action'] == 'divert':
            print(f"  Response: {result['response']}")
    
    # TEST 2: Contextual anchoring - different message contexts
    print("\n\n🎯 TEST 2: Contextual anchoring based on message content")
    
    contextual_cases = [
        ("i love how you tease me", "Teasing/playful anchor"),
        ("there's something genuine here", "Genuine/vulnerable anchor"),
        ("i think you're special", "Confident anchor"),
        ("this feels different", "Generic anchor"),
    ]
    
    for msg, context in contextual_cases:
        # Simulate a meeting request within context
        full_message = f"{msg}, let's meet soon"
        result = validator.check_conversation_rules(full_message)
        print(f"\n  Context: {context}")  
        print(f"  Message: {msg}")
        if result['action'] == 'divert':
            print(f"  ✅ Contextual decline: {result['response']}")
        else:
            print(f"  ❌ Should have diverted")
    
    test_user.delete()
    print("\n✅ Meeting tests complete\n")


def test_vacation_hotel_handling():
    """Test vacation and hotel mention handling"""
    print("\n" + "="*80)
    print("TESTING VACATION & HOTEL CONTEXTS")
    print("="*80)
    
    test_user = User.objects.create_user(
        username='test_vacation_user',
        email='test_vacation@test.com',
        password='testpass123'
    )
    
    validator = ResponseValidator(test_user)
    
    # These should NOT divert - they're just mentioning places
    print("\n✅ TEST: Vacation mentions (SHOULD NOT DIVERT)")
    vacation_messages = [
        "I love Bali",
        "Have you been to Monaco?",
        "There's a nice hotel in Dubai",
        "I've always wanted to visit Tokyo",
        "Maldives would be romantic",
    ]
    
    for msg in vacation_messages:
        result = validator.check_conversation_rules(msg)
        status = "✅ ALLOW" if result['action'] == 'allow' else f"❌ DIVERTED (should allow)"
        print(f"  {msg:40} → {status}")
    
    test_user.delete()
    print("\n✅ Vacation tests complete\n")


def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print("\n" + "="*80)
    print("TESTING EDGE CASES")
    print("="*80)
    
    test_user = User.objects.create_user(
        username='test_edge_user',
        email='test_edge@test.com',
        password='testpass123'
    )
    
    validator = ResponseValidator(test_user)
    
    print("\n1. Case sensitivity tests:")
    cases = [
        "WHERE DO YOU LIVE?",
        "Where do you live?",
        "WhErE dO yOu LiVe?",
    ]
    
    for msg in cases:
        result = validator.check_conversation_rules(msg)
        status = "✅ ALLOW" if result['action'] == 'allow' else "❌ DIVERT"
        print(f"  {msg:40} → {status}")
    
    print("\n2. Negation tests:")
    negation_cases = [
        "i don't want to know where you live",  # Should still allow - just stating preference
        "don't ask my workplace",  # Should allow - they're saying no
    ]
    
    for msg in negation_cases:
        result = validator.check_conversation_rules(msg)
        status = result['action']
        print(f"  {msg:50} → {status}")
    
    print("\n3. Combined tests (location + meeting):")
    combined = [
        "where do you live and when can we meet?",  # Should divert on meeting
        "i want to know your address to pick you up",  # Should divert on address
    ]
    
    for msg in combined:
        result = validator.check_conversation_rules(msg)
        reason = result.get('reason', 'N/A')
        category = result.get('category', 'N/A')
        status = result['action']
        print(f"  {msg:50}")
        print(f"    → Action: {status}, Category: {category}, Reason: {reason}")
    
    test_user.delete()
    print("\n✅ Edge case tests complete\n")


if __name__ == '__main__':
    print("🧪 LOCATION & MEETING RULES VALIDATION TEST SUITE 🧪")
    
    try:
        test_location_rules()
        test_meeting_rules()
        test_vacation_hotel_handling()
        test_edge_cases()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
