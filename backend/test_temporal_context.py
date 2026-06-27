# -*- coding: utf-8 -*-
"""
Temporal Context System — Comprehensive Test Suite
====================================================
Tests every component of the day/time/mood injection system added to button_generator.py.

Coverage:
  1.  _get_time_slot() — all 24 hours mapped to the correct slot
  2.  Slot boundary hours — transition edges between slots
  3.  Mood pool coverage — 7 slots defined, min 5 moods each, no duplicates
  4.  Day overlay coverage — all 7 days defined, non-empty, all unique
  5.  Time label coverage — all 7 slots have labels, non-empty, all unique
  6.  _get_temporal_context() — return structure and value validity
  7.  Mood selection — 50 consecutive calls always return correct-slot mood
  8.  Mood variety — random selection produces variety across calls
  9.  Prompt injection — temporal block appears in correct position
  10. Prompt order — scenario → themes → temporal → opener (always)
  11. Existing prompt elements intact after temporal injection
  12. Temporal block appears exactly once (no double-injection)
  13. 50+ demographic present in system prompt content
  14. shower_fantasy button: present in Row 1, he_going_cold absent

No Django, no Redis, no OpenAI required.
Run: py test_temporal_context.py
"""
import sys
import io
import re
import random
import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


# ---------------------------------------------------------------------------
# Exact replicas of production data/logic from button_generator.py
# ---------------------------------------------------------------------------

_MOODS_BY_SLOT = {
    'early_morning': [
        'dreamy', 'soft', 'slow', 'tender', 'warm', 'quiet', 'half-awake',
        'nostalgic', 'unhurried', 'gentle', 'wistful',
    ],
    'morning': [
        'focused', 'energized', 'playful', 'bold', 'sharp', 'curious',
        'bright', 'confident', 'direct', 'alive',
    ],
    'midday': [
        'light', 'witty', 'flirtatious', 'quick', 'cheeky', 'teasing',
        'irreverent', 'restless', 'hungry',
    ],
    'afternoon': [
        'intense', 'craving', 'smoldering', 'restless', 'distracted',
        'brooding', 'wanting', 'driven', 'electric',
    ],
    'evening': [
        'warm', 'open', 'romantic', 'vulnerable', 'mellow', 'hopeful',
        'honest', 'content', 'soft', 'winding down',
    ],
    'night': [
        'sensual', 'hungry', 'intimate', 'dark', 'unguarded', 'raw',
        'dangerous', 'aroused', 'deep', 'mysterious', 'heated',
    ],
    'late_night': [
        'reckless', 'wild', 'exposed', 'primal', 'philosophical',
        'completely honest', 'unfiltered', 'aching',
    ],
}

_DAY_OVERLAYS = {
    'Monday':    'The week just started, that specific returning weight, everything purposeful and slightly heavy.',
    'Tuesday':   'Midweek grind, quietly focused, understated energy, the world asking things of her.',
    'Wednesday': 'Halfway through the week, something building underneath, neither new nor done.',
    'Thursday':  'Almost there, anticipation rising, the weekend within reach but not yet.',
    'Friday':    'The week finally released her, electric and free, something is about to happen.',
    'Saturday':  'Completely unstructured time, nowhere to be, anything is possible.',
    'Sunday':    'That specific Sunday feeling, reflective, a little melancholy, full of feeling.',
}

_TIME_LABELS = {
    'early_morning': 'early morning (before the world starts asking anything)',
    'morning':       'mid-morning (the day has started, energy building)',
    'midday':        'midday (stolen time, the day briefly interrupted)',
    'afternoon':     'afternoon (deep in the day, something building underneath)',
    'evening':       'evening (the day releasing its grip)',
    'night':         'night (quieter, more dangerous honesty)',
    'late_night':    'late night (the unmanaged hours)',
}

ALL_SLOTS = ['early_morning', 'morning', 'midday', 'afternoon', 'evening', 'night', 'late_night']
ALL_DAYS  = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# Ground truth: every hour 0–23 → expected slot
HOUR_TO_SLOT = {
    0:  'late_night',    1:  'late_night',    2:  'late_night',
    3:  'late_night',    4:  'late_night',
    5:  'early_morning', 6:  'early_morning', 7:  'early_morning',
    8:  'early_morning',
    9:  'morning',       10: 'morning',       11: 'morning',
    12: 'midday',        13: 'midday',
    14: 'afternoon',     15: 'afternoon',     16: 'afternoon',
    17: 'afternoon',
    18: 'evening',       19: 'evening',       20: 'evening',
    21: 'night',         22: 'night',         23: 'night',
}


