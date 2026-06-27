# -*- coding: utf-8 -*-
"""
Question Focus Filter — Standalone Test
========================================
Tests the pure-Python multiple-question detection and best-question selection,
including all 5 combination cases with the meeting filter.

No Django, no OpenAI, no credentials needed.
Run: py test_question_focus.py
"""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


# ---------------------------------------------------------------------------
# Copy exact logic from intent_detector.py
# ---------------------------------------------------------------------------

# ── Meeting filter (copied from intent_detector.py) ──────────────────────

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


# ── Question focus (copied from intent_detector.py) ──────────────────────

_HIGH_Q_PATTERNS = [
    r'\bwhat\s+kind\s+of\s+(woman|person|girl|lady|man)\b',
    r'\bwho\s+(are|were)\s+you\b',
    r'\bwhat\s+(drives|motivates|excites|defines|makes)\s+you\b',
    r'\bwhat\s+do\s+you\s+(value|believe|stand\s+for|care\s+about)\b',
    r'\bwhat\s+are\s+you\s+(really|truly|actually|like|about)\b',
    r'\btell\s+me\s+(about\s+yourself|something\s+real|something\s+deep|something\s+personal)\b',
    r'\bwhat\s+(scares|excites|moves|inspires|gets\s+to)\s+you\b',
    r'\bwhat\s+do\s+you\s+(fear|dream\s+about|long\s+for|wish\s+for)\b',
    r'\bwhat\s+makes\s+you\s+(happy|sad|angry|vulnerable|tick)\b',
    r'\bwhat\s+(do\s+you\s+feel|are\s+you\s+feeling|feeling\s+right\s+now)\b',
    r'\bwhat\s+(turns|gets)\s+you\s+on\b',
    r'\bwhat\s+do\s+you\s+(like|enjoy|prefer|love)\s+(in\s+bed|sexually|intimately)\b',
    r'\bhow\s+do\s+you\s+like\s+(it|to\s+be\s+(touched|held|treated))\b',
    r'\bwhat\s+is\s+your\s+(?:\w+\s+)?(fantasy|dream|desire)\b',
    r'\bwhat\s+are\s+you\s+(into|craving|thinking\s+about|passionate\s+about)\b',
    r'\bwhat\s+(are\s+you\s+looking\s+for|do\s+you\s+want\s+in|do\s+you\s+need)\b',
    r'\bwhat\s+do\s+you\s+(want|need|expect)\s+(from\s+a\s+man|in\s+a\s+(relationship|partner))\b',
    r'\bwhat\s+(would\s+you\s+do|do\s+you\s+think\s+about|do\s+you\s+imagine)\b',
    r'\bhow\s+(would\s+you|do\s+you)\s+(describe\s+yourself|handle|deal)\b',
]
_LOW_Q_PATTERNS = [
    r'\bwhere\s+do\s+you\s+(live|stay|reside)\b',
    r'\bwhat\s+do\s+you\s+do\s+(for\s+work|for\s+a\s+living|as\s+a\s+job)\b',
    r'\bhow\s+old\s+are\s+you\b',
    r'\bdo\s+you\s+(cook|drive|smoke|drink|work\s+out|exercise)\b',
    r'\bare\s+you\s+single\b',
    r'\bdo\s+you\s+have\s+kids\b',
    r'\bwhere\s+are\s+you\s+from\b',
    r'\bwhat\'s\s+your\s+(job|number|instagram|snap|whatsapp|tiktok)\b',
    r'\bwhat\s+city\s+(are\s+you\s+in|do\s+you\s+live\s+in)\b',
    r'\bhow\s+tall\s+are\s+you\b',
    r'\bwhat\s+do\s+you\s+look\s+like\b',
    r'\bare\s+you\s+busy\b',
    r'\bwhat\s+time\s+(is\s+it|do\s+you)\b',
]

def _score_question(question):
    q = question.lower()
    score = 1
    if any(re.search(p, q) for p in _HIGH_Q_PATTERNS):
        score += 3
    if any(re.search(p, q) for p in _LOW_Q_PATTERNS):
        score -= 2
    if 'you' in q:
        score += 1
    if len(question) > 35:
        score += 1
    return max(score, 0)

