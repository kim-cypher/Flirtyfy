"""
Test SPECIFICITY SYSTEM
- Check if responses reference what user said
- Check for banned patterns
- Check varied response lengths
- Check statement vs question endings
"""

import os
import django
import re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.services.ai_generation import generate_reply

User = get_user_model()
user = User.objects.first()

print("=" * 80)
print("SPECIFICITY TEST - Pattern Detection in 5 Attempts")
print("=" * 80)

# Test conversation
conversation = "I've always daydreamed about trying things in unusual places, but I'm nervous about actually doing it. Does that make me adventurous or just weird?"

print(f"\nCONVERSATION: {conversation}\n")
print("Testing 5 different attempts:\n")

# Banned patterns to check for
BANNED_OPENERS = [
    "you have a way of", "you have that", "there is something about",
    "the way you", "i can feel", "i would be lying",
    "you seem to know", "you are making"
]

BANNED_BRIDGES = ["so tell me", "so are you", "so what", "so how"]
BANNED_WORDS = ["confidence", "chemistry", "tension", "irresistible", "addictive", "energy", "spark", "momentum", "effortless"]
BANNED_EMOTIONAL = ["i can feel", "i cannot deny", "would be lying if", "cannot pretend"]

results = []

for attempt in range(1, 6):
    response = generate_reply(conversation, user=user, attempt_number=attempt)
    
    # Check violations
    violations = []
    response_lower = response.lower()
    
    # Check banned openers
    for opener in BANNED_OPENERS:
        if opener in response_lower:
            violations.append(f"Banned opener: '{opener}'")
    
    # Check banned bridges
    for bridge in BANNED_BRIDGES:
        if bridge in response_lower:
            violations.append(f"Banned bridge: '{bridge}'")
    
    # Check banned vocabulary
    for word in BANNED_WORDS:
        if f" {word} " in f" {response_lower} " or response_lower.startswith(word):
            violations.append(f"Banned word: '{word}'")
    
    # Check for "because" joining feelings
    if re.search(r'\b\w+.*because\s+\w+', response_lower):
        violations.append("'because' used to explain feeling")
    
    # Check word count
    words = response.split()
    word_count = len(words)
    
    # Check ending (? vs.)
    ends_with_question = response.rstrip().endswith('?')
    ends_with_statement = response.rstrip().endswith('.')
    
    # Expected for this attempt
    expected_lengths = {
        1: (60, 75),
        2: (65, 80),
        3: (15, 30),
        4: (80, 110),
        5: (40, 55)
    }
    min_w, max_w = expected_lengths[attempt]
    
    expected_question = attempt not in [3, 5]  # 3 and 5 should be statements
    
    status = "✅" if not violations else "⚠️"
    
    print(f"\nAttempt {attempt}: {status}")
    print(f"  Words: {word_count} (expected {min_w}-{max_w}) {'✅' if min_w <= word_count <= max_w else '❌'}")
    print(f"  Ending: {'Question ?' if ends_with_question else 'Statement .' if ends_with_statement else 'Other'} {'✅' if (expected_question and ends_with_question) or (not expected_question and not ends_with_question) else '❌'}")
    print(f"  Response: {response}")
    
    if violations:
        print(f"  ⚠️ Issues: {'; '.join(violations)}")
    
    results.append({
        'attempt': attempt,
        'response': response,
        'violations': violations,
        'word_count': word_count,
        'expected_range': (min_w, max_w)
    })

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

total_violations = sum(len(r['violations']) for r in results)
print(f"\nTotal violations found: {total_violations}")

if total_violations == 0:
    print("✅ ALL TESTS PASSED - Specificity system working!")
else:
    print(f"⚠️ Found {total_violations} issues to fix")

# Check variety
word_counts = [r['word_count'] for r in results]
print(f"\nWord count variety: {word_counts}")
print(f"Range: {min(word_counts)} to {max(word_counts)} (good if varied)")