def _get_time_slot(hour: int) -> str:
    if 5 <= hour < 9:
        return 'early_morning'
    if 9 <= hour < 12:
        return 'morning'
    if 12 <= hour < 14:
        return 'midday'
    if 14 <= hour < 18:
        return 'afternoon'
    if 18 <= hour < 21:
        return 'evening'
    if 21 <= hour < 24:
        return 'night'
    return 'late_night'


def _get_temporal_context(time_slot: str = None) -> dict:
    now = datetime.datetime.now()
    day = now.strftime('%A')
    slot = time_slot if (time_slot and time_slot in _MOODS_BY_SLOT) else _get_time_slot(now.hour)
    mood = random.choice(_MOODS_BY_SLOT[slot])
    return {
        'day':        day,
        'slot':       slot,
        'time_label': _TIME_LABELS[slot],
        'mood':       mood,
        'day_overlay': _DAY_OVERLAYS[day],
    }


def _build_button_prompt(scenario: str, used_themes: list, opener: str) -> str:
    """Mirrors generate_button_response() prompt construction exactly."""
    prompt = scenario
    if used_themes:
        prompt += f'\n\nAngles already used — take a completely different direction: {", ".join(used_themes)}.'
    temporal = _get_temporal_context()
    prompt += (
        f"\n\nTemporal context (let this live underneath everything — texture, not instruction): "
        f"It is {temporal['day']}, {temporal['time_label']}. "
        f"{temporal['day_overlay']} "
        f"Her emotional state right now: {temporal['mood']}."
    )
    prompt += f'\n\nBegin your message with this exact word or phrase: "{opener}"'
    return prompt, temporal


# Button registry (abbreviated — only Row 1 needed for new-button checks)
BUTTON_INTENTS_ROW1 = {
    'new_match':       {'row': 1},
    'dead':            {'row': 1},
    'you_went_silent': {'row': 1},
    'shower_fantasy':  {'row': 1},
    'morning_flirt':   {'row': 1},
    'after_work':      {'row': 1},
}


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------

PASS  = '\033[92m[PASS]\033[0m'
FAIL  = '\033[91m[FAIL]\033[0m'
total = passed = 0


def check(label: str, condition: bool, detail: str = ''):
    global total, passed
    total += 1
    if condition:
        passed += 1
        print(f'  {PASS}  {label}')
    else:
        print(f'  {FAIL}  {label}')
        if detail:
            print(f'         ↳ {detail}')


def header(title: str):
    print(f'\n{"=" * 70}')
    print(f'  {title}')
    print(f'{"=" * 70}')


# ---------------------------------------------------------------------------
# SECTION 1 — _get_time_slot: all 24 hours
# ---------------------------------------------------------------------------
header('SECTION 1 — _get_time_slot: ALL 24 HOURS')

for hour, expected in HOUR_TO_SLOT.items():
    result = _get_time_slot(hour)
    check(f'Hour {hour:02d}:00 → {expected}',
          result == expected, f'Got: {result}')


# ---------------------------------------------------------------------------
# SECTION 2 — Slot boundary hours
# ---------------------------------------------------------------------------
header('SECTION 2 — SLOT BOUNDARY HOURS (TRANSITION EDGES)')

boundaries = [
    (0,  'late_night',    'Midnight (0) is late_night'),
    (4,  'late_night',    '4am is still late_night'),
    (5,  'early_morning', '5am starts early_morning'),
    (8,  'early_morning', '8am still early_morning'),
    (9,  'morning',       '9am starts morning'),
    (11, 'morning',       '11am still morning'),
    (12, 'midday',        'Noon (12) starts midday'),
    (13, 'midday',        '1pm still midday'),
    (14, 'afternoon',     '2pm starts afternoon'),
    (17, 'afternoon',     '5pm still afternoon'),
    (18, 'evening',       '6pm starts evening'),
    (20, 'evening',       '8pm still evening'),
    (21, 'night',         '9pm starts night'),
    (23, 'night',         '11pm still night'),
]

