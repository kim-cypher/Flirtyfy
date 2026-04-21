#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')

import django
django.setup()

from accounts.services.response_validator import ResponseValidator
from django.contrib.auth.models import User

print("\n" + "="*80)
print("BANNED PHRASES VERIFICATION")
print("="*80)

user = User.objects.first()
validator = ResponseValidator(user)

print("\n✅ ResponseValidator loaded successfully")
print(f"✅ Banned phrases count: {len(validator.banned_phrases)}")
print(f"✅ Has _check_banned_phrases method: {hasattr(validator, '_check_banned_phrases')}")

test_cases = [
    ("there's something about you", True, "Should ban"),
    ("what's actually happening", True, "Should ban"),
    ("i actually think", True, "Should ban"),
    ("you know what", True, "Should ban"),
    ("i love your energy", False, "Should allow"),
    ("something unique fascinates me", False, "Should allow"),
]

print("\n" + "-"*80)
print("Testing banned phrase detection:")
print("-"*80)

passed = 0
failed = 0

for text, should_ban, desc in test_cases:
    result = validator._check_banned_phrases(text)
    is_banned = not result['valid']
    
    if is_banned == should_ban:
        print(f"✅ PASS | {desc:20} | '{text}'")
        passed += 1
    else:
        print(f"❌ FAIL | {desc:20} | '{text}'")
        failed += 1

print("\n" + "="*80)
print(f"Results: {passed}/{passed+failed} tests passed")
print("="*80 + "\n")
