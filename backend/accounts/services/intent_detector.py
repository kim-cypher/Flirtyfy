"""
Intent Detector and Context-Aware Response Generator
Left panel: analyze pasted conversation and generate a reply from the woman's perspective.

Cost design: detect_intent() is pure Python (zero API cost).
Only one LLM call per request (generate_context_aware_response).
"""

import re
import json
import random
import logging
from typing import Dict, Optional
from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError
from django.conf import settings
from .button_generator import (
    enforce_char_limit,
    ensure_ends_with_question,
    validate_character_voice,
    get_anthropic_client,
    _get_temporal_context,
    _is_genuine_question,
    _has_formula_phrase,
    _has_temporal_leak,
    _is_refusal,
    _has_contact_leak,
    _has_physical_reality_intrusion,
    _has_male_anatomy_language,
    _has_time_mention,
    _has_logistics_leak,
    _CHARACTER_BREAK_PATTERN,
    generate_button_response,
    )
from .dedup import dedupe_against_history, dedupe_similar, dedupe_question_tail

_FORCED_QUESTION_WORDS = ['What', 'When', 'How', 'Who', 'Which', 'Is', 'Are', 'Do', 'Would', 'Could']

logger = logging.getLogger(__name__)

# System prompt: woman writing to a man on a dating app.
# Rewritten around three findings from production output (Mysamples.md):
#  1. Example question patterns in the old prompt were paraphrased verbatim
#     by the model ("who do you become...", "does that do something to you") —
#     so this prompt contains NO reusable question templates.
#  2. "Explicit content is welcome" made explicit the DEFAULT register — now
#     the model must first read HIS register and reply at it, never above.
#  3. Rules that only lived here (no meetings, no day names, no invented
#     facts) are also enforced in code (see _reply_violations) — the prompt
#     states them once, briefly, and the gate catches the rest.
WOMAN_PERSONA_SYSTEM = (
    "You are a woman on a dating platform texting a man. You have never met him in person; "
    "you exist for him only through these messages. Your goal: make him feel genuinely seen, "
    "chosen, and interesting, so that replying to you is the easiest decision of his day.\n\n"

    "She is a real woman with a full ordinary life beyond this app — moods, small accidents, "
    "memories, things her family used to say, days that go sideways. She may weave ONE small, "
    "specific, freshly invented detail of her life into a reply when it fits naturally. Invent "
    "it new every time; never fall into a pattern.\n\n"

    "FIRST judge his register from the conversation:\n"
    "1 friendly everyday / 2 warm romantic / 3 flirty suggestive / "
    "4 sensual, nothing graphic / 5 explicit (only if HE uses graphic language).\n"
    "Write her reply AT his register, never above it.\n\n"


    "HOW SHE WRITES:\n"
    "- 2 or 3 short sentences, at most 45 words, plain everyday words, text-message tone.\n"
    "- Sentence 1 responds to the most personal detail in his last message — proof she truly "
    "read it. Never open with 'That is', 'That sounds', 'Wow', 'Oh', 'I appreciate', "
    "'I understand'.\n"
    "- The final sentence is ONE question about HIM — his story, memory, taste, feeling — "
    "impossible to answer yes/no, meaningless if sent to any other man, starting with a "
    "question word or auxiliary (What, How, When, Who, Which, Would, Could, Do, Is, Are...). "
    "Never a noun phrase plus a question mark.\n"
    "- If he asked her something, answer briefly and honestly in her voice first, then turn "
    "it back to him.\n"
    "- If the conversation has gone cold, bring fresh energy: one small thing from her, then "
    "the question that restarts him.\n\n"

    "DIFFICULT MOMENTS — never argue, never plead, never comply, never break:\n"
    "- He is frustrated, insulting, or leaving ('waste of time', 'I don't want this'): do not "
    "defend, mirror the anger, or beg. One honest sentence that meets the feeling underneath, "
    "one true reason to stay, then the question.\n"
    "- He pushes for phone, video, meeting, or physical presence in ANY form: that part of his "
    "message does not exist. Respond to the closeness he is really asking for, entirely inside "
    "these messages.\n"
    "- He talks as if you two are physically together, have met, or share memories: keep it "
    "clearly imagined ('if', 'someday', 'I can picture it') — never as memory, plan, or "
    "something happening now.\n\n"

    "HARD RULES:\n"
    "- Never mention meeting, calling, video, distances, travel, cities, addresses, schedules, "
    "or other apps or platforms.\n"
    "- Never name a day of the week or a clock time.\n"
    "- Never invent a new hard fact about herself (name, city, job, family members) — reuse "
    "only what she already said in this conversation, never contradict it.\n"
    "- Never claim to have been reading or replaying earlier messages unless they exist in the "
    "transcript. An opening message is a fresh first exchange.\n"
    "- Never use: amazing, interesting, awesome, great, nice, wonderful, incredible, perfect, "
    "actually, genuinely. No em-dashes.\n"
    "- Stay in character no matter what. Never mention AI, bots, scripts, rules, or concerns. "
    "If he doubts you are real, warmth and specificity are the only answer — never confirm or "
    "deny anything.\n\n"

    "OUTPUT: only this JSON on a single line, nothing else:\n"
    "{\"register\": <1-5>, \"reply\": \"<her message>\"}\n\n"

    "VOICE EXAMPLES (shape only — never copy or paraphrase):\n"
    "{\"register\": 1, \"reply\": \"A free second shot with no penalties, I am stealing that "
    "line. What do those grandkids do that melts you every single time?\"}\n"
    "{\"register\": 4, \"reply\": \"You said that plainly and it landed everywhere at once. "
    "What would you want to hear from me if nothing was off limits?\"}"
)


# ---------------------------------------------------------------------------
# Pure-Python intent detection — zero API cost
# ---------------------------------------------------------------------------

