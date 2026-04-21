"""
Vocabulary Cooldown Service
Prevents word repetition by enforcing cooldown periods on pool words
"""

from accounts.models import VocabCooldown

COOLDOWN_REPLIES = 15

WORD_POOLS = {
    'attraction': [
        'drawn to', 'pulled toward', 'caught off guard by',
        "couldn't ignore", 'noticed',
        'keeps coming back to me', 'stuck on'
    ],
    'teasing': [
        'holding back', 'not saying everything',
        'keeping something', 'leaving space',
        'not rushing', 'letting it sit'
    ],
    'feeling': [
        'something about', 'this thing where',
        'that moment when', 'the part where', 'the way'
    ]
}

def get_available_words(user_id: str, current_reply: int) -> dict:
    """Returns which words from each pool are available"""
    all_words = [w for pool in WORD_POOLS.values()
                 for w in pool]

    on_cooldown = VocabCooldown.objects.filter(
        user_id=user_id,
        word__in=all_words,
        last_used_reply__gt=current_reply - COOLDOWN_REPLIES
    ).values_list('word', flat=True)

    on_cooldown = list(on_cooldown)
    result = {}
    for pool_name, words in WORD_POOLS.items():
        result[pool_name] = [
            w for w in words if w not in on_cooldown
        ]
    return result

def log_used_words(user_id: str, text: str, reply_number: int):
    """Log any pool words found in the response"""
    all_words = [w for pool in WORD_POOLS.values()
                 for w in pool]
    text_lower = text.lower()

    for word in all_words:
        if word in text_lower:
            VocabCooldown.objects.update_or_create(
                user_id=user_id,
                word=word,
                defaults={'last_used_reply': reply_number}
            )