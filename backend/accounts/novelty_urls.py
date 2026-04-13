from django.urls import path
from accounts.novelty_views import ConversationUploadView, AIReplyListView, AIReplyFeedbackView

urlpatterns = [
    path('upload/', ConversationUploadView.as_view(), name='upload'),
    path('replies/', AIReplyListView.as_view(), name='replies'),
    path('feedback/', AIReplyFeedbackView.as_view(), name='ai-reply-feedback'),
]