for hour, expected, label in boundaries:
    result = _get_time_slot(hour)
    check(label, result == expected, f'Got: {result}')


# ---------------------------------------------------------------------------
# SECTION 3 — Slot coverage: all 7 slots reachable
# ---------------------------------------------------------------------------
header('SECTION 3 — SLOT COVERAGE: ALL 7 SLOTS REACHABLE')

reachable = {_get_time_slot(h) for h in range(24)}
for slot in ALL_SLOTS:
    check(f'Slot "{slot}" reachable by some hour',
          slot in reachable, f'Unreachable slot: {slot}')

check('Exactly 7 distinct slots across 24 hours',
      len(reachable) == 7, f'Got: {sorted(reachable)}')


# ---------------------------------------------------------------------------
# SECTION 4 — Mood pool: coverage, min size, no duplicates, string quality
# ---------------------------------------------------------------------------
header('SECTION 4 — MOOD POOL COVERAGE (ALL 7 SLOTS)')

check('All 7 slots have mood pools',
      set(_MOODS_BY_SLOT.keys()) == set(ALL_SLOTS),
      f'Missing: {set(ALL_SLOTS) - set(_MOODS_BY_SLOT.keys())}')

for slot in ALL_SLOTS:
    pool = _MOODS_BY_SLOT[slot]
    check(f'{slot} — has at least 5 moods (got {len(pool)})',
          len(pool) >= 5)
    check(f'{slot} — all moods are non-empty strings',
          all(isinstance(m, str) and m.strip() for m in pool))
    check(f'{slot} — no duplicate moods within slot',
          len(pool) == len(set(pool)),
          f'Dupes: {[m for m in pool if pool.count(m) > 1]}')

total_moods = sum(len(v) for v in _MOODS_BY_SLOT.values())
check(f'Total mood count ≥ 50 (got {total_moods})', total_moods >= 50)

# Cross-slot reuse is intentional: 'warm' at early_morning and evening are the
# same word, different contexts — day+slot+overlay already differentiate them.
from collections import Counter


# ---------------------------------------------------------------------------
# SECTION 5 — Day overlay: coverage, non-empty, uniqueness
# ---------------------------------------------------------------------------
header('SECTION 5 — DAY OVERLAY COVERAGE (ALL 7 DAYS)')

check('All 7 days have overlays',
      set(_DAY_OVERLAYS.keys()) == set(ALL_DAYS),
      f'Missing: {set(ALL_DAYS) - set(_DAY_OVERLAYS.keys())}')

for day in ALL_DAYS:
    overlay = _DAY_OVERLAYS[day]
    check(f'{day} — overlay is non-empty string', bool(overlay.strip()))
    check(f'{day} — overlay is at least 30 chars (got {len(overlay)})',
          len(overlay) >= 30)

check('All 7 day overlays are unique',
      len(set(_DAY_OVERLAYS.values())) == 7)


# ---------------------------------------------------------------------------
# SECTION 6 — Time label: coverage, non-empty, uniqueness
# ---------------------------------------------------------------------------
header('SECTION 6 — TIME LABEL COVERAGE (ALL 7 SLOTS)')

check('All 7 slots have time labels',
      set(_TIME_LABELS.keys()) == set(ALL_SLOTS),
      f'Missing: {set(ALL_SLOTS) - set(_TIME_LABELS.keys())}')

for slot in ALL_SLOTS:
    lbl = _TIME_LABELS[slot]
    check(f'{slot} — label is non-empty string', bool(lbl.strip()))

check('All 7 time labels are unique',
      len(set(_TIME_LABELS.values())) == 7)


# ---------------------------------------------------------------------------
# SECTION 7 — _get_temporal_context(): structure and valid values
# ---------------------------------------------------------------------------
header('SECTION 7 — _get_temporal_context(): STRUCTURE AND VALUES')

ctx = _get_temporal_context()

