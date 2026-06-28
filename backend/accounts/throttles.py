"""
Throttles for the AI-generation endpoints. Every request costs real LLM API
money (Anthropic, and sometimes OpenAI for dedup), and some paths already
make 2-3 calls per single click. These cap two independent things:
  - burst rate: blocks scripted/bot-speed abuse, not normal human clicking
  - daily ceiling: catches runaway loops or bugs, set well above real heavy
    usage so it never blocks a genuine power user
"""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class GenerationBurstThrottle(UserRateThrottle):
    scope = 'generation_burst'


class GenerationDailyThrottle(UserRateThrottle):
    scope = 'generation_daily'


class PaymentInitiateThrottle(UserRateThrottle):
    """Stricter than generation — an STK push interrupts the user's phone
    directly, so repeated triggers are more disruptive than a chat retry."""
    scope = 'payment_initiate'


# Login/Register happen before authentication, so UserRateThrottle (keyed by
# user) can't apply — these are keyed by IP instead. Without these, both
# endpoints had ZERO rate limiting: unlimited password-guessing attempts
# against any account, and unlimited fake-account registration.
class LoginThrottle(AnonRateThrottle):
    scope = 'login'


class RegisterThrottle(AnonRateThrottle):
    scope = 'register'