def extract_best_question(text):
    sentences = _split_sentences(text)
    questions = [s for s in sentences if s.rstrip().endswith('?')]
    if len(questions) <= 1:
        return False, text
    scored = [(_score_question(q), q) for q in questions]
    best_score = max(s for s, _ in scored)
    best = [q for s, q in scored if s == best_score][-1]
    return True, best


# ── Prompt builder (mirrors generate_context_aware_response logic) ────────

def build_prompt(conversation, topic='general', tone='casual'):
    """
    Simulates exactly what generate_context_aware_response builds.
    Returns (prompt_str, flags_dict) without making any API call.
    """
    lines = [l.strip() for l in conversation.split('\n') if l.strip()]
    last_msg = lines[-1] if lines else ''
    meeting_found, clean_substance = extract_meeting_free_substance(last_msg)
    working = clean_substance if meeting_found else _strip_speaker_prefix(last_msg)
    multi_q_found, best_q = extract_best_question(working) if working else (False, '')

    base = f"Conversation (topic: {topic}, tone: {tone}):\n\n{conversation}\n\n"

    if meeting_found and not working:
        injection = (
            "He just pushed to meet in person. Do NOT agree or engage with meeting. "
            "Steer his attention back to this online connection — "
            "make it feel more exciting than any real meeting ever could.\n\n"
            "Write the woman's next reply."
        )
        case = 'FULL_MEETING_REDIRECT'
    elif meeting_found and multi_q_found:
        injection = (
            f"His last message mentioned meeting in person — ignore that completely. "
            f"He also asked several questions — respond only to this one: \"{best_q}\"\n\n"
            "Write the woman's next reply."
        )
        case = 'MEETING_STRIPPED_MULTI_Q'
    elif meeting_found:
        injection = (
            f"His last message mentioned meeting in person — ignore that completely. "
            f"Respond only to this part: \"{working}\"\n\n"
            "Write the woman's next reply."
        )
        case = 'MEETING_STRIPPED_SINGLE'
    elif multi_q_found:
        injection = (
            f"He asked several questions. Respond only to this one: \"{best_q}\"\n\n"
            "Write the woman's next reply."
        )
        case = 'MULTI_Q_NO_MEETING'
    else:
        injection = "Write the woman's next reply."
        case = 'NORMAL'

    prompt = base + injection

    return prompt, {
        'case': case,
        'meeting_found': meeting_found,
        'clean_substance': clean_substance,
        'multi_q_found': multi_q_found,
        'best_q': best_q,
        'injection': injection,  # instruction portion only (not conversation history)
    }


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


# ---------------------------------------------------------------------------
# SECTION 1: Question scoring — does each question get the right score?
# ---------------------------------------------------------------------------

header('SECTION 1 — QUESTION SCORING')

HIGH_VALUE_QUESTIONS = [
    ("Identity question",          "What kind of woman are you really?"),
    ("Character depth",            "What drives you in life?"),
    ("Emotional depth",            "What makes you happy?"),
    ("Fear/vulnerability",         "What scares you the most?"),
    ("Self description",           "How would you describe yourself?"),
    ("Values",                     "What do you value in a person?"),
    ("Sexual preference",          "What turns you on?"),
    ("Fantasy",                    "What is your deepest fantasy?"),
    ("Relationship intent",        "What are you looking for in a man?"),
    ("Desire",                     "What do you want in a relationship?"),
    ("Imagination",                "What would you do if I were there?"),
    ("Craving",                    "What are you craving right now?"),
]

LOW_VALUE_QUESTIONS = [
    ("Where do you live",          "Where do you live?"),
    ("Work/job",                   "What do you do for work?"),
    ("Age",                        "How old are you?"),
    ("Do you cook",                "Do you cook?"),
    ("Single check",               "Are you single?"),
    ("Kids",                       "Do you have kids?"),
    ("Where from",                 "Where are you from?"),
    ("Instagram",                  "What's your instagram?"),
    ("City",                       "What city are you in?"),
    ("Height",                     "How tall are you?"),
]

