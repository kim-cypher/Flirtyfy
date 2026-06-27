from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile


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

    get_or_create_credits(instance)
    grant_credits(instance, WELCOME_CLICKS, 'welcome')
    create_notification(
        instance, 'welcome', "Welcome to Flirtyfy!",
        f"You've got {WELCOME_CLICKS} free clicks to start. Refer a friend and earn "
        "30 more — share your link from your account page."
    )