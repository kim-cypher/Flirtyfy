from django.contrib import admin
from django.contrib.auth.models import User
from .models import UserProfile, UserCredits, CreditGrant, Notification, Payment, PremiumEmail


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    fields = ('bio', 'avatar')


class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'email')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    inlines = [UserProfileInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile)


class CreditGrantInline(admin.TabularInline):
    model = CreditGrant
    extra = 0
    readonly_fields = ('amount', 'reason', 'expires_at', 'created_at')


@admin.register(UserCredits)
class UserCreditsAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_premium', 'available_clicks', 'clicks_used', 'referral_code', 'referred_by', 'created_at')
    list_filter = ('is_premium',)
    search_fields = ('user__username', 'user__email', 'referral_code')
    # is_premium is deliberately editable — manual override/revoke independent
    # of the PremiumEmail allowlist.
    readonly_fields = ('clicks_used', 'referral_code', 'created_at')
    inlines = [CreditGrantInline]

    def available_clicks(self, obj):
        return obj.available_clicks()


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read')
    search_fields = ('user__username', 'title')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount_kes', 'clicks_granted', 'status', 'phone_number', 'mpesa_receipt_number', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'phone_number', 'checkout_request_id', 'mpesa_receipt_number')
    readonly_fields = ('checkout_request_id', 'merchant_request_id', 'raw_callback', 'created_at', 'updated_at')


@admin.register(PremiumEmail)
class PremiumEmailAdmin(admin.ModelAdmin):
    """
    Add an email here → that user (existing or future) gets unlimited
    clicks automatically. See signals.py: grant_premium_to_existing_user
    (flips an existing account immediately) and grant_welcome_credits
    (flips a new signup at registration time).
    """
    list_display = ('email', 'created_at')
    search_fields = ('email',)