print('\n  High-value questions (score > 2 expected):')
for label, q in HIGH_VALUE_QUESTIONS:
    score = _score_question(q)
    check(f'{label} (score={score})', score > 2, f'Question: "{q}"')

print('\n  Low-value questions (score <= 2 expected):')
for label, q in LOW_VALUE_QUESTIONS:
    score = _score_question(q)
    check(f'{label} (score={score})', score <= 2, f'Question: "{q}"')


# ---------------------------------------------------------------------------
# SECTION 2: Best question selection — picks the right one?
# ---------------------------------------------------------------------------

header('SECTION 2 — BEST QUESTION SELECTION')

SELECTION_CASES = [
    {
        'label': "User's original example — 3 questions, pick the personal one",
        'text': "What kind of woman are you really? Do you cook? And what do you do for fun?",
        'expected_best': "What kind of woman are you really?",
        'multi': True,
    },
    {
        'label': "Personal vs logistical — picks personal",
        'text': "What drives you in life? Where are you from?",
        'expected_best': "What drives you in life?",
        'multi': True,
    },
    {
        'label': "Emotional vs work — picks emotional",
        'text': "What do you do for work? What scares you the most?",
        'expected_best': "What scares you the most?",
        'multi': True,
    },
    {
        'label': "Sexual vs domestic — picks sexual",
        'text': "Do you cook? What turns you on?",
        'expected_best': "What turns you on?",
        'multi': True,
    },
    {
        'label': "All high-value — picks last (most recent)",
        'text': "What kind of woman are you? What drives you? What are you craving right now?",
        'expected_best': "What are you craving right now?",
        'multi': True,
    },
    {
        'label': "All low-value — picks last (most recent)",
        'text': "Where do you live? How old are you? Do you cook?",
        'expected_best': "Do you cook?",
        'multi': True,
    },
    {
        'label': "Single question — no selection needed",
        'text': "What kind of woman are you?",
        'expected_best': "What kind of woman are you?",
        'multi': False,
    },
    {
        'label': "No question at all — no selection",
        'text': "I'm a very confident man.",
        'expected_best': "I'm a very confident man.",
        'multi': False,
    },
    {
        'label': "Statement + one question — no selection (only 1 question)",
        'text': "I keep my promises. What do you think about that?",
        'expected_best': "I keep my promises. What do you think about that?",
        'multi': False,
    },
    {
        'label': "Fantasy question beats generic",
        'text': "Are you free later? What is your deepest fantasy?",
        'expected_best': "What is your deepest fantasy?",
        'multi': True,
    },
    {
        'label': "Relationship intent beats where are you from",
        'text': "Where are you from? What are you looking for in a man?",
        'expected_best': "What are you looking for in a man?",
        'multi': True,
    },
    {
        'label': "With speaker prefix — still selects correctly",
        'text': "Him: What drives you? Do you have kids? What do you value?",
        'expected_best': "What do you value?",
        'multi': True,
    },
]

for case in SELECTION_CASES:
    multi, best = extract_best_question(_strip_speaker_prefix(case['text']))
    check(
        f"{case['label']} — multi={multi}",
        multi == case['multi'] and best.strip() == case['expected_best'].strip(),
        f"Expected multi={case['multi']} best=\"{case['expected_best']}\"\n"
        f"         Got    multi={multi}  best=\"{best}\"",
    )


# ---------------------------------------------------------------------------
# SECTION 3: All 5 combination cases with meeting filter
# ---------------------------------------------------------------------------

header('SECTION 3 — ALL 5 COMBINATION CASES')

# Case 1: NORMAL — no meeting, single/no question
print('\n  Case 1: NORMAL (no meeting, no multi-question)')
_, flags = build_prompt(
    "Him: You seem very confident\n"
    "Her: Confidence is the only thing I never run out of\n"
    "Him: That is incredibly attractive"
)
check('Case NORMAL detected', flags['case'] == 'NORMAL')
check('No meeting found', not flags['meeting_found'])
check('No multi-question found', not flags['multi_q_found'])

