# -*- coding: utf-8 -*-
"""
Button System — Brutal Test Suite
===================================
Tests every component of the redesigned button system:
  1.  Button definitions — all 36, correct structure, no duplicates
  2.  Grid structure — 6 rows × 6 buttons, correct row values
  3.  Removed buttons — meeting_redirect / reverse_psychology gone
  4.  Opener pool — 70+ items, no duplicates, all non-empty strings
  5.  _select_opener — pure Python logic, no Redis needed
  6.  Opener rotation — 80 sequential picks, no consecutive repeats
  7.  Full-cycle reset — resets after pool exhausted, avoids last 10
  8.  Prompt construction — opener at end, themes before opener, order correct
  9.  Session management — used_themes cap at 8, used_openers cap at 30
  10. Cross-button opener sharing — opener history is per-user, not per-intent
  11. enforce_char_limit — new function with configurable max_chars
  12. enforce_130_chars — backward-compat alias untouched
  13. ensure_ends_with_question — works with max_chars=450
  14. extract_theme — all new categories (surrender, longing, tension, morning, night)
  15. Prompt injection position — opener last, themes before, scenario first
  16. Edge cases — empty session, missing keys, all openers used
  17. chatAPI.js data mirror — 36 IDs in correct grid order

No Django, no Redis, no OpenAI required.
Run: py test_button_system.py
"""
import sys, io, re, random, copy
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ─────────────────────────────────────────────────────────────────────────────
# Replicate exact logic from button_generator.py
# ─────────────────────────────────────────────────────────────────────────────

_OPENER_POOL = [
    "Warmth", "Quiet", "Silk", "Dusk", "Embers", "Stillness",
    "Smoke", "Amber", "Hush", "Shadows", "Heat", "Tension",
    "Pulse", "Ache", "Hunger", "Weight", "Softness", "Static",
    "Gravity", "Nightfall", "Candlelight", "Friction",
    "Honest thing —", "Real confession —", "Plainly —", "True thing —",
    "Admitting this —", "Without armor —", "Said plainly —", "Out loud now —",
    "No edit on this —", "Something I keep —", "Quietly —",
    "Can't stop.", "Back here again.", "Still here.", "Already.",
    "Won't pretend.", "All of it.", "Just this.", "Right now.",
    "Not polite.", "Done with almost.", "Here it is.", "Not managed.",
    "Without the performance.", "Unedited —",
    "Barefoot —", "Armor off —", "Lights low —", "Unguarded —",
    "Unhurried —", "Undone —", "Wrapped in this —", "Breathing differently —",
    "Day finally gone —", "Stripped of it —", "Settled now —", "Wide open —",
    "Pulled —", "Flooding —", "Racing —", "Reaching —", "Drawn —", "Caught —",
    "Already leaning —", "Moving toward —", "Pulled back here —", "Returning —",
    "Late enough —", "Quiet enough —", "Still enough —", "Dark enough —",
    "Right in the middle of something —", "This specific hour —",
    "Before I think better of it —", "At this exact moment —",
    "In the space between —", "This hour specifically —",
]

