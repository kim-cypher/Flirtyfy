"""
Phrase-level uniqueness check — shared by the left panel (intent_detector.py)
and the button system (button_generator.py).

Catches literal n-gram overlap with a user's OWN reply history, sourced from
the DB (AIReply.normalized_text), not Redis — reuses the 30-day retention
that already exists via AIReply.expires_at, so there is no new storage.

On a collision, only the colliding SENTENCE is rewritten via one small, cheap
LLM call — not a full regeneration. This is a best-effort uniqueness pass,
not a hard gate: if the rewrite call fails, or the result still collides,
the original text is returned unchanged so a response is never blocked.
"""
import re
import logging
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

_DEDUP_DAYS = 30
_DEDUP_LIMIT = 500  # generous cap over realistic 30-day per-user volume


def _extract_ngrams(text: str, n: int = 4) -> set:
    words = re.sub(r'[^a-z\s]', '', text.lower()).split()
    return {' '.join(words[i:i + n]) for i in range(len(words) - n + 1)}


def get_recent_user_texts(user_id: int, days: int = _DEDUP_DAYS, limit: int = _DEDUP_LIMIT) -> list:
    """This user's own past AI-reply texts (left panel + buttons) from the last `days` days."""
    from accounts.novelty_models import AIReply
    since = timezone.now() - timedelta(days=days)
    return list(
        AIReply.objects
        .filter(user_id=user_id, created_at__gte=since)
        .exclude(normalized_text='')
        .order_by('-created_at')
        .values_list('normalized_text', flat=True)[:limit]
    )


def find_repeated_ngram(candidate: str, past_texts: list, n: int = 4):
    """Returns one colliding n-gram string if found, else None."""
    candidate_grams = _extract_ngrams(candidate, n=n)
    if not candidate_grams:
        return None
    for past in past_texts:
        overlap = candidate_grams & _extract_ngrams(past, n=n)
        if overlap:
            return next(iter(overlap))
    return None


def rewrite_colliding_sentence(client, sentence: str, matched_ngram: str, is_question: bool):
    """One small, cheap LLM call: rewrite a single sentence to drop the colliding phrase."""
    if is_question:
        prompt = (
            "Rewrite this question so it asks the same thing in different words.\n"
            f"Do not reuse the exact phrase \"{matched_ngram}\".\n"
            "Keep it a genuine question of similar length, ending in a question mark.\n\n"
            f"Question: \"{sentence.strip()}\"\n\n"
            "Output only the rewritten question, nothing else."
        )
    else:
        prompt = (
            "Rewrite this sentence so it says the same thing in different words.\n"
            f"Do not reuse the exact phrase \"{matched_ngram}\".\n"
            "Keep similar length and tone.\n\n"
            f"Sentence: \"{sentence.strip()}\"\n\n"
            "Output only the rewritten sentence, nothing else."
        )
    try:
        resp = client.messages.create(
            model=_rewrite_model(),
            system="You are a precise rewriting assistant. Output only the requested rewritten text, nothing else.",
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.9,
            max_tokens=40,
        )
        text = resp.content[0].text.strip().strip('"')
        if not text:
            return None
        if is_question and not text.endswith('?'):
            text = text.rstrip('.,!;: ') + '?'
        return text
    except Exception as e:
        logger.error(f"Dedup rewrite call failed: {e}")
        return None


def dedupe_against_history(client, user_id: int, text: str, n: int = 4):
    """
    Checks `text` against the user's last 30 days of AI replies for a literal
    n-gram collision. If found, rewrites only the colliding sentence.

    Returns (final_text, was_rewritten: bool). Never raises; on any failure
    or unresolved collision, returns the original text unchanged.
    """
    past_texts = get_recent_user_texts(user_id)
    if not past_texts:
        return text, False

    matched = find_repeated_ngram(text, past_texts, n=n)
    if not matched:
        return text, False

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    target_idx = None
    for i, s in enumerate(sentences):
        s_norm = re.sub(r'[^a-z\s]', '', s.lower())
        if matched in s_norm:
            target_idx = i
            break

    if target_idx is None:
        # Matched n-gram spans a sentence boundary — rare edge case, leave as-is.
        return text, False

    is_question = sentences[target_idx].strip().endswith('?')
    rewritten_sentence = rewrite_colliding_sentence(client, sentences[target_idx], matched, is_question)
    if not rewritten_sentence:
        return text, False

    sentences[target_idx] = rewritten_sentence
    patched = ' '.join(sentences)

    if find_repeated_ngram(patched, past_texts, n=n):
        logger.warning(f"Dedup rewrite still collided — user:{user_id}, keeping original")
        return text, False

    return patched, True


# ---------------------------------------------------------------------------
# Near-duplicate similarity check — Postgres pg_trgm trigram similarity.
#
# Replaces the OpenAI-embedding "semantic" layer entirely: that layer required
# an OpenAI key, Redis, AND a Celery worker to all be alive (any failure was
# silent), embedded the WRONG text for left-panel replies (the pasted
# conversation instead of the reply), and died completely on OpenAI quota
# errors. Trigram similarity runs synchronously in the same Postgres query
# path with zero external dependencies, and catches heavily-overlapping
# rewordings that the exact 4-gram check misses.
#
# Requires the pg_trgm extension + GIN index (migration
# 0014_enable_pg_trgm_extension).
# ---------------------------------------------------------------------------

