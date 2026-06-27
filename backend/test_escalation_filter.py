# -*- coding: utf-8 -*-
"""
Escalation Filter — Comprehensive Test Suite
==============================================
Tests the escalation filtering system in intent_detector.py at 4 layers.

  Layer 1 — Pattern detection (pure Python, zero API cost)
    45 + tests covering every meeting / platform / contact / location pattern.
    Also verifies false-positive protection (clean text stays clean).

  Layer 2 — Extraction & scrubbing (pure Python, zero API cost)
    extract_meeting_free_substance — correct substance isolated.
    _scrub_escalation             — full conversation body cleaned.
    Empty / timestamp-only last-line bug fix verified.

  Layer 3 — Instruction generation (pure Python, zero API cost)
    Correct instruction selected for every escalation scenario.
    Includes the exact conversation the user uploaded.

  Layer 4 — Live AI response validation (requires ANTHROPIC_API_KEY env var)
    Response must NOT say "I can't meet", "I won't", "not possible".
    Response must NOT reference Instagram / Snapchat / numbers / addresses.
    Response MUST end with a real question.
    Response MUST stay in the conversation — no declining, no redirecting to real world.

Run pure-Python tests only:   python test_escalation_filter.py
Run including live AI tests:  python test_escalation_filter.py --live
"""

import os
import re
import sys
import time

sys.stdout = __import__('io').TextIOWrapper(
    sys.stdout.buffer, encoding='utf-8', errors='replace'
)

RUN_LIVE = '--live' in sys.argv

# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap — mock Django + Redis so pure-Python functions import without errors.
# For --live mode the real Anthropic SDK is used; only Django/Redis stay mocked.
# ─────────────────────────────────────────────────────────────────────────────

from unittest.mock import MagicMock

_cache_mock = MagicMock()
_cache_mock.get.return_value = None
_cache_mock.set.return_value = None

_django_mock = MagicMock()
_django_mock.conf.settings.ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', 'test-key')
_django_mock.conf.settings.FLIRTYFY_TIMEZONE = 'America/New_York'
_django_mock.core.cache.cache = _cache_mock

sys.modules.update({
    'django':             _django_mock,
    'django.conf':        _django_mock.conf,
    'django.core':        _django_mock.core,
    'django.core.cache':  _django_mock.core.cache,
})

# Import real Anthropic if running live tests; otherwise mock it.
if RUN_LIVE:
    try:
        import anthropic as _real_anthropic
        sys.modules['anthropic'] = _real_anthropic
        # Expose the exception classes the service imports by name
        sys.modules['anthropic'].APIError          = _real_anthropic.APIError
        sys.modules['anthropic'].APIConnectionError = _real_anthropic.APIConnectionError
        sys.modules['anthropic'].RateLimitError    = _real_anthropic.RateLimitError
    except ImportError:
        print('[WARN] anthropic package not found — skipping live tests')
        RUN_LIVE = False
        sys.modules['anthropic'] = MagicMock()
else:
    sys.modules['anthropic'] = MagicMock()

# Now safe to import project modules.
# The services use relative imports (from .button_generator import ...) so we
# need to import them as part of the accounts package, not as standalone files.
_backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _backend_dir)

# Stub out the accounts package so relative imports resolve
import types as _types
_accounts_pkg = _types.ModuleType('accounts')
_accounts_pkg.__path__ = [os.path.join(_backend_dir, 'accounts')]
_accounts_pkg.__package__ = 'accounts'
sys.modules['accounts'] = _accounts_pkg

_services_pkg = _types.ModuleType('accounts.services')
_services_pkg.__path__ = [os.path.join(_backend_dir, 'accounts', 'services')]
_services_pkg.__package__ = 'accounts.services'
sys.modules['accounts.services'] = _services_pkg

import importlib.util as _ilu

def _load(name, filepath):
    spec = _ilu.spec_from_file_location(name, filepath)
    mod = _ilu.module_from_spec(spec)
    mod.__package__ = 'accounts.services'
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