# Case 2: MULTI_Q_NO_MEETING
print('\n  Case 2: MULTI_Q_NO_MEETING (no meeting, multiple questions)')
_, flags = build_prompt(
    "Him: You are interesting\n"
    "Her: I know\n"
    "Him: What kind of woman are you really? Do you cook? And what do you do for fun?"
)
check('Case MULTI_Q_NO_MEETING detected', flags['case'] == 'MULTI_Q_NO_MEETING')
check('No meeting found', not flags['meeting_found'])
check('Multi-question found', flags['multi_q_found'])
check('Best question is identity question', flags['best_q'] == 'What kind of woman are you really?')

# Case 3: MEETING_STRIPPED_SINGLE
print('\n  Case 3: MEETING_STRIPPED_SINGLE (meeting + single clean substance)')
_, flags = build_prompt(
    "Him: I noticed you\n"
    "Her: Good\n"
    "Him: I'm good at keeping my word. But if we never met, you will never know that."
)
check('Case MEETING_STRIPPED_SINGLE detected', flags['case'] == 'MEETING_STRIPPED_SINGLE')
check('Meeting found', flags['meeting_found'])
check('Clean substance correct', flags['clean_substance'] == "I'm good at keeping my word.")
check('No multi-question', not flags['multi_q_found'])

# Case 4: MEETING_STRIPPED_MULTI_Q
print('\n  Case 4: MEETING_STRIPPED_MULTI_Q (meeting + multiple questions in substance)')
_, flags = build_prompt(
    "Him: I like you\n"
    "Her: I know\n"
    "Him: What drives you? What kind of woman are you? We should meet up sometime."
)
check('Case MEETING_STRIPPED_MULTI_Q detected', flags['case'] == 'MEETING_STRIPPED_MULTI_Q')
check('Meeting found', flags['meeting_found'])
check('Multi-question found', flags['multi_q_found'])
check('Meeting sentence removed from substance', 'meet up' not in flags['clean_substance'])
check('Best question is high-value', flags['best_q'] in ('What drives you?', 'What kind of woman are you?'))

# Case 5: FULL_MEETING_REDIRECT
print('\n  Case 5: FULL_MEETING_REDIRECT (entire last message is meeting push)')
_, flags = build_prompt(
    "Him: I feel such a connection\n"
    "Her: Me too\n"
    "Him: We should just meet up. Come over to my place this weekend."
)
check('Case FULL_MEETING_REDIRECT detected', flags['case'] == 'FULL_MEETING_REDIRECT')
check('Meeting found', flags['meeting_found'])
check('Clean substance is empty', flags['clean_substance'] == '')
check('No multi-question (nothing to score)', not flags['multi_q_found'])


# ---------------------------------------------------------------------------
# SECTION 4: Prompt injection — what exactly gets sent to the LLM
# ---------------------------------------------------------------------------

header('SECTION 4 — PROMPT INJECTION (what the LLM sees)')

PROMPT_CASES = [
    {
        'scenario': 'Three questions — only best survives',
        'conversation': (
            "Him: Hey you seem interesting\n"
            "Her: I try\n"
            "Him: What kind of woman are you really? Do you cook? And what do you do for fun?"
        ),
        'must_contain': 'What kind of woman are you really?',
        # "Do you cook" stays in conversation history (correct) — check injection only
        'must_not_contain': 'Do you cook',
        'check_injection_only': True,
    },
    {
        'scenario': 'Meeting + questions — both handled',
        'conversation': (
            "Him: I really like you\n"
            "Her: Tell me more\n"
            "Him: What drives you? What do you value? Let's meet up."
        ),
        'must_contain': 'ignore that completely',
        # "meet up" stays in conversation history (correct) — check injection only
        'must_not_contain': 'meet up',
        'check_injection_only': True,
    },
    {
        'scenario': 'Full meeting push — redirect to fantasy',
        'conversation': (
            "Him: I want to see you\n"
            "Her: Why\n"
            "Him: Let's just hang out in person. Come over."
        ),
        'must_contain': 'Do NOT agree',
        'must_not_contain': None,
    },
    {
        'scenario': 'Normal conversation — no injection',
        'conversation': (
            "Him: You are confident\n"
            "Her: Always\n"
            "Him: That energy is rare."
        ),
        'must_contain': 'Write the woman',
        'must_not_contain': 'ignore',
    },
    {
        'scenario': 'Single quality statement — no injection',
        'conversation': (
            "Him: You make me smile\n"
            "Her: I know\n"
            "Him: What is it about you that feels different?"
        ),
        'must_contain': 'Write the woman',
        'must_not_contain': 'several questions',
    },
]

