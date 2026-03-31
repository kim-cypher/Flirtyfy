from django.urls import path
from accounts.novelty_views import ConversationUploadView, AIReplyListView

urlpatterns = [
    path('upload/', ConversationUploadView.as_view(), name='upload'),
    path('replies/', AIReplyListView.as_view(), name='replies'),
]
