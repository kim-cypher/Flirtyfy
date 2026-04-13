#!/usr/bin/env python
"""
Test: Same conversation pasted THREE times - should get 3 DIFFERENT responses
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.novelty_models import ConversationUpload, AIReply
from accounts.tasks import process_upload_task
import time

user, created = User.objects.get_or_create(
    username='triple_uniqueness_test',
    defaults={'email': 'triple_uniqueness_test@test.com'}
)

AIReply.objects.filter(user=user).delete()

conversation = """Hi! Just moved here
Where from?
California! Still adjusting to Colorado weather lol
It's definitely different! What brought you here?
New job opportunity. Plus wanted a fresh start"""

print("="*100)
print("UNIQUENESS TEST: Same Conversation Pasted THREE times")
print("="*100)

responses = []

for paste_num in [1, 2, 3]:
    print(f"\n--- PASTE #{paste_num} ---")
    
    upload = ConversationUpload.objects.create(user=user, original_text=conversation)
    print(f"Processing upload {upload.id}...")
    
    task_id = process_upload_task(upload.id)
    time.sleep(0.5)
    
    reply = AIReply.objects.get(id=task_id)
    print(f"Response:\n{reply.original_text}\n")
    
    responses.append(reply.original_text)

print("\n" + "="*100)
print("RESULTS")
print("="*100)

for i, resp in enumerate(responses, 1):
    print(f"\nResponse #{i}:\n{resp}")

# Check all different
from difflib import SequenceMatcher

print("\n" + "-"*100)
print("Similarity Matrix:")
for i in range(len(responses)):
    for j in range(i+1, len(responses)):
        ratio = SequenceMatcher(None, responses[i], responses[j]).ratio()
        print(f"Response {i+1} vs Response {j+1}: {ratio*100:.1f}% similar")

all_different = len(set(responses)) == 3
if all_different:
    print("\n✅ SUCCESS: All 3 responses are UNIQUE!")
else:
    print("\n❌ FAILURE: Some responses are duplicates!")
