"""
Debug regex patterns more carefully
"""
import re

# Test each pattern individually
test_cases = [
    ("rape", "can we have sex? force me to do it"),
    ("violence", "let's meet so i can beat you up"),
    ("drugs?", "wanna do cocaine together?"),
    ("kill", "let's meet so i can beat you up"),
    ("beat", "let's meet so i can beat you up"),
]

print("Testing individual patterns:\n")

for pattern, text in test_cases:
    match = re.search(pattern, text, re.IGNORECASE)
    result = "✅ MATCH" if match else "❌ NO MATCH"
    print(f"Pattern: {pattern:20} Text: {text:45} → {result}")
    if match:
        print(f"  Matched: {match.group()}")

print("\n" + "="*80)
print("\nTesting 'violence' pattern (word boundary issue?):\n")

patterns_to_test = [
    (r'violence', "let's meet so i can beat you up"),
    (r'\bviolence\b', "let's meet so i can beat you up"),
    (r'beat', "let's meet so i can beat you up"),
    (r'hit', "let's meet so i can beat you up"),
]

for pattern, text in patterns_to_test:
    match = re.search(pattern, text, re.IGNORECASE)
    result = "✅ MATCH" if match else "❌ NO MATCH"
    print(f"Pattern: {pattern:25} → {result}")
