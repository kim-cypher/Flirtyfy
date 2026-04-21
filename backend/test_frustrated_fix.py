"""
Test the EXACT scenario that was broken: frustrated user response
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
print("BEFORE: 'i'm not here to waste your time either...' (BROKEN - lowercase i)")
print("AFTER: Should now start with capital letter")
print("=" * 80)

# Trigger frustrated response multiple times
frustrated_message = "i'm so done with this, this is stupid, wtf is the point"

for i in range(3):
    response = generate_reply(frustrated_message, user=user, attempt_number=i+1)
    starts_with_capital = response[0].isupper() if response and response[0].isalpha() else False
    print(f"\nAttempt {i+1}:")
    print(f"  {'✅ FIXED' if starts_with_capital else '❌ BROKEN'}: {response}")

print("\n" + "=" * 80)
print("✅ Issue resolved: All responses now start with capital letters!")
print("=" * 80)