for case in PROMPT_CASES:
    prompt, flags = build_prompt(case['conversation'])
    ok1 = case['must_contain'] in prompt
    check_target = flags['injection'] if case.get('check_injection_only') else prompt
    ok2 = case['must_not_contain'] not in check_target if case.get('must_not_contain') else True
    print(f'\n  Scenario: {case["scenario"]}')
    print(f'  Case:     {flags["case"]}')
    if flags['meeting_found']:
        print(f'  Meeting stripped, substance: "{flags["clean_substance"]}"')
    if flags['multi_q_found']:
        print(f'  Best question selected: "{flags["best_q"]}"')
    print(f'  Injection: {"..." + prompt[-200:].strip() if len(prompt) > 200 else prompt.strip()}')
    check('Prompt contains expected instruction', ok1, f'Looking for: "{case["must_contain"]}"')
    if case['must_not_contain']:
        check('Prompt excludes unwanted content', ok2, f'Should not contain: "{case["must_not_contain"]}"')


# ---------------------------------------------------------------------------
# SECTION 5: Edge cases
# ---------------------------------------------------------------------------

header('SECTION 5 — EDGE CASES')

# Empty and minimal
multi, best = extract_best_question('')
check('Empty text — no multi-q', not multi)

multi, best = extract_best_question('Hi?')
check('Single very short question — no selection', not multi)

# Questions without ? at end — not counted as questions
multi, best = extract_best_question(
    "Tell me about yourself. What kind of woman are you"  # no ? on second
)
check('Question without ? not counted', not multi)

# Two identical questions — picks last
multi, best = extract_best_question("Are you free later? Are you free later?")
check('Two identical questions — returns last', multi and best == 'Are you free later?')

# Mixed: statement + two questions
multi, best = extract_best_question(
    "I'm ambitious. What drives you? How old are you?"
)
check('Statement + two questions — finds multi', multi)
check('Statement + two questions — picks high-value', best == 'What drives you?')

# All questions in meeting sentence — should be empty after meeting filter
meeting_found, substance = extract_meeting_free_substance(
    "Should we meet up? Come over? Get together sometime?"
)
multi, best = extract_best_question(substance) if substance else (False, '')
check('All questions in meeting sentence — substance empty after filter', substance == '')
check('No questions to score when substance is empty', not multi)

# Questions spread across meeting and non-meeting sentences
meeting_found, substance = extract_meeting_free_substance(
    "What drives you? Let's meet up. What do you value?"
)
multi, best = extract_best_question(substance) if substance else (False, '')
check('Questions split across meeting/non-meeting — only clean questions scored', multi)
check('Meeting question excluded, substance has 2 clean questions', 'meet up' not in substance)

# Speaker prefix on message with multiple questions
msg = "Him: What kind of woman are you really? Do you cook? What do you value?"
stripped = _strip_speaker_prefix(msg)
multi, best = extract_best_question(stripped)
check('Speaker prefix stripped before scoring', multi)
check('Best question correct after prefix strip', best in ('What kind of woman are you really?', 'What do you value?'))

# Single question with meeting in same message — no multi-q after filter
meeting_found, substance = extract_meeting_free_substance(
    "I'm a man of my word. What drives you? But we should meet up."
)
multi, best = extract_best_question(substance) if substance else (False, '')
check('Single question after meeting stripped — no multi-q trigger', not multi)
check('That single question becomes the substance', 'What drives you?' in substance)


# ---------------------------------------------------------------------------
# SECTION 6: Realistic full conversations
# ---------------------------------------------------------------------------

