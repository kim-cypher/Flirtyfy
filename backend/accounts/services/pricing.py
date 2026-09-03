"""
Per-token USD pricing for the Anthropic models this app uses, and a cost helper.

Cache WRITE is priced at the 1-HOUR TTL rate because every cache_control in this
app uses ttl='1h' (see intent_detector.py, button_generator.py, cache_warmer.py).
Cache READ ("hits and refreshes") is the same rate for 5m and 1h.

Keep these numbers in sync with https://www.anthropic.com pricing if rates change.
Rates are quoted per MILLION tokens, then converted to per-token Decimals.
"""
from decimal import Decimal

# USD per 1,000,000 tokens.
_PER_MTOK = {
    'claude-haiku-4-5': {'in': 1,  'out': 5,  'cache_read': 0.10, 'cache_write': 2.00},   # 1h write = 2x base
    'claude-sonnet-5':  {'in': 2,  'out': 10, 'cache_read': 0.20, 'cache_write': 4.00},   # 1h write = 2x base
}

_MILLION = Decimal('1000000')


def _rate(model: str, field: str) -> Decimal:
    m = _PER_MTOK.get(model)
    if not m:
        return Decimal('0')
    return Decimal(str(m[field])) / _MILLION


def compute_cost(model, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens) -> Decimal:
    """USD cost for one API call as a Decimal. Unknown model -> 0 (tokens are
    still stored, so the row is preserved; only the dollar figure is 0)."""
    return (
        _rate(model, 'in') * Decimal(int(input_tokens or 0))
        + _rate(model, 'out') * Decimal(int(output_tokens or 0))
        + _rate(model, 'cache_read') * Decimal(int(cache_read_tokens or 0))
        + _rate(model, 'cache_write') * Decimal(int(cache_write_tokens or 0))
    )


# Revenue is collected in KES (M-Pesa); AI cost is in USD. To compare them for
# the margin report we convert KES -> USD. Update this to your real M-Pesa
# settlement rate whenever it drifts materially.
KES_PER_USD = Decimal('129')


def kes_to_usd(kes) -> Decimal:
    """Convert a KES amount to USD using KES_PER_USD. Returns Decimal."""
    if not kes:
        return Decimal('0')
    return Decimal(kes) / KES_PER_USD