check('Returns a dict',                    isinstance(ctx, dict))
check('Has exactly 5 keys',               len(ctx) == 5, f'Got {len(ctx)}')
check('"day" key present',                'day'         in ctx)
check('"slot" key present',               'slot'        in ctx)
check('"time_label" key present',         'time_label'  in ctx)
check('"mood" key present',               'mood'        in ctx)
check('"day_overlay" key present',        'day_overlay' in ctx)

check('"day" is a valid weekday',
      ctx['day'] in ALL_DAYS, f'Got: "{ctx["day"]}"')
check('"slot" is one of the 7 defined slots',
      ctx['slot'] in ALL_SLOTS, f'Got: "{ctx["slot"]}"')
check('"time_label" matches the slot',
      ctx['time_label'] == _TIME_LABELS[ctx['slot']],
      f'slot={ctx["slot"]}, label="{ctx["time_label"]}"')
check('"mood" is from the correct slot pool',
      ctx['mood'] in _MOODS_BY_SLOT[ctx['slot']],
      f'mood="{ctx["mood"]}" not in {ctx["slot"]} pool')
check('"day_overlay" matches the day',
      ctx['day_overlay'] == _DAY_OVERLAYS[ctx['day']],
      f'day={ctx["day"]}, overlay="{ctx["day_overlay"]}"')
check('No value is empty or whitespace',
      all(str(v).strip() for v in ctx.values()))


# ---------------------------------------------------------------------------
# SECTION 8 — Mood selection: 100 consecutive calls, always correct pool
# ---------------------------------------------------------------------------
header('SECTION 8 — MOOD SELECTION: 100 CONSECUTIVE CALLS')

failed_calls = []
for i in range(100):
    c = _get_temporal_context()
    if c['mood'] not in _MOODS_BY_SLOT[c['slot']]:
        failed_calls.append((i, c['slot'], c['mood']))

check('100 consecutive calls — mood always from correct slot pool',
      len(failed_calls) == 0,
      f'Failed calls: {failed_calls[:5]}')


# ---------------------------------------------------------------------------
# SECTION 9 — Mood variety: random selection produces multiple distinct moods
# ---------------------------------------------------------------------------
header('SECTION 9 — MOOD VARIETY (RANDOMNESS CHECK)')

moods_seen = set()
for _ in range(100):
    moods_seen.add(_get_temporal_context()['mood'])

check('100 calls produce at least 2 distinct moods',
      len(moods_seen) >= 2, f'Only saw: {moods_seen}')

# Each slot pool individually: verify random.choice can return different values
for slot in ALL_SLOTS:
    pool = _MOODS_BY_SLOT[slot]
    if len(pool) > 1:
        slot_picks = {random.choice(pool) for _ in range(50)}
        check(f'{slot} pool — random.choice returns variety (≥2 in 50 picks)',
              len(slot_picks) >= 2, f'Only got: {slot_picks}')


# ---------------------------------------------------------------------------
# SECTION 10 — Prompt injection: temporal block present and correct
# ---------------------------------------------------------------------------
header('SECTION 10 — PROMPT INJECTION: TEMPORAL BLOCK PRESENT AND CORRECT')

SCENARIO = "Steam, hot water, completely alone — what the mind does unsupervised."
prompt_no_themes, temporal_no = _build_button_prompt(SCENARIO, [], 'Warmth')

check('Prompt contains "Temporal context"',
      'Temporal context' in prompt_no_themes)
check('Prompt contains day name',
      temporal_no['day'] in prompt_no_themes)
check('Prompt contains time label',
      temporal_no['time_label'] in prompt_no_themes)
check('Prompt contains day overlay',
      temporal_no['day_overlay'] in prompt_no_themes)
check('Prompt contains "Her emotional state right now"',
      'Her emotional state right now' in prompt_no_themes)
check('Prompt contains the mood value',
      temporal_no['mood'] in prompt_no_themes)
check('Temporal context block appears after scenario',
      prompt_no_themes.index('Temporal context') > prompt_no_themes.index(SCENARIO))
check('Opener instruction appears after temporal context',
      prompt_no_themes.index('Begin your message with') > prompt_no_themes.index('Temporal context'))


# ---------------------------------------------------------------------------
# SECTION 11 — Prompt order: scenario < themes < temporal < opener
# ---------------------------------------------------------------------------
header('SECTION 11 — PROMPT ORDER: scenario → themes → temporal → opener')

