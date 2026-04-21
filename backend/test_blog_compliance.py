"""
Test compliance with Response Writing Blog Rules
Verifies all response templates follow blog requirements
Run inside backend container: docker-compose exec backend python test_blog_compliance.py
"""
import re
import os
import sys

# Add backend to path
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')

import django
django.setup()

from accounts.services.response_validator import ResponseValidator
from accounts.services.ai_generation import generate_reply
from django.contrib.auth.models import User

# Blog rules
BANNED_WORDS = [
    r'\bguessing\b', r'\bmysterious\b', r'\bplayful\b', r'\btempting\b', r'\bintriguing\b',
    r'\bwhat would you do if\b', r'\bwhat about you\b', r'\bI want to keep you\b',
    r'\blet[\'\s]s see where this goes\b', r'\bI like how\b',
    r'\bcertainly\b', r'\babsolutely\b', r'\bof course\b', r'\bgreat question\b',
    r'\bdelve\b', r'\bleverage\b', r'\butilize\b', r'\bfurthermore\b', r'\bmoreover\b'
]

def test_banned_words(text):
    """Test that no banned words appear"""
    violations = []
    for pattern in BANNED_WORDS:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(pattern)
    return violations

def test_contractions(text):
    """Test that contractions are used (don't, I'm, you're, etc)"""
    has_contractions = bool(re.search(r"(don't|can't|won't|I'm|you're|it's|that's|there's|what's|doesn't|i'm|you're)", text, re.IGNORECASE))
    has_uncontracted = bool(re.search(r"\b(do not|cannot|will not|I am|you are|it is|that is)\b", text, re.IGNORECASE))
    return has_contractions, has_uncontracted

def test_starts_with_i(text):
    """Test that response does NOT start with 'I' (case-insensitive)"""
    stripped = text.strip()
    return stripped.lower().startswith('i ')

def test_char_length(text):
    """Test 140-180 character range"""
    return 140 <= len(text) <= 180

def test_ends_with_question(text):
    """Test that response ends with ?"""
    return text.rstrip().endswith('?')

def test_no_lists(text):
    """Test no bullet points, headers, bold"""
    has_list = bool(re.search(r'[\-\*•]|^#+|\*\*', text, re.MULTILINE))
    return not has_list

def test_natural_tone(text):
    """Test for natural texting tone markers"""
    has_informal = bool(re.search(r"(anyway|like|honestly|you know|i mean|haha|lol|kinda|gonna|wanna|nah|yeah)", text, re.IGNORECASE))
    return has_informal

# Create or get test user
test_user, _ = User.objects.get_or_create(
    username='blog_compliance_test',
    defaults={'email': 'test@blog.com'}
)

print("\n" + "="*80)
print("BLOG COMPLIANCE TESTS - ALL RESPONSE TEMPLATES")
print("="*80)

validator = ResponseValidator(test_user)
total_violations = 0
categories_tested = []

# Test diversion templates
print("\n" + "="*80)
print("DIVERSION TEMPLATES (meetup/personal-info diversions)")
print("="*80)

responses = validator.diversion_templates
cat_violations = 0

for idx, response in enumerate(responses, 1):
    print(f"\n--- Diversion Response {idx} ---")
    print(f"Text: {response}")
    print(f"Length: {len(response)} chars")
    
    violations = test_banned_words(response)
    if violations:
        print(f"❌ BANNED WORDS FOUND: {violations}")
        cat_violations += 1
    else:
        print(f"✅ No banned words")
    
    has_contractions, has_uncontracted = test_contractions(response)
    if has_uncontracted:
        print(f"⚠️  Uses uncontracted form")
    if has_contractions:
        print(f"✅ Uses contractions")
    
    if test_starts_with_i(response):
        print(f"❌ VIOLATION: Starts with 'I'")
        cat_violations += 1
    else:
        print(f"✅ Doesn't start with 'I'")
    
    if not test_char_length(response):
        print(f"❌ VIOLATION: Length {len(response)} not in 140-180 range")
        cat_violations += 1
    else:
        print(f"✅ Character length OK (140-180)")
    
    if not test_ends_with_question(response):
        print(f"❌ VIOLATION: Doesn't end with ?")
        cat_violations += 1
    else:
        print(f"✅ Ends with ?")
    
    if not test_no_lists(response):
        print(f"❌ VIOLATION: Contains lists/headers/bold")
        cat_violations += 1
    else:
        print(f"✅ No lists/headers/bold")
    
    if not test_natural_tone(response):
        print(f"⚠️  WARNING: May sound too formal/robotic")
    else:
        print(f"✅ Natural tone markers present")

total_violations += cat_violations
categories_tested.append(("Diversion Templates", cat_violations, len(responses)))

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

for category, violations, count in categories_tested:
    status = "✅" if violations == 0 else "❌"
    print(f"{status} {category}: {count} responses, {violations} violations")

print(f"\nTotal violations: {total_violations}")

if total_violations == 0:
    print("\n✅ ALL RESPONSE TEMPLATES PASS BLOG COMPLIANCE!")
else:
    print(f"\n❌ {total_violations} VIOLATIONS FOUND - TEMPLATES NEED FIXES")


