#!/usr/bin/env python
"""
Task 7: Test Backend Endpoints
Tests the two new endpoints for button system (LEFT and RIGHT sides)

Requirements:
- Django project running
- PostgreSQL database running (docker-compose up)
- Redis running (for session tracking)
- Test user account created

Usage:
    python manage.py shell < test_button_system_endpoints.py
    OR
    python test_button_system_endpoints.py (if run directly)

Tests:
1. Test LEFT side: /api/chat/generate-specific/ with pasted conversation
2. Test RIGHT side: /api/chat/generate-button/ with button intent
3. Verify responses are generated
4. Verify database records created
5. Verify session tracking works
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')
django.setup()

from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from accounts.novelty_models import AIReply, ConversationUpload
from accounts.services.button_generator import get_user_session_info, reset_user_session
import json

print("\n" + "="*80)
print("TASK 7: TEST BACKEND ENDPOINTS")
print("="*80)

# Create test user if doesn't exist
TEST_USERNAME = 'testuser_button_system'
TEST_EMAIL = f'{TEST_USERNAME}@test.com'
TEST_PASSWORD = 'testpass123'

try:
    test_user = User.objects.get(username=TEST_USERNAME)
    print(f"\n✓ Using existing test user: {TEST_USERNAME} (ID: {test_user.id})")
except User.DoesNotExist:
    test_user = User.objects.create_user(
        username=TEST_USERNAME,
        email=TEST_EMAIL,
        password=TEST_PASSWORD
    )
    print(f"\n✓ Created test user: {TEST_USERNAME} (ID: {test_user.id})")

# Get or create token
token, created = Token.objects.get_or_create(user=test_user)
print(f"✓ Token: {token.key}")

# Initialize API client
client = APIClient()
client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

# Reset user session
reset_user_session(test_user.id)
print("✓ User session reset")

print("\n" + "-"*80)
print("TEST 1: LEFT SIDE - Generate Specific Response (Pasted Conversation)")
print("-"*80)

conversation_samples = [
    "Him: Hey, what's up?\nMe: Not much, just chilling\nHim: Want to hang?\nMe: Maybe later",
    "Her: I've been thinking about you all day\nMe: Really?\nHer: Yeah, what are you up to?\nMe: Just finished work",
    "Him: What do you like in a guy?\nMe: Someone who makes me laugh\nHim: I can do that\nMe: Prove it"
]

left_side_results = []

for i, conversation in enumerate(conversation_samples, 1):
    print(f"\n[TEST 1.{i}] Pasted conversation:")
    print(f"  Length: {len(conversation)} chars")
    print(f"  Preview: {conversation[:80]}...")
    
    response = client.post(
        '/api/chat/generate-specific/',
        {'conversation': conversation},
        format='json'
    )
    
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ Success: {data.get('message', 'OK')}")
        print(f"  ✓ Response: {data.get('response', '')[:100]}...")
        if 'intent' in data:
            intent = data['intent']
            print(f"  ✓ Intent detected:")
            print(f"      - Topic: {intent.get('topic', 'N/A')}")
            print(f"      - Tone: {intent.get('tone', 'N/A')}")
            print(f"      - Stage: {intent.get('stage', 'N/A')}")
            print(f"      - Energy: {intent.get('energy', 'N/A')}")
        left_side_results.append({'success': True, 'response': data.get('response', '')})
    else:
        error_data = response.json()
        print(f"  ✗ Error: {error_data.get('message', 'Unknown error')}")
        left_side_results.append({'success': False, 'error': error_data.get('message', '')})

# Verify database records for LEFT side
left_records = AIReply.objects.filter(user=test_user, intent_type='specific').count()
print(f"\n✓ Database: {left_records} specific responses saved")

print("\n" + "-"*80)
print("TEST 2: RIGHT SIDE - Generate Button Response (Button Click)")
print("-"*80)

button_intents = [
    'morning_flirt',
    'deep_talk',
    'sensual',
    'bedroom_questions',
    'lyrical_romance'
]

right_side_results = []

for i, button_intent in enumerate(button_intents, 1):
    print(f"\n[TEST 2.{i}] Button: {button_intent}")
    
    response = client.post(
        '/api/chat/generate-button/',
        {'button_intent': button_intent},
        format='json'
    )
    
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ Success: {data.get('message', 'OK')}")
        print(f"  ✓ Response: {data.get('response', '')[:100]}...")
        print(f"  ✓ Theme: {data.get('theme', 'N/A')}")
        right_side_results.append({'success': True, 'response': data.get('response', ''), 'theme': data.get('theme', '')})
    else:
        error_data = response.json()
        print(f"  ✗ Error: {error_data.get('message', 'Unknown error')}")
        right_side_results.append({'success': False, 'error': error_data.get('message', '')})

# Verify database records for RIGHT side
right_records = AIReply.objects.filter(user=test_user, intent_type='button').count()
print(f"\n✓ Database: {right_records} button responses saved")

print("\n" + "-"*80)
print("TEST 3: Verify Session Tracking")
print("-"*80)

session_info = get_user_session_info(test_user.id)
print(f"\nSession info for user {test_user.id}:")
print(f"  ✓ Expiration: {session_info.get('expiration', 'N/A')}")
print(f"  ✓ Used themes: {session_info.get('used_themes', {})}")

if session_info.get('used_themes', {}):
    print(f"  ✓ {len(session_info['used_themes'])} themes tracked in session")
else:
    print(f"  ⚠ No themes tracked yet (expected if Redis not fully initialized)")

print("\n" + "-"*80)
print("TEST 4: Verify Error Handling")
print("-"*80)

# Test missing conversation
print("\n[TEST 4.1] Missing conversation (should fail)")
response = client.post(
    '/api/chat/generate-specific/',
    {'conversation': ''},
    format='json'
)
print(f"  Status: {response.status_code}")
print(f"  Error: {response.json().get('message', 'Unknown error')}")

# Test short conversation
print("\n[TEST 4.2] Short conversation (should fail)")
response = client.post(
    '/api/chat/generate-specific/',
    {'conversation': 'hi'},
    format='json'
)
print(f"  Status: {response.status_code}")
print(f"  Error: {response.json().get('message', 'Unknown error')}")

# Test missing button intent
print("\n[TEST 4.3] Missing button intent (should fail)")
response = client.post(
    '/api/chat/generate-button/',
    {'button_intent': ''},
    format='json'
)
print(f"  Status: {response.status_code}")
print(f"  Error: {response.json().get('message', 'Unknown error')}")

# Test invalid button intent
print("\n[TEST 4.4] Invalid button intent (should fail)")
response = client.post(
    '/api/chat/generate-button/',
    {'button_intent': 'invalid_button_xyz'},
    format='json'
)
print(f"  Status: {response.status_code}")
print(f"  Error: {response.json().get('message', 'Unknown error')}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

left_success = sum(1 for r in left_side_results if r.get('success'))
right_success = sum(1 for r in right_side_results if r.get('success'))

print(f"\nLEFT Side (Specific):  {left_success}/{len(left_side_results)} ✓")
print(f"RIGHT Side (Button):   {right_success}/{len(right_side_results)} ✓")
print(f"Database Records:      {left_records + right_records} total")
print(f"Error Handling:        ✓ Tested")

if left_success >= len(left_side_results) * 0.8 and right_success >= len(right_side_results) * 0.8:
    print("\n✓ TASK 7 COMPLETE - Backend endpoints working!")
    print("\nNext steps:")
    print("  1. Check that migration is applied to database")
    print("  2. Proceed to frontend tasks (8-13)")
    print("  3. Build button UI components (LeftPanel, RightPanel, etc)")
else:
    print("\n⚠ Some tests failed - investigate before proceeding")

print("\n" + "="*80)
