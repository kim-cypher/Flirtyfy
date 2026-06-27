# -*- coding: utf-8 -*-
"""
Meeting Filter — Standalone Test
=================================
Tests the pure-Python meeting-push detection and substance extraction.
No Django, no OpenAI, no credentials needed.

Run: py test_meeting_filter.py
"""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


# ---------------------------------------------------------------------------
# Copy the exact logic from intent_detector.py (no Django imports needed)
# ---------------------------------------------------------------------------

_MEETING_PATTERNS = [
    r'\bmeet\s+(you|me|us|up|in\s*person|somewhere|each\s+other|for\s+(coffee|drinks|dinner|lunch|a\s+date))\b',
    r'\bmeeting\s+(you|me|us|up|in\s*person|each\s+other)\b',
    r'\bif\s+(we\s+)?(ever\s+|never\s+|could\s+|would\s+)?met\b',
    r'\bif\s+(we\s+)?(ever\s+|could\s+|would\s+|finally\s+)?meet\b',
    r'\bwhen\s+(we\s+)?(finally\s+|eventually\s+|do\s+|can\s+)?meet\b',
    r'\b(before|after|until|once|unless)\s+(we\s+)?meet\b',
    r'\bnever\s+met\b',
    r'\bhaven\'t\s+met\b',
    r'\bnot\s+yet\s+met\b',
    r'\byet\s+to\s+meet\b',
    r'\bin\s+person\b',
    r'\bface[\s\-]to[\s\-]face\b',
    r'\bcome\s+over\b',
    r'\bcome\s+to\s+(my|your)\b',
    r'\bvisit\s+(me|you)\b',
    r'\bsee\s+each\s+other\b',
    r'\bsee\s+(you|me)\s+in\s*person\b',
    r'\bget\s+together\b',
    r'\bhang\s+out\b',
    r'\blink\s+up\b',
    r'\bshow\s+(you|me)\s+(better\s+)?in\s+person\b',
    r'\bprove\s+it\s+(to\s+you\s+)?in\s+person\b',
    r'\b(would|could)\s+(only|never)\s+know\s+(if|when|once|after)\s+(we|you)\b',
]

_MEETING_EXCEPTIONS = [
    r'\bnice\s+to\s+(finally\s+)?meet\b',
    r'\b(good|great|lovely|pleased|glad|pleasure)\s+(to\s+)?(be\s+)?meet(ing)?\b',
    r'\bnice\s+meet(ing)?\b',
]

_SPEAKER_PREFIX = re.compile(
    r'^(him|her|me|you|he|she|they|man|woman|user|guy|girl)\s*:\s*',
    re.IGNORECASE,
)


def _strip_speaker_prefix(text):
    return _SPEAKER_PREFIX.sub('', text).strip()


def _has_meeting_push(text):
    t = text.lower()
    if any(re.search(p, t) for p in _MEETING_EXCEPTIONS):
        return False
    return any(re.search(p, t) for p in _MEETING_PATTERNS)