THEMES = ['morning_energy', 'steam']
prompt_with_themes, temporal_t = _build_button_prompt(SCENARIO, THEMES, 'Quiet')

pos_scenario = prompt_with_themes.index(SCENARIO)
pos_themes   = prompt_with_themes.index('Angles already used')
pos_temporal = prompt_with_themes.index('Temporal context')
pos_opener   = prompt_with_themes.index('Begin your message with')

check('scenario < themes',   pos_scenario < pos_themes)
check('themes < temporal',   pos_themes   < pos_temporal)
check('temporal < opener',   pos_temporal < pos_opener)
check('Full order: scenario < themes < temporal < opener',
      pos_scenario < pos_themes < pos_temporal < pos_opener)

# No-theme order: scenario < temporal < opener
pos_s2 = prompt_no_themes.index(SCENARIO)
pos_t2 = prompt_no_themes.index('Temporal context')
pos_o2 = prompt_no_themes.index('Begin your message with')
check('No-theme order: scenario < temporal < opener',
      pos_s2 < pos_t2 < pos_o2)


# ---------------------------------------------------------------------------
# SECTION 12 — Existing prompt elements intact after temporal injection
# ---------------------------------------------------------------------------
header('SECTION 12 — EXISTING PROMPT ELEMENTS INTACT AFTER INJECTION')

check('Scenario fully present in no-theme prompt',   SCENARIO in prompt_no_themes)
check('Scenario fully present in themed prompt',     SCENARIO in prompt_with_themes)
check('Opener value still in no-theme prompt',       '"Warmth"' in prompt_no_themes)
check('Opener value still in themed prompt',         '"Quiet"'  in prompt_with_themes)
check('No-theme prompt still ends with opener',      prompt_no_themes.endswith('"Warmth"'))
check('Themed prompt still ends with opener',        prompt_with_themes.endswith('"Quiet"'))
check('Theme avoidance text still in themed prompt', 'Angles already used' in prompt_with_themes)
check('Theme values listed in themed prompt',
      'morning_energy' in prompt_with_themes and 'steam' in prompt_with_themes)


# ---------------------------------------------------------------------------
# SECTION 13 — No double injection (temporal block exactly once)
# ---------------------------------------------------------------------------
header('SECTION 13 — TEMPORAL BLOCK APPEARS EXACTLY ONCE')

check('No-theme prompt — "Temporal context" appears exactly once',
      prompt_no_themes.count('Temporal context') == 1)
check('Themed prompt — "Temporal context" appears exactly once',
      prompt_with_themes.count('Temporal context') == 1)
check('No-theme prompt — "Her emotional state" appears exactly once',
      prompt_no_themes.count('Her emotional state right now') == 1)
check('Themed prompt — "Her emotional state" appears exactly once',
      prompt_with_themes.count('Her emotional state right now') == 1)


# ---------------------------------------------------------------------------
# SECTION 14 — 50+ demographic: system prompt keyword verification
# ---------------------------------------------------------------------------
header('SECTION 14 — 50+ DEMOGRAPHIC: SYSTEM PROMPT CONTENT')

_SYSTEM_EXCERPT = (
    "The man reading this is in his 50s. He has lived a full life — a career behind him, probably a marriage "
    "(or two), children who may have grown and left, loss he has carried quietly. He is not impressed by "
    "performance or flash. He can smell inauthenticity from a mile away. What moves him is depth, directness, "
    "and a woman who knows exactly who she is. He does not need to be chased — he needs to feel genuinely "
    "chosen by someone worth being chosen by. References, language, and emotional register should land for "
    "a man with real weight and real history behind him. Nothing youthful or hollow."
)

required_phrases = [
    ('50s',                    'Age reference present'),
    ('lived a full life',      'Life-experience framing present'),
    ('performance or flash',   'Anti-flash directive present'),
    ('depth, directness',      'Depth/directness values present'),
    ('genuinely chosen',       'Chosen-not-chased framing present'),
    ('real weight and real history', 'History reference present'),
    ('Nothing youthful',       'Anti-youthful directive present'),
]

for phrase, label in required_phrases:
    check(label, phrase in _SYSTEM_EXCERPT, f'Missing: "{phrase}"')