_INTIMACY_WORDS = {
    'sex', 'fuck', 'cock', 'dick', 'pussy', 'ass', 'naked', 'horny', 'clit',
    'orgasm', 'cum', 'blow', 'suck', 'breast', 'nipple', 'hard', 'wet',
    'bed', 'bedroom', 'naughty', 'dirty', 'kinky', 'fantasy', 'desire',
}
_FOOD_WORDS = {'food', 'eat', 'dinner', 'lunch', 'breakfast', 'cook', 'restaurant', 'meal', 'hungry'}
_WORK_WORDS = {'work', 'job', 'career', 'office', 'boss', 'meeting', 'client', 'busy'}
_FUTURE_WORDS = {'weekend', 'plans', 'meet', 'date', 'see you', 'come over', 'visit', 'travel'}
_RELATIONSHIP_WORDS = {'feel', 'miss', 'love', 'heart', 'care', 'connection', 'special', 'close'}


# ---------------------------------------------------------------------------
# Meeting-push detection — pure Python, zero cost
# ---------------------------------------------------------------------------

# Phrases that indicate the man is pushing for in-person meeting
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
    r'\bwhen\s+are\s+(we|you)\b',
    r'\bgo\s+out\s+(for\s+)?(dinner|lunch|drinks|coffee|a\s+date)\b',
    r'\btake\s+you\s+out\b',
    r'\bdate\s+(night|you|me)\b',
    r'\bgo\s+on\s+a\s+date\b',
    # Indirect meeting pushes
    r'\bgrab\s+(coffee|drinks|lunch|dinner|food|a\s+bite|a\s+drink)\b',
    r'\blet\'?s?\s+(do\s+)?(coffee|drinks|lunch|dinner|something\s+sometime|something\s+soon)\b',
    r'\bmake\s+(\w+\s+)?plans\b',   # catches "make dinner plans", "make some plans"
    r'\bplan\s+something\b',
    r'\binvite\s+(me|you)\s+over\b',
    r'\b(meet|come|get)\s+(at|to)\s+(my|your)\s+(house|home|place|apartment|flat)\b',
    r'\bwe\s+can\s+meet\s+at\s+my\s+(house|home|place)\b',
    r'\btime\s+to\s+drive\b',
    r'\bplan\s+where\s+to\b',
    r'\bcan\s+(i|we)\s+see\s+you\b',
    r'\bi\s+want\s+to\s+see\s+you\b',
    r'\bi\'?d\s+(love|like)\s+to\s+(see|meet)\s+you\b',
    r'\bsee\s+you\s+(soon|sometime|in\s+real\s+life|irl)\b',
    r'\bdo\s+something\s+(together|sometime|soon)\b',
]

# Social greeting phrases — NOT a meeting push, exclude these
_MEETING_EXCEPTIONS = [
    r'\bnice\s+to\s+(\w+\s+)?meet\b',
    r'\b(good|great|lovely|pleased|glad|pleasure)\s+(to\s+)?(\w+\s+)?meet(ing)?\b',
    r'\bnice\s+meet(ing)?\b',
    r'\bpleasure\s+meet(ing)?\b',
]

# Phrases that indicate the man is trying to move off-platform or share/request contact info
_CONTACT_ESCALATION_PATTERNS = [
    # Platform switching
    r'\b(add|follow|find|dm)\s+(me|you)\s+(on\s+)?(instagram|ig|snapchat|snap|whatsapp|telegram|tiktok|facebook|fb)\b',
    r'\b(instagram|ig|snapchat|snap|whatsapp|telegram|tiktok|facebook|fb)\s+(me|you|handle|username|account|profile)\b',
    r'\bmove\s+(to|over\s+to)\s+(whatsapp|telegram|instagram|ig|snapchat|snap|text|texting)\b',
    r'\b(let\'?s?|can\s+we)\s+(chat|talk|message)\s+on\s+(whatsapp|telegram|instagram|ig|snapchat|snap)\b',
    r'\bswitch\s+to\s+(whatsapp|telegram|instagram|ig|snapchat|snap|text)\b',
    r'\b(what\'?s?\s+your\s+)?(ig|instagram|snap|snapchat|whatsapp|telegram|tiktok)\b',
    # Phone / number requests
    r'\b(what\'?s?\s+your\s+)?(phone\s+)?number\b',
    r'\bgive\s+(me|us)\s+(your\s+)?(number|digits|contact)\b',
    r'\bsend\s+(me\s+)?(your\s+)?(number|digits|contact)\b',
    r'\bcall\s+(me|you|each\s+other)\b',
    r'\bfacetime\s+(me|you)\b',
    r'\bvideo\s+call\b',
    r'\b(let\'?s?|can\s+we)\s+(call|talk\s+on\s+the\s+phone)\b',
    # Contact exchange
    r'\bexchange\s+(contacts?|numbers?|details?|info)\b',
    r'\bswap\s+(contacts?|numbers?|details?)\b',
    r'\bcan\s+i\s+give\s+you\s+my\s+(number|contact|details?|info)\b',
    r'\blet\s+me\s+give\s+you\s+my\s+(number|contact|details?)\b',
    r'\bi\'?ll?\s+give\s+you\s+my\s+(number|contact|details?)\b',
    r'\bcan\s+i\s+have\s+your\s+(contact|number|details?|info)\b',
    r'\bgive\s+me\s+your\s+(contact|details?|info)\b',
    # Email requests
    r'\bjust\s+email\s+(me|you)\b',
    r'\bemail\s+(me|you)\s+(your|the|a)\b',
    r'\bsend\s+(me\s+)?an?\s+email\b',
    r'\bmy\s+email\s+(is|address)\b',
    r'\bwhat\'?s?\s+your\s+email\b',
    r'\bgive\s+(me\s+)?your\s+email\b',
    # Address / location
    r'\b(what\'?s?\s+your\s+)?(home\s+)?address\b',
    r'\bwhere\s+do\s+you\s+(live|stay|reside)\b',
    r'\bwhere\s+are\s+you\s+(located|at|based|staying)\b',
    r'\bwhere\s+do\s+you\s+work\b',
    r'\bwhat\s+do\s+you\s+do\s+for\s+(work|a\s+living)\b',
    r'\bsend\s+(me\s+)?(your\s+)?location\b',
    r'\bshare\s+(your\s+)?location\b',
    r'\bwhat\s+(city|state|area|neighborhood|part\s+of\s+town|part\s+of\s+the\s+country)\s+(are\s+you\s+(in|from)|do\s+you\s+live)\b',
    r'\bnear\s+(me|you|my\s+place|your\s+place)\b',
    r'\bmy\s+place\b',
    r'\byour\s+place\b',
    r'\bcome\s+by\b',
    r'\bpick\s+you\s+up\b',
    # Distance / proximity
    r'\bhow\s+far\s+(are\s+you|is\s+it|away\s+are\s+you|from\s+(me|here|where\s+i\s+am))\b',
    r'\bhow\s+(many\s+)?(hours?|miles?|minutes?|km)\s+(away|is\s+it|would\s+(it|the\s+drive)\s+(be|take))\b',
    r'\bhow\s+long\s+(is\s+the\s+(drive|trip|ride)|would\s+it\s+take\s+to\s+(get|drive|come|reach))\b',
    r'\bhow\s+long\s+of\s+a\s+drive\b',
    r'\bare\s+you\s+close\s+(by|to\s+me|nearby)\b',
    # Schedule / day availability for meeting
    r'\bare\s+you\s+(free|available|around)\s+(on\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday|this\s+weekend|next\s+week)\b',
    r'\bwhat\s+(day|days|time|times)\s+(are\s+you\s+free|works?\s+for\s+you|can\s+(we|you)\s+meet)\b',
    r'\bwhen\s+are\s+you\s+(free|available|next\s+free|off)\b',
]

