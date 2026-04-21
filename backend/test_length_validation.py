"""
Test: Does validate_and_refine fix length violations?
"""
import os
import sys

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')

import django
django.setup()

from django.contrib.auth.models import User
from accounts.services.response_validator import ResponseValidator

# Get test user
try:
    test_user = User.objects.get(email='system_test@blog.com')
except User.DoesNotExist:
    test_user = User.objects.create_user(
        username='system_test',
        email='system_test@blog.com',
        password='testpass'
    )

validator = ResponseValidator(test_user)

# Test cases with known issues
test_responses = [
    "Hmmm, well in my free time, I usually relax with a nice book or get lo",  # Too long
    "Hey, seems like we might have something in common. I really enjoy bein",  # Too long
    "Hey, I like books too, especially mystery novels. What kind of books do you read?",  # Normal
]

print("Testing validate_and_refine():\n")

for idx, response in enumerate(test_responses, 1):
    print(f"\nTest {idx}:")
    print(f"Original: {response}")
    print(f"Length: {len(response)} chars")
    
    is_valid, final_response, log = validator.validate_and_refine(response, max_attempts=3)
    
    print(f"Valid: {is_valid}")
    print(f"Final: {final_response[:80]}")
    print(f"Final Length: {len(final_response)} chars")
    
    if is_valid:
        print(f"✅ PASSED")
        # Verify it's in range
        if 140 <= len(final_response) <= 180:
            print(f"✅ Length in valid range (140-180)")
        else:
            print(f"❌ Length {len(final_response)} still out of range!")
    else:
        print(f"❌ FAILED")
