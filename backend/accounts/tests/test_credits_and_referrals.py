"""
Real regression tests for the click-credits, referral, and notification
system. No M-Pesa/network calls anywhere — those require real Daraja
credentials and are out of scope for an automated test.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from accounts.models import UserCredits, CreditGrant, Notification
from accounts.services.credits import (
    get_available_clicks,
    grant_credits,
    try_consume_click,
    apply_referral,
    gate_check,
    WELCOME_CLICKS,
    REFERRAL_BONUS_CLICKS,
    LOW_CLICKS_THRESHOLD,
)


def make_user(username):
    return User.objects.create_user(username=username, email=f'{username}@test.com', password='x')


class WelcomeCreditsTests(TestCase):
    def test_new_user_gets_welcome_clicks_via_signal(self):
        user = make_user('newbie')
        self.assertEqual(get_available_clicks(user), WELCOME_CLICKS)

    def test_new_user_gets_welcome_notification(self):
        user = make_user('newbie2')
        self.assertTrue(Notification.objects.filter(user=user, type='welcome').exists())

    def test_referral_code_is_unique_and_generated(self):
        user = make_user('newbie3')
        credits = UserCredits.objects.get(user=user)
        self.assertTrue(credits.referral_code)
        self.assertEqual(len(credits.referral_code), 8)


class ClickConsumptionTests(TestCase):
    def test_consume_click_decrements_balance(self):
        user = make_user('clicker')
        start = get_available_clicks(user)
        self.assertTrue(try_consume_click(user))
        self.assertEqual(get_available_clicks(user), start - 1)

    def test_cannot_consume_below_zero(self):
        user = make_user('emptyclicker')
        UserCredits.objects.filter(user=user).update(clicks_used=10**9)  # force way below zero conceptually
        # available_clicks() floors at 0 regardless
        self.assertEqual(get_available_clicks(user), 0)
        self.assertFalse(try_consume_click(user))

    def test_low_clicks_notification_fires_once(self):
        user = make_user('lowclicker')
        credits = UserCredits.objects.get(user=user)
        # Burn down to exactly the threshold boundary
        to_burn = WELCOME_CLICKS - LOW_CLICKS_THRESHOLD
        for _ in range(to_burn):
            try_consume_click(user)
        self.assertEqual(
            Notification.objects.filter(user=user, type='low_clicks').count(), 1
        )
        # Using one more click should NOT fire a second low_clicks notification
        try_consume_click(user)
        self.assertEqual(
            Notification.objects.filter(user=user, type='low_clicks').count(), 1
        )

    def test_out_of_clicks_notification_fires_once_when_exhausted(self):
        user = make_user('exhausted')
        for _ in range(WELCOME_CLICKS):
            try_consume_click(user)
        self.assertFalse(try_consume_click(user))  # now at zero, should fail cleanly
        self.assertEqual(
            Notification.objects.filter(user=user, type='out_of_clicks').count(), 1
        )
        # Trying again while still at zero must not spam a second notification
        try_consume_click(user)
        self.assertEqual(
            Notification.objects.filter(user=user, type='out_of_clicks').count(), 1
        )

    def test_gate_check_fires_out_of_clicks_notification(self):
        # Regression: the view-level pre-flight gate (used to skip the LLM
        # call entirely when balance is already zero) initially only read
        # the balance and never notified — only try_consume_click did. Since
        # the view returns immediately on a failed gate, try_consume_click
        # is never reached on a request that arrives after the balance is
        # already zero (e.g. a second device hitting the gate after an
        # earlier request already exhausted it) — gate_check must notify
        # directly in that case, not rely on try_consume_click to do it.
        user = make_user('gatecheck')
        credits = UserCredits.objects.get(user=user)
        credits.clicks_used = WELCOME_CLICKS  # exhausted without going through try_consume_click
        credits.save()
        self.assertEqual(Notification.objects.filter(user=user, type='out_of_clicks').count(), 0)

        self.assertFalse(gate_check(user))
        self.assertEqual(Notification.objects.filter(user=user, type='out_of_clicks').count(), 1)

        # Repeated gate checks while still at zero must not spam a second notification
        gate_check(user)
        self.assertEqual(Notification.objects.filter(user=user, type='out_of_clicks').count(), 1)

    def test_gate_check_true_when_clicks_available(self):
        user = make_user('gatecheck2')
        self.assertTrue(gate_check(user))

    def test_new_grant_resets_low_and_out_notification_flags(self):
        user = make_user('refilled')
        for _ in range(WELCOME_CLICKS):
            try_consume_click(user)
        credits = UserCredits.objects.get(user=user)
        self.assertTrue(credits.out_of_clicks_notified)

        grant_credits(user, 50, 'purchase')
        credits.refresh_from_db()
        self.assertFalse(credits.out_of_clicks_notified)
        self.assertFalse(credits.low_clicks_notified)


class CreditExpiryTests(TestCase):
    def test_non_expiring_grant_always_counts(self):
        user = make_user('permagrant')
        grant_credits(user, 100, 'purchase')  # no expiry
        self.assertEqual(get_available_clicks(user), WELCOME_CLICKS + 100)

    def test_expired_grant_does_not_count(self):
        user = make_user('expiredgrant')
        credits = UserCredits.objects.get(user=user)
        # Manually create an already-expired grant (bypassing grant_credits'
        # relative-days helper so we can backdate it precisely)
        CreditGrant.objects.create(
            user_credits=credits, amount=30, reason='referral',
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.assertEqual(get_available_clicks(user), WELCOME_CLICKS)  # expired 30 excluded

    def test_not_yet_expired_grant_does_count(self):
        user = make_user('freshgrant')
        grant_credits(user, REFERRAL_BONUS_CLICKS, 'referral', expires_in_days=7)
        self.assertEqual(get_available_clicks(user), WELCOME_CLICKS + REFERRAL_BONUS_CLICKS)


class ReferralTests(TestCase):
    def test_referral_grants_referrer_bonus(self):
        referrer = make_user('referrer')
        referrer_credits = UserCredits.objects.get(user=referrer)
        new_user = make_user('referred')

        applied = apply_referral(new_user, referrer_credits.referral_code)
        self.assertTrue(applied)
        self.assertEqual(get_available_clicks(referrer), WELCOME_CLICKS + REFERRAL_BONUS_CLICKS)

    def test_referral_links_referred_by(self):
        referrer = make_user('referrer2')
        referrer_credits = UserCredits.objects.get(user=referrer)
        new_user = make_user('referred2')

        apply_referral(new_user, referrer_credits.referral_code)
        new_user_credits = UserCredits.objects.get(user=new_user)
        self.assertEqual(new_user_credits.referred_by_id, referrer.id)

    def test_referral_creates_notification_for_referrer(self):
        referrer = make_user('referrer3')
        referrer_credits = UserCredits.objects.get(user=referrer)
        new_user = make_user('referred3')

        apply_referral(new_user, referrer_credits.referral_code)
        self.assertTrue(Notification.objects.filter(user=referrer, type='referral_joined').exists())

    def test_invalid_referral_code_is_a_no_op(self):
        new_user = make_user('lonewolf')
        applied = apply_referral(new_user, 'NOTAREALCODE')
        self.assertFalse(applied)
        self.assertEqual(get_available_clicks(new_user), WELCOME_CLICKS)  # only the normal welcome bonus

    def test_self_referral_is_blocked(self):
        user = make_user('selfreferrer')
        credits = UserCredits.objects.get(user=user)
        applied = apply_referral(user, credits.referral_code)
        self.assertFalse(applied)

    def test_referral_cannot_be_reassigned(self):
        referrer_a = make_user('referrer_a')
        referrer_b = make_user('referrer_b')
        new_user = make_user('referred_twice')

        code_a = UserCredits.objects.get(user=referrer_a).referral_code
        code_b = UserCredits.objects.get(user=referrer_b).referral_code

        self.assertTrue(apply_referral(new_user, code_a))
        self.assertFalse(apply_referral(new_user, code_b))  # already linked — second attempt is a no-op

        new_user_credits = UserCredits.objects.get(user=new_user)
        self.assertEqual(new_user_credits.referred_by_id, referrer_a.id)
        # referrer_b must NOT have received a bonus from the rejected second attempt
        self.assertEqual(get_available_clicks(referrer_b), WELCOME_CLICKS)
