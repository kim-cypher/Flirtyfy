"""
Vocabulary frequency governor — a cooldown layer that sits ON TOP of the hard
bans, not instead of them.

Bans (in prompts + gates) say "never". This governor says "not too often": after
a watched action-word/phrase ships, it goes on cooldown so it cannot recur for
the SAME user within a long window (kills per-user repetition) or dominate ACROSS
users within a short window (softens the cross-user fingerprint). The watch-list
is seeded with known attractors AND grows itself — salient bigrams are frequency-
counted and trending ones get promoted automatically, so the system learns new
attractors instead of us hand-banning each one.

Redis-backed via Django cache, TTL-driven (cooldowns come free from key expiry).
Deliberately NOT the old DB-backed VocabCooldown/NgramLog (deleted in migration
0011), which wrote a row per word per reply. Everything here is best-effort and
never raises — a governor failure must never block a reply.
"""
import re
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

_USER_TTL = 24 * 3600      # a watched term won't repeat for one user within a day
_GLOBAL_TTL = 20 * 60      # soft cross-user spacing to blunt burst fingerprints
_LEARN_TTL = 6 * 3600      # rolling window for bigram frequency counting
_LEARN_THRESHOLD = 8       # bigram occurrences in the window that promote it
_LEARNED_KEY = 'vg:learned'

# Seed watch-list: recurring attractor actions/phrases. FREQUENCY-capped here,
# not banned (hard bans live in the prompts/gates). id -> regex.
_SEED_WATCH = {
    'grin': r'\bgrin(?:s|ning|ned)?\b',
    'smile_fool': r'\bsmil(?:e|es|ing)\b[^.?!]{0,20}\b(?:idiot|fool)\b',
    'beaming': r'\bbeaming\b',
    'rehearsing': r'\brehears(?:e|es|ing|ed)\b',
    'chest': r'\bchest\b',
    'heart_move': r'\bheart\b[^.?!]{0,12}(?:rac|pound|sprint|skip|flutter)',
    'not_gonna_lie': r'\bnot gonna lie\b|\bngl\b',
    'butterflies': r'\bbutterflies\b',
    'blush': r'\bblush(?:ing|ed|es)?\b',
    'stomach_move': r'\bstomach\b[^.?!]{0,12}(?:flip|drop|knot)',
    'left_on_read': r'\bleft (?:me )?on read\b',
}

_STOP = {
    'a', 'an', 'the', 'and', 'or', 'but', 'so', 'to', 'of', 'in', 'on', 'at', 'for',
    'with', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'my', 'your', 'his', 'her',
    'our', 'their', 'this', 'that', 'just', 'already', 'still', 'right', 'now', 'am',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'do', 'does', 'did', 'done',
    'have', 'has', 'had', 'will', 'would', 'could', 'should', 'not', 'yes', 'if',
    'then', 'than', 'as', 'like', 'about', 'into', 'out', 'over', 'under', 'here',
    'there', 'what', 'when', 'who', 'how', 'why', 'which', 'ive', 'youre',
}


def _learned_terms():
    try:
        return cache.get(_LEARNED_KEY) or []
    except Exception:
        return []


def _watch():
    """Seed watch-list plus auto-learned phrases (as escaped-literal regexes)."""
    patterns = dict(_SEED_WATCH)
    for ph in _learned_terms():
        patterns[f'learned:{ph}'] = r'\b' + re.escape(ph) + r'\b'
    return patterns


def _terms_in(text):
    t = ' ' + (text or '').lower() + ' '
    found = []
    for tid, pat in _watch().items():
        try:
            if re.search(pat, t):
                found.append(tid)
        except re.error:
            continue
    return found


def _find_cooled(user_id, text):
    """Watched terms present in text that are currently on cooldown (user or global)."""
    cooled = []
    for tid in _terms_in(text):
        try:
            if cache.get(f'vg:u:{user_id}:{tid}') or cache.get(f'vg:g:{tid}'):
                cooled.append(tid)
        except Exception:
            continue
    return cooled


def _record(user_id, text):
    """Set cooldowns for watched terms used, and update auto-learn counters."""
    for tid in _terms_in(text):
        try:
            cache.set(f'vg:u:{user_id}:{tid}', 1, _USER_TTL)
            cache.set(f'vg:g:{tid}', 1, _GLOBAL_TTL)
        except Exception:
            continue
    _learn(text)


def _learn(text):
    """Count content-word bigrams; promote any that trend to the watch-list."""
    words = re.findall(r'[a-z]{3,}', (text or '').lower())
    for a, b in zip(words, words[1:]):
        if a in _STOP or b in _STOP:
            continue
        bigram = f'{a} {b}'
        key = f'vg:c:{bigram}'
        try:
            n = (cache.get(key) or 0) + 1
            cache.set(key, n, _LEARN_TTL)
            if n >= _LEARN_THRESHOLD:
                learned = _learned_terms()
                if bigram not in learned:
                    learned.append(bigram)
                    cache.set(_LEARNED_KEY, learned[-200:], _LEARN_TTL * 8)
                    logger.info("VocabGovernor learned attractor: %r (count=%s)", bigram, n)
        except Exception:
            continue


def _human(tids):
    """Turn internal term ids into plain hints for the rewrite prompt."""
    return ', '.join(sorted({t.split(':', 1)[-1].replace('_', ' ') for t in tids}))


def _rewrite_avoiding(client, text, cooled):
    from django.conf import settings
    from accounts.services.dedup import log_ai_usage
    model = getattr(settings, 'ANTHROPIC_REWRITE_MODEL', 'claude-haiku-4-5')
    prompt = (
        "Rewrite this dating-app message so it keeps the same meaning, tone, and its "
        "closing question, but avoids these overused ideas/words entirely: "
        f"{_human(cooled)}. Keep it two sentences, natural, ending in a real question.\n\n"
        f"Message: \"{(text or '').strip()}\"\n\n"
        "Output only the rewritten message, nothing else."
    )
    try:
        resp = client.messages.create(
            model=model,
            system="You are a precise rewriting assistant. Output only the rewritten message.",
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.9,
            max_tokens=120,
        )
        log_ai_usage(logger, 'VOCAB_REWRITE', model, resp)
        out = resp.content[0].text.strip().strip('"')
        return out or None
    except Exception as e:
        logger.warning("VocabGovernor rewrite failed: %s", e)
        return None


def enforce(client, user_id, text):
    """Cooldown enforcement. If a watched term in `text` is on cooldown, rewrite to
    drop it (best-effort); then record usage so future generations space it out.
    Returns the (possibly rewritten) text. Never raises."""
    try:
        cooled = _find_cooled(user_id, text)
        if cooled:
            rewritten = _rewrite_avoiding(client, text, cooled)
            if rewritten and not _find_cooled(user_id, rewritten):
                logger.info("VocabGovernor cooled -> rewrote — user:%s terms:%s", user_id, cooled)
                text = rewritten
            else:
                logger.info("VocabGovernor could not clear — user:%s terms:%s (shipping)", user_id, cooled)
        _record(user_id, text)
        return text
    except Exception as e:
        logger.warning("VocabGovernor enforce failed: %s", e)
        return text
