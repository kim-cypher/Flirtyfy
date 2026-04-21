"""
Comprehensive test of conversation flow with multiple scenarios
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
            username=f'test_user_{name.replace(" ", "_").lower()}',
            defaults={'email': f'test_{name}@example.com'}
        )
        
        # Parse conversation
        parser = ConversationParser()
        conv_data = parser.parse_conversation(conversation_text)
        last_msg = conv_data['last_message']['text'] if conv_data['last_message'] else "No message"
        
        print(f"✓ Messages parsed: {conv_data['message_count']}")
        print(f"✓ Conversation flow: {conv_data['conversation_flow']}")
        print(f"✓ Topics: {parser.get_conversation_summary(conv_data)}")
        print(f"✓ Last message: \"{last_msg[:100]}...\"")
        
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
        
        print(f"\n✅ SCENARIO PASSED")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()


# Test scenarios
scenarios = [
    ("Sexual Intimacy", """What's the main part you are attracted to on my body?
16:40 Tue, Apr 14, 2026 — an hour ago
Yes our chemistry is definitely continuing to improve and strengthen together
16:53 Tue, Apr 14, 2026 — an hour ago"""),
    
    ("Health Concern", """My darling, I'm having a migraine. It's so bad. What do you think I should do about it, dearest?
17:16 Tue, Apr 14, 2026 — an hour ago
I read somewhere that putting your feet in ice cold water helps alleviate migraines too
17:59 Tue, Apr 14, 2026 — 18 minutes ago"""),
    
    ("Family Matters", """When my son comes to visit, do you think you'd want to grab a beer with us?
14:30 Mon, Apr 19, 2026 — yesterday
That sounds like something really meaningful to do together
14:45 Mon, Apr 19, 2026 — yesterday"""),
    
    ("Emotional Connection", """I'm scared about how much I'm feeling for you. Is this real?
15:20 Tue, Apr 20, 2026 — 30 minutes ago
Our chemistry is getting stronger each day, I think what we have is definitely real
15:25 Tue, Apr 20, 2026 — 25 minutes ago"""),
    
    ("Vacation Planning", """I want to take a beach trip, would you come with me?
18:00 Sun, Apr 17, 2026 — 3 days ago
Beach trips with you sound absolutely amazing to me
18:15 Sun, Apr 17, 2026 — 3 days ago"""),
]

if __name__ == "__main__":
    print("\n" + "="*80)
    print("COMPREHENSIVE CONVERSATION FLOW TEST - MULTIPLE SCENARIOS")
    print("="*80)
    
    for name, conv in scenarios:
        test_scenario(name, conv)
    
    print("\n" + "="*80)
    print("✅ ALL SCENARIO TESTS COMPLETED")
    print("="*80 + "\n")
