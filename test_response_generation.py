#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')
sys.path.insert(0, 'backend')

django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile
from accounts.novelty_models import ConversationUpload, AIReply
from rest_framework.authtoken.models import Token
from accounts.tasks import process_upload_task
import time

# Get or create test user
user, created = User.objects.get_or_create(
    username='testuser_response',
    defaults={'email': 'testuser_response@test.com'}
)
if created:
    user.set_password('testpass123')
    user.save()
    profile, _ = UserProfile.objects.get_or_create(user=user)

# Delete old replies
AIReply.objects.filter(user=user).delete()

# NEW conversation - totally different topic
test_conversation = """Sarah: Hey, I'm looking for someone who actually gets what I want in life
Tom: What do you want?
Sarah: Someone spontaneous. You know, the kind who would suggest driving to the beach at midnight
Tom: I like midnight adventures. I'm in.
Sarah: Just like that? No hesitation?
Tom: Life's too short to hesitate when something feels right"""

# Create upload
upload = ConversationUpload.objects.create(
    user=user,
    original_text=test_conversation,
    status='pending'
)

print(f'Created upload {upload.id}')
print(f'Processing task...')

# Process the task
task_id = process_upload_task(upload.id)

print(f'Task completed, reply ID: {task_id}')
time.sleep(2)

# Get the reply
reply = AIReply.objects.get(id=task_id)
print(f'\nStatus: {reply.status}')
print(f'Response:\n{reply.original_text}')
