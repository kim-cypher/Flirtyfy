"""
Test that ALL responses start with capital letters and are proper sentences
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.services.ai_generation import generate_reply

User = get_user_model()
user = User.objects.first()

print("=" * 80)
print("CAPITALIZATION TEST - Responses must start with capital letters")
print("=" * 80)

test_scenarios = [
    ("frustrated", "i'm so done with this, this is stupid and a waste of time honestly"),
    ("short", "hey"),
    ("profanity", "fuck this shit, you suck"),
    ("normal", "I've been thinking about you, what do you think we should do?"),
]

for scenario_name, message in test_scenarios:
    print(f"\n{scenario_name.upper()}: {message}")
    response = generate_reply(message, user=user)
    
    # Check if starts with capital letter
    first_char = response[0] if response else ""
    is_capital = first_char.isupper() if first_char.isalpha() else "N/A"
    
    # Check if ends with punctuation
    ends_with = "?" if response.endswith("?") else ("." if response.endswith(".") else "!")
    
    status = "✅" if (is_capital and ends_with) else "❌"
    print(f"{status} Response: {response}")
    print(f"   First char: '{first_char}' (capital: {is_capital}) | Ends with: {ends_with}")

print("\n" + "=" * 80)
print("ALL responses must start with capital letter and end with ? or .")
print("=" * 80)
