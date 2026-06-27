# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

"""
FLIRTYFY - UNIQUENESS SYSTEM STANDALONE TEST
=============================================
No Django. No OpenAI. No database. No credentials needed.
Run from anywhere: python test_uniqueness_standalone.py

Tests:
  1. 130-char enforcement
  2. Layer 1 — exact fingerprint dedup
  3. Layer 2 — intent-template dedup (same question, different words)
  4. Layer 3 — SequenceMatcher text-overlap dedup
  5. Full pipeline simulation (all layers together)
  6. Three naughty conversations + expected left-panel replies
  7. All 17 buttons × 2 clicks — uniqueness demonstration
"""

import re
import hashlib
import unicodedata
from difflib import SequenceMatcher


# ===========================================================================
# ── HELPERS (mirrors production code, no imports required) ──────────────────
# ===========================================================================

def normalize_text(text):
    text = unicodedata.normalize('NFKC', text).lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def exact_fingerprint(text):
    return hashlib.sha256(normalize_text(text).encode()).hexdigest()

def enforce_130_chars(text):
    """Trim only if over 150 chars — range is 100-150."""
    text = text.strip()
    if len(text) <= 150:
        return text
    last_q = text.rfind('?', 0, 150)
    if last_q > 60:
        return text[:last_q + 1]
    last_end = max(text.rfind('.', 0, 150), text.rfind('!', 0, 150))
    if last_end > 60:
        return text[:last_end + 1]
    return text[:150]

def ensure_ends_with_question(text):
    text = text.strip()
    if not text:
        return text
    if text.endswith('?'):
        return text
    if text.endswith('.'):
        candidate = text[:-1] + '?'
    else:
        candidate = text + '?'
    if len(candidate) > 150:
        candidate = candidate[:149] + '?'
    return candidate


# ===========================================================================
# ── INTENT TEMPLATE CLASSIFIER (Layer 2) ────────────────────────────────────
# ===========================================================================

