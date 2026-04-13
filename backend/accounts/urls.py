from django.urls import path
from .views import RegisterView, LoginView, ChatView, LocationSearchView
from .health_check import (
    health_basic,
    health_detailed,
    metrics,
    check_system_resources,
)

# API Endpoints
urlpatterns = [
    # Health check endpoints (public, no auth required)
    path('health/', health_basic, name='health_basic'),
    path('health/detailed/', health_detailed, name='health_detailed'),
    path('metrics/', metrics, name='metrics'),
    path('resources/', check_system_resources, name='resources'),
    
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    
    # Chat and location endpoints (require authentication)
    path('chat/', ChatView.as_view(), name='chat'),
    path('locations/', LocationSearchView.as_view(), name='locations'),
]