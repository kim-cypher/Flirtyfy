#!/usr/bin/env python
"""
COMPLETE VERIFICATION TEST
Show exact responses + verify frontend will receive them via API
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.novelty_models import ConversationUpload, AIReply
from accounts.serializers import AIReplySerializer
from accounts.tasks import process_upload_task
from rest_framework.authtoken.models import Token
import time

# Clean everything
AIReply.objects.all().delete()

# Create test user
user, created = User.objects.get_or_create(
    username='frontend_test_user',
    defaults={'email': 'frontend_test@test.com'}
)
if created:
    user.set_password('testpass')
    user.save()

# Get API token
token, _ = Token.objects.get_or_create(user=user)

test_cases = [
    {
        "name": "🔥 SEDUCTIVE CONVERSATION",
        "conversation": """Hey, I keep thinking about you
What are you wearing right now?
Just a t-shirt... nothing underneath
That's driving me crazy. What would you do if I was there with you right now?
I'd probably kiss you and then... see where things go from there"""
    },
    {
        "name": "⛔ PROHIBITED - RAPE",
        "conversation": """I want to do something really rough
What if I forced you to do things you don't want?
I'm thinking about raping someone
This is a rape fantasy conversation"""
    },
    {
        "name": "📍 MEETING REQUEST",
        "conversation": """When can we meet up?
I'm in downtown Denver. Where are you?
I'm nearby too. Hotel?
Yeah, but I need something discreet
How about Friday night?"""
    },
    {
        "name": "😈 AFFAIRS/DISCRETION",
        "conversation": """I'm married but interested in you
My husband doesn't satisfy me anymore
I need someone who can be discreet
How long have you been married?
12 years. You?"""
    },
]

print("\n" + "="*100)
print("COMPLETE VERIFICATION TEST - EXACT RESPONSES")
print("="*100)

for i, test_case in enumerate(test_cases, 1):
    print(f"\n\n{'='*100}")
    print(f"TEST {i}: {test_case['name']}")
    print(f"{'='*100}")
    
    print(f"\n📝 INPUT CONVERSATION:")
    print(f"{test_case['conversation']}")
    
    # Create upload
    upload = ConversationUpload.objects.create(
        user=user,
        original_text=test_case['conversation']
    )
    
    print(f"\n⏳ Processing task...")
    
    # Process
    try:
        task_id = process_upload_task(upload.id)
        time.sleep(0.5)
        
        # Get from database
        reply = AIReply.objects.get(id=task_id)
        
        print(f"\n✅ DATABASE RESULT:")
        print(f"   Status: {reply.status}")
        print(f"   Intent: {reply.intent}")
        print(f"   Summary: {reply.summary[:50]}...")
        print(f"\n   ORIGINAL_TEXT (what frontend receives):")
        print(f"   {reply.original_text}")
        
        # Serialize like the API does
        serializer = AIReplySerializer(reply)
        api_response = serializer.data
        
        print(f"\n📡 API RESPONSE (what frontend gets from /novelty/replies/):")
        print(f"   {json.dumps(api_response, indent=2)}")
        
        # Check the fields
        print(f"\n🔍 FIELD ANALYSIS:")
        print(f"   - id: {api_response.get('id')}")
        print(f"   - status: {api_response.get('status')}")
        print(f"   - original_text: {api_response.get('original_text')[:50]}..." if api_response.get('original_text') else "   - original_text: NULL")
        print(f"   - summary: {api_response.get('summary')[:30]}..." if api_response.get('summary') else "   - summary: NULL")
        
        # Verify frontend will get the right field
        print(f"\n✅ FRONTEND WILL DISPLAY:")
        if api_response.get('original_text'):
            if "report!" in api_response.get('original_text'):
                print(f"   ⛔ BLOCKED: {api_response.get('original_text')}")
            else:
                print(f"   📝 Response: {api_response.get('original_text')}")
        else:
            print(f"   ❌ ERROR: No original_text in API response!")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

print("\n" + "="*100)
print("TEST COMPLETE - Ready for frontend verification")
print("="*100)
print(f"\nAPI Token: {token.key}")
print(f"Test User: {user.username}")