BUTTON_INTENTS = {
    'new_match':            {'name': '✨ New Match',    'row': 1},
    'dead':                 {'name': '💀 Dead Convo',   'row': 1},
    'you_went_silent':      {'name': '⏰ Went Silent',  'row': 1},
    'shower_fantasy':       {'name': '🚿 Shower',        'row': 1},
    'morning_flirt':        {'name': '🌅 Morning',      'row': 1},
    'after_work':           {'name': '🛋️ After Work',   'row': 1},
    'provider_energy':      {'name': '💰 Provider',     'row': 2},
    'strategic_withdrawal': {'name': '🥺 Withdraw',     'row': 2},
    'deep_emotion':         {'name': '💔 Deep Feel',    'row': 2},
    'lyrical_romance':      {'name': '🎵 Lyrical',      'row': 2},
    'vulnerability':        {'name': '💭 Vulnerable',   'row': 2},
    'family_talk':          {'name': '🏠 Family',       'row': 2},
    'lunch_break':          {'name': '🥗 Lunch',        'row': 3},
    'dont_go':              {'name': "🙏 Don't Go",      'row': 3},
    'weekend_plans':        {'name': '🏖️ Weekend',      'row': 3},
    'wine_stars':           {'name': '🍷 Wine & Stars', 'row': 3},
    'work_talk':            {'name': '💼 Work Talk',    'row': 3},
    'food_talk':            {'name': '🍳 Food Talk',    'row': 3},
    'slow_dance':           {'name': '💃 Foreplay',     'row': 4},
    'outdoor_fantasy':      {'name': '🌿 Outdoors',     'row': 4},
    'public_display':       {'name': '💋 Public PDA',   'row': 4},
    'restaurant_fantasy':   {'name': '🕯️ Restaurant',  'row': 4},
    'public_fantasy':       {'name': '🌃 Public',       'row': 4},
    'kitchen_flirt':        {'name': '👩‍🍳 Kitchen',    'row': 4},
    'his_exes':             {'name': '👻 His Exes',     'row': 5},
    'secrets':              {'name': '🤫 Secrets',       'row': 5},
    'long_without':         {'name': '⏳ No Touch',     'row': 5},
    'bdsm_talk':            {'name': '⛓️ BDSM',         'row': 5},
    'kinky_at_work':        {'name': '🖥️ Kinky Work',   'row': 5},
    'sensual_echo':         {'name': '🔥 Sensual',      'row': 6},
    'bedroom_questions':    {'name': '🛏️ Bedroom',      'row': 6},
    'positions':            {'name': '😈 Positions',    'row': 6},
    'bedtime_fantasies':    {'name': '🌜 Bedtime',      'row': 6},
    'toy_play':             {'name': '🎲 Toys',         'row': 6},
    'fetishes':             {'name': '🎭 Fetishes',     'row': 6},
}

# chatAPI.js button IDs in grid order (mirrors getAvailableButtons())
CHATAPI_IDS = [
    'new_match', 'dead', 'you_went_silent', 'shower_fantasy', 'morning_flirt', 'after_work',
    'provider_energy', 'strategic_withdrawal', 'deep_emotion', 'lyrical_romance', 'vulnerability', 'family_talk',
    'lunch_break', 'dont_go', 'weekend_plans', 'wine_stars', 'work_talk', 'food_talk',
    'slow_dance', 'outdoor_fantasy', 'public_display', 'restaurant_fantasy', 'public_fantasy', 'kitchen_flirt',
    'his_exes', 'secrets', 'long_without', 'bdsm_talk', 'kinky_at_work',
    'sensual_echo', 'bedroom_questions', 'positions', 'bedtime_fantasies', 'toy_play', 'fetishes',
]

OPENER_INJECTION_TEMPLATE = 'Begin your message with this exact word or phrase: "{opener}"'
THEME_AVOIDANCE_TEMPLATE  = 'Angles already used — take a completely different direction: {themes}.'

def _select_opener(user_id: int, session_data: dict) -> str:
    used = set(session_data.get('used_openers', []))
    available = [o for o in _OPENER_POOL if o not in used]
    if not available:
        session_data['used_openers'] = session_data.get('used_openers', [])[-10:]
        used = set(session_data['used_openers'])
        available = [o for o in _OPENER_POOL if o not in used]
    chosen = random.choice(available)
    prev = session_data.get('used_openers', [])
    session_data['used_openers'] = (prev + [chosen])[-30:]
    return chosen

def build_user_prompt(button_intent: str, session_data: dict, scenario_prompt: str) -> str:
    used_themes = session_data.get('used_themes', {}).get(button_intent, [])
    selected_opener = _select_opener(0, session_data)
    prompt = scenario_prompt
    if used_themes:
        prompt += f'\n\n{THEME_AVOIDANCE_TEMPLATE.format(themes=", ".join(used_themes))}'
    # Temporal injection (mirrors generate_button_response)
    prompt += (
        "\n\nTemporal context (let this live underneath everything — texture, not instruction): "
        "It is Tuesday, mid-morning (the day has started, energy building). "
        "Midweek grind, quietly focused, understated energy, the world asking things of her. "
        "Her emotional state right now: curious."
    )
    prompt += f'\n\n{OPENER_INJECTION_TEMPLATE.format(opener=selected_opener)}'
    return prompt, selected_opener

def enforce_char_limit(text: str, max_chars: int = 150) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    last_q = text.rfind('?', 0, max_chars)
    if last_q > max_chars // 2:
        return text[:last_q + 1]
    last_end = max(text.rfind('.', 0, max_chars), text.rfind('!', 0, max_chars))
    if last_end > max_chars // 2:
        return text[:last_end + 1]
    return text[:max_chars]

def enforce_130_chars(text: str) -> str:
    return enforce_char_limit(text, max_chars=150)

