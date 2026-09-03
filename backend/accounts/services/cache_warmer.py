"""
Idle-aware warm-keeper for the static system-prompt cache.

Why: the left-panel persona (~1.8k tokens) is identical on every call and, on
Sonnet, is cached with a 1-hour TTL. During busy hours real traffic refreshes
that cache for free. During a quiet gap longer than an hour it would expire, so
the next user pays a cold cache WRITE instead of a cheap cache READ. This module
fires ONE tiny prefill just before the TTL lapses to keep the entry alive.

Idle-aware (this is the whole point): every left-panel generation stamps "now"
in Redis (Django cache). The scheduled `warm_cache` command only pings when that
stamp is older than _REFRESH_AFTER_SECONDS — so it never fires while real
traffic is flowing, and during a quiet stretch it fires at most ~once/hour.

No-op on Haiku: Haiku's 4k cache minimum means the persona never caches there,
so a warm ping produces no cache hit. Warming only pays off once the FAST model
is Sonnet (which caches ~1.8k-token prefixes). warm_now() always targets
settings.ANTHROPIC_FAST_MODEL, i.e. whatever model real drafts currently use.
"""
import logging
import time

from django.conf import settings
from django.core.cache import cache

from .dedup import log_ai_usage

logger = logging.getLogger(__name__)

_ACTIVITY_KEY = 'ai_cache:last_touch'
# Persona cache TTL is 1h (3600s). Refresh once the last touch is this old,
# leaving a safe margin for a ~5-minute scheduler interval plus Django boot.
_REFRESH_AFTER_SECONDS = 45 * 60
# The activity stamp must comfortably outlive the refresh window.
_STAMP_TTL_SECONDS = 3 * 60 * 60


def touch_activity() -> None:
    """Stamp 'the persona cache was just touched'. Called on every left-panel
    generation and after each warm ping. Never raises — must not break a reply."""
    try:
        cache.set(_ACTIVITY_KEY, time.time(), _STAMP_TTL_SECONDS)
    except Exception:
        pass


def seconds_since_touch():
    """Seconds since the persona cache was last touched, or None if unknown."""
    try:
        last = cache.get(_ACTIVITY_KEY)
        if last is None:
            return None
        return max(0.0, time.time() - float(last))
    except Exception:
        return None


def warm_now(client) -> bool:
    """Fire one minimal prefill that refreshes the persona cache for the model
    real left-panel drafts currently use. Returns True if a call was made.
    Never raises."""
    # Deferred import avoids a circular import (intent_detector imports this module).
    from .intent_detector import WOMAN_PERSONA_SYSTEM
    model = settings.ANTHROPIC_FAST_MODEL
    try:
        resp = client.messages.create(
            model=model,
            # Byte-identical to the real left-panel request so it refreshes the
            # SAME cache entry (same text, same cache_control, same model).
            system=[{
                'type': 'text',
                'text': WOMAN_PERSONA_SYSTEM,
                'cache_control': {'type': 'ephemeral', 'ttl': '1h'},
            }],
            messages=[{'role': 'user', 'content': 'warm'}],
            thinking={'type': 'disabled'},
            max_tokens=1,  # 1 (not 0) for SDK/model robustness; prefill still caches
        )
        log_ai_usage(logger, 'WARMUP', model, resp)
        touch_activity()
        return True
    except Exception as e:
        logger.warning("Cache warm ping failed: %s", e)
        return False