header('SECTION 6 — REALISTIC FULL CONVERSATIONS')

REAL_CONVOS = [
    {
        'label': 'Dating app opener, multiple questions in last message',
        'conversation': (
            "Him: Just matched with you, you look interesting\n"
            "Her: That's a start\n"
            "Him: Haha fair enough. So what kind of woman are you? Do you cook? Are you single?"
        ),
        'expected_case': 'MULTI_Q_NO_MEETING',
        'expected_best_contains': 'kind of woman',
    },
    {
        'label': 'Emotional escalation, single quality + meeting push',
        'conversation': (
            "Him: I've never talked to anyone like you\n"
            "Her: That's because there's no one like me\n"
            "Him: I believe that. I'm a very loyal person. If we met you'd know."
        ),
        'expected_case': 'MEETING_STRIPPED_SINGLE',
        'expected_best_contains': None,
    },
    {
        'label': 'Sexual escalation, single question, no meeting',
        'conversation': (
            "Him: I've been thinking about you\n"
            "Her: Tell me\n"
            "Him: What turns you on?"
        ),
        'expected_case': 'NORMAL',
        'expected_best_contains': None,
    },
    {
        'label': 'Three questions, one of them has meeting in it',
        'conversation': (
            "Him: I'm curious about you\n"
            "Her: Ask away\n"
            "Him: What drives you? Should we meet up? What do you value in life?"
        ),
        'expected_case': 'MEETING_STRIPPED_MULTI_Q',
        'expected_best_contains': 'value',
    },
    {
        'label': 'Full meeting push — nothing else in last message',
        'conversation': (
            "Him: This connection feels real\n"
            "Her: It is\n"
            "Him: We should get together. Come over this weekend."
        ),
        'expected_case': 'FULL_MEETING_REDIRECT',
        'expected_best_contains': None,
    },
    {
        'label': 'Man compliments then asks multiple questions',
        'conversation': (
            "Him: You are very confident\n"
            "Her: Confidence is my natural state\n"
            "Him: I love that. What makes you this way? Where are you from? How old are you?"
        ),
        'expected_case': 'MULTI_Q_NO_MEETING',
        'expected_best_contains': 'makes you this way',
    },
]

for case in REAL_CONVOS:
    _, flags = build_prompt(case['conversation'])
    case_ok = flags['case'] == case['expected_case']
    best_ok = (
        case['expected_best_contains'] in flags['best_q']
        if case['expected_best_contains']
        else True
    )
    check(
        f"{case['label']} — case={flags['case']}",
        case_ok and best_ok,
        f"Expected case={case['expected_case']}, got={flags['case']}\n"
        f"         Expected best contains \"{case['expected_best_contains']}\", got \"{flags['best_q']}\"",
    )


# ---------------------------------------------------------------------------
# FINAL RESULTS
# ---------------------------------------------------------------------------

header('RESULTS')
color = '\033[92m' if passed == total else '\033[91m'
print(f'\n  {color}{passed}/{total} tests passed\033[0m\n')

if passed == total:
    print('  All tests passed.\n')
    print('  What this adds to the system:')
    print()
    print('  5 prompt paths (all decided in pure Python, zero cost):')
    print()
    print('  NORMAL              - No meeting, 0-1 questions → clean reply')
    print('  MULTI_Q_NO_MEETING  - No meeting, 2+ questions  → focus on best question')
    print('  MEETING_STRIPPED_SINGLE - Meeting + 1 substance → ignore meeting')
    print('  MEETING_STRIPPED_MULTI_Q - Meeting + 2+ q in substance → ignore meeting + focus best q')
    print('  FULL_MEETING_REDIRECT   - Entire message = meeting → redirect to fantasy')
    print()
    print('  Question scoring:')
    print('  HIGH: identity, emotion, intimacy, relationship intent → +3')
    print('  LOW:  logistics, domestic, basic facts                 → -2')
    print('  Tiebreaker: last question wins (most recent in his mind)')
else:
    print('  Some tests failed — see [FAIL] lines above.')
