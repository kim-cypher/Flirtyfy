"""
Debug conversation parser
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')

django.setup()

from accounts.services.conversation_parser import ConversationParser

test_conversation = """I've always wanted to try outdoor sex, something about the thrill of it really gets me.
15:40 Tue, Apr 14, 2026 — 3 hours ago
What position do you think would be most comfortable for that kind of adventure?
15:45 Tue, Apr 14, 2026 — 3 hours ago"""

parser = ConversationParser()
conv_data = parser.parse_conversation(test_conversation)

print(f"Raw text:\n{conv_data['raw_text']}\n")
print(f"Messages count: {conv_data['message_count']}")
print("\nMessages:")
for i, msg in enumerate(conv_data['messages'], 1):
    print(f"\n  Message {i}:")
    print(f"    Timestamp: {msg['timestamp']}")
    print(f"    Time ago: {msg['time_ago']}")
    print(f"    Text: \"{msg['text'][:100]}...\"" if len(msg['text']) > 100 else f"    Text: \"{msg['text']}\"")
    print(f"    Speaker: {msg['speaker']}")
    print(f"    Is question: {msg['is_question']}")

print(f"\nLast message: \"{conv_data['last_message']['text']}\"")
