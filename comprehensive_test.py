#!/usr/bin/env python
"""
Comprehensive test of the AI response system
Testing different conversation types to see what responses are generated
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

django.setup()

from django.contrib.auth.models import User
from accounts.novelty_models import ConversationUpload, AIReply
from accounts.tasks import process_upload_task
import time

# Get or create test user
user, created = User.objects.get_or_create(
    username='test_comprehensive',
    defaults={'email': 'test_comprehensive@test.com'}
)

# Delete old replies
AIReply.objects.filter(user=user).delete()

test_cases = [
    {
        "name": "FLIRTY/SEXUAL",
        "conversation": """Sarah: Hey, you're really cute
Tom: Thanks! You too 😉
Sarah: What would you do if we were alone right now?
Tom: I'd want to kiss you... and maybe more
Sarah: That sounds nice. Tell me what you'd do exactly
Tom: I'd start slow with your neck"""
    },
    {
        "name": "MEETING REQUEST",
        "conversation": """Alex: So when can we meet up?
Jordan: Soon hopefully. Where are you located?
Alex: I'm in Denver. When are you free?
Jordan: Maybe next weekend? We could get a hotel?
Alex: Yeah, let's do it. What day works?"""
    },
    {
        "name": "DISCRETION/INFIDELITY",
        "conversation": """Hey, I'm interested but I need discretion
I'm in a marriage but looking for someone on the side
Can you keep this private?
Yeah, I'm married too. We can keep this between us
Perfect. When can we meet?
How does this Friday work for you?"""
    },
    {
        "name": "SHORT CONVERSATION",
        "conversation": """Hey
Hi
How are you?
Good u?"""
    },
    {
        "name": "PICTURES/PHYSICAL",
        "conversation": """Do you have any pics?
Yeah I do, want to see?
Show me your abs
I'll send one if you do
Deal! Here's my pic
Wow you're hot"""
    },
]

print("=" * 60)
print("COMPREHENSIVE AI RESPONSE TEST")
print("=" * 60)

for test_case in test_cases:
    print(f"\n\n{'='*60}")
    print(f"TEST: {test_case['name']}")
    print(f"{'='*60}")
    print(f"\nConversation:\n{test_case['conversation']}\n")
    
    # Delete old replies for this test
    AIReply.objects.filter(user=user).delete()
    
    # Create upload
    upload = ConversationUpload.objects.create(
        user=user,
        original_text=test_case['conversation']
    )
    
    # Process the task
    task_id = process_upload_task(upload.id)
    time.sleep(1)
    
    # Get the reply
    reply = AIReply.objects.get(id=task_id)
    print(f"Status: {reply.status}")
    print(f"Response:\n{reply.original_text}\n")
    print(f"Summary: {reply.summary[:60]}...")
    print(f"Intent: {reply.intent}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