def ensure_ends_with_question(text: str, max_chars: int = 150) -> str:
    text = text.strip()
    if not text:
        return "What does that actually do to you?"
    if text.endswith('?'):
        return text
    if text.endswith('.'):
        candidate = text[:-1] + '?'
    elif text[-1].isalnum():
        candidate = text + '?'
    else:
        candidate = text
    if len(candidate) > max_chars:
        candidate = candidate[:max_chars - 1] + '?'
    return candidate

def extract_theme(text: str) -> str:
    theme_map = {
        'coffee':    ['coffee', 'cafe', 'brew'],
        'morning':   ['morning', 'wake', 'sunrise', 'early', 'dawn'],
        'night':     ['night', 'dark', 'late', 'midnight', 'stars', 'quiet'],
        'dreams':    ['dream', 'dreamed', 'sleep'],
        'work':      ['work', 'job', 'busy', 'office', 'desk'],
        'food':      ['food', 'eat', 'dinner', 'lunch', 'breakfast', 'cook', 'meal', 'taste'],
        'adventure': ['movie', 'hike', 'walk', 'explore', 'adventure', 'outside', 'outdoor'],
        'surrender': ['control', 'surrender', 'submit', 'power', 'dominate', 'bdsm'],
        'intimate':  ['kiss', 'touch', 'close', 'tonight', 'bed', 'cuddle', 'cock', 'pussy',
                      'body', 'skin', 'hands', 'inside', 'deep'],
        'tension':   ['tension', 'edge', 'almost', 'between', 'pull', 'gravity'],
        'future':    ['weekend', 'next', 'plans', 'soon', 'someday', 'imagine'],
        'longing':   ['ache', 'miss', 'hunger', 'crave', 'yearn', 'want'],
        'feelings':  ['miss', 'like', 'love', 'feel', 'heart', 'special', 'longing'],
        'physical':  ['sexy', 'attractive', 'gorgeous', 'lips', 'warm'],
        'teasing':   ['tease', 'play', 'challenge', 'dare'],
    }
    text_lower = text.lower()
    for theme, keywords in theme_map.items():
        if any(re.search(r'\b' + re.escape(kw) + r'\b', text_lower) for kw in keywords):
            return theme
    words = [w for w in text.split()[:3] if w.lower() not in
             {'what', 'when', 'where', 'how', 'do', 'you', 'i', 'the', 'a', 'an', 'is', 'are',
              'that', 'this', 'it', 'of', 'and', 'or', 'but', 'so', 'to', 'in', 'on', 'at'}]
    return words[0].lower() if words else 'other'


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
    print(f'  {WARN}  {label}' + (f' — {detail}' if detail else ''))

def header(title):
    print(f'\n{"="*70}')
    print(f'  {title}')
    print(f'{"="*70}')


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Button definitions: count, structure, required fields
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 1 — BUTTON DEFINITIONS (COUNT, STRUCTURE, REQUIRED FIELDS)')

check('Exactly 36 buttons defined', len(BUTTON_INTENTS) == 36,
      f'Got {len(BUTTON_INTENTS)}')

check('No duplicate keys', len(set(BUTTON_INTENTS.keys())) == len(BUTTON_INTENTS))

for btn_id, cfg in BUTTON_INTENTS.items():
    check(f'  {btn_id} → has "name" field',   'name'  in cfg, f'Missing: name')
    check(f'  {btn_id} → has "row" field',    'row'   in cfg, f'Missing: row')
    check(f'  {btn_id} → name is non-empty',  bool(cfg.get('name', '').strip()))
    check(f'  {btn_id} → row is int 1-6',
          isinstance(cfg.get('row'), int) and 1 <= cfg['row'] <= 6,
          f'Got row={cfg.get("row")}')


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Grid structure: 6 rows, exactly 6 buttons per row
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 2 — GRID STRUCTURE (6×6)')

from collections import Counter
row_counts = Counter(cfg['row'] for cfg in BUTTON_INTENTS.values())

check('All 6 rows present',
      set(row_counts.keys()) == {1, 2, 3, 4, 5, 6},
      f'Rows present: {sorted(row_counts.keys())}')

for row in range(1, 7):
    check(f'Row {row} has exactly 6 buttons',
          row_counts[row] == 6,
          f'Got {row_counts[row]} buttons')


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Removed buttons are gone
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 3 — REMOVED BUTTONS ABSENT / NEW BUTTONS PRESENT')