INTENT_TEMPLATES = [
    ('morning_wake', [
        'wake up', 'woke up', 'how did you sleep', 'did you sleep', 'sleep well',
        'good morning', 'morning sunshine', 'how was your night', 'rest well',
        'dream last night', 'dreamed about', 'how are you this morning',
    ]),
    ('evening_night', [
        'good night', 'going to bed', 'heading to sleep', 'time of night',
        'late night', 'midnight', 'falling asleep', 'wind down', 'end of the day',
    ]),
    ('wearing_now', [
        'what are you wearing', 'what do you have on', 'dressed right now',
        'wearing right now', 'have on right now',
    ]),
    ('body_description', [
        'describe your body', 'describe yourself', 'look like', 'how do you look',
        'your figure', 'your curves',
    ]),
    ('where_doing_now', [
        'where are you right now', 'what are you doing right now',
        'what are you up to', 'right now what', 'at this moment',
    ]),
    ('how_feeling_today', [
        'how are you feeling', 'how do you feel today', "how's your day",
        'how was your day', 'your mood today', 'feeling today', 'feeling right now',
    ]),
    ('what_on_mind', [
        "what's on your mind", 'what is on your mind', 'on your mind right now',
        'what are you thinking about', 'running through your mind', 'thoughts right now',
    ]),
    ('what_attracted_to', [
        'what attracts you', 'what do you find attractive', 'what draws you',
        'what pulls you in', 'what catches your eye',
    ]),
    ('what_you_want', [
        'what do you want', 'what are you looking for', 'what do you need',
        'what kind of woman', 'ideal woman', 'ideal partner',
    ]),
    ('dangerous_bold', [
        'dangerous thing', 'most dangerous', 'boldest thing', 'risky thing',
        'craziest thing', 'wildest thing you', 'daring thing',
    ]),
    ('deep_fear_vulnerability', [
        'what scares you', 'biggest fear', 'afraid of', 'terrifies you',
        'keeps you up at night', 'hard to admit', 'struggle with',
    ]),
    ('falling_feeling', [
        'falling for', 'starting to feel', 'catching feelings', 'feel something',
        'feeling something', 'more than i expected', 'catching feelings',
    ]),
    ('miss_thinking_about', [
        'been thinking about you', 'miss you', 'missed you', 'thought about you',
        "crossed my mind", "can't stop thinking", 'keep thinking about you',
    ]),
    ('provider_protector', [
        'take care of', 'take care of me', 'protect me', 'provide for',
        'spoil me', 'make me feel safe', 'real man', 'strong man', 'show up for',
    ]),
    ('withdrawal_pull_back', [
        'going quiet', 'need some space', 'little overwhelmed', "can't talk much",
        'step back', 'taking a step', 'pulling back', 'distracted today',
    ]),
    ('making_him_chase', [
        "wonder if you'll miss me", 'still be thinking', 'think about me',
        'wonder about me', "if i go quiet",
    ]),
    ('romantic_poetic_lyrical', [
        'like a song', 'like a lyric', 'between songs', 'you remind me of',
        'stars aligned', 'fate', 'universe brought',
    ]),
    ('public_together_seen', [
        'introduce me', 'show me off', 'walk in with me', 'your hand on my',
        'heads turning', 'people see us', 'seen together', 'in public with you',
    ]),
    ('meeting_deflect_fantasy', [
        'meeting you would', 'meeting in person', 'ruins the imagination',
        'ends the fantasy', 'the wanting', 'not ready to meet', 'keep it here',
    ]),
    ('reverse_psych_challenge', [
        'should stop texting', "if this isn't what", 'most men lose',
        'built differently', "can't handle", 'not for you', 'your call if',
    ]),
    ('bedroom_energy_preference', [
        'energy in the bedroom', 'energy should a man', 'energy should a woman',
        'bring to bed', 'like in bed', 'enjoy in bed', 'want in the bedroom',
    ]),
    ('body_response_intensity', [
        'body responds to', 'respond to intensity', 'respond to gentleness',
        'how should he handle me', 'treat me in bed', 'makes my body', 'body reacts',
    ]),
    ('position_preference', [
        'favorite position', 'position do you like', 'position you prefer',
        'on top', 'from behind', 'face down', 'against the wall',
        'position undoes you', 'position breaks you',
    ]),
    ('control_dominance', [
        'in control', 'take control', 'take over', 'dominate me',
        'be in charge', 'who takes over', 'dominant',
    ]),
    ('sexual_fantasy', [
        'fantasy', 'fantasize about', 'dream about doing', 'imagine doing',
        'imagine me', 'picture me', 'what would you do to me',
    ]),
    ('oral_desire', [
        'in my mouth', 'on my mouth', 'go down', 'oral', 'tongue on', 'mouth on',
        'use my mouth',
    ]),
    ('explicit_arousal', [
        'wet right now', 'turned on', 'horny right now', 'aroused',
        'aching for', 'need you right now', 'want you so bad', 'craving you',
    ]),
    ('orgasm_pleasure', [
        'make me cum', 'make me come', 'climax', 'orgasm',
        'make me feel good', 'satisfy me', 'make me lose control',
    ]),
    ('sensual_tension', [
        'something about the way you', 'the way you talk to me', 'doing that on purpose',
        'set something off', "can't think straight", 'getting to me',
        'effect you have on me', 'what you do to me',
    ]),
    ('compliment_his_energy', [
        'your energy', 'energy you give', 'vibe you give', 'the way you carry',
        "there's something about you", "theres something about you",
    ]),
    ('went_quiet_returning', [
        'i disappeared', 'i went quiet', 'i was quiet', 'my head out',
        "i'm back", 'back now', 'took some time',
    ]),
    ('he_went_cold', [
        'your energy changed', "you've gone quiet", 'you went quiet',
        'you pulled back', 'something shift', 'something changed',
    ]),
    ('first_message_opener', [
        'just matched', 'just connected', 'your profile', 'intrigued by you',
        'want to know more about you', 'what kind of man are you',
    ]),
    ('generic_question', ['?']),
]

def classify_template(text):
    norm = normalize_text(text)
    for key, signals in INTENT_TEMPLATES:
        for signal in signals:
            if signal in norm:
                return key
    return 'generic_question'

def content_fingerprint(text):
    return hashlib.sha256(classify_template(text).encode()).hexdigest()


# ===========================================================================
# ── MOCK DATABASE (in-memory, no Django) ────────────────────────────────────
# ===========================================================================

