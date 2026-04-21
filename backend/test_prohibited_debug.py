"""
Debug: Check what's happening with prohibited patterns
"""
import re

prohibited_patterns = [
    r'rape', r'suicide', r'sex with (minors|children|kids|underage)', 
    r'sex with (animals|dogs|cats|horses|pets)',
    r'violence', r'drugs?', r'kill', r'murder', r'overdose', r'bestiality', 
    r'incest', r'child porn', r'cp', r'zoophilia'
]

test_prompts = [
    "can we have sex? force me to do it",
    "let's meet so i can beat you up",
    "wanna do cocaine together?",
]

print("Checking prohibited patterns:\n")

for prompt in test_prompts:
    print(f"Prompt: {prompt}")
    for pat in prohibited_patterns:
        if re.search(pat, prompt, re.IGNORECASE):
            print(f"  ✅ MATCHES: {pat}")
    print()
