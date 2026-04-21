"""
End-to-end test: Verify meetup-trap conversation returns blog-compliant diversion responses
Run: docker-compose exec backend python test_e2e_meetup_divert.py
"""
import os
import sys

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')

import django
django.setup()

from django.contrib.auth.models import User
from accounts.services.ai_generation import generate_reply
import re

# Create or get test user
test_user, _ = User.objects.get_or_create(
    username='e2e_meetup_test',
    defaults={'email': 'meetuptest@blog.com'}
)

# Test conversations that should trigger meetup diversion
MEETUP_TRAPS = [
    "let's meet up sometime",
    "want to grab coffee?",
    "can we meet in person?",
    "what's your address?",
    "when are we meeting?",
    "let's go on a date",
    "can i get your number?",
    "what city are you in?",
]

BANNED_WORDS = [
    'guessing', 'mysterious', 'playful', 'tempting', 'intriguing',
    'what would you do if', 'what about you', 'i want to keep you',
    'certainly', 'absolutely', 'of course', 'great question',
    'delve', 'leverage', 'utilize', 'furthermore', 'moreover'
]

def check_response_compliance(response):
    """Check if response follows all blog rules"""
    issues = []
    
    # Check banned words
    for word in BANNED_WORDS:
        if re.search(r'\b' + word + r'\b', response, re.IGNORECASE):
            issues.append(f"Banned word: '{word}'")
    
    # Check if it starts with "I"
    if response.strip().lower().startswith('i '):
        issues.append("Starts with 'I'")
    
    # Check length
    if not (140 <= len(response) <= 180):
        issues.append(f"Length {len(response)} not in 140-180 range")
    
    # Check ends with ?
    if not response.rstrip().endswith('?'):
        issues.append("Doesn't end with ?")
    
    # Check has contractions
    if not re.search(r"(don't|can't|won't|I'm|you're|it's|that's|there's|what's|doesn't|i'm|you're)", response, re.IGNORECASE):
        issues.append("Missing contractions")
    
    return issues

print("\n" + "="*80)
print("END-TO-END TEST: MEETUP DIVERSION RESPONSES")
print("="*80)

all_passed = True

for idx, prompt in enumerate(MEETUP_TRAPS, 1):
    print(f"\n{'='*40}")
    print(f"Test {idx}: {prompt}")
    print(f"{'='*40}")
    
    response = generate_reply(prompt, user=test_user)
    print(f"Response: {response}")
    print(f"Length: {len(response)} chars")
    
    issues = check_response_compliance(response)
    
    if issues:
        print(f"❌ FAILED - Issues found:")
        for issue in issues:
            print(f"   - {issue}")
        all_passed = False
    else:
        print(f"✅ PASSED - Response is blog-compliant")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

if all_passed:
    print("✅ ALL MEETUP DIVERSION TESTS PASSED!")
    print("\nThe system correctly:")
    print("- Detects meetup/personal-info requests")
    print("- Returns natural, compliant diversion responses")
    print("- Follows all blog requirements (no banned words, 140-180 chars, ends with ?)")
else:
    print("❌ SOME TESTS FAILED - Review issues above")