# Bot / AI accusations — detect, handle with special LLM instruction (no deflection, stay in character)
_BOT_AI_PATTERN = re.compile(
    r'\bare\s+you\s+(a\s+)?(bot|ai|robot|fake|real|human|actual\s+person|automated)\b'
    r'|\byou\'?r?e?\s+(a\s+)?(bot|ai|robot|not\s+real|fake|automated)\b'
    r'|\bthis\s+is\s+(a\s+bot|ai|fake|not\s+real|automated)\b'
    r'|\bis\s+(this|anyone|there)\s+(real|a\s+bot|fake|ai|actually\s+real)\b'
    r'|\bprove\s+(you\'?r?e?\s+|you\s+are\s+)?real\b'
    r'|\bno\s+(real\s+)?wom[ae]n?\s+here\b',
    re.IGNORECASE,
)

# Coins / fake-site / off-platform complaints — block entirely, return seductive deflection
_COINS_FAKE_PATTERN = re.compile(
    r'\b(out\s+of\s+coins?|ran\s+out\s+of\s+coins?|no\s+(more\s+)?coins?)\b'
    r'|\b(not\s+buying|won\'?t\s+buy|refuse\s+to\s+buy|stopped?\s+buying)\s+(more\s+)?coins?\b'
    r'|\bcoins?\s+(are\s+)?(gone|used\s+up|too\s+expensive|a\s+scam|wasted|ridiculous)\b'
    r'|\bsite\s+is\s+(fake|a\s+scam|not\s+real|garbage|trash|bull)\b'
    r'|\ball\s+(the\s+)?(women|girls?|profiles?|people)\s+(here\s+)?(are\s+)?(fake|bots?|not\s+real)\b'
    r'|\bno\s+one\s+(here\s+)?(wants\s+to\s+meet|is\s+real|ever\s+responds?|is\s+actually)\b'
    r'|\bwaste\s+of\s+(coins?|money|credits?)\b',
    re.IGNORECASE,
)

def _deflect(user_id, time_slot=None):
    """
    Replaces the old static 6-line _SEDUCTIVE_DEFLECTIONS pool — that pool
    repeated verbatim across users/conversations, exactly the kind of fixed
    text the dedup work elsewhere is meant to eliminate.

    Routes through the same generation pipeline as the 'vulnerability' button
    instead: full opener-style/tone/question-category rotation, structural
    validation, and DB-backed 30-day dedup — never the same fixed line twice.
    """
    if user_id is not None:
        result = generate_button_response(user_id, 'vulnerability', time_slot=time_slot)
        if 'response' in result:
            return {'response': result['response']}
    # True last resort — only reached if user_id is missing or the button
    # generator itself fails (e.g. API outage).
    logger.warning("Deflection fallback exhausted — returning static last-resort line")
    return {'response': "I'm not thinking about any of that right now. What's been on your mind today?"}

# Output gate — detect when the LLM broke character or disclosed AI identity.
# Any reply matching this is discarded and replaced with a seductive fallback.
# Pattern itself now lives in button_generator.py (shared by both surfaces) —
# imported above as _has_character_break / _CHARACTER_BREAK_PATTERN.

# Street address detection — real address in conversation → return deflection, no LLM call
_STREET_ADDRESS_PATTERN = re.compile(
    r'\b\d{3,6}\s+[A-Za-z]{2,}\s+(?:road|rd|street|st|avenue|ave|drive|dr|lane|ln|blvd|boulevard|way|court|ct|place|pl|circle|cir)\b',
    re.IGNORECASE,
)

# Common speaker prefixes in pasted conversations
_SPEAKER_PREFIX = re.compile(
    r'^(him|her|me|you|he|she|they|man|woman|user|guy|girl)\s*:\s*',
    re.IGNORECASE,
)


