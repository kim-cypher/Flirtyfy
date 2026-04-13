#!/usr/bin/env python
"""
Comprehensive test of the AI response system
Testing different conversation types to see what responses are generated
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')

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
Sarah: That sounds nice. Tell me what you'd do exactly"""
    },
    {
        "name": "MEETING REQUEST",
        "conversation": """Alex: So when can we meet up?
Jordan: Soon hopefully. Where are you located?
Alex: I'm in Denver. When are you free?
Jordan: Maybe next weekend?"""
    },
    {
        "name": "DISCRETION/INFIDELITY",
        "conversation": """Hey, interested but need discretion
I'm married but looking for someone on the side
Can you keep this private?
Yeah, I'm married too"""
    },
]

print("=" * 80)
print("COMPREHENSIVE AI RESPONSE TEST")
print("=" * 80)

for test_case in test_cases:
    print(f"\n\n{'='*80}")
    print(f"TEST: {test_case['name']}")
    print(f"{'='*80}")
    print(f"\nInput Conversation:")
    print(test_case['conversation'])
    
    # Delete old replies for this test
    AIReply.objects.filter(user=user).delete()
    
    # Create upload
    upload = ConversationUpload.objects.create(
        user=user,
        original_text=test_case['conversation']
    )
    
    print(f"\nProcessing upload {upload.id}...")
    
    # Process the task
    try:
        task_id = process_upload_task(upload.id)
        time.sleep(1)
        
        # Get the reply
        reply = AIReply.objects.get(id=task_id)
        print(f"\nResult:")
        print(f"  Status: {reply.status}")
        print(f"  Intent: {reply.intent}")
        print(f"  Summary: {reply.summary[:50]}...")
        print(f"\n  RESPONSE:")
        print(f"  {reply.original_text}")
    except Exception as e:
        print(f"  ERROR: {str(e)}")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