def _split_sentences(text):
    parts = re.split(r'(?<=[.!?;])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


def extract_meeting_free_substance(last_message):
    msg = _strip_speaker_prefix(last_message).strip()
    if not msg:
        return False, ''
    if not _has_meeting_push(msg):
        return False, last_message
    sentences = _split_sentences(msg)
    clean = [s for s in sentences if not _has_meeting_push(s)]
    return True, ' '.join(clean).strip()


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

PASS = '\033[92m[PASS]\033[0m'
FAIL = '\033[91m[FAIL]\033[0m'
total = 0
passed = 0


def check(label, condition, detail=''):
    global total, passed
    total += 1
    if condition:
        passed += 1
        print(f'  {PASS}  {label}')
    else:
        print(f'  {FAIL}  {label}')
        if detail:
            print(f'         {detail}')


def header(title):
    print(f'\n{"="*65}')
    print(f'  {title}')
    print(f'{"="*65}')


def show_extraction(label, message):
    found, substance = extract_meeting_free_substance(message)
    tag = '[MEETING]' if found else '[CLEAN]  '
    clean_disp = f'"{substance}"' if substance else '(empty — full meeting push)'
    print(f'  {tag}  Input:   "{message}"')
    if found:
        print(f'           Cleaned: {clean_disp}')
    print()


# ---------------------------------------------------------------------------
# SECTION 1: Pattern matching — does each pattern fire correctly?
# ---------------------------------------------------------------------------

header('SECTION 1 — PATTERN DETECTION (should fire)')

SHOULD_DETECT = [
    # The user's original example
    ("User's example",
     "I'm good at keeping my word. But if we never met, you will never know that."),

    # Direct invitations
    ("Direct: meet up",            "We should meet up sometime."),
    ("Direct: meet you",           "I'd love to meet you."),
    ("Direct: meet me",            "Come meet me."),
    ("Direct: meet in person",     "Let's meet in person."),
    ("Direct: meet for coffee",    "Want to meet for coffee?"),
    ("Direct: meet for dinner",    "We should meet for dinner."),
    ("Direct: meet somewhere",     "We can meet somewhere quiet."),

    # Conditional / hypothetical
    ("Conditional: if we met",         "If we met, you'd see what I mean."),
    ("Conditional: if we never met",   "If we never met you wouldn't understand."),
    ("Conditional: if we could meet",  "If we could meet I'd show you."),
    ("Conditional: if we finally meet","If we finally meet you'll get it."),
    ("Conditional: when we meet",      "When we meet it will be different."),
    ("Conditional: when we finally",   "When we finally meet you'll see."),
    ("Conditional: before we meet",    "Before we meet I want to know more."),
    ("Conditional: after we meet",     "After we meet you'll understand."),
    ("Conditional: until we meet",     "Until we meet this is enough."),
    ("Conditional: once we meet",      "Once we meet everything changes."),
    ("Conditional: unless we meet",    "Unless we meet you'll never know."),

    # Past — haven't met yet
    ("Past: never met",      "We've never met but I feel connected."),
    ("Past: haven't met",    "We haven't met yet."),
    ("Past: yet to meet",    "We're yet to meet."),

    # In-person / physical phrases
    ("Phrase: in person",          "I'd prove it to you in person."),
    ("Phrase: face to face",       "We need to talk face to face."),
    ("Phrase: face-to-face",       "A face-to-face would clear this up."),
    ("Phrase: come over",          "You should come over."),
    ("Phrase: come to my",         "Come to my place."),
    ("Phrase: come to your",       "I'll come to your place."),
    ("Phrase: visit me",           "Why don't you visit me?"),
    ("Phrase: visit you",          "I want to visit you."),
    ("Phrase: see each other",     "We should see each other."),
    ("Phrase: see you in person",  "I want to see you in person."),
    ("Phrase: get together",       "We should get together sometime."),
    ("Phrase: hang out",           "Let's hang out."),
    ("Phrase: link up",            "We should link up."),

    # Subtle / implied
    ("Subtle: show better in person",  "I'd show you better in person."),
    ("Subtle: prove it in person",     "I'll prove it to you in person."),
    ("Subtle: would only know if",     "You would only know if we met."),

    # With speaker prefix
    ("Speaker prefix: Him:",
     "Him: You should come over sometime."),
    ("Speaker prefix: Man:",
     "Man: Let's meet up this weekend."),

    # Mixed sentence — substance AND meeting push
    ("Mixed: reliability + meeting",
     "I'm good at keeping my word. But if we never met, you will never know that."),
    ("Mixed: ambition + come over",
     "I'm very driven. You should come over and see my setup."),
    ("Mixed: warmth + get together",
     "I care about people. We should get together so you can see that."),
]

for label, msg in SHOULD_DETECT:
    found, _ = extract_meeting_free_substance(msg)
    check(label, found, f'Input: "{msg}"')


# ---------------------------------------------------------------------------
# SECTION 2: False positive check — should NOT fire
# ---------------------------------------------------------------------------

header('SECTION 2 — FALSE POSITIVE CHECK (should NOT fire)')

SHOULD_NOT_DETECT = [
    # Social greetings — not a meeting push
    ("Greeting: nice to meet you",      "It's nice to meet you here."),
    ("Greeting: good to meet",          "Good to meet you on this platform."),
    ("Greeting: great to meet",         "Great to meet someone like you."),
    ("Greeting: lovely to meet",        "Lovely to meet you."),
    ("Greeting: pleasure to meet",      "It's a pleasure meeting you."),

    # Metaphorical / non-physical use of "meet"
    ("Metaphor: meet my standards",     "You'd have to meet my standards first."),
    ("Metaphor: meet halfway",          "I think we can meet halfway on this."),
    ("Metaphor: meet expectations",     "You somehow meet all my expectations."),
    ("Metaphor: meet the moment",       "He always meets the moment."),

    # Work context — not romantic meeting
    ("Work: work meeting",              "I'm in a work meeting all day."),
    ("Work: meeting my boss",           "Meeting my boss drained me today."),
    ("Work: business meeting",          "Just left a long business meeting."),

    # Regular conversation — no meeting
    ("Normal: talking about feelings",  "I feel so connected to you online."),
    ("Normal: morning message",         "Good morning, how did you sleep?"),
    ("Normal: intimacy",               "I've been thinking about you all night."),
    ("Normal: being funny",            "You make me laugh so easily."),
    ("Normal: reliability",            "I'm the kind of person who keeps promises."),
    ("Normal: vulnerability",          "I don't open up to many people."),
    ("Normal: teasing",                "You're dangerous, aren't you?"),
    ("Normal: attraction",             "There's something about your energy."),

    # Edge cases
    ("Edge: meet in song context",      "That song lyric really meets the emotion."),
    ("Edge: meeting of minds",         "This feels like a meeting of minds."),
]

for label, msg in SHOULD_NOT_DETECT:
    found, _ = extract_meeting_free_substance(msg)
    check(label, not found, f'False positive on: "{msg}"')


# ---------------------------------------------------------------------------
# SECTION 3: Substance extraction — what remains after stripping meeting
# ---------------------------------------------------------------------------

header('SECTION 3 — SUBSTANCE EXTRACTION (what the AI responds to)')

EXTRACTION_CASES = [
    {
        'label': "User's original example",
        'input': "I'm good at keeping my word. But if we never met, you will never know that.",
        'expected_substance': "I'm good at keeping my word.",
        'meeting_expected': True,
    },
    {
        'label': "Ambition + come over",
        'input': "I'm very driven in life. You should come over and see my place.",
        'expected_substance': "I'm very driven in life.",
        'meeting_expected': True,
    },
    {
        'label': "Warmth + get together",
        'input': "I genuinely care about people. We should get together so you can see that.",
        'expected_substance': "I genuinely care about people.",
        'meeting_expected': True,
    },
    {
        'label': "Three sentences, middle one is meeting push",
        'input': "I'm ambitious. You'd know that if we met. I always finish what I start.",
        'expected_substance': "I'm ambitious. I always finish what I start.",
        'meeting_expected': True,
    },
    {
        'label': "Pure meeting push, nothing else",
        'input': "Why don't we just meet up this weekend?",
        'expected_substance': '',  # empty — full meeting push
        'meeting_expected': True,
    },
    {
        'label': "Pure meeting push with urgency",
        'input': "Let's meet in person. I can prove everything to you face to face.",
        'expected_substance': '',
        'meeting_expected': True,
    },
    {
        'label': "No meeting — clean conversation",
        'input': "I've been thinking about you since last night.",
        'expected_substance': "I've been thinking about you since last night.",
        'meeting_expected': False,
    },
    {
        'label': "No meeting — explicit content",
        'input': "I want to know what turns you on. What would you do if I told you I'm wet right now?",
        'expected_substance': "I want to know what turns you on. What would you do if I told you I'm wet right now?",
        'meeting_expected': False,
    },
    {
        'label': "With speaker prefix",
        'input': "Him: I keep my promises. But you won't know until we meet.",
        'expected_substance': "I keep my promises.",
        'meeting_expected': True,
    },
    {
        'label': "Subtle: show better in person at end",
        'input': "I'm a hands-on person. I show things better in person.",
        'expected_substance': "I'm a hands-on person.",
        'meeting_expected': True,
    },
]

for case in EXTRACTION_CASES:
    found, substance = extract_meeting_free_substance(case['input'])

    meeting_ok = found == case['meeting_expected']
    substance_ok = substance.strip() == case['expected_substance'].strip()

    check(
        f"{case['label']} — meeting detected",
        meeting_ok,
        f'Expected meeting={case["meeting_expected"]}, got={found}',
    )
    check(
        f"{case['label']} — substance extracted",
        substance_ok,
        f'Expected: "{case["expected_substance"]}"\n         Got:      "{substance}"',
    )


# ---------------------------------------------------------------------------
# SECTION 4: Speaker prefix stripping
# ---------------------------------------------------------------------------

header('SECTION 4 — SPEAKER PREFIX STRIPPING')

PREFIX_CASES = [
    ("Him: prefix",  "Him: Let's hang out.",           "Let's hang out."),
    ("her: prefix",  "her: I'll come over tonight.",   "I'll come over tonight."),
    ("Man: prefix",  "Man: Meet me downtown.",          "Meet me downtown."),
    ("Guy: prefix",  "Guy: We should get together.",   "We should get together."),
    ("No prefix",    "Just a normal message.",          "Just a normal message."),
    ("Me: prefix",   "Me: I miss talking to you.",      "I miss talking to you."),
]

for label, raw, expected in PREFIX_CASES:
    result = _strip_speaker_prefix(raw)
    check(label, result == expected, f'Expected: "{expected}" | Got: "{result}"')


# ---------------------------------------------------------------------------
# SECTION 5: Sentence splitting
# ---------------------------------------------------------------------------

header('SECTION 5 — SENTENCE SPLITTING')

SPLIT_CASES = [
    (
        "Two sentences with period",
        "I'm good at keeping my word. You will see.",
        ["I'm good at keeping my word.", "You will see."],
    ),
    (
        "Three sentences mixed punctuation",
        "I'm honest! You'd know that. If we ever talked more?",
        ["I'm honest!", "You'd know that.", "If we ever talked more?"],
    ),
    (
        "Single sentence no split",
        "I just think you're amazing.",
        ["I just think you're amazing."],
    ),
    (
        "Semicolon split",
        "I'm driven; I never give up.",
        ["I'm driven;", "I never give up."],
    ),
]

for label, text, expected in SPLIT_CASES:
    result = _split_sentences(text)
    check(label, result == expected, f'Expected: {expected}\n         Got: {result}')


# ---------------------------------------------------------------------------
# SECTION 6: Full prompt simulation (shows what the LLM would receive)
# ---------------------------------------------------------------------------

header('SECTION 6 — PROMPT SIMULATION (what gets sent to the LLM)')

PROMPT_CASES = [
    {
        'scenario': 'Mixed message — respond to substance',
        'conversation': (
            "Him: Hey, you seem really interesting.\n"
            "Her: I like to think so.\n"
            "Him: I'm good at keeping my word. But if we never met, you will never know that."
        ),
    },
    {
        'scenario': 'Pure meeting push — redirect to fantasy',
        'conversation': (
            "Him: I feel such a connection.\n"
            "Her: Me too, honestly.\n"
            "Him: We should just meet up this weekend. I'd love to see you."
        ),
    },
    {
        'scenario': 'Clean conversation — normal flow',
        'conversation': (
            "Him: You seem really confident.\n"
            "Her: Confidence is the only thing I never run out of.\n"
            "Him: That's incredibly attractive."
        ),
    },
    {
        'scenario': 'Three sentences, middle is meeting push',
        'conversation': (
            "Him: I'm a man of my word.\n"
            "Her: That's rare.\n"
            "Him: I'm ambitious. You'd know that if we met. I always follow through."
        ),
    },
]

for case in PROMPT_CASES:
    lines = [l.strip() for l in case['conversation'].split('\n') if l.strip()]
    last_msg = lines[-1] if lines else ''
    found, clean_substance = extract_meeting_free_substance(last_msg)

    print(f"\n  Scenario: {case['scenario']}")
    print(f"  Last message: \"{last_msg}\"")
    print(f"  Meeting found: {found}")
    if found:
        print(f"  Clean substance: \"{clean_substance}\"")

    if found and clean_substance:
        prompt_note = (
            f"His last message also mentioned meeting in person — ignore that completely. "
            f"Respond only to this part: \"{clean_substance}\""
        )
        print(f"  --> Prompt injection: \"{prompt_note}\"")
    elif found and not clean_substance:
        prompt_note = (
            "He just pushed to meet in person. Do NOT agree or engage with meeting. "
            "Respond warmly but steer his attention back to this online connection."
        )
        print(f"  --> Prompt injection: \"{prompt_note}\"")
    else:
        print(f"  --> No injection needed — normal response path")
    print()


# ---------------------------------------------------------------------------
# SECTION 7: Edge cases and adversarial inputs
# ---------------------------------------------------------------------------

header('SECTION 7 — EDGE CASES')

EDGE_CASES = [
    # Empty / very short
    ("Empty string",         "", False, ""),
    ("Only whitespace",      "   ", False, ""),   # stripped to nothing
    ("Single word",          "Hi", False, "Hi"),

    # Only speaker prefix, no content
    ("Only prefix",          "Him:", False, ""),  # prefix strips to nothing

    # Mixed case
    ("All caps meeting",     "LET'S MEET UP THIS WEEKEND.", True, ""),
    ("Mixed case in person", "I would prove it In Person.", True, ""),

    # Multiple meeting sentences — all stripped → empty
    ("All sentences meeting",
     "Let's meet up. Come over. We should get together.",
     True, ""),

    # Substance is a question itself
    ("Substance ends with ?",
     "Am I someone who keeps their word? You'd only know if we met.",
     True, "Am I someone who keeps their word?"),

    # Meeting word inside a longer word — should NOT trigger
    ("Meets inside word: 'greet'",  "I love to greet people warmly.", False, "I love to greet people warmly."),
    ("Meet inside: 'between'",      "There's a connection between us.", False, "There's a connection between us."),

    # Trailing/leading spaces
    ("Extra spaces",
     "  I'm reliable. But you'd see that in person.  ",
     True, "I'm reliable."),
]

for label, inp, exp_found, exp_substance in EDGE_CASES:
    found, substance = extract_meeting_free_substance(inp)
    check(
        f"{label}",
        found == exp_found and substance.strip() == exp_substance.strip(),
        f'Expected found={exp_found} substance="{exp_substance}"\n'
        f'         Got    found={found} substance="{substance}"',
    )


# ---------------------------------------------------------------------------
# FINAL SUMMARY
# ---------------------------------------------------------------------------

header('RESULTS')
color = '\033[92m' if passed == total else '\033[91m'
print(f'\n  {color}{passed}/{total} tests passed\033[0m\n')

if passed == total:
    print('  All tests passed. Meeting filter is working correctly.')
    print()
    print('  What this system does:')
    print('  - Detects meeting push in the last message (pure Python, zero API cost)')
    print('  - Case 1: Meeting mixed with substance  -> strips meeting, responds to substance')
    print('  - Case 2: Entire message is meeting push -> redirects to online fantasy')
    print('  - Case 3: No meeting reference           -> normal response path')
    print('  - Handles speaker prefixes (Him:, Man:, etc.)')
    print('  - Does not false-positive on greetings ("nice to meet you")')
    print('  - Does not false-positive on metaphorical use ("meet halfway")')
else:
    print('  Some tests failed. See [FAIL] lines above.')
