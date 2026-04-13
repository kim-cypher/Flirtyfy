#!/usr/bin/env python
"""
Verify that API returns responses in correct order (newest first)
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

user, created = User.objects.get_or_create(
    username='api_order_test',
    defaults={'email': 'api_order_test@test.com'}
)

AIReply.objects.filter(user=user).delete()

# First conversation
conv1 = "Hi there\nHey! How are you?"
# Second conversation (DIFFERENT)
conv2 = "Hi there 😉\nHey! How's it going?\nPretty good. Your pics are hot"

print("="*100)
print("API ORDERING TEST")
print("="*100)

responses = []

print(f"\n--- UPLOAD #1 ---")
upload1 = ConversationUpload.objects.create(user=user, original_text=conv1)
print(f"Upload ID: {upload1.id}")
task_id1 = process_upload_task(upload1.id)
time.sleep(0.5)
reply1 = AIReply.objects.get(id=task_id1)
print(f"Reply 1 ID: {reply1.id}")
print(f"Reply 1 Response: {reply1.original_text[:50]}...")
responses.append(reply1)

print(f"\n--- UPLOAD #2 (different conversation) ---")
upload2 = ConversationUpload.objects.create(user=user, original_text=conv2)
print(f"Upload ID: {upload2.id}")
task_id2 = process_upload_task(upload2.id)
time.sleep(0.5)
reply2 = AIReply.objects.get(id=task_id2)
print(f"Reply 2 ID: {reply2.id}")
print(f"Reply 2 Response: {reply2.original_text[:50]}...]")
responses.append(reply2)

print(f"\n\n" + "="*100)
print("API RESPONSE ORDER (what frontend polls)")
print("="*100)

# Simulate what the API returns
api_replies = AIReply.objects.filter(user=user).order_by('-created_at')
print(f"\nTotal replies: {api_replies.count()}")
print(f"\nOrder returned by API:\n")

for i, reply in enumerate(api_replies):
    print(f"{i+1}. ID={reply.id}, created_at={reply.created_at}")
    print(f"   Response: {reply.original_text[:60]}...")

print(f"\n\n" + "="*100)
print("VERIFICATION")
print("="*100)

first_in_api = api_replies.first()
print(f"\nFirst reply returned by API:")
print(f"  ID: {first_in_api.id}")
print(f"  Expected: {reply2.id} (the latest/second one)")

if first_in_api.id == reply2.id:
    print(f"\n✅ PASS: API returns LATEST reply first")
    print(f"   Frontend will show: {first_in_api.original_text[:60]}...")
else:
    print(f"\n❌ FAIL: API returns OLD reply first")
    print(f"   Frontend will show old response instead of new one")
