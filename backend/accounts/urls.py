from django.urls import path
from .views import RegisterView, LoginView, ChatView, LocationSearchView

# API Endpoints
urlpatterns = [
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    
    # Chat and location endpoints (require authentication)
    path('chat/', ChatView.as_view(), name='chat'),
    path('locations/', LocationSearchView.as_view(), name='locations'),
]