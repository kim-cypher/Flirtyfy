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
import hashlib
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

_USER_TTL = 24 * 3600      # a watched term won't repeat for one user within a day
_GLOBAL_TTL = 20 * 60      # soft cross-user spacing to blunt burst fingerprints
_LEARN_TTL = 6 * 3600      # rolling window for bigram frequency counting
_LEARN_THRESHOLD = 8       # bigram occurrences in the window that promote it
_LEARNED_KEY = 'vg:learned'

# ── Cross-user phrase cooldown ──────────────────────────────────────────────
# The word watch-list above catches single attractor words. This catches whole
# multi-word PHRASES ("my mind keeps drifting back", "who makes the first move")
# that the per-user dedup layers can't see: those compare a user only to their
# OWN history, so a stock phrase can ship to many DIFFERENT accounts unnoticed —
# a cross-account fingerprint. Here, every shipped reply's distinctive n-grams
# are recorded in a GLOBAL (all-users) cooldown; any later reply that reuses a
# still-hot phrase gets rewritten. No hand-listing — it works for any phrase and
# caps how many accounts can ever share the same wording within the window.
_PHRASE_TTL = 12 * 3600    # how long a shipped phrase is "taken" across ALL users
# n-gram lengths tracked as phrases. The longer spans (6-7) exist to catch
# stopword-heavy verbatim REPEATS — especially recycled questions like "are you
# the type who chases or the type who waits" — that no 4/5-word window can flag
# under the content-word bar. A 6+ word span shared across accounts is a stock
# phrase, not coincidence, so this adds coverage without loosening short phrases.
_PHRASE_NS = (4, 5, 6, 7)
_PHRASE_MIN_CONTENT = 3    # a tracked phrase must carry >= this many non-stop words

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


def _phrase_words(text):
    return re.sub(r'[^a-z\s]', ' ', (text or '').lower()).split()


def _salient_phrases(text):
    """Distinctive content n-grams in `text` -> {phrase: global_cache_key}.

    Keeps only n-grams carrying enough non-stopword tokens to be a real
    fingerprint (generic connective phrases like "are you the one who" are
    skipped), so normal language isn't sterilised — only recurring stock wording."""
    words = _phrase_words(text)
    out = {}
    for n in _PHRASE_NS:
        for i in range(len(words) - n + 1):
            gram = words[i:i + n]
            if sum(1 for w in gram if w not in _STOP) < _PHRASE_MIN_CONTENT:
                continue
            phrase = ' '.join(gram)
            out[phrase] = 'vg:p:' + hashlib.md5(phrase.encode('utf-8')).hexdigest()[:16]
    return out


def _find_hot_phrases(text):
    """Salient phrases in `text` recently shipped to ANY user (cross-user cooldown).
    Returns raw phrase strings, longest-first with contained overlaps collapsed."""
    salient = _salient_phrases(text)
    if not salient:
        return []
    try:
        present = cache.get_many(list(salient.values()))
    except Exception:
        return []
    hot = sorted((ph for ph, key in salient.items() if key in present), key=len, reverse=True)
    kept = []
    for ph in hot:
        if not any(ph in longer for longer in kept):
            kept.append(ph)
    return kept


def _record_phrases(text):
    """Mark this shipped reply's distinctive phrases as globally taken."""
    salient = _salient_phrases(text)
    if not salient:
        return
    try:
        cache.set_many({key: 1 for key in salient.values()}, _PHRASE_TTL)
    except Exception:
        pass


def _human_list(tids):
    """Turn internal term ids into plain hints for the rewrite prompt."""
    return sorted({t.split(':', 1)[-1].replace('_', ' ') for t in tids})


def _human(tids):
    return ', '.join(_human_list(tids))


def _rewrite_avoiding(client, text, avoid):
    from django.conf import settings
    from accounts.services.dedup import log_ai_usage
    model = getattr(settings, 'ANTHROPIC_REWRITE_MODEL', 'claude-haiku-4-5')
    avoid_str = '; '.join(avoid)
    prompt = (
        "Rewrite this dating-app message so it keeps the same meaning, tone, length, "
        "and its closing question, but avoids these overused words/phrases entirely — "
        f"do not reuse them or a close paraphrase: {avoid_str}.\n"
        "Keep the same number of sentences, natural, ending in a real question.\n\n"
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


def _flag_count(user_id, text):
    """How many watched words + hot phrases remain in `text` (0 == clean)."""
    return len(_find_cooled(user_id, text)) + len(_find_hot_phrases(text))


def _best_rewrite(client, user_id, text, avoid, attempts=2):
    """Try up to `attempts` rewrites; return (best_text, best_flag_count).

    Rewrites are non-deterministic — one roll can still echo a flagged phrase —
    so we keep the cleanest of a couple of tries and stop early on a clean one."""
    best, best_score = None, None
    for _ in range(attempts):
        cand = _rewrite_avoiding(client, text, avoid)
        if not cand:
            continue
        score = _flag_count(user_id, cand)
        if best is None or score < best_score:
            best, best_score = cand, score
        if best_score == 0:
            break
    return best, best_score


def enforce(client, user_id, text):
    """Two cooldowns in one pass, both best-effort:

      1. WORDS — watched attractor words on per-user (24h) / global (20m) cooldown.
      2. PHRASES — distinctive multi-word n-grams shipped to ANY user within the
         phrase window (cross-account fingerprint protection).

    If either fires, rewrite to drop the offending wording; then record the final
    text's words and phrases so future generations space them out. Returns the
    (possibly rewritten) text. Never raises.

    Key rule: we only keep the ORIGINAL if no rewrite is strictly better. The
    original IS the repeat we're trying to kill, so a partially-improved rewrite
    always beats shipping the exact phrase again."""
    try:
        cooled = _find_cooled(user_id, text)
        hot = _find_hot_phrases(text)
        avoid = _human_list(cooled) + hot
        if avoid:
            orig_score = len(cooled) + len(hot)
            cand, cand_score = _best_rewrite(client, user_id, text, avoid)
            if cand is not None and cand_score < orig_score:
                if cand_score == 0:
                    logger.info(
                        "VocabGovernor cleaned — user:%s words:%s phrases:%s", user_id, cooled, hot
                    )
                else:
                    logger.info(
                        "VocabGovernor reduced — user:%s %s->%s flags (words:%s phrases:%s)",
                        user_id, orig_score, cand_score, cooled, hot,
                    )
                text = cand
            else:
                logger.info(
                    "VocabGovernor could not improve — user:%s words:%s phrases:%s (shipping original)",
                    user_id, cooled, hot,
                )
        _record(user_id, text)
        _record_phrases(text)
        return text
    except Exception as e:
        logger.warning("VocabGovernor enforce failed: %s", e)
        return text