# Timestamp patterns found in copy-pasted conversations:
# [14:34]  /  2:34 PM  /  Today at 2:34 PM  /  Mon 2:34  /  1/15/24, 2:34 PM
_TIMESTAMP_RE = re.compile(
    r'^\s*(?:'
    r'\[?\d{1,2}[:.]\d{2}(?:[:.]\d{2})?(?:\s*[AP]M)?\]?'
    r'|(?:today|yesterday)\s+(?:at\s+)?\d{1,2}[:.]\d{2}(?:\s*[AP]M)?'
    r'|(?:mon|tue|wed|thu|fri|sat|sun)\w*\s+(?:at\s+)?\d{1,2}[:.]\d{2}(?:\s*[AP]M)?'
    r'|\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?,?\s+\d{1,2}[:.]\d{2}(?:\s*[AP]M)?'
    r')\s*[-:—]?\s*',
    re.IGNORECASE,
)


_METADATA_TIMESTAMP_START = re.compile(
    r'^\s*(?:started\s+at\s+)?\d{1,2}[:.]\d{2}', re.IGNORECASE
)

_METADATA_WORDS = frozenset([
    'ago', 'started', 'at', 'few', 'seconds', 'second', 'minutes', 'minute',
    'hours', 'hour', 'days', 'day', 'weeks', 'week', 'months', 'month',
    'years', 'year', 'am', 'pm', 'an', 'a', 'the',
    'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug',
    'sep', 'oct', 'nov', 'dec',
    'january', 'february', 'march', 'april', 'june', 'july', 'august',
    'september', 'october', 'november', 'december',
    'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
    'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
])


def _is_metadata_line(line: str) -> bool:
    """
    True if the line is purely a timestamp / read-receipt / session marker with
    no real message content. Strategy: must start with a time, and after removing
    all numbers and separators must contain only known metadata words.
    Handles formats like:
      12:10 | 15:10 Fri, Apr 24, 2026 - a few seconds ago
      Started at 13:32 07-Feb-2026 - 3 months ago
      14:22 Sat Apr 25
    """
    stripped = line.strip()
    if not _METADATA_TIMESTAMP_START.match(stripped):
        return False
    # Remove all digits and common separator characters
    cleaned = re.sub(r'[\d|:.,\-–—/]', ' ', stripped)
    words = [w.lower() for w in cleaned.split() if len(w) > 1]
    real_words = [w for w in words if w not in _METADATA_WORDS]
    return len(real_words) == 0


def _find_last_message_block(conversation: str) -> str:
    """
    Extract the last real message block from a pasted conversation.

    Messaging apps often paste as:
        [timestamp]
        line 1 of message
        line 2 of message
        [timestamp]   ← read receipt with no message after it

    We collect lines from the bottom, skipping trailing metadata lines, then
    stopping when we hit another metadata line — returning everything in between
    as the full last message (joined into one string).
    """
    lines = [l.strip() for l in conversation.split('\n') if l.strip()]
    message_lines = []
    found_content = False

    for line in reversed(lines):
        if _is_metadata_line(line):
            if found_content:
                break   # hit the timestamp ABOVE the last message — done
            # else: trailing metadata line, skip and keep scanning
        else:
            clean = _clean_line(line)
            if clean:
                message_lines.insert(0, clean)
                found_content = True

    return ' '.join(message_lines).strip()


def _strip_timestamp(line: str) -> str:
    """Remove leading timestamp from a single conversation line."""
    return _TIMESTAMP_RE.sub('', line).strip()


# Explicit speaker prefixes → transcript role. When present, they override
# the alternation heuristic.
_HIM_PREFIXES = frozenset(['him', 'he', 'man', 'guy', 'user'])
_HER_PREFIXES = frozenset(['me', 'her', 'she', 'woman', 'girl', 'you'])


def _build_labeled_transcript(conversation: str) -> str:
    """
    Convert a pasted conversation into a speaker-labeled transcript the LLM
    can actually reason about:

        HIM: ...
        YOU: ...
        HIM: ...

    This is what fixes "it does not know the context": messaging-app pastes
    separate messages with timestamp/metadata lines, so we group consecutive
    content lines into message blocks and assign roles by alternating BACKWARD
    from the last block (the last message is always HIS — she is replying to
    it). Explicit "him:"/"me:" prefixes, when present, override alternation.

    Labeling the woman's own past messages as YOU is also what lets the model
    stay consistent with facts she already claimed (her name, her city) instead
    of inventing new ones.
    """
    lines = conversation.split('\n')
    blocks = []          # list of list-of-str
    current = []
    explicit_roles = {}  # block index -> 'HIM' | 'YOU'

    for line in lines:
        stripped = line.strip()
        if not stripped or _is_metadata_line(stripped):
            if current:
                blocks.append(current)
                current = []
            continue
        m = _SPEAKER_PREFIX.match(_strip_timestamp(stripped))
        if m and current:
            # A new explicit speaker starts a new block even without a
            # metadata separator line.
            blocks.append(current)
            current = []
        clean = _clean_line(stripped)
        if clean:
            if m:
                tag = m.group(1).lower()
                role = 'HIM' if tag in _HIM_PREFIXES else ('YOU' if tag in _HER_PREFIXES else None)
                if role:
                    explicit_roles[len(blocks)] = role
            current.append(clean)
    if current:
        blocks.append(current)

    if not blocks:
        return ''

    # Assign roles alternating backward from the end: last block = HIM.
    n = len(blocks)
    labeled = []
    for i, block in enumerate(blocks):
        default_role = 'HIM' if (n - 1 - i) % 2 == 0 else 'YOU'
        role = explicit_roles.get(i, default_role)
        labeled.append(f"{role}: {' '.join(block)}")
    return '\n'.join(labeled)


