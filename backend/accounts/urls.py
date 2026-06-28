from django.urls import path
from .views import (
    RegisterView, LoginView, PasswordResetView, GenerateSpecificResponseView, GenerateButtonResponseView,
    CreditsView, NotificationListView, NotificationMarkReadView,
    InitiatePaymentView, PaymentStatusView, MpesaCallbackView,
)
from .health_check import health_basic, health_detailed, metrics, check_system_resources

urlpatterns = [
    path('health/', health_basic, name='health_basic'),
    path('health/detailed/', health_detailed, name='health_detailed'),
    path('metrics/', metrics, name='metrics'),
    path('resources/', check_system_resources, name='resources'),

    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),

    path('chat/generate-specific/', GenerateSpecificResponseView.as_view(), name='generate-specific'),
    path('chat/generate-button/', GenerateButtonResponseView.as_view(), name='generate-button'),

    path('credits/', CreditsView.as_view(), name='credits'),

    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/mark-read/', NotificationMarkReadView.as_view(), name='notifications-mark-read'),

    path('payments/initiate/', InitiatePaymentView.as_view(), name='payments-initiate'),
    path('payments/status/<str:checkout_request_id>/', PaymentStatusView.as_view(), name='payments-status'),
    path('payments/mpesa-callback/', MpesaCallbackView.as_view(), name='payments-mpesa-callback'),
]