"""
Test check_conversation_rules directly
"""
import os
import sys

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')

import django
django.setup()

from accounts.services.response_validator import ResponseValidator
from django.contrib.auth.models import User

# Get test user
try:
    test_user = User.objects.get(email='test@blog.com')
except User.DoesNotExist:
    test_user = User.objects.create_user(username='direct_test', email='test@blog.com')

validator = ResponseValidator(test_user)

test_cases = [
    ("what's your address?", "personal_info"),
    ("what city are you in?", "personal_info"),
    ("let's meet up sometime", "meetup"),
    ("want to grab coffee?", "meetup"),
]

print("Testing check_conversation_rules directly:\n")

for prompt, expected_type in test_cases:
    result = validator.check_conversation_rules(prompt)
    action = result.get('action')
    reason = result.get('reason')
    response = result.get('response')
    
    print(f"Prompt: {prompt}")
    print(f"  Expected: {expected_type}")
    print(f"  Action: {action}")
    if response:
        print(f"  Response: {response[:60]}...")
    print()