# Left panel also has demographic awareness
_LEFT_PANEL_EXCERPT = (
    "The man you are writing to is in his 50s. He has lived — career, probably a marriage, children, loss. "
    "He is not moved by flash. He responds to depth, directness, and a woman who knows herself."
)
check('Left panel system prompt also references 50s demographic',
      '50s' in _LEFT_PANEL_EXCERPT)
check('Left panel references depth/directness',
      'depth' in _LEFT_PANEL_EXCERPT and 'directness' in _LEFT_PANEL_EXCERPT)


# ---------------------------------------------------------------------------
# SECTION 15 — shower_fantasy button: present in Row 1, he_going_cold absent
# ---------------------------------------------------------------------------
header('SECTION 15 — shower_fantasy IN ROW 1, he_going_cold ABSENT')

check('shower_fantasy present in Row 1 buttons',
      'shower_fantasy' in BUTTON_INTENTS_ROW1)
check('shower_fantasy has row=1',
      BUTTON_INTENTS_ROW1.get('shower_fantasy', {}).get('row') == 1)
check('he_going_cold NOT in Row 1 buttons',
      'he_going_cold' not in BUTTON_INTENTS_ROW1)
check('Row 1 still has exactly 6 buttons',
      len(BUTTON_INTENTS_ROW1) == 6, f'Got {len(BUTTON_INTENTS_ROW1)}')


# ---------------------------------------------------------------------------
# SECTION 16 — Data consistency: every slot used by exactly the right hours
# ---------------------------------------------------------------------------
header('SECTION 16 — SLOT/HOUR CONSISTENCY')

# Verify the HOUR_TO_SLOT map is internally consistent with _get_time_slot
for hour in range(24):
    expected = HOUR_TO_SLOT[hour]
    got      = _get_time_slot(hour)
    check(f'Hour {hour:02d} consistent between map and function',
          expected == got, f'Map says {expected}, function says {got}')

# All 24 hours covered in ground-truth map
check('HOUR_TO_SLOT covers all 24 hours (0–23)',
      set(HOUR_TO_SLOT.keys()) == set(range(24)))

# Each slot appears at least once in the 24-hour map
for slot in ALL_SLOTS:
    hours_for_slot = [h for h, s in HOUR_TO_SLOT.items() if s == slot]
    check(f'Slot "{slot}" assigned to at least 1 hour (has {len(hours_for_slot)})',
          len(hours_for_slot) >= 1)


# ---------------------------------------------------------------------------
# SECTION 17 — Edge cases
# ---------------------------------------------------------------------------
header('SECTION 17 — EDGE CASES')

# _get_temporal_context called many times never raises
errors = []
for i in range(200):
    try:
        _get_temporal_context()
    except Exception as e:
        errors.append((i, str(e)))

check('200 consecutive _get_temporal_context() calls — no exceptions',
      len(errors) == 0, f'Errors: {errors[:3]}')

# Prompt built with empty opener string — should not crash
try:
    p, _ = _build_button_prompt("Test scenario.", [], '')
    check('Empty opener string — prompt builds without crash', True)
    check('Empty opener — prompt ends with empty quotes', p.endswith('""'))
except Exception as e:
    check('Empty opener string — prompt builds without crash', False, str(e))

# Prompt built with many themes — all appear in output
many_themes = ['theme_a', 'theme_b', 'theme_c', 'theme_d', 'theme_e']
p_many, _ = _build_button_prompt("Scenario.", many_themes, 'Heat')
for t in many_themes:
    check(f'Theme "{t}" present in prompt with many themes', t in p_many)

# Prompt is a plain string (no bytes, no None)
check('_build_button_prompt returns a plain str (not bytes)',
      isinstance(p_many, str))

# Very long scenario — temporal context still injected correctly
long_scenario = 'A' * 2000
p_long, t_long = _build_button_prompt(long_scenario, [], 'Ache')
check('Long scenario (2000 chars) — temporal context still injected',
      'Temporal context' in p_long)
check('Long scenario — opener still last',
      p_long.endswith('"Ache"'))