_SIMILARITY_THRESHOLD = 0.5  # trigram similarity; 0.5+ means heavy overlap


def _normalize_for_similarity(text: str) -> str:
    """Match views._normalize_text so candidate and stored texts compare fairly."""
    text = re.sub(r'[^\w\s]', '', text.lower())
    return re.sub(r'\s+', ' ', text).strip()


def find_similar_past_reply(user_id: int, text: str, days: int = _DEDUP_DAYS,
                            threshold: float = _SIMILARITY_THRESHOLD):
    """Most-similar past AIReply above `threshold`, or None. Never raises."""
    from accounts.novelty_models import AIReply
    from django.contrib.postgres.search import TrigramSimilarity

    normalized = _normalize_for_similarity(text)
    if not normalized:
        return None
    since = timezone.now() - timedelta(days=days)
    try:
        return (
            AIReply.objects
            .filter(user_id=user_id, created_at__gte=since)
            .exclude(normalized_text='')
            .annotate(sim=TrigramSimilarity('normalized_text', normalized))
            .filter(sim__gt=threshold)
            .order_by('-sim')
            .first()
        )
    except Exception as e:
        logger.error(f"Trigram similarity lookup failed (is pg_trgm installed?): {e}")
        return None


def _rewrite_model():
    from django.conf import settings
    return getattr(settings, 'ANTHROPIC_REWRITE_MODEL', 'claude-haiku-4-5')


def rewrite_similar_collision(client, text: str, reference_text: str):
    """One LLM call: rewrite the full message to stop resembling a specific past reply."""
    prompt = (
        "Rewrite this message so it keeps the same warmth and intent, but uses clearly "
        "different imagery, structure, and wording than the reference message below.\n"
        "Do not reuse its sentence shape, its specific images, or its phrasing.\n\n"
        f"Reference (avoid resembling this): \"{reference_text.strip()}\"\n\n"
        f"Message to rewrite: \"{text.strip()}\"\n\n"
        "Keep the same number of sentences and similar length, ending in a genuine question. "
        "Output only the rewritten message, nothing else."
    )
    try:
        resp = client.messages.create(
            model=_rewrite_model(),
            system="You are a precise rewriting assistant. Output only the requested rewritten message, nothing else.",
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.95,
            max_tokens=130,
        )
        out = resp.content[0].text.strip().strip('"')
        if not out:
            return None
        if not out.endswith('?'):
            out = out.rstrip('.,!;: ') + '?'
        return out
    except Exception as e:
        logger.error(f"Similarity dedup rewrite call failed: {e}")
        return None


def dedupe_similar(client, user_id: int, text: str, threshold: float = _SIMILARITY_THRESHOLD):
    """
    Synchronous near-duplicate check against the user's 30-day history using
    pg_trgm. On a high-similarity hit, rewrites the whole message via one
    cheap LLM call.

    Returns (final_text, was_rewritten: bool). Never raises; any failure
    returns the original text unchanged — best-effort pass, never a hard gate.
    """
    closest = find_similar_past_reply(user_id, text, threshold=threshold)
    if closest is None:
        return text, False

    rewritten = rewrite_similar_collision(client, text, closest.normalized_text)
    if not rewritten:
        return text, False

    return rewritten, True


# ---------------------------------------------------------------------------
# Question-tail uniqueness — the final question is where repetition is most
# visible to a customer ("Could you handle knowing exactly what I was thinking
# right now?" appeared under six different buttons). Compares the candidate's
# final question against the ENDINGS of past replies (every reply ends with
# its question) and rewrites just the question on a collision.
# ---------------------------------------------------------------------------

def dedupe_question_tail(client, user_id: int, text: str, threshold: float = 0.72):
    """Returns (final_text, was_rewritten: bool). Never raises."""
    from difflib import SequenceMatcher

    try:
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        if not sentences or not sentences[-1].strip().endswith('?'):
            return text, False
        tail_raw = sentences[-1].strip()
        tail = _normalize_for_similarity(tail_raw)
        tail_words = tail.split()
        if len(tail_words) < 4:
            return text, False

        for past in get_recent_user_texts(user_id):
            past_words = past.split()
            if len(past_words) < 4:
                continue
            past_tail = ' '.join(past_words[-len(tail_words):])
            if SequenceMatcher(None, tail, past_tail).ratio() >= threshold:
                rewritten_q = rewrite_colliding_sentence(
                    client, tail_raw, past_tail, is_question=True
                )
                if rewritten_q:
                    sentences[-1] = rewritten_q
                    return ' '.join(sentences), True
                return text, False
        return text, False
    except Exception as e:
        logger.error(f"Question-tail dedup failed: {e}")
        return text, False