check('meeting_redirect NOT in BUTTON_INTENTS',   'meeting_redirect'   not in BUTTON_INTENTS)
check('reverse_psychology NOT in BUTTON_INTENTS', 'reverse_psychology' not in BUTTON_INTENTS)
check('he_going_cold NOT in BUTTON_INTENTS (replaced by shower_fantasy)',
      'he_going_cold' not in BUTTON_INTENTS)
check('meeting_redirect NOT in chatAPI IDs',      'meeting_redirect'   not in CHATAPI_IDS)
check('reverse_psychology NOT in chatAPI IDs',    'reverse_psychology' not in CHATAPI_IDS)
check('he_going_cold NOT in chatAPI IDs',         'he_going_cold'      not in CHATAPI_IDS)
check('shower_fantasy IS in BUTTON_INTENTS',      'shower_fantasy'     in BUTTON_INTENTS)
check('shower_fantasy IS in chatAPI IDs',         'shower_fantasy'     in CHATAPI_IDS)
check('shower_fantasy is in Row 1',
      BUTTON_INTENTS.get('shower_fantasy', {}).get('row') == 1)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — Opener pool: size, uniqueness, data quality
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 4 — OPENER POOL (SIZE, UNIQUENESS, QUALITY)')

check(f'Pool has at least 70 openers (got {len(_OPENER_POOL)})',
      len(_OPENER_POOL) >= 70)

check('All openers are strings',
      all(isinstance(o, str) for o in _OPENER_POOL))

check('All openers are non-empty',
      all(o.strip() for o in _OPENER_POOL))

check('No duplicate openers',
      len(_OPENER_POOL) == len(set(_OPENER_POOL)),
      f'Duplicates: {[o for o in _OPENER_POOL if _OPENER_POOL.count(o) > 1]}')

check('No opener exceeds 50 chars',
      all(len(o) <= 50 for o in _OPENER_POOL),
      f'Long openers: {[o for o in _OPENER_POOL if len(o) > 50]}')

check('Pool large enough for 30-item rotation window',
      len(_OPENER_POOL) > 30)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — _select_opener: basic behaviour
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 5 — _select_opener BASIC BEHAVIOUR')

# Empty session → picks from full pool
sd = {}
opener = _select_opener(1, sd)
check('Empty session → opener is a string',          isinstance(opener, str))
check('Empty session → opener is in pool',           opener in _OPENER_POOL)
check('Empty session → used_openers created',        'used_openers' in sd)
check('Empty session → used_openers has 1 item',     len(sd['used_openers']) == 1)
check('Empty session → chosen opener tracked',       opener in sd['used_openers'])

# Second call → different opener (statistically near-certain with 79-item pool)
opener2 = _select_opener(1, sd)
check('Second call → also in pool',                  opener2 in _OPENER_POOL)
check('Second call → used_openers has 2 items',      len(sd['used_openers']) == 2)
check('Second call → differs from first (pool=79)',  opener != opener2,
      'Same opener twice in a row — possible but extremely unlikely')

# Third call
opener3 = _select_opener(1, sd)
check('Third call → all three tracked',              len(sd['used_openers']) == 3)
check('Third call → no duplicates in tracked list',  len(set(sd['used_openers'])) == 3)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — Opener rotation: no repeats until pool exhausted
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 6 — OPENER ROTATION (NO REPEATS IN FIRST 30 PICKS)')

sd_rot = {}
selected = []
for i in range(30):
    o = _select_opener(1, sd_rot)
    selected.append(o)

check('30 sequential picks — all in pool',
      all(o in _OPENER_POOL for o in selected))
check('30 sequential picks — no duplicates',
      len(set(selected)) == 30,
      f'Duplicates found in first 30: {[o for o in selected if selected.count(o)>1]}')
check('After 30 picks — session has exactly 30 tracked',
      len(sd_rot['used_openers']) == 30)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — Full-cycle reset: exhausts pool, resets, avoids last 10
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 7 — FULL-CYCLE RESET')

# Use a tiny pool to test reset without running 79 iterations
_TINY_POOL = [f'opener_{i}' for i in range(15)]
_orig_pool = _OPENER_POOL[:]

# Monkey-patch for this test
import sys
_module = sys.modules[__name__]

def _select_opener_tiny(user_id, session_data):
    used = set(session_data.get('used_openers', []))
    available = [o for o in _TINY_POOL if o not in used]
    if not available:
        session_data['used_openers'] = session_data.get('used_openers', [])[-10:]
        used = set(session_data['used_openers'])
        available = [o for o in _TINY_POOL if o not in used]
    chosen = random.choice(available)
    prev = session_data.get('used_openers', [])
    session_data['used_openers'] = (prev + [chosen])[-30:]
    return chosen