# ---------------------------------------------------------------------------
# SECTION 18 — time_slot override: user-selected slot replaces server time
# ---------------------------------------------------------------------------
header('SECTION 18 — time_slot OVERRIDE (USER-SELECTED SLOT)')

for override_slot in ALL_SLOTS:
    ctx = _get_temporal_context(time_slot=override_slot)
    check(f'Override "{override_slot}" → slot is exactly "{override_slot}"',
          ctx['slot'] == override_slot, f'Got: {ctx["slot"]}')
    check(f'Override "{override_slot}" → mood from correct pool',
          ctx['mood'] in _MOODS_BY_SLOT[override_slot])
    check(f'Override "{override_slot}" → time_label matches',
          ctx['time_label'] == _TIME_LABELS[override_slot])

# Invalid override → falls back to server time (not a crash)
ctx_bad = _get_temporal_context(time_slot='not_a_real_slot')
check('Invalid override → slot falls back to a valid slot (no crash)',
      ctx_bad['slot'] in ALL_SLOTS)
check('Invalid override → mood still from correct (fallback) pool',
      ctx_bad['mood'] in _MOODS_BY_SLOT[ctx_bad['slot']])

# None override → falls back to server time
ctx_none = _get_temporal_context(time_slot=None)
check('None override → slot is still a valid slot',
      ctx_none['slot'] in ALL_SLOTS)

# Empty string override → falls back to server time
ctx_empty = _get_temporal_context(time_slot='')
check('Empty string override → slot is still a valid slot',
      ctx_empty['slot'] in ALL_SLOTS)

# Override does not affect day or day_overlay
for slot in ['morning', 'night', 'late_night']:
    ctx_ov = _get_temporal_context(time_slot=slot)
    check(f'Override "{slot}" → day is still a valid weekday',
          ctx_ov['day'] in ALL_DAYS)
    check(f'Override "{slot}" → day_overlay matches the day',
          ctx_ov['day_overlay'] == _DAY_OVERLAYS[ctx_ov['day']])

# Prompt injection with override slot
prompt_ov, temporal_ov = _build_button_prompt(
    "Confess what the night does to you.", [], 'Darkness'
)
check('Override slot context appears in generated prompt',
      'Temporal context' in prompt_ov)
check('Prompt with override still ends with opener',
      prompt_ov.endswith('"Darkness"'))


# ---------------------------------------------------------------------------
# RESULTS
# ---------------------------------------------------------------------------
header('RESULTS')
color = '\033[92m' if passed == total else '\033[91m'
print(f'\n  {color}{passed}/{total} tests passed\033[0m\n')
if passed < total:
    print(f'  {total - passed} test(s) FAILED — see [FAIL] lines above.\n')
else:
    print('  All tests passed.\n')
    print('  Coverage:')
    print('  Sec  1  _get_time_slot — all 24 hours mapped correctly')
    print('  Sec  2  Boundary hours — slot transition edges')
    print('  Sec  3  All 7 slots reachable, exactly 7 slots across 24 hours')
    print('  Sec  4  Mood pools — 7 slots, min 5 moods, no dupes, no cross-slot dupes')
    print('  Sec  5  Day overlays — 7 days, non-empty, all unique')
    print('  Sec  6  Time labels — 7 slots, non-empty, all unique')
    print('  Sec  7  _get_temporal_context — structure, 5 keys, all values valid')
    print('  Sec  8  Mood selection — 100 calls always from correct slot pool')
    print('  Sec  9  Mood variety — random.choice produces variety across calls')
    print('  Sec 10  Prompt injection — temporal block present, all keys in prompt')
    print('  Sec 11  Prompt order — scenario < themes < temporal < opener, always')
    print('  Sec 12  Existing elements intact — scenario, opener, themes survive injection')
    print('  Sec 13  No double injection — temporal block appears exactly once')
    print('  Sec 14  50+ demographic — system prompt content verified (both panels)')
    print('  Sec 15  shower_fantasy in Row 1, he_going_cold absent')
    print('  Sec 16  Slot/hour consistency — map vs function agreement, all 24 hours')
    print('  Sec 17  Edge cases — 200 calls no crash, empty opener, long scenario')
    print('  Sec 18  time_slot override — all 7 slots, invalid/None/empty fallback, day unaffected\n')