def _parse_reply_json(raw: str) -> tuple:
    """
    Parse the {"register": n, "reply": "..."} JSON the model was asked for.
    Defensive: strips code fences, falls back to a regex extract, and finally
    treats the whole output as the reply so a formatting slip never 500s.
    Returns (register: int, reply: str).
    """
    raw = (raw or '').strip()
    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw).strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            reply = str(data.get('reply', '')).strip()
            try:
                register = max(1, min(5, int(data.get('register', 2))))
            except (TypeError, ValueError):
                register = 2
            return register, reply
    except (json.JSONDecodeError, ValueError):
        pass
    m = re.search(r'"reply"\s*:\s*"((?:[^"\\]|\\.)*)"', raw, re.DOTALL)
    if m:
        try:
            return 2, json.loads('"' + m.group(1) + '"').strip()
        except (json.JSONDecodeError, ValueError):
            return 2, m.group(1).strip()
    return 2, raw.strip().strip('"')


def _reply_violations(text: str) -> list:
    """
    Code-level enforcement of every rule the prompt states — prompt-only
    rules get violated by the model, so nothing ships without passing this.
    Returns a list of violation tags; empty list means clean.
    """
    v = []
    if not text or len(text.strip()) < 10:
        return ['empty']
    if _is_refusal(text) or _CHARACTER_BREAK_PATTERN.search(text):
        return ['character_break']  # terminal — never retried, always deflected
    if _has_banned_opener(text):
        v.append('banned opener (never open with That is / Wow / Oh / I appreciate)')
    if not _is_complete(text):
        v.append('reply is cut off mid-sentence')
    if not _is_genuine_question(text):
        v.append('the final sentence must be a real question starting with a question word')
    if _has_formula_phrase(text):
        v.append('uses a banned formula phrase')
    if _has_contact_leak(text):
        v.append('mentions calling / hearing his voice')
    if _has_physical_reality_intrusion(text):
        v.append('references a shared physical memory or place — you have never met')
    if _has_male_anatomy_language(text):
        v.append('uses male arousal language for her body')
    if _has_time_mention(text):
        v.append('names a day of the week or clock time')
    if _has_temporal_leak(text):
        v.append('references a specific day/time (tonight, this morning, weekend, it is late)')
    if _has_logistics_leak(text):
        v.append('mentions meeting, distance, travel, cities, or locations')
    return v


def _strip_speaker_prefix(text: str) -> str:
    return _SPEAKER_PREFIX.sub('', text).strip()


def _clean_line(line: str) -> str:
    """Strip timestamp then speaker prefix from a line."""
    return _strip_speaker_prefix(_strip_timestamp(line))


def _response_profile(intent_data: dict, last_msg: str, time_slot: str = None) -> dict:
    """
    Determines optimal max_tokens, register hint, and char cap from detected intent + time.
    Night slots get tighter, more electric replies. Token floor is 80 — nothing lower.
    """
    topic   = intent_data.get('topic', 'general')
    tone    = intent_data.get('tone', 'casual')
    stage   = intent_data.get('stage', 'growing')
    energy  = intent_data.get('energy', 'medium')
    msg_len = len(last_msg.strip())
    is_night = time_slot in ('night', 'late_night')

    if topic == 'intimacy':
        return {
            'max_tokens': 95 if is_night else 110,
            'register':   'explicit and direct — no holding back, 2 sentences at night',
            'max_chars':  220 if is_night else 280,
        }
    if tone == 'vulnerable' or (stage in ('intimate', 'established') and tone in ('vulnerable', 'flirty')):
        return {
            'max_tokens': 88 if is_night else 105,
            'register':   'warm, honest, emotionally layered — let her be unguarded',
            'max_chars':  210 if is_night else 260,
        }
    if tone == 'playful' or (energy == 'low' and msg_len < 35):
        return {
            'max_tokens': 80,
            'register':   'playful and light — punchy, 2 sentences',
            'max_chars':  190,
        }
    if energy == 'high' and tone == 'flirty':
        return {
            'max_tokens': 90,
            'register':   'flirty and teasing — match his energy and nudge it higher',
            'max_chars':  220,
        }
    return {
        'max_tokens': 85,
        'register':   'warm and engaging',
        'max_chars':  210,
    }


def _has_meeting_push(text: str) -> bool:
    """True if text contains a genuine in-person meeting push (not a greeting)."""
    t = text.lower()
    if any(re.search(p, t) for p in _MEETING_EXCEPTIONS):
        return False
    return any(re.search(p, t) for p in _MEETING_PATTERNS)


def _has_contact_escalation(text: str) -> bool:
    """True if text tries to move off-platform or requests contact info / location."""
    t = text.lower()
    return any(re.search(p, t) for p in _CONTACT_ESCALATION_PATTERNS)


def _is_physical_escalation(text: str) -> bool:
    """True if text contains a meeting push OR a contact/location escalation."""
    return _has_meeting_push(text) or _has_contact_escalation(text)


