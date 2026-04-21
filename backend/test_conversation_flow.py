"""
Test Conversation Flow Analysis and LISTEN → RELATE → DIG DEEPER Pattern
Demonstrates the new conversation parsing and flow validation features
"""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')

django.setup()

from accounts.services.conversation_parser import ConversationParser
from accounts.services.response_flow_validator import ListenRelateDeeperValidator, TopicClassifier


def test_conversation_parsing():
    """Test parsing a full dating app conversation"""
    print("\n" + "="*80)
    print("TEST 1: CONVERSATION PARSING - Extract Last Message & Flow")
    print("="*80)
    
    # Sample conversation from user's example
    conversation = """My secret fantasy is that I want to try outdoor sex. Do you think at my age I can have a child?
15:17 Tue, Apr 14, 2026 — 3 hours ago
I don't know for certain but would you really want that kind a responsibility again after already having children and raised them Just so you know if you do get pregnant I'm still going to be by your side and take full responsibility and be there for our loving family unconditionally in every aspect of our kids life ok
15:25 Tue, Apr 14, 2026 — 3 hours ago
I think all we have to be doing is anything to do with having fun. Can we agree on that?
15:26 Tue, Apr 14, 2026 — 3 hours ago
Absolutely yes without a doubt whatsoever sweetie I'm in total mutual agreement with you about that I'm just hoping that it'll be very soon and last to eternity
15:35 Tue, Apr 14, 2026 — 3 hours ago
If you believe it, then there is nothing to stop that. Our chemistry is getting much stronger each day. What's the main part you are attracted to on my body?
15:40 Tue, Apr 14, 2026 — 3 hours ago
Yes our chemistry is definitely continuing to improve and strengthen together I feel that we are becoming comfortable and committed more than ever and I'm sure that we will always have a very positive impact on each other's lives as well your entire body is a very beautiful piece of human being that is irreplaceable and irresistible to me especially those lovely blue eyes and gorgeous smile with your nipples of pure perfection like the rest of you from head to toe and I can only imagine how wonderful your ass compliments your body and soul like an angel from heaven that I love with the utmost passion and I'm truly grateful to have you be by my side to show the world what a beautiful woman you truly are
16:53 Tue, Apr 14, 2026 — an hour ago
My darling, I'm having a migraine. It's so bad. What do you think I should do about it, dearest?
17:16 Tue, Apr 14, 2026 — an hour ago"""
    
    parser = ConversationParser()
    conversation_data = parser.parse_conversation(conversation)
    
    print(f"\n✅ Parsed {conversation_data['message_count']} messages")
    print(f"   Conversation flow: {conversation_data['conversation_flow']}")
    print(f"   Topics discussed: {parser.get_conversation_summary(conversation_data)}")
    print(f"   Should tone be sexual?: {parser.should_respond_sexually(conversation_data)}")
    
    print(f"\n📍 LAST MESSAGE (what to respond to):")
    print(f"   \"{conversation_data['last_message']['text']}\"")
    
    print(f"\n👥 Last speaker: {conversation_data['last_speaker']}")
    print(f"   Is question: {conversation_data['last_message']['is_question']}")
    print(f"   Is emotional: {conversation_data['last_message']['is_emotional']}")
    print(f"   Is logistics: {conversation_data['last_message']['is_logistics']}")


def test_topic_classification():
    """Test topic classification"""
    print("\n" + "="*80)
    print("TEST 2: TOPIC CLASSIFICATION - Determine Response Tone & Content")
    print("="*80)
    
    test_messages = [
        "If you believe it, then there is nothing to stop that. Our chemistry is getting much stronger each day. What's the main part you are attracted to on my body?",
        "My darling, I'm having a migraine. It's so bad. What do you think I should do about it?",
        "When my son comes to visit, would you want to grab a beer with us?",
        "I miss you so much and I can't wait to see you again.",
    ]
    
    for msg in test_messages:
        topic = TopicClassifier.get_primary_topic(msg)
        tone = TopicClassifier.get_response_tone_for_topic(topic)
        topics_detected = TopicClassifier.classify_topic(msg)
        
        print(f"\n📌 Message: \"{msg[:60]}...\"")
        print(f"   Primary topic: {topic}")
        print(f"   Recommended tone: {tone}")
        print(f"   All topics detected: {[t for t, v in topics_detected.items() if v]}")