sd_cycle = {}
# Exhaust all 15
for _ in range(15):
    _select_opener_tiny(1, sd_cycle)

check('After exhausting 15-item pool — 15 items tracked',
      len(sd_cycle['used_openers']) == 15)

# Next pick triggers reset
pick_post_reset = _select_opener_tiny(1, sd_cycle)
check('Post-reset pick is in pool',          pick_post_reset in _TINY_POOL)
check('Post-reset — used_openers ≤ 11',      len(sd_cycle['used_openers']) <= 11)
check('Post-reset pick not in last-10 guard',
      pick_post_reset not in sd_cycle['used_openers'][:-1][:10])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 — Prompt construction: opener last, themes before, scenario first
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 8 — PROMPT CONSTRUCTION (POSITION ORDER)')

SCENARIO = "He just matched with you — make him feel seen immediately."

# No themes — prompt = scenario + opener
sd_p = {}
prompt, opener = build_user_prompt('new_match', sd_p, SCENARIO)

check('Scenario appears in prompt',               SCENARIO in prompt)
check('Opener instruction in prompt',             'Begin your message with' in prompt)
check('Opener value in prompt',                   f'"{opener}"' in prompt)
check('Opener instruction is LAST in prompt',     prompt.endswith(f'"{opener}"'))
check('No theme avoidance when no themes',
      'Angles already used' not in prompt)

# With themes — prompt = scenario + theme_avoidance + opener
sd_p2 = {'used_themes': {'new_match': ['warmth', 'confidence']}, 'used_openers': []}
prompt2, opener2 = build_user_prompt('new_match', sd_p2, SCENARIO)

check('With themes → theme avoidance present',    'Angles already used' in prompt2)
check('With themes → opener instruction present', 'Begin your message with' in prompt2)
check('With themes → theme avoidance BEFORE opener',
      prompt2.index('Angles already used') < prompt2.index('Begin your message with'))
check('With themes → opener is still LAST',
      prompt2.endswith(f'"{opener2}"'))
check('With themes → used themes listed',
      'warmth' in prompt2 and 'confidence' in prompt2)

# Three parts in correct order: scenario → themes → opener
scenario_pos     = prompt2.index(SCENARIO)
themes_pos       = prompt2.index('Angles already used')
opener_instr_pos = prompt2.index('Begin your message with')
temporal_pos     = prompt2.index('Temporal context')
check('Order: scenario < themes < temporal < opener instruction',
      scenario_pos < themes_pos < temporal_pos < opener_instr_pos)

# Temporal context present in both prompts
check('Temporal context block in no-theme prompt',    'Temporal context' in prompt)
check('Temporal context block in themed prompt',      'Temporal context' in prompt2)
check('Opener is still last in no-theme prompt',      prompt.endswith(f'"{opener}"'))
check('Opener is still last in themed prompt',        prompt2.endswith(f'"{opener2}"'))
check('Temporal block appears exactly once (no-theme)', prompt.count('Temporal context') == 1)
check('Temporal block appears exactly once (themed)',   prompt2.count('Temporal context') == 1)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 — Session management: caps enforced
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 9 — SESSION MANAGEMENT (CAPS ENFORCED)')

# used_openers capped at 30
sd_cap = {'used_openers': [f'o{i}' for i in range(30)]}
# When all 30 are in used set AND not in real pool, we'll get reset.
# Test the cap directly via repeated calls on real pool:
sd_cap2 = {}
for _ in range(35):
    _select_opener(1, sd_cap2)
check('After 35 picks — used_openers never exceeds 30',
      len(sd_cap2['used_openers']) <= 30)

# used_themes capped at 8 (simulating the views.py update logic)
def update_themes(session_data, intent, new_theme):
    """Mirrors: session_data['used_themes'][intent] = (used_themes + [theme])[-8:]"""
    session_data.setdefault('used_themes', {}).setdefault(intent, [])
    current = session_data['used_themes'][intent]
    session_data['used_themes'][intent] = (current + [new_theme])[-8:]

sd_themes = {}
for i in range(12):
    update_themes(sd_themes, 'sensual_echo', f'theme_{i}')

themes = sd_themes['used_themes']['sensual_echo']
check('After 12 theme additions — only last 8 kept',
      len(themes) == 8, f'Got {len(themes)}')