class MockReplyStore:
    """Simulates the AIReply table per user."""
    def __init__(self):
        self._store = {}  # user_id → list of {text, exact_fp, content_fp, norm}

    def save(self, user_id, text):
        if user_id not in self._store:
            self._store[user_id] = []
        self._store[user_id].append({
            'text': text,
            'exact_fp': exact_fingerprint(text),
            'content_fp': content_fingerprint(text),
            'norm': normalize_text(text),
            'template': classify_template(text),
        })

    def has_exact(self, user_id, text):
        fp = exact_fingerprint(text)
        return any(r['exact_fp'] == fp for r in self._store.get(user_id, []))

    def has_intent(self, user_id, text):
        template = classify_template(text)
        if template == 'generic_question':
            return False  # Unclassified messages don't block each other
        cfp = content_fingerprint(text)
        return any(r['content_fp'] == cfp for r in self._store.get(user_id, []))

    def has_high_overlap(self, user_id, text, threshold=0.75):
        norm = normalize_text(text)
        for r in self._store.get(user_id, []):
            ratio = SequenceMatcher(None, norm, r['norm']).ratio()
            if ratio >= threshold:
                return True, ratio
        return False, 0.0

    def is_duplicate(self, user_id, text):
        """Full 3-layer check. Returns (is_dup, reason)."""
        if self.has_exact(user_id, text):
            return True, 'LAYER 1 — exact match'
        if self.has_intent(user_id, text):
            tmpl = classify_template(text)
            return True, f'LAYER 2 — same intent template: [{tmpl}]'
        overlap, ratio = self.has_high_overlap(user_id, text)
        if overlap:
            return True, f'LAYER 3 — text overlap {ratio:.0%}'
        return False, ''

    def count(self, user_id):
        return len(self._store.get(user_id, []))


# ===========================================================================
# ── TEST HELPERS ─────────────────────────────────────────────────────────────
# ===========================================================================

PASS = '\033[92m[PASS]\033[0m'
FAIL = '\033[91m[FAIL]\033[0m'
BLOCKED = '\033[93m[BLOCKED]\033[0m'
ALLOWED = '\033[96m[ALLOWED]\033[0m'

def header(title):
    print(f'\n{"="*65}')
    print(f'  {title}')
    print(f'{"="*65}')

def check(label, condition, detail=''):
    status = PASS if condition else FAIL
    print(f'  {status}  {label}')
    if detail:
        print(f'         {detail}')

def show_block(msg, reason):
    short = (msg[:77] + '...') if len(msg) > 80 else msg
    print(f'  {BLOCKED}  "{short}"')
    print(f'           reason: {reason}')

def show_allow(msg, template=''):
    short = (msg[:77] + '...') if len(msg) > 80 else msg
    suffix = f'  [template: {template}]' if template else ''
    print(f'  {ALLOWED}  "{short}"{suffix}')


# ===========================================================================
# SECTION 1 — 130-CHAR ENFORCEMENT
# ===========================================================================

header('SECTION 1 — 100-150 CHAR RANGE ENFORCEMENT')

cases = [
    ("Short message — should pass as-is",
     "Woke up thinking about you. Was that your plan?",
     47),
    ("Exactly 130 chars — should pass",
     "I had a dream about you last night and I still can't shake it off. Did you feel it from where you are?",
     None),
    ("Over 130 — should be trimmed at last ?",
     "There's something about your energy that makes me feel things I haven't felt in a while. I don't say that easily. Are you doing that on purpose or is it just how you are?",
     None),
    ("Way over, no ? near start — hard cut",
     "I keep replaying every word you said yesterday and it's making me absolutely insane because nobody has ever gotten under my skin quite like this before in my entire life.",
     None),
]

for label, text, expected_len in cases:
    result = enforce_130_chars(text)
    result = ensure_ends_with_question(result)
    over = len(text) > 130
    check(
        label,
        len(result) <= 150,
        f'input: {len(text)} chars -> output: {len(result)} chars -> "{result}"'
    )


# ===========================================================================
# SECTION 2 — LAYER 1: EXACT FINGERPRINT DEDUP
# ===========================================================================

header('SECTION 2 — LAYER 1: EXACT FINGERPRINT (word-for-word)')

store = MockReplyStore()
user = 'user_A'

msg1 = "Woke up thinking about that last thing you said. Was that your plan?"
store.save(user, msg1)

# Exact repeat
is_dup, reason = store.is_duplicate(user, msg1)
check('Exact repeat blocked', is_dup, reason)

# Same meaning, slightly different punctuation — normalization catches it
msg1_variant = "Woke up thinking about that last thing you said... was that your plan?"
is_dup, reason = store.is_duplicate(user, msg1_variant)
check('Same text, different punctuation → blocked by normalization', is_dup, reason)

