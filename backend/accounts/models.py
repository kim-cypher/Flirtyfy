from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    age = models.IntegerField(default=18, help_text="User must be 18+ to use this app")
    date_of_birth = models.DateField(null=True, blank=True, help_text="Stored for age verification")
    age_verified = models.BooleanField(default=False, help_text="Confirms user is 18+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'


class UserCredits(models.Model):
    """
    Server-side click balance, tied to the user account — not a device or
    browser session, so the balance is correct no matter which computer the
    same account logs in from. Actual available clicks = sum of non-expired
    CreditGrant amounts minus clicks_used (see available_clicks()).
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='credits')
    clicks_used = models.PositiveIntegerField(default=0)
    referral_code = models.CharField(max_length=12, unique=True, db_index=True)
    referred_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals_made'
    )
    # Guards against re-firing the same "low/out of clicks" notification on
    # every single click once the threshold is crossed — reset when a new
    # grant pushes the balance back up.
    low_clicks_notified = models.BooleanField(default=False)
    out_of_clicks_notified = models.BooleanField(default=False)
    # Unlimited clicks, never deducted. Set automatically when the user's
    # email matches a PremiumEmail row (see signals.py), or toggled directly
    # here in admin for a manual override.
    is_premium = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def available_clicks(self) -> int:
        total_granted = self.grants.filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        return max(total_granted - self.clicks_used, 0)

    def __str__(self):
        return f"{self.user.username} credits"

    class Meta:
        verbose_name = 'User Credits'
        verbose_name_plural = 'User Credits'


class CreditGrant(models.Model):
    """One grant of clicks — welcome bonus, referral bonus, purchase, or a
    manual admin adjustment. Kept as individual rows (not a single counter)
    so referral bonuses can expire independently of permanent grants, and so
    the balance is always auditable."""
    REASON_CHOICES = [
        ('welcome', 'Welcome bonus'),
        ('referral', 'Referral bonus'),
        ('purchase', 'Purchase'),
        ('admin', 'Admin adjustment'),
    ]
    user_credits = models.ForeignKey(UserCredits, on_delete=models.CASCADE, related_name='grants')
    amount = models.IntegerField()
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Null = never expires")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_credits.user.username} +{self.amount} ({self.reason})"

    class Meta:
        indexes = [models.Index(fields=['user_credits', 'expires_at'])]


class Notification(models.Model):
    """In-app notification — shown in the notification bell, not email."""
    TYPE_CHOICES = [
        ('welcome', 'Welcome'),
        ('low_clicks', 'Low Clicks'),
        ('out_of_clicks', 'Out of Clicks'),
        ('referral_joined', 'Referral Joined'),
        ('payment_success', 'Payment Success'),
        ('payment_failed', 'Payment Failed'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=120)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'is_read', '-created_at'])]

    def __str__(self):
        return f"{self.user.username}: {self.title}"


class Payment(models.Model):
    """One M-Pesa STK Push attempt. Daraja calls our webhook asynchronously
    once the user completes (or cancels/fails) the prompt on their phone —
    status starts 'pending' and is updated by MpesaCallbackView."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    phone_number = models.CharField(max_length=20)
    amount_kes = models.DecimalField(max_digits=10, decimal_places=2)
    clicks_granted = models.PositiveIntegerField()
    checkout_request_id = models.CharField(max_length=100, unique=True, db_index=True)
    merchant_request_id = models.CharField(max_length=100, blank=True)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    raw_callback = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount_kes} KES - {self.status}"


class PremiumEmail(models.Model):
    """
    Admin-managed allowlist. Adding a row here immediately flips that user
    to premium (unlimited clicks) if the account already exists, and
    automatically flips them to premium the moment they register if it
    doesn't exist yet — see signals.py for both paths.
    """
    email = models.EmailField(unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = 'Premium Email'
        verbose_name_plural = 'Premium Emails'