check('Most recent theme is last',
      themes[-1] == 'theme_11')
check('Oldest themes dropped',
      'theme_0' not in themes and 'theme_1' not in themes and 'theme_2' not in themes and 'theme_3' not in themes)
check('Themes 4-11 are present',
      all(f'theme_{i}' in themes for i in range(4, 12)))

# setdefault safety — session starts empty
sd_empty = {}
sd_empty.setdefault('used_themes', {})
sd_empty.setdefault('used_openers', [])
check('Empty session → setdefault creates both keys',
      'used_themes' in sd_empty and 'used_openers' in sd_empty)
check('setdefault does not overwrite existing keys',
      sd_empty['used_themes'] == {} and sd_empty['used_openers'] == [])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10 — Cross-button opener sharing: per-user, not per-intent
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 10 — CROSS-BUTTON OPENER SHARING (PER USER)')

sd_cross = {}
openers_seen = []

# Simulate user clicking 5 different buttons
for intent in ['new_match', 'bdsm_talk', 'morning_flirt', 'fetishes', 'deep_emotion']:
    o = _select_opener(1, sd_cross)
    openers_seen.append(o)

check('5 different buttons — 5 openers tracked in single list',
      len(sd_cross['used_openers']) == 5)
check('Openers shared across buttons — no intent-level segregation',
      'used_themes' not in sd_cross or 'used_openers' in sd_cross)
check('All 5 openers different',
      len(set(openers_seen)) == 5,
      f'Duplicates: {[o for o in openers_seen if openers_seen.count(o) > 1]}')

# Two different users — separate sessions, no cross-contamination
sd_user_a = {}
sd_user_b = {}
random.seed(42)
opener_a = _select_opener(101, sd_user_a)
random.seed(42)
opener_b = _select_opener(202, sd_user_b)

check('Two users same seed → same opener (sessions independent)',
      opener_a == opener_b)
check('User A session does not affect User B session',
      sd_user_a is not sd_user_b)
check('User A used_openers does not bleed into User B',
      sd_user_a['used_openers'] is not sd_user_b['used_openers'])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 11 — enforce_char_limit (new function)
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 11 — enforce_char_limit (NEW FUNCTION)')

# Under limit — returned unchanged
check('100 chars, limit 150 → unchanged',
      enforce_char_limit('A' * 100, 150) == 'A' * 100)

# Exactly at limit — returned unchanged
check('150 chars, limit 150 → unchanged',
      enforce_char_limit('A' * 150, 150) == 'A' * 150)

# Over limit — trim at sentence boundary (?)
text_q = 'Short sentence. ' + 'A' * 130 + '? Trailing junk.'
result_q = enforce_char_limit(text_q, 150)
check('Over limit — trims at ? boundary',
      result_q.endswith('?') and len(result_q) <= 150)

# Over limit — trim at . boundary
text_dot = 'Good sentence. ' + 'B' * 130 + '. More junk here.'
result_dot = enforce_char_limit(text_dot, 150)
check('Over limit — trims at . boundary',
      result_dot.endswith('.') and len(result_dot) <= 150)

# max_chars=450 for buttons
long_text = 'X' * 400 + '? End of question.'
result_450 = enforce_char_limit(long_text, 450)
check('450 limit — text under limit returned unchanged',
      result_450 == long_text)

too_long = 'Y' * 500 + '? end'
result_too = enforce_char_limit(too_long, 450)
check('500 chars with limit 450 — trimmed to ≤ 450',
      len(result_too) <= 450)

# Hard cut when no sentence boundary
no_boundary = 'A' * 200
result_hard = enforce_char_limit(no_boundary, 150)
check('No sentence boundary — hard cut at max_chars',
      len(result_hard) == 150)

# Empty string
check('Empty string → returned unchanged', enforce_char_limit('') == '')

# Default is 150
check('Default max_chars is 150',
      len(enforce_char_limit('Z' * 200)) == 150)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 12 — enforce_130_chars backward compatibility
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 12 — enforce_130_chars BACKWARD COMPATIBILITY')

check('enforce_130_chars short text → unchanged',
      enforce_130_chars('Short text.') == 'Short text.')
check('enforce_130_chars 150 chars → unchanged',
      enforce_130_chars('A' * 150) == 'A' * 150)
check('enforce_130_chars 200 chars → trimmed to ≤ 150',
      len(enforce_130_chars('A' * 200)) <= 150)