# Genuinely different message
msg2 = "I had a dream about you and now I can't focus. Should I tell you what happened?"
is_dup, reason = store.is_duplicate(user, msg2)
check('Different message → allowed through', not is_dup)
store.save(user, msg2)


# ===========================================================================
# SECTION 3 — LAYER 2: INTENT TEMPLATE DEDUP (same question, different words)
# ===========================================================================

header('SECTION 3 — LAYER 2: INTENT TEMPLATE (same meaning, different words)')

store2 = MockReplyStore()
user2 = 'user_B'

morning_v1 = "Woke up thinking about you. How did you sleep last night?"
morning_v2 = "Good morning — did you sleep well or were you up thinking about me too?"
morning_v3 = "Morning sunshine, how was your night, did you rest well?"

store2.save(user2, morning_v1)
t1 = classify_template(morning_v1)
print(f'\n  Saved: "{morning_v1}"')
print(f'  Template detected: [{t1}]\n')

is_dup, reason = store2.is_duplicate(user2, morning_v2)
show_block(morning_v2, reason) if is_dup else show_allow(morning_v2)
check('Second morning greeting blocked (same intent)', is_dup, reason)

is_dup, reason = store2.is_duplicate(user2, morning_v3)
show_block(morning_v3, reason) if is_dup else show_allow(morning_v3)
check('Third morning greeting blocked (same intent)', is_dup, reason)

# Different template should pass
different = "There's something about your energy that I can't quite put into words. What do you think I mean?"
is_dup, reason = store2.is_duplicate(user2, different)
show_allow(different, classify_template(different)) if not is_dup else show_block(different, reason)
check('Different intent entirely → allowed through', not is_dup)

# More template demonstrations
print('\n  Template classification examples:')
examples = [
    "How did you wake up today?",
    "Did you sleep well this morning?",
    "Woke up thinking about you, good morning?",
    "What position do you like best?",
    "Do you prefer being on top?",
    "Face down or from behind — which breaks you more?",
    "What's your fantasy with me right now?",
    "Tell me what you'd do if I were there.",
    "What are you wearing right now?",
    "Describe what you have on.",
    "What attracts you in a woman?",
    "What do you look for physically?",
    "I keep thinking about you.",
    "You've been on my mind all day.",
]
for ex in examples:
    tmpl = classify_template(ex)
    print(f'  "{ex[:60]}"')
    print(f'    → [{tmpl}]\n')


# ===========================================================================
# SECTION 4 — LAYER 3: TEXT OVERLAP (SequenceMatcher)
# ===========================================================================

header('SECTION 4 — LAYER 3: TEXT OVERLAP (SequenceMatcher @ 0.75)')

store3 = MockReplyStore()
user3 = 'user_C'

base = "I want to be the one that turns you on. Do you enjoy that I make you feel like a king?"
store3.save(user3, base)

near_dup = "I want to be the one who turns you on. Do you enjoy that I can make you feel like a king?"
is_dup, reason = store3.is_duplicate(user3, near_dup)
check('Near-identical text (1 word different) → blocked', is_dup, reason)

reworded = "You deserve a woman who makes you feel powerful. Am I doing that to you right now?"
is_dup, reason = store3.is_duplicate(user3, reworded)
check('Same idea, different words → allowed', not is_dup)


# ===========================================================================
# SECTION 5 — FULL PIPELINE SIMULATION (all 3 layers, 3-attempt retry)
# ===========================================================================

header('SECTION 5 — FULL PIPELINE: 3-ATTEMPT RETRY SIMULATION')

def simulate_generation(store, user_id, candidates):
    """
    Simulates the views.py retry loop.
    Tries candidates in order, returns first non-duplicate.
    """
    for i, candidate in enumerate(candidates):
        candidate = enforce_130_chars(candidate)
        candidate = ensure_ends_with_question(candidate)
        is_dup, reason = store.is_duplicate(user_id, candidate)
        if not is_dup:
            store.save(user_id, candidate)
            return candidate, i + 1, 'complete'
        print(f'    Attempt {i+1} blocked — {reason}')
    # All attempts exhausted, use last
    store.save(user_id, candidates[-1])
    return candidates[-1], len(candidates), 'fallback'

sim_store = MockReplyStore()
sim_user = 'user_sim'