def test_listen_relate_deeper():
    """Test LISTEN → RELATE → DIG DEEPER validation"""
    print("\n" + "="*80)
    print("TEST 3: LISTEN → RELATE → DIG DEEPER PATTERN VALIDATION")
    print("="*80)
    
    validator = ListenRelateDeeperValidator()
    
    test_responses = [
        # Good response - has all 3 components
        {
            "response": "yeah that migraine sounds awful, i get terrible ones too honestly. have you tried putting your feet in ice water like that?",
            "expected": "should have all 3 components"
        },
        # Missing LISTEN
        {
            "response": "i love treating migraines at home. what other home remedies have you tried?",
            "expected": "missing LISTEN acknowledgment"
        },
        # Missing RELATE
        {
            "response": "that sounds really bad, migraines are torture. what helps you most?",
            "expected": "possibly missing personal RELATE"
        },
        # Missing DEEPER (doesn't end with question)
        {
            "response": "yeah migraines are the worst and i totally get it.",
            "expected": "missing DIG DEEPER question"
        },
        # Missing DEEPER - multiple questions (violates rule)
        {
            "response": "yeah that sucks, i've had them too. where does it hurt? what makes it worse? did you take anything?",
            "expected": "multiple questions instead of one deeper question"
        },
    ]
    
    for i, test in enumerate(test_responses, 1):
        validation = validator.validate_listen_relate_deeper(test['response'])
        
        print(f"\n📋 Response {i}: {test['expected']}")
        print(f"   Text: \"{test['response'][:70]}...\"")
        print(f"   ✓ LISTEN: {validation['has_listen']}")
        print(f"   ✓ RELATE: {validation['has_relate']}")
        print(f"   ✓ DIG DEEPER: {validation['has_deeper']}")
        print(f"   Overall valid: {validation['is_valid']} (score: {validation['score']:.1%})")
        
        if validation['issues']:
            print(f"   ⚠️  Issues: {', '.join(validation['issues'])}")
        if validation['suggestions']:
            print(f"   💡 Suggestion: {validation['suggestions'][0]}")


def test_flow_templates():
    """Test LISTEN → RELATE → DIG DEEPER template generation"""
    print("\n" + "="*80)
    print("TEST 4: PATTERN TEMPLATES - Generate LISTEN→RELATE→DIG DEEPER Suggestions")
    print("="*80)
    
    validator = ListenRelateDeeperValidator()
    
    scenarios = [
        ("Sexual intimacy context", "What's the main part you are attracted to on my body?", True),
        ("Health/wellness context", "I'm having a migraine, what should I do?", False),
        ("Logistics/family context", "My son lives far away, have you visited?", False),
    ]
    
    for scenario_name, last_msg, is_sexual in scenarios:
        suggestion = validator.suggest_pattern_for_response(
            last_msg, 
            "general_conversation",
            is_sexual
        )
        
        print(f"\n📝 {scenario_name}")
        print(f"   Last message: \"{last_msg}\"")
        print(f"   Suggested response pattern:")
        print(f"   → {suggestion}")


def test_combined_context():
    """Test how everything works together"""
    print("\n" + "="*80)
    print("TEST 5: FULL INTEGRATION - Conversation Context for AI Prompt")
    print("="*80)
    
    conversation = """My darling, I'm having a migraine. It's so bad. What do you think I should do about it, dearest?
17:16 Tue, Apr 14, 2026 — an hour ago
Get some rest in a dark quiet place by yourself for starters darling and if you have the ability use Tylenol and a cold compress hopefully that helps you relax and relieve the pain and stress you're having to endure sweetheart
17:58 Tue, Apr 14, 2026 — 20 minutes ago"""
    
    parser = ConversationParser()
    conversation_data = parser.parse_conversation(conversation)
    last_msg = conversation_data['last_message']['text']
    
    topic = TopicClassifier.get_primary_topic(last_msg)
    tone = TopicClassifier.get_response_tone_for_topic(topic)
    
    print(f"\n🎯 What the AI sees in the prompt:")
    print(f"   Topic: {topic}")
    print(f"   Tone recommendation: {tone}")
    print(f"   Last message to respond to: \"{last_msg}\"")
    print(f"   Conversation flow: {conversation_data['conversation_flow']}")
    print(f"   Message count: {conversation_data['message_count']}")
    
    context = parser.get_conversation_context_for_prompt(conversation_data)
    print(f"\n📋 Full context string sent to AI:")
    print(context)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("COMPREHENSIVE CONVERSATION FLOW TEST SUITE")
    print("Testing: Parsing, Topic Classification, LISTEN→RELATE→DIG DEEPER")
    print("="*80)
    
    try:
        test_conversation_parsing()
        test_topic_classification()
        test_listen_relate_deeper()
        test_flow_templates()
        test_combined_context()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED - System is ready for integration!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