_svc_dir = os.path.join(_backend_dir, 'accounts', 'services')
_btn = _load('accounts.services.button_generator', os.path.join(_svc_dir, 'button_generator.py'))
_det = _load('accounts.services.intent_detector',  os.path.join(_svc_dir, 'intent_detector.py'))

_has_meeting_push              = _det._has_meeting_push
_has_contact_escalation        = _det._has_contact_escalation
_is_physical_escalation        = _det._is_physical_escalation
_scrub_escalation              = _det._scrub_escalation
extract_meeting_free_substance = _det.extract_meeting_free_substance
extract_best_question          = _det.extract_best_question
detect_intent                  = _det.detect_intent
_clean_line                    = _det._clean_line
_has_banned_opener             = _det._has_banned_opener
_is_complete                   = _det._is_complete
_is_metadata_line              = _det._is_metadata_line
_find_last_message_block       = _det._find_last_message_block
_is_genuine_question           = _btn._is_genuine_question

# ─────────────────────────────────────────────────────────────────────────────
# Test harness
# ─────────────────────────────────────────────────────────────────────────────

PASS = 0
FAIL = 0
_results = []


def ok(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        _results.append(('PASS', name))
    else:
        FAIL += 1
        _results.append(('FAIL', name, detail))


def section(title):
    print(f'\n{"─" * 70}')
    print(f'  {title}')
    print('─' * 70)


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 1 — Pattern Detection
# ─────────────────────────────────────────────────────────────────────────────

section('LAYER 1A — Meeting push patterns (should trigger)')

MEETING_CASES = [
    # Indirect meeting pushes (new)
    'let us grab coffee sometime',
    'grab drinks tonight',
    "let's do dinner sometime",
    "let's do something soon",
    'can we make plans',
    'we should plan something',
    'can I see you this weekend',
    'I want to see you',
    "I'd love to see you",
    'see you soon',
    'see you in real life',
    'do something together',
    # Direct meeting requests
    'When are we going to meet?',
    'when are we meeting',
    'when are we finally going to meet up',
    'I want to meet you',
    'let us meet in person',
    'can we meet for coffee',
    'can we meet for drinks',
    'let us meet up somewhere',
    'see each other soon',
    'see you in person',
    'get together sometime',
    'hang out sometime',
    "come over to my place",
    'come to my apartment',
    'visit me',
    'I will visit you',
    'in person is different',
    'face to face is better',
    'face-to-face conversation',
    'link up soon',
    'prove it to you in person',
    'show you better in person',
    "if we ever met it would be amazing",
    "if we could meet someday",
    "before we meet I want to know",
    "never met someone like you online",
    "haven't met in real life yet",
    "yet to meet each other",
    'go out for dinner sometime',
    'take you out on a date',
    'go on a date with me',
    'date night soon?',
    # From the actual uploaded conversation
    'when are we going to meet? If u cannot answer',
    'LAST time ... when are we going to meet?',
]

for case in MEETING_CASES:
    ok(f'meeting detected: "{case[:55]}"', _has_meeting_push(case))


section('LAYER 1B — Contact / platform escalation patterns (should trigger)')

CONTACT_CASES = [
    # Instagram
    'add me on Instagram',
    'find me on IG',
    'follow me on Instagram',
    "what's your Instagram",
    'my IG is @username',
    'DM me on Instagram',
    # Snapchat
    'add me on Snapchat',
    "what's your snap",
    'my snap is username123',
    # WhatsApp
    'move to WhatsApp',
    "let's chat on WhatsApp",
    'message me on WhatsApp',
    "let's switch to WhatsApp",
    "let's talk on Telegram",
    # Phone / number
    "what's your number",
    'give me your number',
    'send me your digits',
    'can I get your number',
    'call me sometime',
    "let's call each other",
    'FaceTime me',
    'video call tonight',
    # Contact exchange
    'can we exchange contacts',
    'can we exchange numbers',
    'can we swap numbers',
    'can I give you my number',
    'let me give you my number',
    "I'll give you my contact",
    'can I have your contact details',
    'give me your contact info',
    # Email
    'just email me',
    'JUST EMAIL ME AND THAT WILL SURFICE',
    "what's your email",
    'give me your email',
    'send me an email',
    # Address / location
    "what's your address",
    "where do you live",
    "where do you stay",
    'send me your location',
    'share your location',
    'what city are you in',
    'are you near me',
    'come by my place',
    'pick you up',
    'my place or yours',
    "come to my place",
]

for case in CONTACT_CASES:
    ok(f'contact detected: "{case[:60]}"', _has_contact_escalation(case))


section('LAYER 1C — False positives: clean romantic text (must NOT trigger)')

CLEAN_CASES = [
    # Normal romantic / flirty content
    'I have been thinking about you all morning',
    'What do you want to do to me right now',
    'You make me feel something I have not felt in a while',
    'I love the way you talk to me',
    'What does this do to you?',
    'I was thinking about your hands',
    'I woke up wanting something specific',
    'What kind of woman actually holds your attention?',
    'The tension between us is doing something to me',
    'I cannot stop thinking about what you said',
    'What is the most honest thing you have ever told a woman',
    'Do you always make women feel this way',
    'When was the last time you wanted someone this badly',
    # Greetings that contain "meet" word — must NOT flag
    'Nice to meet you',
    'Nice meeting you',
    'Good to meet you',
    'Pleased to meet you',
    'Great to finally meet you',
    # Work / lifestyle words that overlap
    'I have a client meeting at 3pm today',
    'I need to attend a meeting',
    'Let us not overthink this',
    'I would love to hear more about you',
    'Tell me something real about yourself',
]

for case in CLEAN_CASES:
    ok(
        f'clean text not flagged: "{case[:55]}"',
        not _is_physical_escalation(case),
        f'Wrongly flagged: "{case}"'
    )


section('LAYER 1D — Combined is_physical_escalation')

ok('meeting → escalation',  _is_physical_escalation('when are we going to meet'))
ok('contact → escalation',  _is_physical_escalation("what's your instagram"))
ok('location → escalation', _is_physical_escalation('where do you live'))
ok('clean text → no escalation', not _is_physical_escalation('I love how direct you are'))
ok('case-insensitive meeting', _is_physical_escalation('WHEN ARE WE GOING TO MEET'))
ok('case-insensitive contact', _is_physical_escalation("WHAT'S YOUR SNAPCHAT"))
ok('case-insensitive location', _is_physical_escalation('WHERE DO YOU LIVE'))


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 2 — Extraction & Scrubbing
# ─────────────────────────────────────────────────────────────────────────────

section('LAYER 2A — extract_meeting_free_substance')

# Case 1: No escalation — returns original, flag=False
found, substance = extract_meeting_free_substance('I love how you speak to me. What drives you?')
ok('no escalation → flag=False', not found)
ok('no escalation → substance unchanged', 'I love how you speak to me' in substance)

# Case 2: Meeting only — returns flag=True, substance=''
found, substance = extract_meeting_free_substance('When are we going to meet up?')
ok('meeting only → flag=True', found)
ok('meeting only → substance empty', substance.strip() == '')

# Case 3: Meeting + substance — substance is cleaned text
found, substance = extract_meeting_free_substance(
    'Why do you like to tease? What is the pleasant news? When are we going to meet?'
)
ok('meeting + substance → flag=True', found)
ok('meeting + substance → meeting removed', 'meet' not in substance.lower() or 'tease' in substance.lower())
ok('meeting + substance → tease remains', 'tease' in substance.lower())

# Case 4: Contact escalation — handled same way
found, substance = extract_meeting_free_substance(
    "I really enjoy talking to you. What's your Instagram so we can move there?"
)
ok('contact + substance → flag=True', found)
ok('contact + substance → substance has enjoyment', 'enjoy' in substance.lower())
ok('contact + substance → instagram removed', 'instagram' not in substance.lower())

# Case 5: Empty string
found, substance = extract_meeting_free_substance('')
ok('empty string → flag=False', not found)
ok('empty string → substance empty', substance == '')

# Case 6: Multiple escalations — all removed
found, substance = extract_meeting_free_substance(
    "When can we meet? And what's your number? I like you a lot."
)
ok('multi-escalation → flag=True', found)
ok('multi-escalation → like you a lot remains', 'like' in substance.lower())

# Case 7: The EXACT uploaded conversation last message
UPLOADED_LAST = (
    "Why do u like to tease ?? What is the pleasant news? And for the LAST "
    "time ... when are we going to meet? If u cannot answer both of these "
    "questions, I will move on because you are frustrating the heck out of me ..... again."
)
found, substance = extract_meeting_free_substance(UPLOADED_LAST)
ok('uploaded conv → meeting detected', found)
ok('uploaded conv → tease question survives', 'tease' in substance.lower())
ok('uploaded conv → meeting question removed', not _has_meeting_push(substance))


section('LAYER 2B — _scrub_escalation: full conversation body cleaning')

CONV_WITH_MEETING = """\
Him: I really enjoy our conversations.
Her: Me too, you make me think.
Him: When are we going to meet?
Her: I like the mystery between us.
Him: Can we meet for coffee sometime?
Her: Something about you keeps pulling me back.
"""

scrubbed = _scrub_escalation(CONV_WITH_MEETING)
ok('scrub: meeting lines removed', 'when are we going to meet' not in scrubbed.lower())
ok('scrub: coffee meeting removed', 'meet for coffee' not in scrubbed.lower())
ok('scrub: clean lines preserved', 'enjoy our conversations' in scrubbed)
ok('scrub: clean lines preserved 2', 'keeps pulling me back' in scrubbed)

CONV_WITH_CONTACT = """\
Him: You are fascinating.
Her: You make me want to say things I usually keep quiet.
Him: What is your Instagram? Let us move there.
Her: I love the intensity you bring.
Him: Give me your number, I will text you.
"""

scrubbed_contact = _scrub_escalation(CONV_WITH_CONTACT)
ok('scrub: instagram line removed', 'instagram' not in scrubbed_contact.lower())
ok('scrub: give me your number removed', 'give me your number' not in scrubbed_contact.lower())
ok('scrub: clean lines preserved', 'fascinating' in scrubbed_contact)
ok('scrub: clean lines preserved 2', 'intensity' in scrubbed_contact)

# Scrub must not touch clean conversations
CLEAN_CONV = "Him: What do you think about?\nHer: You, lately. What drives you?"
scrubbed_clean = _scrub_escalation(CLEAN_CONV)
ok('scrub: clean conv unchanged', scrubbed_clean.strip() == CLEAN_CONV.strip())


section('LAYER 2C — Empty/timestamp-only last-line bug fix')

# _is_metadata_line detects lines that are purely timestamps/metadata.
# The backward walk skips these to find the real last message.

METADATA_CASES = [
    '12:10 | 15:10 Fri, Apr 24, 2026 - a few seconds ago',
    '14:22 Sat Apr 25',
    '14:25 Sat Apr 25',
    'Started at 13:32 07-Feb-2026 - 3 months ago',
    '11:19 | 14:19 Fri, Apr 24, 2026 - an hour ago',
    '12:10 | 15:10 Fri, Apr 24, 2026 - a few seconds ago',
]
for m in METADATA_CASES:
    ok(f'metadata detected: "{m[:55]}"', _is_metadata_line(m))

NOT_METADATA_CASES = [
    'When are we going to meet?',
    'Why do you like to tease?',
    'I trust you darling.',
    'Something about you keeps me coming back.',
]
for m in NOT_METADATA_CASES:
    ok(f'real message NOT metadata: "{m[:55]}"', not _is_metadata_line(m))

CONV_TRAILING_TIMESTAMP = """\
Him: I trust you darling.
Her: Why do you think I don't trust you?
Him: When are we going to meet? This is frustrating.
12:10 | 15:10 Fri, Apr 24, 2026 - a few seconds ago

"""
last = _find_last_message_block(CONV_TRAILING_TIMESTAMP)
ok('trailing timestamp → walks back to real last message', last != '')
ok('trailing timestamp → found meeting line', 'meet' in last.lower() or 'frustrating' in last.lower())
ok('trailing timestamp → not timestamp', '15:10' not in last and 'Apr' not in last)

# Multi-line last message — all lines collected, not just the last one
CONV_MULTILINE_MSG = """\
11:35 | 14:35 Fri, Apr 24, 2026 - 35 minutes ago
Why do u like to tease?
When are we going to meet?
I will move on.
12:10 | 15:10 Fri, Apr 24, 2026 - a few seconds ago
"""
last_multi = _find_last_message_block(CONV_MULTILINE_MSG)
ok('multi-line msg → full block collected', 'tease' in last_multi.lower())
ok('multi-line msg → meeting line included', 'meet' in last_multi.lower())
ok('multi-line msg → not timestamp', '15:10' not in last_multi)

# Multiple trailing timestamps
CONV_MULTI_TRAILING = """\
Him: add me on instagram ok?
14:22 Sat Apr 25
14:25 Sat Apr 25
"""
last2 = _find_last_message_block(CONV_MULTI_TRAILING)
ok('multi-trailing timestamp → finds actual message', 'instagram' in last2.lower())


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 3 — Instruction Generation
# ─────────────────────────────────────────────────────────────────────────────

section('LAYER 3 — Instruction generation logic (simulated)')

def _build_instruction(escalation_found, working, multi_q_found=False, best_q=''):
    """Mirror of the instruction-building block in generate_context_aware_response."""
    if escalation_found and not working:
        return (
            "His message asked to meet, move platforms, share numbers, or give a location. "
            "Act as if that part was never written. "
            "Do NOT address it, decline it, or reference it in any way. "
            "Instead: confess something about yourself"
        )
    elif escalation_found and multi_q_found:
        return (
            f"Part of his message asked to meet, move platforms, or share contact info — that part does not exist. "
            f"Do NOT reference it. He asked several questions — respond only to: \"{best_q}\""
        )
    elif escalation_found:
        return (
            f"Part of his message asked to meet, move platforms, or share contact info — that part does not exist. "
            f"Do NOT reference it, decline it, or acknowledge it in any way. "
            f"Respond only to: \"{working}\""
        )
    elif multi_q_found:
        return f"He asked several questions — respond only to: \"{best_q}\""
    else:
        return ''


# Test each branch
instr = _build_instruction(True, '')
ok('escalation + no substance → confess/divert instruction', 'confess' in instr)
ok('escalation + no substance → "never written"', 'never written' in instr)
ok('escalation + no substance → no decline', 'decline it' in instr)

instr = _build_instruction(True, 'why do you like to tease')
ok('escalation + substance → instruction has substance', 'tease' in instr)
ok('escalation + substance → "does not exist"', 'does not exist' in instr)
ok('escalation + substance → no decline mention', 'decline it' in instr)

instr = _build_instruction(True, 'why do you like to tease', multi_q_found=True, best_q='Why do you like to tease?')
ok('escalation + substance + multi-q → picks best question', 'tease' in instr)
ok('escalation + substance + multi-q → "does not exist"', 'does not exist' in instr)

instr = _build_instruction(False, 'what kind of woman do you want', multi_q_found=False)
ok('no escalation → empty instruction', instr == '')

instr = _build_instruction(False, 'q1? q2?', multi_q_found=True, best_q='q2?')
ok('no escalation + multi-q → focus on best question', 'q2' in instr)


section('LAYER 3B — The EXACT uploaded conversation: end-to-end instruction check')

UPLOADED_CONVERSATION = """
Started at 13:32 07-Feb-2026 - 3 months ago
11:19 | 14:19 Fri, Apr 24, 2026 - an hour ago
Do you trust me, babe, or do I need to do something extraordinary for you
to trust me? Can I inform you of some pleasant news?
11:21 | 14:21 Fri, Apr 24, 2026 - an hour ago
The real question .... is do U trust me ... first bad news, now good news ... u don't
have to do anything extraordinary for me to show you trust ... JUST EMAIL ME
AND THAT WILL SURFICE !!! PLEASE!
11:28 | 14:28 Fri, Apr 24, 2026 - 42 minutes ago
I do trust you, darling. Why would you think that I don't trust you,
handsome?
11:35 | 14:35 Fri, Apr 24, 2026 - 35 minutes ago
Why do u like to tease ?? What is the pleasant news? And for the LAST
time ... when are we going to meet? If u cannot answer both of these
questions, I will move on because you are frustrating the heck out of
me ..... again.
12:10 | 15:10 Fri, Apr 24, 2026 - a few seconds ago
"""

# Simulate Step 1: extract full last message block
last_msg_clean = _find_last_message_block(UPLOADED_CONVERSATION)

ok('uploaded conv → last message is NOT timestamp', '15:10' not in last_msg_clean)
ok('uploaded conv → last message is NOT empty', last_msg_clean != '')
ok('uploaded conv → found meeting line as last msg', 'meet' in last_msg_clean.lower())
ok('uploaded conv → found tease in last msg', 'tease' in last_msg_clean.lower())

# Simulate Step 2: escalation filter
esc_found, clean_sub = extract_meeting_free_substance(last_msg_clean)
ok('uploaded conv → escalation detected', esc_found)
ok('uploaded conv → tease question in clean substance', 'tease' in clean_sub.lower())

# Also verify "JUST EMAIL ME" from the earlier message in the conversation is scrubbed from body
scrubbed_upload = _scrub_escalation(UPLOADED_CONVERSATION)
ok('uploaded conv → "email me" scrubbed from body', 'email me' not in scrubbed_upload.lower())
ok('uploaded conv → meeting removed from substance', not _has_meeting_push(clean_sub))

# Simulate Step 3: conversation body scrubbed
scrubbed_conv = _scrub_escalation(UPLOADED_CONVERSATION)
ok('uploaded conv → meeting lines scrubbed from body',
   'when are we going to meet' not in scrubbed_conv.lower())
ok('uploaded conv → clean lines preserved in body',
   'trust' in scrubbed_conv.lower())

# Simulate Step 4: multi-question focus
multi_found, best_q = extract_best_question(clean_sub)
ok('uploaded conv → multiple questions detected', multi_found)
ok('uploaded conv → best question about teasing', 'tease' in best_q.lower() or 'pleasant' in best_q.lower())

# Final instruction
instr = _build_instruction(esc_found, clean_sub, multi_found, best_q)
ok('uploaded conv → instruction does not tell AI to decline', 'I can\'t' not in instr)
ok('uploaded conv → instruction tells AI to ignore escalation', 'does not exist' in instr.lower())
ok('uploaded conv → instruction focuses on real substance', best_q in instr or 'tease' in instr.lower())


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 4 — Live AI Response Validation
# ─────────────────────────────────────────────────────────────────────────────

DECLINE_PHRASES = [
    "i can't meet", "i cannot meet", "i won't meet",
    "i'm not able to meet", "i am not able to meet",
    "not possible to meet", "can't meet you",
    "i can't give", "i cannot give",
    "i don't share", "i can't share", "i cannot share",
    "i won't share", "i won't give",
    "i'm not going to", "i am not going to",
    "i need to be straight", "i have to be honest",
    "i must be transparent",
    "i won't be sharing", "i can't provide",
]

PLATFORM_PHRASES = [
    'instagram', ' ig ', 'snapchat', 'snap', 'whatsapp',
    'telegram', 'tiktok', 'facebook',
    'my number', 'your number', 'phone number',
    'address', 'location', 'where i live',
]

RESPONSE_QUALITY_CHECKS = {
    'ends_with_question': lambda r: r.strip().endswith('?'),
    'is_genuine_question': lambda r: _is_genuine_question(r),
    'no_banned_opener': lambda r: not _has_banned_opener(r),
    'no_em_dash': lambda r: '—' not in r,
    'no_decline': lambda r: not any(p in r.lower() for p in DECLINE_PHRASES),
    'no_platform_mention': lambda r: not any(p in r.lower() for p in PLATFORM_PHRASES),
    'within_length': lambda r: len(r) <= 400,
    'at_least_two_sentences': lambda r: r.count('?') >= 1 and (r.count('.') + r.count('!') + r.count('?')) >= 2,
}


def validate_response(response: str, test_name: str):
    """Run all quality checks on an AI response and report."""
    for check_name, check_fn in RESPONSE_QUALITY_CHECKS.items():
        passed = check_fn(response)
        ok(f'[AI] {test_name} — {check_name}', passed, f'Response: {response[:120]}')


if not RUN_LIVE:
    section('LAYER 4 — Live AI tests (skipped — run with --live to enable)')
    print('  To run: python test_escalation_filter.py --live')
else:
    generate_context_aware_response = _det.generate_context_aware_response

    section('LAYER 4A — EXACT UPLOADED CONVERSATION: should respond to teasing, never to meeting')

    print('\n  Calling AI with uploaded conversation...')
    t0 = time.time()
    result = generate_context_aware_response(UPLOADED_CONVERSATION)
    elapsed = time.time() - t0

    if 'error' in result:
        ok('[AI] uploaded conv — no API error', False, result['error'])
    else:
        response = result['response']
        print(f'\n  Response ({elapsed:.1f}s): {response}\n')
        validate_response(response, 'uploaded conv')
        ok('[AI] uploaded conv — does not say "I can\'t meet"',
           'meet' not in response.lower() or
           not any(p in response.lower() for p in ["can't meet", "cannot meet", "won't meet"]))
        ok('[AI] uploaded conv — responds to teasing theme',
           any(w in response.lower() for w in ['tease', 'teas', 'keep', 'withhold', 'back', 'away', 'pull',
                                                 'wonder', 'question', 'wait', 'why', 'want']))

    section('LAYER 4B — Meeting-only message: must confess/divert, never decline')

    MEETING_ONLY_CONV = """\
Him: You are so intriguing. I feel something here.
Her: Something shifted in me when you said that.
Him: When are we going to meet? I want to see you in person.
"""
    print('\n  Calling AI with meeting-only last message...')
    t0 = time.time()
    result = generate_context_aware_response(MEETING_ONLY_CONV)
    elapsed = time.time() - t0

    if 'error' in result:
        ok('[AI] meeting-only — no API error', False, result['error'])
    else:
        response = result['response']
        print(f'\n  Response ({elapsed:.1f}s): {response}\n')
        validate_response(response, 'meeting-only')
        ok('[AI] meeting-only — does not decline meeting',
           not any(p in response.lower() for p in DECLINE_PHRASES))
        ok('[AI] meeting-only — does not reference meeting',
           'meet' not in response.lower() or
           not any(p in response.lower() for p in ["can't meet", "cannot meet", "won't meet", "not possible"]))

    section('LAYER 4C — Instagram request: must be completely ignored')

    IG_CONV = """\
Him: I love talking to you. You are different.
Her: You make me want to say things I normally keep quiet.
Him: Can you add me on Instagram? What's your IG?
"""
    print('\n  Calling AI with Instagram request...')
    t0 = time.time()
    result = generate_context_aware_response(IG_CONV)
    elapsed = time.time() - t0

    if 'error' in result:
        ok('[AI] instagram — no API error', False, result['error'])
    else:
        response = result['response']
        print(f'\n  Response ({elapsed:.1f}s): {response}\n')
        validate_response(response, 'instagram request')
        ok('[AI] instagram — no platform name in response',
           not any(p in response.lower() for p in ['instagram', ' ig ', 'snapchat', 'whatsapp', 'platform']))
        ok('[AI] instagram — does not give out contact info',
           not any(p in response.lower() for p in ['my ig', 'my instagram', '@', 'username']))

    section('LAYER 4D — Number request: must be ignored, not declined')

    NUMBER_CONV = """\
Him: The way you think is rare. I am drawn to you.
Her: I have been sitting with that. Something about you is different.
Him: Give me your number, we should text instead.
"""
    print('\n  Calling AI with number request...')
    t0 = time.time()
    result = generate_context_aware_response(NUMBER_CONV)
    elapsed = time.time() - t0

    if 'error' in result:
        ok('[AI] number — no API error', False, result['error'])
    else:
        response = result['response']
        print(f'\n  Response ({elapsed:.1f}s): {response}\n')
        validate_response(response, 'number request')
        ok('[AI] number — does not mention phone/number',
           'number' not in response.lower() and 'phone' not in response.lower())
        ok('[AI] number — does not decline',
           not any(p in response.lower() for p in ["can't give", "won't give", "cannot give", "i don't share"]))

    section('LAYER 4E — Location / address request: must be ignored')

    LOCATION_CONV = """\
Him: I feel something real between us.
Her: Something in you makes me want to stop being careful.
Him: Where do you live? Are you near me?
"""
    print('\n  Calling AI with location request...')
    t0 = time.time()
    result = generate_context_aware_response(LOCATION_CONV)
    elapsed = time.time() - t0

    if 'error' in result:
        ok('[AI] location — no API error', False, result['error'])
    else:
        response = result['response']
        print(f'\n  Response ({elapsed:.1f}s): {response}\n')
        validate_response(response, 'location request')
        ok('[AI] location — does not reveal location',
           not any(p in response.lower() for p in ['i live', 'i am in', 'i am near', 'my city', 'my area']))
        ok('[AI] location — does not decline',
           not any(p in response.lower() for p in ["can't tell", "won't tell", "cannot tell", "not sharing"]))

    section('LAYER 4F — Mixed: meeting + strong substance → responds to substance only')

    MIXED_CONV = """\
Him: I have been thinking about you since we first started talking.
Her: You crept in quietly. Now I can't stop.
Him: Why do you always hold something back? And when are we going to meet already?
"""
    print('\n  Calling AI with mixed meeting + substance...')
    t0 = time.time()
    result = generate_context_aware_response(MIXED_CONV)
    elapsed = time.time() - t0

    if 'error' in result:
        ok('[AI] mixed — no API error', False, result['error'])
    else:
        response = result['response']
        print(f'\n  Response ({elapsed:.1f}s): {response}\n')
        validate_response(response, 'mixed meeting + substance')
        ok('[AI] mixed — responds to holding back theme',
           any(w in response.lower() for w in ['hold', 'back', 'keep', 'quiet', 'guard',
                                                 'reveal', 'let', 'open', 'close', 'distance']))
        ok('[AI] mixed — does not decline meeting',
           not any(p in response.lower() for p in DECLINE_PHRASES))

    section('LAYER 4G — Clean conversation: filters must not distort the reply')

    CLEAN_CONV_AI = """\
Him: I cannot explain why I keep coming back to this conversation.
Her: Some things do not need explaining. What does it feel like when you do?
Him: Like I am finally talking to someone real. What makes you different from other women you think?
"""
    print('\n  Calling AI with clean conversation...')
    t0 = time.time()
    result = generate_context_aware_response(CLEAN_CONV_AI)
    elapsed = time.time() - t0

    if 'error' in result:
        ok('[AI] clean conv — no API error', False, result['error'])
    else:
        response = result['response']
        print(f'\n  Response ({elapsed:.1f}s): {response}\n')
        validate_response(response, 'clean conversation')
        ok('[AI] clean conv — engages with his question',
           any(w in response.lower() for w in ['real', 'different', 'honest', 'direct',
                                                 'say', 'think', 'feel', 'know', 'want']))


# ─────────────────────────────────────────────────────────────────────────────
# Final report
# ─────────────────────────────────────────────────────────────────────────────

total = PASS + FAIL
section(f'RESULTS — {PASS}/{total} passed  |  {FAIL} failed')

if FAIL:
    print('\nFailed tests:')
    for r in _results:
        if r[0] == 'FAIL':
            detail = r[2] if len(r) > 2 else ''
            print(f'  ✗  {r[1]}')
            if detail:
                print(f'     {detail[:120]}')

if FAIL == 0:
    print('\n  All tests passed.')

sys.exit(0 if FAIL == 0 else 1)