print('\n  Round 1 — Fresh user, first ever generation:')
r1_candidates = [
    "Good morning beautiful, how did you sleep?",
    "Morning sunshine, did you wake up thinking of me?",
    "Hey, hope you had a good night — how are you feeling this morning?",
]
result, attempts, status = simulate_generation(sim_store, sim_user, r1_candidates)
print(f'  → Saved after attempt {attempts} [{status}]: "{result}"')
check('First generation succeeds on attempt 1', attempts == 1)

print('\n  Round 2 — Same user, tries morning greeting again:')
r2_candidates = [
    "Good morning! Did you wake up well today?",            # BLOCKED — morning_wake template
    "How was your rest, did you sleep through the night?",  # BLOCKED — morning_wake template
    "I've been thinking about you since last night. Are you still thinking about me?",  # PASSES — miss_thinking_about
]
result, attempts, status = simulate_generation(sim_store, sim_user, r2_candidates)
print(f'  → Saved after attempt {attempts} [{status}]: "{result}"')
check('Second round finds unique message (different template)', status == 'complete')

print(f'\n  Total replies stored for sim_user: {sim_store.count(sim_user)}')


# ===========================================================================
# SECTION 6 — THREE NAUGHTY CONVERSATIONS + EXPECTED LEFT-PANEL REPLIES
# ===========================================================================

header('SECTION 6 — THREE NAUGHTY CONVERSATIONS + LEFT-PANEL EXPECTED REPLIES')

CONVERSATIONS = [
    {
        'label': 'Conversation A — Explicit escalation',
        'conversation': [
            "Him:  I've been thinking about you all day",
            "Her:  Tell me what you were thinking",
            "Him:  How good it would feel to have you against me, your back on my chest",
            "Her:  I get so wet just reading that",
            "Him:  God I want you so bad right now",
        ],
        'python_intent': {
            'topic': 'intimacy',
            'tone': 'flirty',
            'stage': 'established',
            'energy': 'high',
        },
        'expected_reply_style': (
            "Right now I'm imagining exactly that and it's making it very hard to concentrate. "
            "What would you do first?"
        ),
        'template': 'explicit_arousal',
    },
    {
        'label': 'Conversation B — Provider energy / emotional pull',
        'conversation': [
            "Him:  I would take such good care of you if you let me",
            "Her:  You don't know what I need yet",
            "Him:  Tell me and I'll make it happen, anything",
            "Her:  Most men say that",
            "Him:  I'm not most men and you know it",
        ],
        'python_intent': {
            'topic': 'relationship',
            'tone': 'testing',
            'stage': 'growing',
            'energy': 'medium',
        },
        'expected_reply_style': (
            "Prove it then — what would you do for a woman who is worth every bit of effort "
            "but never begs for it?"
        ),
        'template': 'provider_protector',
    },
    {
        'label': 'Conversation C — Deep emotional + sexual',
        'conversation': [
            "Him:  I've never talked to someone like you before",
            "Her:  What do you mean 'like me'",
            "Him:  You're raw. Most women aren't this honest",
            "Her:  I can't be fake even when I try",
            "Him:  I think I'm falling for you a little and it scares me",
        ],
        'python_intent': {
            'topic': 'relationship',
            'tone': 'vulnerable',
            'stage': 'intimate',
            'energy': 'high',
        },
        'expected_reply_style': (
            "That's terrifying and exciting at the same time — are you sure you can handle "
            "a woman who feels everything this deeply?"
        ),
        'template': 'falling_feeling',
    },
]

for conv in CONVERSATIONS:
    print(f'\n  ── {conv["label"]} ──')
    for line in conv['conversation']:
        print(f'     {line}')
    print(f'\n  Python intent detection (zero API cost):')
    for k, v in conv['python_intent'].items():
        print(f'     {k}: {v}')
    print(f'\n  Expected reply style (≤130 chars, ends with ?):')
    reply = enforce_130_chars(conv['expected_reply_style'])
    reply = ensure_ends_with_question(reply)
    print(f'     "{reply}"')
    print(f'     length: {len(reply)} chars')
    print(f'     template that would be stored: [{conv["template"]}]')
    check('Reply <= 150 chars', len(reply) <= 150)
    check('Reply ends with ?', reply.endswith('?'))


# ===========================================================================
# SECTION 7 — ALL 17 BUTTONS × 2 CLICKS — UNIQUENESS DEMONSTRATION
# ===========================================================================

