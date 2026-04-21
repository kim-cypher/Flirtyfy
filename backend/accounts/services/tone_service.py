"""
Tone Rotation Service
Ensures emotional variety by rotating through 7 different tones
"""

from accounts.models import ResponseLog
from collections import Counter

TONES = [
    'playful', 'vulnerable', 'confident',
    'distracted', 'intense', 'soft', 'challenging'
]

def get_forbidden_tones(conversation_id: int) -> list:
    last_7 = ResponseLog.objects.filter(
        conversation_id=conversation_id
    ).order_by('-reply_number')[:7].values_list(
        'tone_used', flat=True
    )
    last_7 = list(last_7)
    forbidden = []

    # Never repeat same tone consecutively
    if last_7:
        forbidden.append(last_7[0])

    # Never use same tone more than twice in 7 replies
    counts = Counter(last_7)
    for tone, count in counts.items():
        if count >= 2:
            forbidden.append(tone)

    return list(set(forbidden))

def get_available_tones(conversation_id: int) -> list:
    forbidden = get_forbidden_tones(conversation_id)
    return [t for t in TONES if t not in forbidden]