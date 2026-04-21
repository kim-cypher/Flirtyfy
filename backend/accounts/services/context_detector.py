"""
Context Trigger Detection Service
Detects when users mention real-world scenarios that should trigger contextual flirt anchoring
"""

CONTEXT_TRIGGERS = {
    'restaurant': [
        'restaurant', 'dinner', 'eat', 'food', 'cuisine',
        'italian', 'sushi', 'date night', 'reservation',
        'menu', 'table', 'drinks', 'wine', 'coffee'
    ],
    'vacation': [
        'vacation', 'trip', 'travel', 'hotel', 'beach',
        'flight', 'weekend away', 'road trip', 'getaway',
        'resort', 'airbnb', 'destination'
    ],
    'car': [
        'car', 'drive', 'driving', 'ride', 'road',
        'pick you up', 'my car', 'night drive'
    ],
    'movie': [
        'netflix', 'movie', 'film', 'watch', 'series',
        'episode', 'cinema', 'come over'
    ],
    'cooking': [
        'cook', 'cooking', 'kitchen', 'recipe', 'made',
        'bake', 'jollof', 'meal', 'i can make'
    ],
    'meeting': [
        'meet', 'see you', 'my number', 'call me',
        'whatsapp', 'come over', 'pick you up',
        'my place', 'your place', 'this week'
    ]
}

def detect_context_triggers(text: str) -> list:
    text_lower = text.lower()
    detected = []
    for trigger, keywords in CONTEXT_TRIGGERS.items():
        if any(kw in text_lower for kw in keywords):
            detected.append(trigger)
    return detected