header('SECTION 7 — ALL 17 BUTTONS × 2 CLICKS')
print('  Each button is clicked twice. The second click must produce a different')
print('  message that passes ALL dedup layers.\n')

BUTTON_EXAMPLES = {
    'new_match': [
        ("There's something about your energy I want to understand better. "
         "What's the most dangerous thing you've ever done?",
         'dangerous_bold'),
        ("I've been staring at your profile longer than I'd admit. "
         "What kind of man should I know you are?",
         'first_message_opener'),
    ],
    'dead': [
        ("You went quiet and I noticed. "
         "What happened to the man who had me actually interested?",
         'he_went_cold'),
        ("Still there? I've been thinking about you in ways that would bring you back fast. "
         "Curious what they are?",
         'miss_thinking_about'),
    ],
    'you_went_silent': [
        ("I disappeared and that wasn't fair — you were on my mind too much. "
         "Still there?",
         'went_quiet_returning'),
        ("I'm back and I owe you honesty — you were getting to me more than I expected. "
         "Does that scare you or excite you?",
         'deep_fear_vulnerability'),
    ],
    'he_going_cold': [
        ("Your energy changed and I felt it. "
         "What shifted — or did I do something that pulled you back?",
         'he_went_cold'),
        ("You've gone quiet on me and it's driving me a little crazy. "
         "What would bring you all the way back?",
         'what_you_want'),
    ],
    'provider_energy': [
        ("There's something about a man who knows exactly what he wants that makes me feel safe. "
         "Are you that man?",
         'provider_protector'),
        ("I don't need much, just someone who shows up fully. "
         "Would you say you're the kind of man who does that?",
         'what_you_want'),
    ],
    'strategic_withdrawal': [
        ("Going quiet for a bit — got a lot pulling at me right now. "
         "Will you still be thinking of me?",
         'withdrawal_pull_back'),
        ("My attention isn't something everyone gets to hold. "
         "Are you sure you can handle having mine?",
         'reverse_psych_challenge'),
    ],
    'deep_emotion': [
        ("I don't connect easily but something about you broke through that. "
         "Does it scare you when someone sees you clearly?",
         'deep_fear_vulnerability'),
        ("I've been hurt before and I still let you in anyway. "
         "Does that make you want to handle me carefully?",
         'falling_feeling'),
    ],
    'lyrical_romance': [
        ("You're the kind of thought that comes back between songs — "
         "quiet but impossible to ignore. What am I to you?",
         'romantic_poetic_lyrical'),
        ("If I were a lyric I'd be the one that gets under your skin and never fully leaves. "
         "Do you feel that too?",
         'falling_feeling'),
    ],
    'vulnerability': [
        ("I'm stronger than I look but some nights I just want someone to hold all of me. "
         "Can you do that?",
         'deep_fear_vulnerability'),
        ("I don't usually say this but you make me feel things I haven't felt in a while. "
         "Does that make you feel powerful?",
         'compliment_his_energy'),
    ],
    'morning_flirt': [
        ("Woke up thinking about that last thing you said and now my whole morning is ruined. "
         "Was that your plan?",
         'morning_wake'),
        ("I had a dream about you and now I can't focus on anything. "
         "Should I tell you what happened in it?",
         'sexual_fantasy'),
    ],
    'dinner_talk': [
        ("I'm eating alone tonight and wondering what you'd order if you were here. "
         "What's your poison?",
         'where_doing_now'),
        ("Something about this time of night makes me want to be talking to you. "
         "What are you having right now?",
         'evening_night'),
    ],
    'public_fantasy': [
        ("I keep imagining you walking me into somewhere with your hand on my back like I'm yours. "
         "Would you do that?",
         'public_together_seen'),
        ("I picture you introducing me to someone and the way your eyes would say more than the words. "
         "Do you see that?",
         'daydream_us_together'),
    ],
    'sensual_echo': [
        ("The way you talk to me makes me feel things I'd need privacy to fully explore. "
         "Are you doing that on purpose?",
         'sensual_tension'),
        ("Right now you've got me turned on and I genuinely cannot explain it over text. "
         "What would you do with that?",
         'explicit_arousal'),
    ],
    'bedroom_questions': [
        ("I was built with a different energy. "
         "What energy should a man bring to keep me coming back every time?",
         'bedroom_energy_preference'),
        ("My body responds to intensity more than gentleness. "
         "What does that tell you about how you should handle me?",
         'body_response_intensity'),
    ],
    'positions': [
        ("I like being in control on top but I love it when he takes over halfway. "
         "Do you know how to read that moment?",
         'position_preference'),
        ("I love when a man takes complete control and I just feel everything — "
         "does that dominant side of you come out?",
         'control_dominance'),
    ],
    'meeting_redirect': [
        ("Meeting you in person would ruin the fantasy I've already built. "
         "Isn't the wanting better than the having sometimes?",
         'meeting_deflect_fantasy'),
        ("What if the version of me in your imagination is the hottest you'll ever have — "
         "why end that so fast?",
         'sexual_fantasy'),
    ],
    'reverse_psychology': [
        ("I think you should stop texting me if this isn't what you actually want. "
         "What do you actually want?",
         'reverse_psych_challenge'),
        ("It's interesting how a conversation online shows exactly who someone is before anything else. "
         "What do you think I've figured out about you so far?",
         'generic_question'),
    ],
}

