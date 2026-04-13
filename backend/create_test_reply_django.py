import os
import sys
import django

os.environ['DJANGO_SETTINGS_MODULE'] = 'flirty_backend.settings'
sys.path.insert(0, '/app')

django.setup()

from django.contrib.auth.models import User
from accounts.novelty_models import ConversationUpload, AIReply
from datetime import datetime, timedelta

# Get the first active user
user = User.objects.filter(is_active=True).first()
if user:
    print(f"Using user: {user.email} ({user.username})")
    
    # Create test conversation
    upload = ConversationUpload.objects.create(
        user=user,
        original_text="Hey, I've been thinking about you. Want to grab coffee?",
        status='completed'
    )
    
    # Create test reply
    reply = AIReply.objects.create(
        user=user,
        upload=upload,
        original_text="I'd absolutely love to! Coffee sounds perfect. How about Friday evening?",
        normalized_text="i'd absolutely love to coffee sounds perfect how about friday evening",
        fingerprint="test_123",
        summary="Enthusiastic agreement with time suggestion",
        intent="accept_invitation",
        status='complete',
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(days=45),
    )
    
    print(f"SUCCESS! Created reply:")
    print(f"  User: {user.id}")
    print(f"  Upload ID: {upload.id}")
    print(f"  Reply ID: {reply.id}")
    print(f"  Status: {reply.status}")
    print(f"  Text: {reply.original_text}")
else:
    print("No user found")