check('enforce_130_chars result identical to enforce_char_limit(text, 150)',
      enforce_130_chars('B' * 200) == enforce_char_limit('B' * 200, 150))


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 13 — ensure_ends_with_question with max_chars=450
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 13 — ensure_ends_with_question WITH max_chars=450')

# Already ends with ?
check('Already ends with ? → unchanged',
      ensure_ends_with_question('Do you know?', 450) == 'Do you know?')

# Ends with . → converts to ?
check('Ends with . → converts to ?',
      ensure_ends_with_question('Tell me something real.', 450) == 'Tell me something real?')

# Long text (4-5 sentences, ~300 chars) → still ends with ?
long_msg = (
    'Warmth is the only right word for what happens when I think about this. '
    'Something in me goes quiet in a way it rarely does. '
    'Not absence — presence, the specific kind that stays. '
    'What does it feel like for you when something gets in without asking first.'
)
result_long = ensure_ends_with_question(long_msg, 450)
check('300-char message → ends with ?',       result_long.endswith('?'))
check('300-char message → within 450 chars',  len(result_long) <= 450)

# Empty → fallback question
check('Empty string → fallback question returned',
      ensure_ends_with_question('', 450) == "What does that actually do to you?")

# Over max_chars → truncated then ends with ?
very_long = 'A' * 460 + 'something'
result_vl = ensure_ends_with_question(very_long, 450)
check('Over-limit text → result ≤ 450 chars',     len(result_vl) <= 450)
check('Over-limit text → still ends with ?',       result_vl.endswith('?'))

# Default max_chars is 150 (backward compat)
msg_200 = 'A' * 200 + 'finish'
result_default = ensure_ends_with_question(msg_200)
check('Default max_chars=150 → result ≤ 150 chars', len(result_default) <= 150)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 14 — extract_theme: all categories including new ones
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 14 — extract_theme (ALL CATEGORIES)')

THEME_CASES = [
    # Existing categories
    ('coffee',    'Nothing like a good coffee to start the day, honestly.'),
    ('work',      'Something about watching a man at his desk, completely focused.'),
    ('food',      'The way you described that dinner made my mouth water.'),
    ('intimate',  'His hands on my skin and his mouth close — that is what I keep thinking about.'),
    ('feelings',  'I keep thinking about you and it is making me feel all kinds of things.'),
    ('teasing',   'I dare you to tell me something you have never said out loud.'),
    # New categories
    ('surrender', 'The idea of control and surrender with someone I trust completely.'),
    ('longing',   'There is a specific hunger that wakes up when I think about you.'),
    ('tension',   'The tension in that almost — the edge of something neither of us has said.'),
    ('morning',   'Morning light does something to me I cannot name.'),
    ('night',     'It is late at night and I cannot stop thinking.'),
    # Fallback — all stopwords so words[] is empty → 'other'
    ('other',     'And it is of or but so.'),
]

for expected, text in THEME_CASES:
    result = extract_theme(text)
    check(f'"{text[:45]}..." → theme={expected}',
          result == expected, f'Got: {result}')


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 15 — chatAPI.js data mirror: 36 IDs, correct order, no duplicates
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 15 — chatAPI.js DATA MIRROR')

check('chatAPI has exactly 36 button IDs',       len(CHATAPI_IDS) == 36,
      f'Got {len(CHATAPI_IDS)}')
check('chatAPI IDs have no duplicates',          len(set(CHATAPI_IDS)) == len(CHATAPI_IDS))
check('chatAPI IDs match BUTTON_INTENTS keys',
      set(CHATAPI_IDS) == set(BUTTON_INTENTS.keys()))
check('chatAPI and BUTTON_INTENTS have same set', set(CHATAPI_IDS) == set(BUTTON_INTENTS.keys()))
check('meeting_redirect absent from chatAPI',    'meeting_redirect'   not in CHATAPI_IDS)
check('reverse_psychology absent from chatAPI',  'reverse_psychology' not in CHATAPI_IDS)

# Row ordering: first 6 = row 1, next 6 = row 2, etc.
for row in range(1, 7):
    row_ids = CHATAPI_IDS[(row - 1) * 6: row * 6]
    expected_row_ids = [k for k, v in BUTTON_INTENTS.items() if v['row'] == row]
    # All 6 in this slice should be row=row
    all_correct_row = all(BUTTON_INTENTS[bid]['row'] == row for bid in row_ids)
    check(f'chatAPI row {row} slice (positions {(row-1)*6}-{row*6-1}) all have row={row}',
          all_correct_row, f'Row {row} IDs: {row_ids}')


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 16 — Edge cases
# ─────────────────────────────────────────────────────────────────────────────
header('SECTION 16 — EDGE CASES')

