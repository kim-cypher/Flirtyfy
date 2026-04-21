"""
Test if diversion templates pass validate_and_refine
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
    test_user = User.objects.create_user(username='validation_test', email='test@blog.com', password='testpass')

validator = ResponseValidator(test_user)

print("Testing if diversion templates pass validate_and_refine:\n")

for idx, template in enumerate(validator.diversion_templates, 1):
    print(f"Template {idx}:")
    print(f"  Text: {template}")
    print(f"  Length: {len(template)} chars")
    
    is_valid, final_response, validation_log = validator.validate_and_refine(template, max_attempts=1)
    
    print(f"  Valid: {is_valid}")
    if is_valid:
        print(f"  ✅ PASSED")
    else:
        print(f"  ❌ FAILED")
        print(f"  Response: {final_response[:100]}...")
        # Print last few log entries
        if validation_log:
            print(f"  Last log entries:")
            for line in validation_log[-5:]:
                print(f"    {line}")
    print()
