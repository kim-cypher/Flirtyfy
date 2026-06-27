"""
Intent Template Classifier — Layer 2 Dedup (pure Python, zero API cost)

Maps a generated message to an intent template key.
Two messages with the same template key are considered semantic duplicates
even if they use completely different words.

Example:
  "How did you wake up today?"          → template: morning_wake
  "Did you sleep well this morning?"    → template: morning_wake
  → BLOCKED as duplicate

  "What position breaks you every time?" → template: position_preference
  "Do you like being on top?"            → template: position_preference
  → BLOCKED as duplicate

The hash of the template key is stored in AIReply.content_fingerprint.
Checked in views.py alongside the exact fingerprint before saving.
"""

import re
import hashlib
import unicodedata


# ---------------------------------------------------------------------------
# Template definitions
# Each entry: template_key → list of keyword signals
# First match wins (ordered from most specific to most general)
# ---------------------------------------------------------------------------

INTENT_TEMPLATES = [

    # ── MORNING / TIME ──────────────────────────────────────────────────────
    ('morning_wake', [
        'wake up', 'woke up', 'just woke', 'how did you sleep', 'did you sleep',
        'sleep well', 'slept well', 'good morning', 'morning sunshine', 'morning babe',
        'how was your night', 'night was', 'rest well', 'rested', 'dream last night',
        'dreamed about', 'how are you this morning', 'start your morning',
    ]),
    ('evening_night', [
        'good night', 'going to bed', 'heading to sleep', 'time of night',
        'tonight before', 'late night', 'midnight', 'falling asleep',
        'wind down', 'winding down', 'end of the day', 'night routine',
    ]),

    # ── APPEARANCE / BODY ────────────────────────────────────────────────────
    ('wearing_now', [
        'what are you wearing', 'what do you have on', 'dressed right now',
        'in right now', 'wearing right now', 'have on right now',
    ]),
    ('body_description', [
        'describe your body', 'describe yourself', 'look like', 'how do you look',
        'your figure', 'your physique', 'your curves', 'your frame',
    ]),

    # ── LOCATION / ACTIVITY ──────────────────────────────────────────────────
    ('where_doing_now', [
        'where are you right now', 'what are you doing right now', 'up to right now',
        'what are you up to', 'right now what', 'at this moment',
    ]),
    ('plans_today', [
        'plans for today', 'plans tonight', 'doing today', 'doing tonight',
        'what\'s on your agenda', 'schedule today', 'busy today', 'free today',
    ]),

    # ── FEELINGS / MOOD ──────────────────────────────────────────────────────
    ('how_feeling_today', [
        'how are you feeling', 'how do you feel today', 'how\'s your day',
        'how was your day', 'your mood today', 'feeling today', 'feeling right now',
    ]),
    ('what_on_mind', [
        "what's on your mind", 'what is on your mind', 'on your mind right now',
        'what are you thinking about', 'running through your mind', 'thoughts right now',
    ]),

    # ── ATTRACTION / INTEREST ────────────────────────────────────────────────
    ('what_attracted_to', [
        'what attracts you', 'what do you find attractive', 'what draws you',
        'what pulls you in', 'what makes someone attractive', 'what catches your eye',
    ]),
    ('what_you_want', [
        'what do you want', 'what are you looking for', 'what do you need',
        'what kind of woman', 'what kind of person', 'ideal woman', 'ideal partner',
    ]),

    # ── DANGER / ADVENTURE ───────────────────────────────────────────────────
    ('dangerous_bold', [
        'dangerous thing', 'most dangerous', 'boldest thing', 'risky thing',
        'craziest thing', 'wildest thing you', 'daring thing',
    ]),
    ('secret_hidden', [
        'secret about you', 'nobody knows', 'hidden side', 'don\'t show people',
        'keep to yourself', 'private about', 'never told anyone',
    ]),

    # ── EMOTIONAL DEPTH ──────────────────────────────────────────────────────
    ('deep_fear_vulnerability', [
        'what scares you', 'biggest fear', 'afraid of', 'terrifies you',
        'keeps you up at night', 'vulnerable about', 'hard to admit',
        'difficult for you', 'struggle with', 'hard for you to',
    ]),
    ('falling_feeling', [
        'falling for', 'starting to feel', 'catching feelings', 'feel something',
        'feeling something', 'more than i expected', 'more than i thought',
        'didn\'t expect to feel', 'didn\'t plan on',
    ]),
    ('miss_thinking_about', [
        'been thinking about you', 'miss you', 'missed you', 'thought about you',
        'crossed my mind', 'on my mind all', 'can\'t stop thinking',
        'keep thinking about you',
    ]),

    # ── PROVIDER / STRENGTH ──────────────────────────────────────────────────
    ('provider_protector', [
        'take care of', 'take care of me', 'protect me', 'provide for',
        'spoil me', 'make me feel safe', 'real man', 'strong man',
        'step up', 'show up for', 'be there for',
    ]),

    # ── CHASE / WITHDRAWAL ───────────────────────────────────────────────────
    ('withdrawal_pull_back', [
        'going quiet', 'need some space', 'little overwhelmed', 'busy right now',
        'can\'t talk much', 'lot on my mind', 'step back', 'taking a step',
        'pulling back', 'distracted today',
    ]),
    ('making_him_chase', [
        'wonder if you\'ll miss me', 'still be thinking', 'think about me',
        'wonder about me', 'notice i\'m gone', 'notice if i disappear',
        'if i go quiet',
    ]),

    # ── ROMANTIC / POETIC ────────────────────────────────────────────────────
    ('romantic_poetic_lyrical', [
        'like a song', 'like a lyric', 'like a poem', 'music and you',
        'between songs', 'underneath a song', 'you remind me of', 'poetic',
        'universe brought', 'stars aligned', 'fate',
    ]),
    ('daydream_us_together', [
        'imagine us together', 'picture us', 'daydream about us', 'vision of us',
        'imagine being with you', 'imagine you and me',
    ]),

    # ── PUBLIC FANTASY ───────────────────────────────────────────────────────
    ('public_together_seen', [
        'introduce me', 'show me off', 'walk in with me', 'your hand on my',
        'walking beside you', 'heads turning', 'people see us', 'seen together',
        'in public with you', 'imagine us in public',
    ]),

    # ── MEETING DEFLECT ───────────────────────────────────────────────────────
    ('meeting_deflect_fantasy', [
        'meeting you would', 'meeting in person', 'seeing you would',
        'the wanting', 'the fantasy', 'ruins the imagination', 'ends the fantasy',
        'why rush', 'not ready to meet', 'keep it here', 'online is',
    ]),

    # ── REVERSE PSYCHOLOGY ────────────────────────────────────────────────────
    ('reverse_psych_challenge', [
        'should stop texting', 'if this isn\'t what', 'most men lose',
        'built differently', 'can\'t handle', 'not for you', 'walk away',
        'if you\'re not serious', 'your call if', 'up to you if',
    ]),

    # ── SEXUAL — BEDROOM PREFERENCE ──────────────────────────────────────────
    ('bedroom_energy_preference', [
        'energy in the bedroom', 'energy should a man', 'energy should a woman',
        'energy do you bring', 'bring to bed', 'like in bed',
        'enjoy in bed', 'prefer in bed', 'want in the bedroom',
    ]),
    ('body_response_intensity', [
        'body responds to', 'respond to intensity', 'respond to gentleness',
        'how should he handle me', 'treat me in bed', 'makes my body', 'body reacts',
    ]),

    # ── SEXUAL — POSITION / SCENARIO ─────────────────────────────────────────
    ('position_preference', [
        'favorite position', 'position do you like', 'position you prefer',
        'on top', 'from behind', 'face down', 'against the wall',
        'position undoes you', 'position breaks you', 'like it',
    ]),
    ('control_dominance', [
        'in control', 'take control', 'take over', 'dominate me',
        'be in charge', 'let me take', 'who leads', 'who takes over',
        'submissive', 'dominant',
    ]),

    # ── SEXUAL — FANTASY / DESIRE ─────────────────────────────────────────────
    ('sexual_fantasy', [
        'fantasy', 'fantasize about', 'dream about doing', 'imagine doing',
        'imagine me', 'picture me', 'think about doing to me',
        'what would you do to me', 'what would you do if i',
    ]),
    ('oral_desire', [
        'in my mouth', 'on my mouth', 'go down', 'oral', 'blow',
        'tongue on', 'mouth on', 'use my mouth',
    ]),
    ('explicit_arousal', [
        'wet right now', 'turned on', 'hard right now', 'horny right now',
        'aroused', 'throbbing', 'aching for', 'need you right now',
        'want you so bad', 'craving you',
    ]),
    ('orgasm_pleasure', [
        'make me cum', 'make me come', 'climax', 'orgasm', 'make me feel good',
        'pleasure me', 'satisfy me', 'make me lose control',
    ]),

    # ── SENSUAL / GENERAL FLIRT ──────────────────────────────────────────────
    ('sensual_tension', [
        'something about the way you', 'the way you talk to me', 'doing that on purpose',
        'set something off', 'can\'t think straight', 'getting to me',
        'effect you have on me', 'what you do to me',
    ]),
    ('compliment_his_energy', [
        'your energy', 'energy you give', 'vibe you give', 'the way you carry',
        "there's something about you", "theres something about you",
    ]),

    # ── COMEBACK / RE-ENTRY ──────────────────────────────────────────────────
    ('went_quiet_returning', [
        'i disappeared', 'i went quiet', 'i was quiet', 'my head out',
        'sort myself out', 'i\'m back', 'back now', 'took some time',
    ]),
    ('he_went_cold', [
        'your energy changed', 'you\'ve gone quiet', 'you went quiet',
        'you pulled back', 'something shift', 'something changed',
        'short replies', 'one word replies',
    ]),
    ('first_message_opener', [
        'just matched', 'just connected', 'your profile', 'intrigued by you',
        'want to know more about you', 'what kind of man are you',
        'tell me something', 'introduce yourself',
    ]),

    # ── GENERIC FALLBACK ─────────────────────────────────────────────────────
    ('generic_question', ['?']),
]


def _normalize(text: str) -> str:
    text = unicodedata.normalize('NFKC', text).lower()
    text = re.sub(r'[^\w\s\'\?]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def classify_intent_template(text: str) -> str:
    """
    Classify a generated message into an intent template key.
    Returns the first matching template key, or 'generic_question'.

    Pure Python — no API call, runs in <1ms.
    """
    if not text:
        return 'generic_question'

    norm = _normalize(text)

    for template_key, signals in INTENT_TEMPLATES:
        for signal in signals:
            if signal in norm:
                return template_key

    return 'generic_question'


def get_content_fingerprint(text: str) -> str:
    """
    SHA-256 of the intent template key.
    Two semantically identical messages (different words, same question)
    will produce the same content fingerprint.

    Stored in AIReply.content_fingerprint.
    """
    template_key = classify_intent_template(text)
    return hashlib.sha256(template_key.encode()).hexdigest()


def get_template_key(text: str) -> str:
    """Convenience wrapper — returns the template key string (for logging/debug)."""
    return classify_intent_template(text)
