"""
Structure Rotation Service
Ensures response variety by rotating through 7 different structural patterns
"""

from accounts.models import ResponseLog

STRUCTURES = ['A', 'B', 'C', 'D', 'E', 'F', 'G']

STRUCTURE_DESCRIPTIONS = {
    'A': 'Short statement. Longer trailing thought... question',
    'B': 'Mid length observation, pause, then question',
    'C': 'Vulnerable admission then pivot to question',
    'D': 'Playful deflection then unexpected question',
    'E': 'Callback to earlier in conversation then question',
    'F': 'Single punchy line. silence. then question',
    'G': 'Slightly unfinished thought... then question'
}

def get_forbidden_structures(conversation_id: int) -> list:
    """
    Returns structures that cannot be used next:
    - Last used structure
    - Any structure used more than once in last 7 replies
    """
    last_7 = ResponseLog.objects.filter(
        conversation_id=conversation_id
    ).order_by('-reply_number')[:7].values_list(
        'structure_used', flat=True
    )

    last_7 = list(last_7)
    forbidden = []

    # Block last used
    if last_7:
        forbidden.append(last_7[0])

    # Block any used more than once in last 7
    from collections import Counter
    counts = Counter(last_7)
    for structure, count in counts.items():
        if count >= 2:
            forbidden.append(structure)

    return list(set(forbidden))

def get_available_structures(conversation_id: int) -> list:
    forbidden = get_forbidden_structures(conversation_id)
    return [s for s in STRUCTURES if s not in forbidden]

def get_structure_instruction(structure: str) -> str:
    return STRUCTURE_DESCRIPTIONS[structure]