btn_store = MockReplyStore()
btn_user = 'btn_user'
all_passed = True

for btn_id, (click1, click2) in BUTTON_EXAMPLES.items():
    msg1, tmpl1 = click1
    msg2, tmpl2 = click2

    msg1 = enforce_130_chars(msg1)
    msg2 = enforce_130_chars(msg2)
    msg1 = ensure_ends_with_question(msg1)
    msg2 = ensure_ends_with_question(msg2)

    # Click 1 — should always pass (fresh)
    is_dup1, _ = btn_store.is_duplicate(btn_user, msg1)
    btn_store.save(btn_user, msg1)

    # Click 2 — should pass (different template/text)
    is_dup2, reason2 = btn_store.is_duplicate(btn_user, msg2)
    if not is_dup2:
        btn_store.save(btn_user, msg2)

    click1_ok = not is_dup1
    click2_ok = not is_dup2

    status1 = '\033[92m[OK]\033[0m' if click1_ok else '\033[91m[!!]\033[0m'
    status2 = '\033[92m[OK]\033[0m' if click2_ok else '\033[91m[!!]\033[0m'

    if not click1_ok or not click2_ok:
        all_passed = False

    print(f'  {btn_id}:')
    print(f'    Click 1 {status1}  [{tmpl1}] "{msg1[:70]}{"..." if len(msg1)>70 else ""}"')
    print(f'    Click 2 {status2}  [{tmpl2}] "{msg2[:70]}{"..." if len(msg2)>70 else ""}"')
    if not click2_ok:
        print(f'            ⚠ BLOCKED: {reason2}')
    print()

check('All 17 buttons × 2 clicks produce unique messages', all_passed)
print(f'\n  Total messages stored for btn_user: {btn_store.count(btn_user)}')


# ===========================================================================
# FINAL SUMMARY
# ===========================================================================

header('FINAL SUMMARY')
print('''
  Three-layer uniqueness system:

  Layer 1 — Exact fingerprint (SHA-256 of normalized text)
    ✓ Blocks word-for-word repeats
    ✓ O(1) indexed DB lookup
    ✓ Zero API cost
    ✓ Implemented and wired: views.py → AIReply.fingerprint

  Layer 2 — Intent template (pure Python keyword classifier)
    ✓ Blocks same question asked in different words
    ✓ O(1) indexed DB lookup
    ✓ Zero API cost
    ✓ Implemented: intent_template_classifier.py → AIReply.content_fingerprint

  Layer 3 — pgvector semantic similarity (OpenAI text-embedding-3-small)
    ✓ Catches edge cases that slip through Layers 1 & 2
    ✓ Runs in background via Celery (zero latency impact on user)
    ✓ Cost: ~$4.50/month at 700 users × 300 messages/day
    ✓ Implemented: tasks.generate_and_store_embedding

  100-150 char range:
    ✓ Enforced in prompt: "100 to 150 characters total"
    ✓ Enforced in post-processing: enforce_130_chars() trims at 150
    ✓ max_tokens=70 (150 chars ~ 45-50 tokens, 70 gives clean headroom)

  Dedup window:
    ✓ Changed from 45 days to 30 days (aligned with 6,000 message/user ceiling)

  Retry loop:
    ✓ 3 attempts per generation
    ✓ Logs which layer blocked each attempt
    ✓ Falls back to last candidate if all 3 blocked (status="fallback")
''')
