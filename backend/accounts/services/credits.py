"""
Click-credit accounting. Server-side, tied to the user account — correct
across any device/session since the balance lives in the DB, keyed by user,
never in localStorage or a per-device session.

Design: a CreditGrant row per top-up (welcome, referral, purchase, admin),
each optionally with its own expiry, plus a single running clicks_used
counter. available_clicks() = sum of non-expired grants - clicks_used.
This keeps referral bonuses expiring independently of permanent credits,
and keeps the whole balance auditable (see Django admin).

Concurrency note: try_consume_click() uses select_for_update() so two
simultaneous requests from two devices on the same account can't both
succeed past zero. The earlier "is there a click available" check used for
UX gating (e.g. before paying for an LLM call) is advisory only — the
atomic deduction here is the actual source of truth and can never go
negative, even if the advisory check raced with another request.
"""
import logging
import random
import string

from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .notifications import create_notification

logger = logging.getLogger(__name__)

WELCOME_CLICKS = 15
REFERRAL_BONUS_CLICKS = 30
REFERRAL_BONUS_EXPIRY_DAYS = 7
LOW_CLICKS_THRESHOLD = 3


def generate_referral_code() -> str:
    from accounts.models import UserCredits
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not UserCredits.objects.filter(referral_code=code).exists():
            return code


def get_or_create_credits(user):
    from accounts.models import UserCredits
    credits, created = UserCredits.objects.get_or_create(
        user=user, defaults={'referral_code': generate_referral_code()}
    )
    return credits


def get_available_clicks(user) -> int:
    return get_or_create_credits(user).available_clicks()


def gate_check(user) -> bool:
    """
    Read-only pre-flight check, used before spending any LLM cost. Returns
    True if a click is available. If not, fires the out-of-clicks
    notification (once) right here — a user being turned away at the gate
    is exactly when they need to hear about it, and this is the only path
    that runs when they're already at zero (try_consume_click is never
    reached in that case, since the view returns immediately on a False gate).

    Premium accounts always pass — never gated, never notified.
    """
    credits = get_or_create_credits(user)
    if credits.is_premium:
        return True
    available = credits.available_clicks()
    if available <= 0:
        _notify_out_of_clicks_once(user, credits)
    return available > 0


def grant_credits(user, amount: int, reason: str, expires_in_days: int = None):
    """Adds a CreditGrant row. Used for welcome bonus, referral bonus, purchases, admin top-ups."""
    from accounts.models import CreditGrant
    credits = get_or_create_credits(user)
    expires_at = timezone.now() + timedelta(days=expires_in_days) if expires_in_days else None
    CreditGrant.objects.create(user_credits=credits, amount=amount, reason=reason, expires_at=expires_at)

    # A fresh grant means they're no longer "low"/"out" — let those notices fire again next time.
    update_fields = []
    if credits.low_clicks_notified and credits.available_clicks() > LOW_CLICKS_THRESHOLD:
        credits.low_clicks_notified = False
        update_fields.append('low_clicks_notified')
    if credits.out_of_clicks_notified and credits.available_clicks() > 0:
        credits.out_of_clicks_notified = False
        update_fields.append('out_of_clicks_notified')
    if update_fields:
        credits.save(update_fields=update_fields)

    logger.info(f"Granted {amount} clicks to user {user.id} ({reason})")
    return credits.available_clicks()


def try_consume_click(user) -> bool:
    """
    Atomically deducts one click if available. Returns True if consumed,
    False if the user has none left. Call this only after a generation has
    already succeeded — never deduct for a request that errored.

    Premium accounts always succeed and are never deducted — clicks_used
    stays untouched, so there's nothing to ever run out of.
    """
    from accounts.models import UserCredits
    with transaction.atomic():
        credits = UserCredits.objects.select_for_update().get_or_create(
            user=user, defaults={'referral_code': generate_referral_code()}
        )[0]
        if credits.is_premium:
            return True
        available = credits.available_clicks()
        if available <= 0:
            _notify_out_of_clicks_once(user, credits)
            return False

        credits.clicks_used += 1
        remaining = available - 1
        update_fields = ['clicks_used']

        if 0 < remaining <= LOW_CLICKS_THRESHOLD and not credits.low_clicks_notified:
            create_notification(
                user, 'low_clicks', "You're running low on clicks",
                f"You have {remaining} click{'s' if remaining != 1 else ''} left. "
                "Refer a friend for 30 free clicks, or top up to keep going."
            )
            credits.low_clicks_notified = True
            update_fields.append('low_clicks_notified')

        credits.save(update_fields=update_fields)

        if remaining <= 0:
            _notify_out_of_clicks_once(user, credits)

        return True


def _notify_out_of_clicks_once(user, credits):
    if credits.out_of_clicks_notified:
        return
    create_notification(
        user, 'out_of_clicks', "You're out of clicks",
        "You've used all your clicks. Top up to keep the conversation going, "
        "or refer a friend for 30 free bonus clicks."
    )
    credits.out_of_clicks_notified = True
    credits.save(update_fields=['out_of_clicks_notified'])


def apply_referral(new_user, referral_code: str) -> bool:
    """
    Links new_user to the referrer identified by referral_code, and grants
    the referrer their bonus. Returns True if a valid referral was applied.
    No-op (returns False) if the code is invalid, belongs to new_user
    themselves, or new_user was already referred by someone.
    """
    from accounts.models import UserCredits

    if not referral_code:
        return False

    new_user_credits = get_or_create_credits(new_user)
    if new_user_credits.referred_by_id is not None:
        return False  # already linked once — never re-assignable

    try:
        referrer_credits = UserCredits.objects.select_related('user').get(referral_code=referral_code.strip().upper())
    except UserCredits.DoesNotExist:
        return False

    referrer = referrer_credits.user
    if referrer.id == new_user.id:
        return False  # can't refer yourself

    new_user_credits.referred_by = referrer
    new_user_credits.save(update_fields=['referred_by'])

    grant_credits(referrer, REFERRAL_BONUS_CLICKS, 'referral', expires_in_days=REFERRAL_BONUS_EXPIRY_DAYS)
    create_notification(
        referrer, 'referral_joined', "Your friend joined!",
        f"{new_user.username} signed up using your referral link. "
        f"You earned {REFERRAL_BONUS_CLICKS} bonus clicks — valid for {REFERRAL_BONUS_EXPIRY_DAYS} days."
    )
    logger.info(f"Referral applied — referrer:{referrer.id} new_user:{new_user.id}")
    return True
