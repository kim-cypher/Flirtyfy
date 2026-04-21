"""
Quick test to diagnose conversation upload issues
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')

django.setup()

from django.contrib.auth.models import User
from accounts.novelty_models import ConversationUpload
from accounts.tasks import process_upload_task
import traceback

try:
    # Create or get test user
    user, created = User.objects.get_or_create(
        username='testuser_conv',
        defaults={'email': 'test@example.com'}
    )
    print(f"✅ User: {user} (created={created})")
    
    # Create a test conversation
    conversation_text = """My secret fantasy is outdoor sex. Do you think at my age I can have a child?
15:17 Tue, Apr 14, 2026 — 3 hours ago
I don't know for certain but would you really want that kind a responsibility
15:25 Tue, Apr 14, 2026 — 3 hours ago
I think all we have to be doing is anything to do with having fun. Can we agree on that?
15:26 Tue, Apr 14, 2026 — 3 hours ago
You're so sweet and amazing, and I believe our affection towards each other would keep getting stronger and better. Would you consider us a perfect match for each other?
16:53 Tue, Apr 14, 2026 — an hour ago
My darling, I'm having a migraine. It's so bad. What do you think I should do about it, dearest?
17:16 Tue, Apr 14, 2026 — an hour ago"""
    
    # Try to create upload
    upload = ConversationUpload.objects.create(
        user=user,
        original_text=conversation_text
    )
    print(f"✅ ConversationUpload created: {upload.id}")
    
    # Try to process it
    print("\n⏳ Processing upload (this may take a moment)...")
    result = process_upload_task(upload.id)
    
    print(f"✅ Process completed with result: {result}")
    
    # Check if reply was created
    from accounts.novelty_models import AIReply
    replies = AIReply.objects.filter(upload=upload)
    print(f"✅ AIReply objects created: {replies.count()}")
    
    for reply in replies:
        print(f"   - Reply: {reply.original_text[:100]}...")
        print(f"     Status: {reply.status}")
        if reply.error:
            print(f"     Error: {reply.error}")
    
    print("\n✅ TEST PASSED - Conversation upload works!")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\n📋 Full traceback:")
    traceback.print_exc()
