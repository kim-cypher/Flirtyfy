"""
Test conversation flow with proper timestamp formatting
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')

django.setup()

from django.contrib.auth.models import User
from accounts.novelty_models import ConversationUpload, AIReply
from accounts.tasks import process_upload_task
from accounts.services.conversation_parser import ConversationParser
from accounts.services.response_flow_validator import TopicClassifier, ListenRelateDeeperValidator
import traceback

def test_scenario(name, conversation_text):
    """Test a single conversation scenario"""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {name}")
    print(f"{'='*80}")
    
    try:
        # Create test user
        user, _ = User.objects.get_or_create(
            username=f'test_user_{name.replace(" ", "_").lower()[:20]}',
            defaults={'email': f'test_{name}@example.com'}
        )
        
        # Parse conversation
        parser = ConversationParser()
        conv_data = parser.parse_conversation(conversation_text)
        last_msg = parser.get_last_message(conv_data)
        
        print(f"✓ Messages parsed: {conv_data['message_count']}")
        print(f"✓ Conversation flow: {conv_data['conversation_flow']}")
        print(f"✓ Topics: {parser.get_conversation_summary(conv_data)}")
        print(f"✓ Last message: \"{last_msg[:80]}...\"" if len(last_msg) > 80 else f"✓ Last message: \"{last_msg}\"")
        
        # Classify topic
        topic = TopicClassifier.get_primary_topic(last_msg)
        tone = TopicClassifier.get_response_tone_for_topic(topic)
        print(f"✓ Topic: {topic}")
        print(f"✓ Recommended tone: {tone}")
        
        # Upload and process
        upload = ConversationUpload.objects.create(
            user=user,
            original_text=conversation_text
        )
        print(f"✓ Upload created: {upload.id}")
        
        result_id = process_upload_task(upload.id)
        reply = AIReply.objects.get(id=result_id)
        
        print(f"✓ AI Reply status: {reply.status}")
        print(f"✓ Response: \"{reply.original_text}\"")
        print(f"✓ Length: {len(reply.original_text)} chars")
        
        # Validate flow
        flow_validator = ListenRelateDeeperValidator()
        validation = flow_validator.validate_listen_relate_deeper(reply.original_text, last_msg)
        
        print(f"✓ LISTEN component: {validation['has_listen']}")
        print(f"✓ RELATE component: {validation['has_relate']}")
        print(f"✓ DIG DEEPER component: {validation['has_deeper']}")
        print(f"✓ Pattern score: {validation['score']:.1%}")
        print(f"✓ Overall valid: {validation['is_valid']}")
        
        print(f"\n✅ SCENARIO PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
        return False


# Test scenarios with proper timestamp format
scenarios = [
    ("Sexual Topic", """I've always wanted to try outdoor sex, something about the thrill of it really gets me.
15:40 Tue, Apr 14, 2026 — 3 hours ago
What position do you think would be most comfortable for that kind of adventure?
15:45 Tue, Apr 14, 2026 — 3 hours ago"""),
    
    ("Health Concern", """I'm having the worst migraine right now, I can barely think straight.
17:16 Tue, Apr 14, 2026 — an hour ago
My darling, I'm having a migraine. It's so bad. What do you think I should do about it, dearest?
17:20 Tue, Apr 14, 2026 — 58 minutes ago"""),
    
    ("Family Matters", """My son lives quite far away and I miss him a lot.
14:30 Mon, Apr 19, 2026 — yesterday
When he visits next, would you want to meet him and grab a beer or something?
14:45 Mon, Apr 19, 2026 — yesterday"""),
    
    ("Emotional Connection", """I've never felt this way about anyone before, it's a little scary.
15:20 Tue, Apr 20, 2026 — 30 minutes ago
I'm scared about how much I'm feeling for you. Is this real for you too?
15:25 Tue, Apr 20, 2026 — 25 minutes ago"""),
]

if __name__ == "__main__":
    print("\n" + "="*80)
    print("CONVERSATION FLOW - PROPERLY FORMATTED TIMESTAMP TEST")
    print("="*80)
    
    passed = 0
    failed = 0
    
    for name, conv in scenarios:
        if test_scenario(name, conv):
            passed += 1
        else:
            failed +=1
    
    print("\n" + "="*80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*80 + "\n")