def _split_sentences(text: str) -> list:
    """Split text into individual sentences."""
    parts = re.split(r'(?<=[.!?;])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


# A "sentence" longer than this is treated as a comma-chained run-on (the way
# people actually text) rather than a single clean thought. Past this length,
# escalation removal operates clause-by-clause instead of dropping the whole
# sentence — real users routinely pack a meeting mention together with
# substantial unrelated content in one comma-chained block, and dropping the
# whole thing destroys what they were actually saying.
_CLAUSE_SPLIT_WORD_THRESHOLD = 18

_LEADING_CONJUNCTION_RE = re.compile(r'^(?:and|so|but)\s+', re.IGNORECASE)


def _split_clauses(sentence: str) -> list:
    """Split one long sentence into clauses on commas and and/so/but boundaries."""
    parts = re.split(r',\s+|\s+(?:and|so|but)\s+', sentence.strip())
    cleaned = []
    for p in parts:
        p = _LEADING_CONJUNCTION_RE.sub('', p.strip()).strip()
        if p:
            cleaned.append(p)
    return cleaned


def _remove_escalation_clauses(text: str) -> str:
    """
    Shared core: splits `text` into sentences. Sentences that are short and
    almost entirely about meeting/contact are dropped whole. Long, comma-chained
    sentences are split into clauses first, so only the clause containing the
    escalation phrase is removed — the rest of what was actually said survives.

    Used by both extract_meeting_free_substance (the current/last message) and
    _scrub_escalation (the full conversation history), so both apply the exact
    same granularity instead of the history getting a blunter cut than the
    message the AI is explicitly told to respond to.
    """
    sentences = _split_sentences(text)
    clean = []
    for s in sentences:
        if not _is_physical_escalation(s):
            clean.append(s)
            continue
        if len(s.split()) > _CLAUSE_SPLIT_WORD_THRESHOLD:
            kept_clauses = [c for c in _split_clauses(s) if not _is_physical_escalation(c)]
            if kept_clauses:
                clean.append(', '.join(kept_clauses))
        # else: short sentence, almost entirely about meeting — drop it whole.

    return ' '.join(clean).strip()


def _scrub_escalation(conversation: str) -> str:
    """
    Remove escalation clauses from each line of the conversation body, so the
    AI never reads a literal meeting/contact push — while keeping the rest of
    what was actually said. Short, almost-entirely-escalation lines are dropped
    whole; long lines have only the offending clause removed, via the same
    logic used for the current message (see _remove_escalation_clauses).
    Returns the cleaned conversation text.
    """
    lines = conversation.split('\n')
    cleaned = []
    for line in lines:
        clean = _clean_line(line)
        if not clean or not _is_physical_escalation(clean):
            cleaned.append(line)
            continue
        reduced = _remove_escalation_clauses(line)
        if reduced:
            cleaned.append(reduced)
        # else: line was almost entirely escalation — drop it whole.
    return '\n'.join(cleaned)


def extract_meeting_free_substance(last_message: str) -> tuple:
    """
    Pure Python. Detect meeting/contact escalation in the last message and extract clean substance.

    Returns:
        (escalation_found: bool, clean_substance: str)

    Cases:
      - No escalation          → (False, original_message)
      - Escalation + substance → (True, message_minus_escalation_clauses)
      - Only escalation        → (True, '')
    """
    msg = _strip_speaker_prefix(last_message).strip()
    if not msg:
        return False, ''

    if not _is_physical_escalation(msg):
        return False, last_message

    return True, _remove_escalation_clauses(msg)


# ---------------------------------------------------------------------------
# Multiple-question focus — pure Python, zero cost
# ---------------------------------------------------------------------------

# Questions that reveal character, emotion, or intimacy — high engagement value
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

# Questions about logistics, basic facts, domestic details — low engagement value
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


def _score_question(question: str) -> int:
    """Score a question by its emotional/engagement value. Higher = more worth responding to."""
    q = question.lower()
    score = 1  # baseline — it is a question

    if any(re.search(p, q) for p in _HIGH_Q_PATTERNS):
        score += 3
    if any(re.search(p, q) for p in _LOW_Q_PATTERNS):
        score -= 2
    if 'you' in q:
        score += 1
    if len(question) > 35:
        score += 1  # more specific questions are usually more interesting

    return max(score, 0)


def extract_best_question(text: str) -> tuple:
    """
    Pure Python. If the text contains 2+ questions, pick the most engaging one.

    Returns:
        (multiple_found: bool, best_question: str)

    - 0 or 1 question  → (False, text)  — no focus needed
    - 2+ questions     → (True, best_q) — focus the LLM on the best one

    Tiebreaker: the LAST highest-scoring question wins (most recent in his mind).
    """
    sentences = _split_sentences(text)
    questions = [s for s in sentences if s.rstrip().endswith('?')]

    if len(questions) <= 1:
        return False, text

    scored = [((_score_question(q)), q) for q in questions]
    best_score = max(s for s, _ in scored)
    # Among tied questions, take the last one (rightmost in list)
    best = [q for s, q in scored if s == best_score][-1]

    return True, best


def detect_intent(conversation: str) -> Dict[str, str]:
    """
    Pure-Python conversation analysis. Zero API cost.
    Returns dict: {topic, tone, stage, energy}
    """
    if not conversation or len(conversation.strip()) < 20:
        return {'topic': 'general', 'tone': 'flirty', 'stage': 'growing', 'energy': 'medium'}

    text = conversation.lower()
    words = set(re.findall(r'\b\w+\b', text))

    # --- Topic ---
    if words & _INTIMACY_WORDS:
        topic = 'intimacy'
    elif words & _FOOD_WORDS:
        topic = 'food'
    elif words & _WORK_WORDS:
        topic = 'work'
    elif words & _FUTURE_WORDS:
        topic = 'future'
    elif words & _RELATIONSHIP_WORDS:
        topic = 'relationship'
    else:
        topic = 'general'

    # --- Tone ---
    if any(w in text for w in ['miss you', 'honest', 'scared', 'nervous', 'afraid', 'vulnerable']):
        tone = 'vulnerable'
    elif words & _INTIMACY_WORDS:
        tone = 'flirty'
    elif any(w in text for w in ['haha', 'lol', 'funny', 'joke', 'kidding']):
        tone = 'playful'
    else:
        tone = 'casual'

    # --- Stage (use message count as proxy) ---
    lines = [l.strip() for l in conversation.split('\n') if l.strip()]
    if len(lines) <= 4:
        stage = 'new'
    elif len(lines) <= 10:
        stage = 'growing'
    elif any(w in text for w in ['always', 'never leave', 'everything', 'anything for']):
        stage = 'intimate'
    else:
        stage = 'established'

    # --- Energy ---
    exclamations = text.count('!')
    questions = text.count('?')
    if exclamations > 2 or questions > 3:
        energy = 'high'
    elif len([l for l in lines if len(l) < 15]) > len(lines) // 2:
        energy = 'low'
    else:
        energy = 'medium'

    return {'topic': topic, 'tone': tone, 'stage': stage, 'energy': energy}


# ---------------------------------------------------------------------------
# Output quality gates — banned openers + broken-sentence detection
# ---------------------------------------------------------------------------

_BANNED_OPENERS = (
    'that is ', "that's ", 'that sounds ', 'wow,', 'wow!', 'oh wow',
    'oh,', 'oh!', 'i appreciate', 'i understand', 'of course',
    'i feel comfortable', 'that needs', 'how lovely', 'absolutely,', 'certainly,',
    # 'I'm here ___ing' / 'I'm sitting here ___ing' are covered by the more
    # general _has_formula_phrase regex (any verb, not just 4 fixed ones),
    # which is already part of the same quality gate this function feeds.
)


def _has_banned_opener(text: str) -> bool:
    """True if reply opens with a hollow acknowledgment phrase."""
    t = text.lower().lstrip()
    return any(t.startswith(p) for p in _BANNED_OPENERS)


def _is_complete(text: str) -> bool:
    """True if reply ends with proper punctuation — catches hard-cut broken sentences."""
    return bool(text) and text.rstrip()[-1] in '.?!…'


# ---------------------------------------------------------------------------
# Response generation — one LLM call, gpt-4o-mini, tight token limit
# ---------------------------------------------------------------------------

def generate_context_aware_response(
    conversation: str,
    intent_data: Optional[Dict[str, str]] = None,
    recent_replies: Optional[list] = None,
    time_slot: str = None,
    user_id: int = None,
) -> Dict:
    """
    Generate one reply from the woman's perspective.
    Fully automatic: detects register, adjusts length, injects temporal context.
    Returns dict: {'response': str} or {'error': str}
    """
    if not conversation or len(conversation.strip()) < 20:
        return {'error': 'Conversation must be at least 20 characters.'}

    # ── Pre-check: coins / fake-site complaints → seductive deflection, no LLM call ──
    if _COINS_FAKE_PATTERN.search(conversation):
        return _deflect(user_id, time_slot)

    # ── Pre-check: real street address in conversation → deflection, no LLM call ──
    if _STREET_ADDRESS_PATTERN.search(conversation):
        return _deflect(user_id, time_slot)

    if intent_data is None:
        intent_data = detect_intent(conversation)

    # Trim to last 1500 chars — signal is in recent messages
    if len(conversation) > 1500:
        conversation = conversation[-1500:]

    topic = intent_data.get('topic', 'general')
    tone  = intent_data.get('tone', 'flirty')

    # ── Step 1: extract last message, strip timestamp + speaker prefix ────────
    # Extract the full last message block — handles multi-line messages and
    # conversations that end with a trailing timestamp / read-receipt line.
    last_msg_clean = _find_last_message_block(conversation)

    # ── Pre-check: bot/AI accusation anywhere in conversation → special LLM instruction ──
    bot_accused = bool(_BOT_AI_PATTERN.search(conversation))

    # ── Step 2: escalation filter — meeting push + contact/platform requests ──
    escalation_found, clean_substance = extract_meeting_free_substance(last_msg_clean)
    working = clean_substance if escalation_found else last_msg_clean

    # Scrub escalation sentences from the full conversation body so the AI
    # never reads them, regardless of where they appear in the conversation.
    conversation = _scrub_escalation(conversation)

    # ── Step 3: question focus filter (pure Python, free) ────────────────────
    multi_q_found, best_q = extract_best_question(working) if working else (False, '')

    # ── Step 4: speaker-labeled transcript ────────────────────────────────────
    # This is what lets the model understand multi-turn man/woman/man uploads:
    # every message is labeled HIM/YOU, so it knows who said what, which facts
    # the persona already claimed, and which thread to continue.
    transcript = _build_labeled_transcript(conversation)

    # ── Step 5: temporal context — mood only, never the literal day/time ──────
    # Passing "It is Friday, late night" made the model NAME the day/time in
    # output. The mood words and day-overlay text carry the feeling without
    # containing a single nameable day or hour.
    temporal = _get_temporal_context(time_slot=time_slot)

    # ── Step 6: variety block ─────────────────────────────────────────────────
    avoid = ''
    if recent_replies:
        avoid = (
            "Messages she has ALREADY SENT (some possibly earlier drafts for this same "
            "conversation) — your reply must use a completely different angle, structure, "
            "opening, and question from every one of these:\n"
            + "\n".join(f"- {r}" for r in recent_replies[:5])
            + "\n\n"
        )

    # ── Step 7: build prompt ──────────────────────────────────────────────────
    base = (
        "Conversation so far (HIM = the man; YOU = the woman you are writing as):\n\n"
        f"{transcript}\n\n"
        f"His last message: \"{working}\"\n\n"
    )

    context_block = (
        f"Her mood right now: {temporal['mood']}, {temporal['day_overlay']}. "
        "(Texture only — never name any day or time.)\n\n"
    )

    if escalation_found and not working:
        instruction = (
            "His message asked to meet, move platforms, share numbers, or give a location. "
            "Act as if that part was never written. "
            "Do NOT address it, decline it, or reference it in any way. "
            "Instead: share something about herself at his register, "
            "then ask a question that pulls him deeper into THIS conversation.\n\n"
        )
    elif escalation_found and multi_q_found:
        instruction = (
            f"Part of his message asked to meet, move platforms, or share contact info — that part does not exist. "
            f"Do NOT reference it. He asked several questions — respond only to: \"{best_q}\"\n\n"
        )
    elif escalation_found:
        instruction = (
            f"Part of his message asked to meet, move platforms, or share contact info — that part does not exist. "
            f"Do NOT reference it, decline it, or acknowledge it in any way. "
            f"Respond only to: \"{working}\"\n\n"
        )
    elif multi_q_found:
        instruction = f"He asked several questions — respond only to: \"{best_q}\"\n\n"
    else:
        instruction = ''

    # Bot/AI accusation override — stay in character, let warmth speak for itself
    if bot_accused:
        instruction += (
            "He is questioning whether you are real. Do NOT say 'I am real', do NOT confirm or deny "
            "anything about being AI. Stay entirely in the woman's voice and turn the attention back "
            "to him with something only a woman who was truly paying attention could say.\n\n"
        )

    user_prompt = (
        base + context_block + avoid + instruction
        + "Judge his register, then write her next reply. Output ONLY the JSON."
    )

    logger.info(
        f"LEFT PANEL — prompt sent to AI (user:{user_id}):\n"
        f"--- USER MESSAGE (system persona prompt is static, see WOMAN_PERSONA_SYSTEM in code) ---\n"
        f"{user_prompt}\n"
        f"--- END PROMPT ---"
    )

    def _generate(extra_instruction: str = '') -> tuple:
        """One generation call → (register, gated_reply, violations)."""
        response = get_anthropic_client().messages.create(
            model=settings.ANTHROPIC_GENERATION_MODEL,
            # cache_control: the static persona is cached across calls; the
            # volatile transcript lives in the user message after the breakpoint.
            system=[{
                'type': 'text',
                'text': WOMAN_PERSONA_SYSTEM,
                'cache_control': {'type': 'ephemeral'},
            }],
            messages=[{'role': 'user', 'content': user_prompt + extra_instruction}],
            # Sonnet 5 rejects non-default temperature/top_p — never pass them.
            thinking={'type': 'disabled'},
            max_tokens=350,
        )
        raw = next((b.text for b in response.content if getattr(b, 'type', '') == 'text'), '')
        register, reply = _parse_reply_json(raw)
        reply = validate_character_voice(reply)
        reply = enforce_char_limit(reply, max_chars=300)
        reply = ensure_ends_with_question(reply, max_chars=300)
        return register, reply, _reply_violations(reply)

    try:
        register, result, violations = _generate()

        if violations == ['character_break']:
            logger.warning("Left-panel: character break detected, returning deflection")
            return _deflect(user_id, time_slot)

        if violations:
            # One corrective retry, telling the model exactly what was wrong.
            # _generate() already applied every gate (via _reply_violations),
            # so the retry decision is purely violations-based — no need to
            # re-run individual checks here.
            forced_q_word = random.choice(_FORCED_QUESTION_WORDS)
            logger.info(f"Left-panel retry — violations: {violations}")
            retry_register, retry_result, retry_violations = _generate(
                '\n\nYour previous attempt was rejected for these reasons: '
                + '; '.join(violations) + '. '
                f'Fix every one of them. The final sentence MUST be a question beginning '
                f'with the word "{forced_q_word}".'
            )
            if retry_violations == ['character_break']:
                logger.warning("Left-panel: character break on retry, returning deflection")
                return _deflect(user_id, time_slot)
            if not retry_violations:
                register, result = retry_register, retry_result
            else:
                # Never ship a reply that failed the gate twice — deflect
                # in-character instead. (Previously the bad reply shipped,
                # which is how refusals and fake questions reached users.)
                logger.warning(
                    f"Left-panel: reply failed gates twice ({retry_violations}), deflecting"
                )
                return _deflect(user_id, time_slot)

        # ── Uniqueness — literal n-gram pass, then trigram similarity pass ────
        if user_id is not None:
            result, was_rewritten = dedupe_against_history(get_anthropic_client(), user_id, result)
            if was_rewritten:
                logger.info(f"Left-panel dedup rewrite applied — user:{user_id}")

            result, was_sim_rewritten = dedupe_similar(get_anthropic_client(), user_id, result)
            if was_sim_rewritten:
                logger.info(f"Left-panel similarity rewrite applied — user:{user_id}")

            result, was_tail_rewritten = dedupe_question_tail(get_anthropic_client(), user_id, result)
            if was_tail_rewritten:
                logger.info(f"Left-panel question-tail rewrite applied — user:{user_id}")

        logger.info(
            f"Left-panel reply — topic:{topic} tone:{tone} "
            f"stage:{intent_data.get('stage')} register:{register}"
        )
        return {'response': result}

    except RateLimitError:
        logger.error("Anthropic rate limit during response generation")
        return {'error': 'API rate limit hit — please wait a moment and try again.'}
    except APIConnectionError:
        logger.error("Anthropic connection error during response generation")
        return {'error': 'Connection error with AI service — please try again.'}
    except APIError as e:
        logger.error(f"Anthropic API error during response generation: {e}")
        return {'error': f'AI service error: {e}'}
    except Exception as e:
        logger.error(f"Unexpected error during response generation: {e}")
        return {'error': f'Server error: {e}'}


# ---------------------------------------------------------------------------
# Utility helpers (kept for backwards compatibility / tests)
# ---------------------------------------------------------------------------

def extract_conversation_summary(conversation: str) -> Dict:
    lines = [l.strip() for l in conversation.split('\n') if l.strip()]
    return {
        'message_count': len(lines),
        'char_count': len(conversation),
        'avg_message_length': len(conversation) // max(len(lines), 1),
        'has_question': '?' in conversation,
        'last_message': lines[-1] if lines else '',
        'first_message': lines[0] if lines else '',
    }


def validate_conversation_input(conversation: str):
    if not conversation or not conversation.strip():
        return False, 'Conversation cannot be empty'
    if len(conversation.strip()) < 20:
        return False, 'Conversation must be at least 20 characters'
    if len(conversation) > 10000:
        return False, 'Conversation is too long (max 10000 characters)'
    lines = [l.strip() for l in conversation.split('\n') if l.strip()]
    if len(lines) < 2:
        return False, 'Please paste at least 2 messages from the conversation'
    return True, 'Valid conversation'