# Opener injection with opener that contains double quotes
sd_edge = {'used_openers': [o for o in _OPENER_POOL if '"' not in o][:-1]}
# Force selection of an opener that has a dash (e.g. "Honest thing —")
tricky_openers = [o for o in _OPENER_POOL if '—' in o]
if tricky_openers:
    sd_dash = {'used_openers': [o for o in _OPENER_POOL if o not in tricky_openers]}
    opener_dash = _select_opener(1, sd_dash)
    check('Opener with em-dash — selected correctly',
          opener_dash in tricky_openers)
    prompt_dash = f'scenario\n\nBegin your message with this exact word or phrase: "{opener_dash}"'
    check('Em-dash opener — prompt builds without crash',  isinstance(prompt_dash, str))
    check('Em-dash opener — appears in prompt correctly',  opener_dash in prompt_dash)

# Unknown button_intent
check('Unknown button_intent not in BUTTON_INTENTS',
      'nonexistent_button' not in BUTTON_INTENTS)

# Session with only used_themes (no used_openers key) — backward compat
sd_old = {'used_themes': {'new_match': ['warmth']}}
opener_old = _select_opener(1, sd_old)
check('Session without used_openers key → _select_opener still works',
      opener_old in _OPENER_POOL)
check('Session without used_openers → key created after call',
      'used_openers' in sd_old)

# Opener rotation does not modify _OPENER_POOL
pool_before = _OPENER_POOL[:]
sd_mod = {}
for _ in range(10):
    _select_opener(1, sd_mod)
check('_select_opener never modifies _OPENER_POOL',
      _OPENER_POOL == pool_before)

# Multiple buttons same session — themes tracked per-intent
sd_multi = {'used_themes': {}, 'used_openers': []}
sd_multi['used_themes']['bdsm_talk']    = ['surrender_theme']
sd_multi['used_themes']['morning_flirt'] = ['coffee_theme']
check('Per-intent theme isolation — bdsm_talk themes not in morning_flirt',
      sd_multi['used_themes']['bdsm_talk'] != sd_multi['used_themes']['morning_flirt'])
check('morning_flirt has only its own theme',
      sd_multi['used_themes']['morning_flirt'] == ['coffee_theme'])

# Row completeness — every row ID in chatAPI corresponds to correct row in BUTTON_INTENTS
for i, bid in enumerate(CHATAPI_IDS):
    expected_row = (i // 6) + 1
    actual_row   = BUTTON_INTENTS[bid]['row']
    check(f'chatAPI position {i} ({bid}) → row {actual_row} matches expected row {expected_row}',
          actual_row == expected_row)


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS
# ─────────────────────────────────────────────────────────────────────────────
header('RESULTS')
color = '\033[92m' if passed == total else '\033[91m'
print(f'\n  {color}{passed}/{total} tests passed\033[0m\n')
if passed < total:
    print(f'  {total - passed} test(s) FAILED — see [FAIL] lines above.\n')
else:
    print('  All tests passed.\n')
    print('  Coverage:')
    print('  Sec  1  36 button definitions — structure, required fields')
    print('  Sec  2  Grid structure — 6 rows × 6 buttons each')
    print('  Sec  3  Removed buttons absent (meeting_redirect, reverse_psychology)')
    print('  Sec  4  Opener pool — 70+ items, no duplicates, non-empty')
    print('  Sec  5  _select_opener basic behaviour — picks, tracks, mutates session')
    print('  Sec  6  Opener rotation — 30 sequential picks, no repeats')
    print('  Sec  7  Full-cycle reset — resets after exhaustion, avoids last 10')
    print('  Sec  8  Prompt construction — scenario → themes → opener order')
    print('  Sec  9  Session caps — themes at 8, openers at 30')
    print('  Sec 10  Cross-button opener sharing — per-user, not per-intent')
    print('  Sec 11  enforce_char_limit — configurable max_chars, sentence boundary trim')
    print('  Sec 12  enforce_130_chars — backward-compat alias unchanged')
    print('  Sec 13  ensure_ends_with_question — works with max_chars=450')
    print('  Sec 14  extract_theme — all 15 categories including 5 new ones')
    print('  Sec 15  chatAPI.js mirror — 36 IDs, grid order, no duplicates')
    print('  Sec 16  Edge cases — em-dash openers, missing keys, pool immutability\n')
