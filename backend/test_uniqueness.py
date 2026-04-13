#!/usr/bin/env python
"""
Test: Same conversation pasted TWICE should generate DIFFERENT responses
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.novelty_models import ConversationUpload, AIReply
from accounts.tasks import process_upload_task
from accounts.serializers import AIReplySerializer
import time

# Create test user
user, created = User.objects.get_or_create(
    username='uniqueness_test_user',
    defaults={'email': 'uniqueness_test@test.com'}
)

# Clear old replies
AIReply.objects.filter(user=user).delete()

# THE SAME CONVERSATION
conversation = """Hi! Just moved here
Where from?
California! Still adjusting to Colorado weather lol
It's definitely different! What brought you here?
New job opportunity. Plus wanted a fresh start
That's awesome. What do you do?
I work in marketing. You?
I'm in tech. We should grab coffee sometime
I'd like that! Any favorite spots downtown?"""

print("="*100)
print("UNIQUENESS TEST: Same Conversation Pasted TWICE")
print("="*100)

print(f"\n📝 CONVERSATION (pasting twice):")
print(conversation)

responses = []

for paste_num in [1, 2]:
    print(f"\n\n--- PASTE #{paste_num} ---")
    
    # Create upload
    upload = ConversationUpload.objects.create(
        user=user,
        original_text=conversation
    )
    
    print(f"Processing upload {upload.id}...")
    
    # Process
    task_id = process_upload_task(upload.id)
    time.sleep(0.5)
    
    # Get reply
    reply = AIReply.objects.get(id=task_id)
    
    print(f"\nDatabase ID: {reply.id}")
    print(f"Status: {reply.status}")
    print(f"Fingerprint: {reply.fingerprint[:20]}...")
    print(f"Response:\n{reply.original_text}\n")
    
    responses.append(reply.original_text)

print("\n" + "="*100)
print("COMPARISON")
print("="*100)

print(f"\nResponse #1:\n{responses[0]}")
print(f"\nResponse #2:\n{responses[1]}")

if responses[0] == responses[1]:
    print("\n❌ FAIL: Both responses are IDENTICAL!")
    print("This means uniqueness checking is NOT working.")
else:
    print("\n✅ PASS: Responses are DIFFERENT!")
    print("This means uniqueness checking IS working.")

# Calculate similarity
from difflib import SequenceMatcher
ratio = SequenceMatcher(None, responses[0], responses[1]).ratio()
print(f"\nText Similarity: {ratio*100:.1f}%")
if ratio > 0.9:
    print("⚠️ Still too similar (>90%)")
elif ratio > 0.8:
    print("⚠️ Somewhat similar (>80%)")
else:
    print("✅ Sufficiently different (<80%)")
