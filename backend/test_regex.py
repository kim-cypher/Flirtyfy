"""
Quick regex test to verify personal_info patterns match
"""
import re

personal_info_patterns = [
    r'\b(address|phone|number|call|whatsapp|snapchat|location|where do you live|where are you from|what city|what state|are you real|are you close|are you nearby|are you in town|can I visit|can I come)\b'
]

test_prompts = [
    "what's your address?",
    "what city are you in?",
    "let's meet up sometime",
]

for prompt in test_prompts:
    print(f"\nPrompt: {prompt}")
    for pat in personal_info_patterns:
        match = re.search(pat, prompt, re.IGNORECASE)
        print(f"  Pattern matches: {bool(match)}")
        if match:
            print(f"  Matched: {match.group()}")
