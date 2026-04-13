#!/usr/bin/env python
"""
Create a test AI reply manually to test the UI
"""

import os
import sys
import django

# Add backend to path
sys.path.insert(0, 'c:\\Users\\kiman\\Projects\\Flirtyfy\\backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.novelty_models import ConversationUpload, AIReply
from datetime import datetime, timedelta

print("=== CREATING TEST REPLY ===\n")

# Get or create a test user
user, created = User.objects.get_or_create(
    email='testuser_for_reply@test.com',
    defaults={
        'username': 'testuser_for_reply',
    }
)
if created:
    print(f"Created new test user: {user.username}")
else:
    print(f"Using existing user: {user.username}")

# Create a test conversation upload
upload = ConversationUpload.objects.create(
    user=user,
    original_text="Hey, I've been thinking about you. Want to grab coffee sometime?",
    status='pending'
)
print(f"Created conversation upload: {upload.id}")

# Create a test AI reply
reply = AIReply.objects.create(
    user=user,
    upload=upload,
    original_text="That sounds great! I'd love to. How about Friday evening? ☕",
    normalized_text="that sounds great i'd love to how about friday evening",
    fingerprint="abc123",
    summary="Positive response to coffee invitation",
    intent="accept_invitation",
    status='complete',
    created_at=datetime.now(),
    expires_at=datetime.now() + timedelta(days=45),
)
print(f"Created AI reply: {reply.id}")
print(f"Reply text: {reply.original_text}")

print(f"\nNow test on frontend:")
print(f"1. Login with: testuser_for_reply@test.com (need to set password first)")
print(f"   Or use any user you've already created")
print(f"2. Go to Chat tab")
print(f"3. Paste: 'Hey, I've been thinking about you. Want to grab coffee sometime?'")
print(f"4. Upload")
print(f"5. You should now see the AI reply!")

# Actually, let's find a real user and set their password
print(f"\n=== GETTING EXISTING USER ===")
try:
    real_user = User.objects.filter(is_active=True).first()
    if real_user:
        print(f"Found user: {real_user.email} ({real_user.username})")
        
        # Create a conversation and reply for this user
        upload2 = ConversationUpload.objects.create(
            user=real_user,
            original_text="Hey, I've been thinking about you lately. Want to grab coffee?",
            status='completed'
        )
        reply2 = AIReply.objects.create(
            user=real_user,
            upload=upload2,
            original_text="I'd love to! Friday evening works perfectly for me 😊",
            normalized_text="i'd love to friday evening works perfectly for me",
            fingerprint="reply_" + str(real_user.id),
            summary="Positive acceptance with enthusiasm",
            intent="accept_and_suggest_time",
            status='complete',
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=45),
        )
        print(f"\nCreated test reply for user {real_user.email}:")
        print(f"- Upload ID: {upload2.id}")
        print(f"- Reply ID: {reply2.id}")
        print(f"- Reply text: {reply2.original_text}")
        print(f"\nNow login and try uploading the same conversation!")
except Exception as e:
    print(f"Error: {e}")
