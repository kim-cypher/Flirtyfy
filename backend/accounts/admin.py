from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import (
    UserProfile, UserCredits, CreditGrant, Notification, Payment, PremiumEmail, AIUsage,
)


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


def _tokens_expr():
    """Fresh combined-sum expression each call (don't reuse one instance across
    querysets — Django resolves expressions in place)."""
    return (
        Sum('input_tokens') + Sum('output_tokens')
        + Sum('cache_read_tokens') + Sum('cache_write_tokens')
    )


@admin.register(AIUsage)
class AIUsageAdmin(admin.ModelAdmin):
    """Per-call AI cost/usage log + a summary dashboard on the changelist.

    The dashboard (top of the page) answers: how many tokens & how much cash the
    whole system used, per day, which users used the most, and the split by call
    type — over a selectable window (1 day / 2 wks / 3 wks / 30 / 90 days via the
    links). The raw rows below support date + label/model drill-down.
    """
    change_list_template = 'admin/accounts/aiusage/change_list.html'
    list_display = (
        'created_at', 'user', 'label', 'model',
        'input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_write_tokens', 'cost_usd',
    )
    list_filter = ('label', 'model')
    search_fields = ('user__username', 'user__email')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = (
        'created_at', 'user', 'label', 'model',
        'input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_write_tokens', 'cost_usd',
    )

    def has_add_permission(self, request):
        return False  # rows are written by the app, never by hand

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        try:
            extra_context.update(self._dashboard(request))
        except Exception:
            pass  # a broken dashboard must never hide the raw log
        return super().changelist_view(request, extra_context=extra_context)

    def _dashboard(self, request):
        try:
            window = int(request.GET.get('window_days', 1))
        except (TypeError, ValueError):
            window = 1
        window = max(1, min(window, 90))
        since = timezone.now() - timedelta(days=window)
        qs = AIUsage.objects.filter(created_at__gte=since)

        totals = qs.aggregate(
            calls=Count('id'),
            in_t=Sum('input_tokens'), out_t=Sum('output_tokens'),
            cr_t=Sum('cache_read_tokens'), cw_t=Sum('cache_write_tokens'),
            cost=Sum('cost_usd'),
        )
        per_day = list(
            qs.annotate(day=TruncDate('created_at')).values('day')
              .annotate(calls=Count('id'), tok=_tokens_expr(), cost=Sum('cost_usd'))
              .order_by('-day')
        )
        top_users = list(
            qs.filter(user__isnull=False).values('user__username')
              .annotate(calls=Count('id'), tok=_tokens_expr(), cost=Sum('cost_usd'))
              .order_by('-tok')[:25]
        )
        per_label = list(
            qs.values('label')
              .annotate(calls=Count('id'), cost=Sum('cost_usd'))
              .order_by('-cost')
        )
        return {
            'usage_window': window,
            'usage_totals': totals,
            'usage_per_day': per_day,
            'usage_top_users': top_users,
            'usage_per_label': per_label,
        }