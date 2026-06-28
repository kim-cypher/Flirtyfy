from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, PremiumEmail


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(post_save, sender=User)
def grant_welcome_credits(sender, instance, created, **kwargs):
    """New account → 15 free clicks + a welcome notification. Referral
    linkage (if a ?ref= code was supplied at signup) is applied separately
    in RegisterSerializer.create(), since it needs data this signal doesn't
    have access to."""
    if not created:
        return
    from .services.credits import get_or_create_credits, grant_credits, WELCOME_CLICKS
    from .services.notifications import create_notification

    credits = get_or_create_credits(instance)
    grant_credits(instance, WELCOME_CLICKS, 'welcome')

    # Pre-provisioned via admin (PremiumEmail added before this user ever
    # signed up) — flip them premium immediately, before they hit any limit.
    is_premium = PremiumEmail.objects.filter(email=instance.email.strip().lower()).exists()
    if is_premium:
        credits.is_premium = True
        credits.save(update_fields=['is_premium'])
        create_notification(
            instance, 'welcome', "Welcome to Flirtyfy — you're Premium!",
            "Your account has unlimited clicks. No limits, no waiting."
        )
        return

    create_notification(
        instance, 'welcome', "Welcome to Flirtyfy!",
        f"You've got {WELCOME_CLICKS} free clicks to start. Refer a friend and earn "
        "30 more — share your link from your account page."
    )


@receiver(post_save, sender=PremiumEmail)
def grant_premium_to_existing_user(sender, instance, created, **kwargs):
    """Admin adds an email that already has an account → flip it to premium
    right away, instead of waiting for them to re-register (they can't)."""
    if not created:
        return
    try:
        user = User.objects.get(email__iexact=instance.email)
    except User.DoesNotExist:
        return  # no account yet — grant_welcome_credits handles it if/when they sign up

    from .services.credits import get_or_create_credits
    from .services.notifications import create_notification

    credits = get_or_create_credits(user)
    if credits.is_premium:
        return  # already premium — don't re-notify
    credits.is_premium = True
    credits.save(update_fields=['is_premium'])
    create_notification(
        user, 'welcome', "You've been upgraded to Premium!",
        "Your account now has unlimited clicks. No limits, no waiting."
    )