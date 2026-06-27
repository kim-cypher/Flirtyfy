# -*- coding: utf-8 -*-
"""
Variety Injection — Brutal Test Suite
======================================
Tests the recent_replies / avoid-block feature added to
generate_context_aware_response().

Covers:
  1.  Avoid block construction (exact strings, bullets, endings)
  2.  All 5 prompt cases WITH avoid block
  3.  All 5 prompt cases WITHOUT avoid block (regression)
  4.  List truncation — strictly capped at 3
  5.  Edge cases (empty string, None values, special chars, emoji, newlines)
  6.  Prompt structure / positional order (brutal)
  7.  Triple filter combination (meeting + multi_q + recent_replies)
  8.  Redis session simulation (views.py logic, no real Redis needed)
  9.  Realistic reply histories — stress tests
  10. Cross-contamination guard (two users)
  11. Instruction wording — exact text checks
  12. "Write the woman's next reply." is always the final token

No Django, no OpenAI, no Redis required.
Run: py test_variety_injection.py
"""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ─────────────────────────────────────────────────────────────────────────────
# Replicate exact logic from intent_detector.py  (keep in sync manually)
# ─────────────────────────────────────────────────────────────────────────────

_MEETING_PATTERNS = [
    r'\bmeet\s+(you|me|us|up|in\s*person|somewhere|each\s+other|for\s+(coffee|drinks|dinner|lunch|a\s+date))\b',
    r'\bmeeting\s+(you|me|us|up|in\s*person|each\s+other)\b',
    r'\bif\s+(we\s+)?(ever\s+|never\s+|could\s+|would\s+)?met\b',
    r'\bif\s+(we\s+)?(ever\s+|could\s+|would\s+|finally\s+)?meet\b',
    r'\bwhen\s+(we\s+)?(finally\s+|eventually\s+|do\s+|can\s+)?meet\b',
    r'\b(before|after|until|once|unless)\s+(we\s+)?meet\b',
    r'\bnever\s+met\b', r'\bhaven\'t\s+met\b', r'\bnot\s+yet\s+met\b',
    r'\byet\s+to\s+meet\b', r'\bin\s+person\b', r'\bface[\s\-]to[\s\-]face\b',
    r'\bcome\s+over\b', r'\bcome\s+to\s+(my|your)\b', r'\bvisit\s+(me|you)\b',
    r'\bsee\s+each\s+other\b', r'\bsee\s+(you|me)\s+in\s*person\b',
    r'\bget\s+together\b', r'\bhang\s+out\b', r'\blink\s+up\b',
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
    r'\bare\s+you\s+single\b', r'\bdo\s+you\s+have\s+kids\b',
    r'\bwhere\s+are\s+you\s+from\b',
    r'\bwhat\'s\s+your\s+(job|number|instagram|snap|whatsapp|tiktok)\b',
    r'\bwhat\s+city\s+(are\s+you\s+in|do\s+you\s+live\s+in)\b',
    r'\bhow\s+tall\s+are\s+you\b', r'\bwhat\s+do\s+you\s+look\s+like\b',
    r'\bare\s+you\s+busy\b', r'\bwhat\s+time\s+(is\s+it|do\s+you)\b',
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

# ── Exact constants from intent_detector.py ───────────────────────────────────
AVOID_HEADER = (
    "Your last few replies — vary the opening energy or question style, "
    "don't echo the same angle:\n"
)
WRITE_INSTRUCTION = "Write the woman's next reply."

def _build_avoid(recent_replies):
    """Mirrors Step 4 in generate_context_aware_response."""
    if not recent_replies:
        return ''
    return (
        AVOID_HEADER
        + "\n".join(f"• {r}" for r in recent_replies[:3])
        + "\n\n"
    )

def build_prompt(conversation, topic='general', tone='casual', recent_replies=None):
    """
    Full mirror of generate_context_aware_response() prompt-building logic.
    Returns (prompt, flags) — no API call.
    """
    lines = [l.strip() for l in conversation.split('\n') if l.strip()]
    last_msg = lines[-1] if lines else ''
    meeting_found, clean_substance = extract_meeting_free_substance(last_msg)
    working = clean_substance if meeting_found else _strip_speaker_prefix(last_msg)
    multi_q_found, best_q = extract_best_question(working) if working else (False, '')

    avoid = _build_avoid(recent_replies)
    base = f"Conversation (topic: {topic}, tone: {tone}):\n\n{conversation}\n\n"

    if meeting_found and not working:
        case_instr = (
            "He just pushed to meet in person. Do NOT agree or engage with meeting. "
            "Steer his attention back to this online connection — "
            "make it feel more exciting than any real meeting ever could.\n\n"
        )
        case = 'FULL_MEETING_REDIRECT'
    elif meeting_found and multi_q_found:
        case_instr = (
            f"His last message mentioned meeting in person — ignore that completely. "
            f"He also asked several questions — respond only to this one: \"{best_q}\"\n\n"
        )
        case = 'MEETING_STRIPPED_MULTI_Q'
    elif meeting_found:
        case_instr = (
            f"His last message mentioned meeting in person — ignore that completely. "
            f"Respond only to this part: \"{working}\"\n\n"
        )
        case = 'MEETING_STRIPPED_SINGLE'
    elif multi_q_found:
        case_instr = (
            f"He asked several questions. Respond only to this one: \"{best_q}\"\n\n"
        )
        case = 'MULTI_Q_NO_MEETING'
    else:
        case_instr = ''
        case = 'NORMAL'

    prompt = base + case_instr + avoid + WRITE_INSTRUCTION

    return prompt, {
        'case': case,
        'meeting_found': meeting_found,
        'clean_substance': clean_substance,
        'multi_q_found': multi_q_found,
        'best_q': best_q,
        'avoid': avoid,
        'case_instr': case_instr,
        'base': base,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Redis session simulation  (mirrors views.py logic, no real Redis)
# ─────────────────────────────────────────────────────────────────────────────

def session_read(store, user_id):
    """Mirrors: cache.get(f"user_specific_{user_id}") or {}"""
    return store.get(f"user_specific_{user_id}", {})

def session_write(store, user_id, response_text):
    """Mirrors the Redis write block in GenerateSpecificResponseView."""
    key = f"user_specific_{user_id}"
    s = store.get(key, {})
    prev = s.get('recent_replies', [])
    s['recent_replies'] = ([response_text] + prev)[:3]
    store[key] = s

def session_get_replies(store, user_id):
    s = store.get(f"user_specific_{user_id}", {})
    return s.get('recent_replies', [])


# ─────────────────────────────────────────────────────────────────────────────
# Test harness
# ─────────────────────────────────────────────────────────────────────────────

PASS = '\033[92m[PASS]\033[0m'
FAIL = '\033[91m[FAIL]\033[0m'
WARN = '\033[93m[WARN]\033[0m'
total = passed = 0

def check(label, condition, detail=''):
    global total, passed
    total += 1
    if condition:
        passed += 1
        print(f'  {PASS}  {label}')
    else:
        print(f'  {FAIL}  {label}')
        if detail:
            print(f'         ↳ {detail}')

def warn(label, detail=''):
    """Known edge-case behaviour worth noting but not a hard failure."""
    print(f'  {WARN}  {label}' + (f' — {detail}' if detail else ''))

def header(title):
    print(f'\n{"="*68}')
    print(f'  {title}')
    print(f'{"="*68}')


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Avoid block construction
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 1 — AVOID BLOCK CONSTRUCTION')

# None → empty string
check('None  → avoid is empty string', _build_avoid(None) == '')

# [] → empty string
check('[]    → avoid is empty string', _build_avoid([]) == '')

# Single reply
a1 = _build_avoid(['Reply A'])
check('1 reply → block exists',                  a1 != '')
check('1 reply → header present',               AVOID_HEADER in a1)
check('1 reply → correct bullet',               '• Reply A' in a1)
check('1 reply → ends with double newline',     a1.endswith('\n\n'))
check('1 reply → only one bullet',              a1.count('•') == 1)

# Two replies
a2 = _build_avoid(['Reply A', 'Reply B'])
check('2 replies → 2 bullets',                  a2.count('•') == 2)
check('2 replies → Reply A bullet present',     '• Reply A' in a2)
check('2 replies → Reply B bullet present',     '• Reply B' in a2)
check('2 replies → Reply A before Reply B',     a2.index('Reply A') < a2.index('Reply B'))

# Three replies
a3 = _build_avoid(['R1', 'R2', 'R3'])
check('3 replies → exactly 3 bullets',          a3.count('•') == 3)
check('3 replies → order preserved (R1 first)', a3.index('R1') < a3.index('R2') < a3.index('R3'))

# Exact full string check for 3 replies
expected_3 = (
    AVOID_HEADER +
    "• R1\n• R2\n• R3\n\n"
)
check('3 replies → exact string match',         _build_avoid(['R1', 'R2', 'R3']) == expected_3)

# Four replies — only first 3 used
a4 = _build_avoid(['R1', 'R2', 'R3', 'R4'])
check('4 replies → still 3 bullets',            a4.count('•') == 3)
check('4 replies → R4 NOT in block',            'R4' not in a4)
check('4 replies → R1 R2 R3 present',           all(f'• {r}' in a4 for r in ['R1', 'R2', 'R3']))

# Ten replies — only first 3 used
a10 = _build_avoid([f'Reply{i}' for i in range(10)])
check('10 replies → still 3 bullets',           a10.count('•') == 3)
check('10 replies → only Reply0 Reply1 Reply2', all(f'• Reply{i}' in a10 for i in range(3)))
check('10 replies → Reply3-9 absent',           all(f'Reply{i}' not in a10 for i in range(3, 10)))

# Realistic 100-150 char replies
real1 = "You surprise me every time. What's your move next?"
real2 = "I don't give that away easily. What makes you think you can handle it?"
real3 = "Some things are better felt than explained. What do you feel right now?"
a_real = _build_avoid([real1, real2, real3])
check('Realistic replies → all 3 bullets present',
      all(f'• {r}' in a_real for r in [real1, real2, real3]))

# Emoji preserved
a_emoji = _build_avoid(["You're fire 🔥 What's your secret?"])
check('Emoji in reply → preserved in block', '🔥' in a_emoji)

# Quotes preserved
a_quotes = _build_avoid(['She said "never" but meant something else. Prove her wrong?'])
check('Quotes in reply → preserved', '"never"' in a_quotes)

# Long reply (150 chars) — no truncation by avoid block
long_reply = 'A' * 150
a_long = _build_avoid([long_reply])
check('150-char reply → fully preserved in block', ('• ' + long_reply) in a_long)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — All 5 cases WITH avoid block
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 2 — ALL 5 CASES WITH AVOID BLOCK')

REPLIES_3 = [
    "You surprise me every time. What's your move?",
    "I'm the kind of woman who keeps you guessing. You ready?",
    "Not everyone gets this side of me. What made you different?",
]

# Case NORMAL + avoid
prompt, f = build_prompt(
    "Him: You are confident\nHer: Always\nHim: That energy is rare.",
    recent_replies=REPLIES_3,
)
check('NORMAL+avoid → case is NORMAL',              f['case'] == 'NORMAL')
check('NORMAL+avoid → avoid block present',         AVOID_HEADER in prompt)
check('NORMAL+avoid → all 3 bullets in prompt',     all(f'• {r}' in prompt for r in REPLIES_3))
check('NORMAL+avoid → ends with WRITE_INSTRUCTION', prompt.endswith(WRITE_INSTRUCTION))
check('NORMAL+avoid → avoid directly before WRITE', prompt.endswith(f['avoid'] + WRITE_INSTRUCTION))

# Case MULTI_Q_NO_MEETING + avoid
prompt, f = build_prompt(
    "Him: I like you\nHer: I know\n"
    "Him: What kind of woman are you really? Do you cook? What do you value?",
    recent_replies=REPLIES_3,
)
check('MULTI_Q+avoid → case is MULTI_Q_NO_MEETING',   f['case'] == 'MULTI_Q_NO_MEETING')
check('MULTI_Q+avoid → avoid block present',           AVOID_HEADER in prompt)
check('MULTI_Q+avoid → case instruction present',      'He asked several questions' in prompt)
check('MULTI_Q+avoid → case instruction before avoid',
      prompt.index('He asked several questions') < prompt.index(AVOID_HEADER))
check('MULTI_Q+avoid → ends with WRITE_INSTRUCTION',   prompt.endswith(WRITE_INSTRUCTION))
check('MULTI_Q+avoid → avoid directly before WRITE',   prompt.endswith(f['avoid'] + WRITE_INSTRUCTION))

# Case MEETING_STRIPPED_SINGLE + avoid
prompt, f = build_prompt(
    "Him: I noticed you\nHer: Good\n"
    "Him: I keep my promises. If we never met you would never know.",
    recent_replies=REPLIES_3,
)
check('MTG_SINGLE+avoid → case is MEETING_STRIPPED_SINGLE', f['case'] == 'MEETING_STRIPPED_SINGLE')
check('MTG_SINGLE+avoid → avoid block present',              AVOID_HEADER in prompt)
check('MTG_SINGLE+avoid → meeting instruction present',      'ignore that completely' in prompt)
check('MTG_SINGLE+avoid → meeting instruction before avoid',
      prompt.index('ignore that completely') < prompt.index(AVOID_HEADER))
check('MTG_SINGLE+avoid → ends with WRITE_INSTRUCTION',      prompt.endswith(WRITE_INSTRUCTION))
check('MTG_SINGLE+avoid → avoid directly before WRITE',      prompt.endswith(f['avoid'] + WRITE_INSTRUCTION))

# Case MEETING_STRIPPED_MULTI_Q + avoid
prompt, f = build_prompt(
    "Him: I like you\nHer: I know\n"
    "Him: What drives you? What do you value? Let's meet up.",
    recent_replies=REPLIES_3,
)
check('MTG_MULTI_Q+avoid → case is MEETING_STRIPPED_MULTI_Q', f['case'] == 'MEETING_STRIPPED_MULTI_Q')
check('MTG_MULTI_Q+avoid → avoid block present',               AVOID_HEADER in prompt)
check('MTG_MULTI_Q+avoid → meeting instruction present',       'ignore that completely' in prompt)
check('MTG_MULTI_Q+avoid → best question present',             f['best_q'] in prompt)
check('MTG_MULTI_Q+avoid → meeting instruction before avoid',
      prompt.index('ignore that completely') < prompt.index(AVOID_HEADER))
check('MTG_MULTI_Q+avoid → ends with WRITE_INSTRUCTION',       prompt.endswith(WRITE_INSTRUCTION))
check('MTG_MULTI_Q+avoid → avoid directly before WRITE',       prompt.endswith(f['avoid'] + WRITE_INSTRUCTION))

# Case FULL_MEETING_REDIRECT + avoid
prompt, f = build_prompt(
    "Him: I feel a connection\nHer: Me too\n"
    "Him: We should just meet up. Come over this weekend.",
    recent_replies=REPLIES_3,
)
check('FULL_REDIRECT+avoid → case is FULL_MEETING_REDIRECT', f['case'] == 'FULL_MEETING_REDIRECT')
check('FULL_REDIRECT+avoid → avoid block present',            AVOID_HEADER in prompt)
check('FULL_REDIRECT+avoid → Do NOT agree present',           'Do NOT agree' in prompt)
check('FULL_REDIRECT+avoid → Do NOT before avoid',
      prompt.index('Do NOT agree') < prompt.index(AVOID_HEADER))
check('FULL_REDIRECT+avoid → ends with WRITE_INSTRUCTION',    prompt.endswith(WRITE_INSTRUCTION))
check('FULL_REDIRECT+avoid → avoid directly before WRITE',    prompt.endswith(f['avoid'] + WRITE_INSTRUCTION))


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — All 5 cases WITHOUT avoid block (regression)
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 3 — ALL 5 CASES WITHOUT AVOID BLOCK (REGRESSION)')

CONVOS = {
    'NORMAL': "Him: You are confident\nHer: Always\nHim: That energy is rare.",
    'MULTI_Q': "Him: I like you\nHer: I know\nHim: What kind of woman are you? Do you cook? What do you value?",
    'MTG_SINGLE': "Him: I noticed you\nHer: Good\nHim: I keep my promises. If we never met you would never know.",
    'MTG_MULTI_Q': "Him: I like you\nHer: I know\nHim: What drives you? What do you value? Let's meet up.",
    'FULL_REDIRECT': "Him: I feel a connection\nHer: Me too\nHim: We should meet up. Come over this weekend.",
}

for label, conv in CONVOS.items():
    for no_avoid in [None, []]:
        prompt, f = build_prompt(conv, recent_replies=no_avoid)
        check(f'{label}+no_avoid({no_avoid!r}) → AVOID_HEADER absent',
              AVOID_HEADER not in prompt)
        check(f'{label}+no_avoid({no_avoid!r}) → no bullet points',
              '•' not in prompt)
        check(f'{label}+no_avoid({no_avoid!r}) → ends with WRITE_INSTRUCTION',
              prompt.endswith(WRITE_INSTRUCTION))


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — List truncation — strictly capped at 3
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 4 — LIST TRUNCATION (STRICTLY CAPPED AT 3)')

CONV = "Him: Hey\nHer: Hi\nHim: You seem interesting."

for n in [4, 5, 7, 10, 20, 50]:
    replies = [f"Reply number {i}" for i in range(n)]
    prompt, _ = build_prompt(CONV, recent_replies=replies)
    bullet_count = prompt.count('•')
    check(f'{n} replies passed → exactly 3 bullets in prompt', bullet_count == 3,
          f'got {bullet_count} bullets')
    for i in range(3):
        check(f'{n} replies → Reply number {i} present',    f'Reply number {i}' in prompt)
    for i in range(3, n):
        check(f'{n} replies → Reply number {i} ABSENT',     f'Reply number {i}' not in prompt)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — Edge cases
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 5 — EDGE CASES')

# Single empty string in list — [''] is truthy, block IS built (current behavior)
a_empty_str = _build_avoid([''])
check("[''] is truthy → block is built (current behavior)", a_empty_str != '')
check("[''] → contains bullet with empty content",         '• ' in a_empty_str)
warn("KNOWN: [''] produces '• ' bullet — cosmetically ugly but harmless")

# None inside list — f"• {None}" = "• None"
a_none_item = _build_avoid([None, 'real reply'])
check("[None, 'real'] → does not crash",               a_none_item != '')
check("[None, 'real'] → 'None' string appears",        '• None' in a_none_item)
warn("KNOWN: None in list produces '• None' — caller should sanitize")

# Reply containing newlines — embedded newlines in bullet
a_newline = _build_avoid(["Line one\nLine two"])
check("Reply with \\n → block is built without crashing",  a_newline != '')
check("Reply with \\n → bullet created",                   '• Line one' in a_newline)

# Reply with double quotes
a_dq = _build_avoid(['She said "yes" eventually. Interested?'])
check('Reply with double quotes → preserved', '"yes"' in a_dq)

# Reply with unicode em-dash
a_emdash = _build_avoid(['Mysterious — always. Can you handle that?'])
check('Reply with em-dash → preserved', '—' in a_emdash)

# Reply with all emoji
a_emoji_only = _build_avoid(['🔥😍💋'])
check('Emoji-only reply → preserved', '🔥😍💋' in a_emoji_only)

# Very long reply (200 chars) — no truncation inside avoid block
long = 'X' * 200
a_long200 = _build_avoid([long])
check('200-char reply → fully in block (avoid block does not truncate)',
      ('• ' + long) in a_long200)

# Single-item list
a_single = _build_avoid(['Only one reply so far.'])
check('Single-item list → 1 bullet',       a_single.count('•') == 1)
check('Single-item list → header present', AVOID_HEADER in a_single)
check('Single-item list → ends \\n\\n',    a_single.endswith('\n\n'))

# Duplicate replies in list
a_dup = _build_avoid(['Same reply', 'Same reply', 'Same reply'])
check('3 identical replies → still 3 bullets', a_dup.count('•') == 3)

# Reply that contains the AVOID_HEADER text (injection edge case)
# The LLM never produces this 80-char instruction string as a dating reply,
# but we document actual behavior: AVOID_HEADER appears twice (in the block
# header AND embedded in the bullet). Cosmetically confusing, not broken.
tricky = AVOID_HEADER.strip()
a_tricky = _build_avoid([tricky, 'normal reply'])
check('Reply containing AVOID_HEADER → block is built without crashing',
      a_tricky != '' and a_tricky.endswith('\n\n'))
check('Reply containing AVOID_HEADER → normal reply still present',
      '• normal reply' in a_tricky)
warn('KNOWN: reply containing AVOID_HEADER text causes header to appear twice — '
     'impossible in practice (LLM never generates this string as a dating reply)')


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — Prompt structure / positional order
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 6 — PROMPT STRUCTURE & POSITIONAL ORDER')

REPLIES_2 = ["First reply here.", "Second reply here."]

POSITION_CASES = [
    ('NORMAL',
     "Him: You are confident\nHer: Always\nHim: That energy is rare."),
    ('MULTI_Q_NO_MEETING',
     "Him: Hey\nHer: Hi\nHim: What kind of woman are you? Do you cook? What do you value?"),
    ('MEETING_STRIPPED_SINGLE',
     "Him: Trust me\nHer: Prove it\nHim: I keep my word. If we never met you'd never know."),
    ('MEETING_STRIPPED_MULTI_Q',
     "Him: I like you\nHer: I know\nHim: What drives you? What do you value? Let's hang out."),
    ('FULL_MEETING_REDIRECT',
     "Him: I feel it\nHer: Me too\nHim: We should get together. Come over."),
]

for case_name, conv in POSITION_CASES:
    prompt, f = build_prompt(conv, recent_replies=REPLIES_2)

    # 1. Conversation appears in prompt
    first_line = conv.split('\n')[0]
    check(f'{case_name} → conversation present in prompt', first_line in prompt)

    # 2. WRITE_INSTRUCTION is last
    check(f'{case_name} → WRITE_INSTRUCTION is last token',
          prompt.endswith(WRITE_INSTRUCTION))

    # 3. Avoid block is present
    check(f'{case_name} → avoid block present', AVOID_HEADER in prompt)

    # 4. Avoid block appears after conversation
    check(f'{case_name} → conversation before avoid',
          prompt.index(first_line) < prompt.index(AVOID_HEADER))

    # 5. Avoid block appears before WRITE_INSTRUCTION
    check(f'{case_name} → avoid before WRITE_INSTRUCTION',
          prompt.index(AVOID_HEADER) < prompt.rindex(WRITE_INSTRUCTION))

    # 6. Nothing after WRITE_INSTRUCTION
    write_pos = prompt.rindex(WRITE_INSTRUCTION)
    check(f'{case_name} → nothing after WRITE_INSTRUCTION',
          prompt[write_pos + len(WRITE_INSTRUCTION):] == '')

    # 7. Case instruction (if any) is between conversation and avoid
    if f['case_instr']:
        instr_snippet = f['case_instr'][:25]
        check(f'{case_name} → case instruction between conversation and avoid',
              prompt.index(first_line) < prompt.index(instr_snippet) < prompt.index(AVOID_HEADER))

    # 8. Avoid block directly precedes WRITE_INSTRUCTION
    check(f'{case_name} → avoid directly precedes WRITE_INSTRUCTION',
          prompt.endswith(f['avoid'] + WRITE_INSTRUCTION))


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — Triple filter combination
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 7 — TRIPLE FILTER COMBINATION (ALL 3 FILTERS ACTIVE)')

# All 3: meeting_stripped_multi_q + recent_replies
prompt, f = build_prompt(
    "Him: I like you\nHer: I know\n"
    "Him: What drives you? What kind of woman are you? Let's meet up.",
    recent_replies=REPLIES_3,
)
check('Triple → case is MEETING_STRIPPED_MULTI_Q',     f['case'] == 'MEETING_STRIPPED_MULTI_Q')
check('Triple → meeting found',                         f['meeting_found'])
check('Triple → multi_q found',                         f['multi_q_found'])
check('Triple → avoid block present',                   AVOID_HEADER in prompt)
check('Triple → meeting instruction present',           'ignore that completely' in prompt)
check('Triple → best question present',                 f['best_q'] in prompt)
check('Triple → correct order: conv→meeting→avoid→write',
      (prompt.index('Him: I like you') <
       prompt.index('ignore that completely') <
       prompt.index(AVOID_HEADER) <
       prompt.rindex(WRITE_INSTRUCTION)))
check('Triple → all 3 recent replies in prompt',
      all(f'• {r}' in prompt for r in REPLIES_3))
check('Triple → ends with WRITE_INSTRUCTION',           prompt.endswith(WRITE_INSTRUCTION))
check('Triple → avoid directly before WRITE',           prompt.endswith(f['avoid'] + WRITE_INSTRUCTION))

# All 3: full_meeting_redirect + recent_replies
prompt, f = build_prompt(
    "Him: I feel a connection\nHer: Me too\n"
    "Him: We should get together. Come over this weekend.",
    recent_replies=REPLIES_3,
)
check('Triple REDIRECT → case is FULL_MEETING_REDIRECT', f['case'] == 'FULL_MEETING_REDIRECT')
check('Triple REDIRECT → avoid block present',            AVOID_HEADER in prompt)
check('Triple REDIRECT → Do NOT before avoid',
      prompt.index('Do NOT agree') < prompt.index(AVOID_HEADER))
check('Triple REDIRECT → avoid before WRITE',
      prompt.index(AVOID_HEADER) < prompt.rindex(WRITE_INSTRUCTION))
check('Triple REDIRECT → ends with WRITE_INSTRUCTION',    prompt.endswith(WRITE_INSTRUCTION))

# All 3: multi_q + recent_replies (no meeting)
prompt, f = build_prompt(
    "Him: Tell me\nHer: Ask\n"
    "Him: What kind of woman are you? Do you cook? What are you craving?",
    recent_replies=REPLIES_3,
)
check('Triple NO_MEETING → case is MULTI_Q_NO_MEETING',  f['case'] == 'MULTI_Q_NO_MEETING')
check('Triple NO_MEETING → avoid block present',          AVOID_HEADER in prompt)
check('Triple NO_MEETING → question instruction present', 'He asked several questions' in prompt)
check('Triple NO_MEETING → question before avoid',
      prompt.index('He asked several questions') < prompt.index(AVOID_HEADER))
check('Triple NO_MEETING → ends with WRITE_INSTRUCTION',  prompt.endswith(WRITE_INSTRUCTION))
check('Triple NO_MEETING → all recent replies present',
      all(f'• {r}' in prompt for r in REPLIES_3))


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 — Redis session simulation (views.py logic)
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 8 — REDIS SESSION SIMULATION')

store = {}  # in-memory stand-in for Redis

# User 1 — simulate 6 sequential reply generations
USER1 = 1
REPLIES_GENERATED = [
    "You surprise me every time. What's your move?",
    "I'm the kind of woman who keeps you guessing. Ready?",
    "Not everyone gets this side of me. What made you different?",
    "I don't give that away easily. Can you handle the real me?",
    "Confidence is the only thing I never run out of. What about you?",
    "There's a version of me most men never get to see. Curious?",
]

# Before any generation
check('Before gen → recent_replies is []',
      session_get_replies(store, USER1) == [])

# After 1st generation
session_write(store, USER1, REPLIES_GENERATED[0])
r = session_get_replies(store, USER1)
check('After gen 1 → 1 reply in session',       len(r) == 1)
check('After gen 1 → correct reply stored',     r[0] == REPLIES_GENERATED[0])

# After 2nd generation
session_write(store, USER1, REPLIES_GENERATED[1])
r = session_get_replies(store, USER1)
check('After gen 2 → 2 replies in session',     len(r) == 2)
check('After gen 2 → newest reply is first',    r[0] == REPLIES_GENERATED[1])
check('After gen 2 → oldest reply is second',   r[1] == REPLIES_GENERATED[0])

# After 3rd generation
session_write(store, USER1, REPLIES_GENERATED[2])
r = session_get_replies(store, USER1)
check('After gen 3 → 3 replies in session',     len(r) == 3)
check('After gen 3 → order: newest→oldest',
      r == [REPLIES_GENERATED[2], REPLIES_GENERATED[1], REPLIES_GENERATED[0]])

# After 4th generation — oldest (gen 0) should be dropped
session_write(store, USER1, REPLIES_GENERATED[3])
r = session_get_replies(store, USER1)
check('After gen 4 → still 3 replies (cap enforced)',   len(r) == 3)
check('After gen 4 → gen 0 reply DROPPED',              REPLIES_GENERATED[0] not in r)
check('After gen 4 → gen 3 is first',                   r[0] == REPLIES_GENERATED[3])
check('After gen 4 → gen 2 is second',                  r[1] == REPLIES_GENERATED[2])
check('After gen 4 → gen 1 is third',                   r[2] == REPLIES_GENERATED[1])

# After 5th generation
session_write(store, USER1, REPLIES_GENERATED[4])
r = session_get_replies(store, USER1)
check('After gen 5 → still 3 replies',                  len(r) == 3)
check('After gen 5 → gen 4 is first',                   r[0] == REPLIES_GENERATED[4])
check('After gen 5 → gen 1 dropped',                    REPLIES_GENERATED[1] not in r)

# After 6th generation
session_write(store, USER1, REPLIES_GENERATED[5])
r = session_get_replies(store, USER1)
check('After gen 6 → still 3 replies',                  len(r) == 3)
check('After gen 6 → always newest 3: gen5, gen4, gen3',
      r == [REPLIES_GENERATED[5], REPLIES_GENERATED[4], REPLIES_GENERATED[3]])

# What the 7th generation SEES — should receive the 3 most recent
recent_for_gen7 = session_get_replies(store, USER1)
prompt_gen7, _ = build_prompt(
    "Him: Still here\nHer: Always\nHim: Tell me something real.",
    recent_replies=recent_for_gen7,
)
check('Gen 7 prompt → sees gen5 reply',  f'• {REPLIES_GENERATED[5]}' in prompt_gen7)
check('Gen 7 prompt → sees gen4 reply',  f'• {REPLIES_GENERATED[4]}' in prompt_gen7)
check('Gen 7 prompt → sees gen3 reply',  f'• {REPLIES_GENERATED[3]}' in prompt_gen7)
check('Gen 7 prompt → does NOT see gen0 reply', REPLIES_GENERATED[0] not in prompt_gen7)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 — Cross-contamination guard (two users)
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 9 — CROSS-CONTAMINATION GUARD (TWO USERS)')

store2 = {}
USER_A, USER_B = 101, 202

session_write(store2, USER_A, "User A reply 1")
session_write(store2, USER_A, "User A reply 2")
session_write(store2, USER_B, "User B reply 1")

rA = session_get_replies(store2, USER_A)
rB = session_get_replies(store2, USER_B)

check('User A has 2 replies',                       len(rA) == 2)
check('User B has 1 reply',                         len(rB) == 1)
check('User A session contains only User A replies', all('User A' in r for r in rA))
check('User B session contains only User B replies', all('User B' in r for r in rB))
check('User A replies not in User B session',        not any(r in rB for r in rA))
check('User B replies not in User A session',        not any(r in rA for r in rB))

# Keys are different
check('Session keys are user-specific',
      f"user_specific_{USER_A}" != f"user_specific_{USER_B}")

# Zero cross-contamination in generated prompts
conv_same = "Him: Hey\nHer: Hi\nHim: What are you craving right now?"
pA, _ = build_prompt(conv_same, recent_replies=rA)
pB, _ = build_prompt(conv_same, recent_replies=rB)
check('User A prompt contains no User B reply', 'User B' not in pA)
check('User B prompt contains no User A reply', 'User A' not in pB)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10 — Instruction wording — exact text checks
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 10 — INSTRUCTION WORDING (EXACT TEXT)')

a = _build_avoid(['reply'])
check('Header starts correctly',
      a.startswith("Your last few replies — vary the opening energy or question style"))
check('Header contains "don\'t echo the same angle"',
      "don't echo the same angle" in a)
check('Bullet uses "•" character (not "-" or "*")',
      '• reply' in a)
check('No trailing text after final \\n\\n',
      a == AVOID_HEADER + "• reply\n\n")

# Verify exact AVOID_HEADER constant
check('AVOID_HEADER ends with \\n (not \\n\\n)',
      AVOID_HEADER.endswith('\n') and not AVOID_HEADER.endswith('\n\n'))
check('WRITE_INSTRUCTION exact text',
      WRITE_INSTRUCTION == "Write the woman's next reply.")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 11 — Realistic stress tests
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 11 — REALISTIC STRESS TESTS')

REALISTIC_HISTORIES = [
    # Heavy user — 8 replies, only last 3 should appear
    {
        'label': 'Heavy user (8 recent replies) — only 3 newest injected',
        'replies': [
            "There's a version of me most men never get to see. Curious?",       # gen 7 (newest)
            "Confidence is the only thing I never run out of. What about you?",  # gen 6
            "I don't give that away easily. Can you handle the real me?",        # gen 5
            "Not everyone gets this side of me. What made you different?",       # gen 4
            "I'm the kind of woman who keeps you guessing. Ready?",              # gen 3
            "You surprise me every time. What's your move?",                     # gen 2
            "Mystery is part of the package. Can you keep up?",                  # gen 1
            "I only show this side when it's earned. Have you earned it?",       # gen 0
        ],
        'expect_in': [
            "There's a version of me most men never get to see. Curious?",
            "Confidence is the only thing I never run out of. What about you?",
            "I don't give that away easily. Can you handle the real me?",
        ],
        'expect_out': [
            "Not everyone gets this side of me. What made you different?",
            "I only show this side when it's earned. Have you earned it?",
        ],
    },
    # Sexual escalation replies
    {
        'label': 'Sexual escalation replies — correctly injected',
        'replies': [
            "You'd be surprised what I'm thinking about right now. Interested?",
            "I know exactly what I want. The question is — do you?",
            "My standards are high and my patience is low. Still here?",
        ],
        'expect_in': [
            "You'd be surprised what I'm thinking about right now. Interested?",
            "I know exactly what I want. The question is — do you?",
            "My standards are high and my patience is low. Still here?",
        ],
        'expect_out': [],
    },
]

STRESS_CONV = "Him: I think about you\nHer: Good\nHim: What are you craving right now?"

for tc in REALISTIC_HISTORIES:
    prompt, f = build_prompt(STRESS_CONV, recent_replies=tc['replies'])
    check(f"{tc['label']} — avoid block present", AVOID_HEADER in prompt)
    check(f"{tc['label']} — exactly 3 bullets", prompt.count('•') == 3)
    for r in tc['expect_in']:
        check(f"{tc['label']} — expected reply IN prompt", f'• {r}' in prompt,
              f'Missing: "{r[:50]}..."')
    for r in tc['expect_out']:
        check(f"{tc['label']} — old reply NOT in prompt", f'• {r}' not in prompt,
              f'Should be absent: "{r[:50]}..."')
    check(f"{tc['label']} — ends with WRITE_INSTRUCTION", prompt.endswith(WRITE_INSTRUCTION))


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 12 — "Write the woman's next reply." is always the final token
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 12 — WRITE INSTRUCTION IS ALWAYS THE FINAL TOKEN')

FINAL_TOKEN_CASES = [
    ("NORMAL no avoid",      "Him: Hey\nHer: Hi\nHim: Tell me about yourself.", None),
    ("NORMAL with avoid",    "Him: Hey\nHer: Hi\nHim: Tell me about yourself.", ['R1']),
    ("MULTI_Q no avoid",     "Him: Hey\nHer: Hi\nHim: What kind of woman are you? Do you cook?", None),
    ("MULTI_Q with avoid",   "Him: Hey\nHer: Hi\nHim: What kind of woman are you? Do you cook?", ['R1', 'R2']),
    ("MTG no avoid",         "Him: Hey\nHer: Hi\nHim: I keep my word. If we never met you'd never know.", None),
    ("MTG with avoid",       "Him: Hey\nHer: Hi\nHim: I keep my word. If we never met you'd never know.", ['R1']),
    ("MTG_MULTI no avoid",   "Him: Hey\nHer: Hi\nHim: What drives you? What do you value? Let's hang out.", None),
    ("MTG_MULTI with avoid", "Him: Hey\nHer: Hi\nHim: What drives you? What do you value? Let's hang out.", ['R1', 'R2', 'R3']),
    ("REDIRECT no avoid",    "Him: Hey\nHer: Hi\nHim: We should just meet up. Come over.", None),
    ("REDIRECT with avoid",  "Him: Hey\nHer: Hi\nHim: We should just meet up. Come over.", ['R1', 'R2']),
]

for label, conv, replies in FINAL_TOKEN_CASES:
    prompt, _ = build_prompt(conv, recent_replies=replies)
    check(f'{label} → ends with exact WRITE_INSTRUCTION',
          prompt.endswith(WRITE_INSTRUCTION))
    trailing = prompt[prompt.rindex(WRITE_INSTRUCTION) + len(WRITE_INSTRUCTION):]
    check(f'{label} → nothing after WRITE_INSTRUCTION',
          trailing == '', f'Got: {repr(trailing)}')


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS
# ─────────────────────────────────────────────────────────────────────────────
header('RESULTS')
color = '\033[92m' if passed == total else '\033[91m'
print(f'\n  {color}{passed}/{total} tests passed\033[0m\n')

failed = total - passed
if failed:
    print(f'  {failed} test(s) failed — see [FAIL] lines above.\n')
else:
    print('  All tests passed.\n')
    print('  Coverage summary:')
    print('  Sec  1  Avoid block construction — exact strings, bullets, endings')
    print('  Sec  2  All 5 cases with avoid block — positional checks')
    print('  Sec  3  All 5 cases without avoid block — regression')
    print('  Sec  4  List truncation — strictly capped at 3')
    print('  Sec  5  Edge cases — empty string, None, emoji, quotes, long text')
    print('  Sec  6  Prompt structure — brutal positional order checks')
    print('  Sec  7  Triple filter combination — all 3 filters active')
    print('  Sec  8  Redis session simulation — 6-generation flow')
    print('  Sec  9  Cross-contamination guard — two users')
    print('  Sec 10  Instruction wording — exact text')
    print('  Sec 11  Realistic stress tests — heavy users, sexual content')
    print('  Sec 12  WRITE_INSTRUCTION always final token, 10 cases\n')
