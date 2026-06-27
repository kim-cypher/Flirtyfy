"""
Throttles for the AI-generation endpoints. Every request costs real LLM API
money (Anthropic, and sometimes OpenAI for dedup), and some paths already
make 2-3 calls per single click. These cap two independent things:
  - burst rate: blocks scripted/bot-speed abuse, not normal human clicking
  - daily ceiling: catches runaway loops or bugs, set well above real heavy
    usage so it never blocks a genuine power user
"""
from rest_framework.throttling import UserRateThrottle


class GenerationBurstThrottle(UserRateThrottle):
    scope = 'generation_burst'


class GenerationDailyThrottle(UserRateThrottle):
    scope = 'generation_daily'


class PaymentInitiateThrottle(UserRateThrottle):
    """Stricter than generation — an STK push interrupts the user's phone
    directly, so repeated triggers are more disruptive than a chat retry."""
    scope = 'payment_initiate'
