import logging
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

from accounts.novelty_models import ConversationUpload, AIReply, AIReplyFeedback
from accounts.serializers import ConversationUploadSerializer, AIReplySerializer, AIReplyFeedbackSerializer
from accounts.tasks import process_upload_task

logger = logging.getLogger(__name__)

RATE_LIMIT = 100  # max uploads per 5 minutes (increased for testing)
RATE_PERIOD = 300  # seconds


class ConversationUploadView(generics.CreateAPIView):
    """Handle conversation uploads"""
    serializer_class = ConversationUploadSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Create with rate limiting and abuse prevention"""
        user_id = request.user.id
        key = f"chat_upload_rate_{user_id}"
        count = cache.get(key, 0)
        
        if count >= RATE_LIMIT:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return Response(
                {"detail": "Rate limit exceeded. Please wait before uploading more chats."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # Abuse prevention: track repeated prohibited/abusive triggers
        abuse_key = f"chat_abuse_{user_id}"
        abuse_count = cache.get(abuse_key, 0)
        
        if abuse_count >= 5:
            logger.warning(f"User {user_id} temporarily banned for repeated abuse triggers.")
            return Response(
                {"detail": "You have been temporarily blocked due to repeated abusive or prohibited content."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        cache.set(key, count + 1, timeout=RATE_PERIOD)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Save upload and trigger async processing"""
        upload = serializer.save(user=self.request.user)
        logger.info(f"Conversation uploaded by user {self.request.user.id}, upload id {upload.id}")
        
        # Try async via Celery, fallback to sync if Celery not available
        try:
            process_upload_task.delay(upload.id)
        except Exception as e:
            logger.warning(f"Celery not available, processing synchronously: {e}")
            try:
                process_upload_task(upload.id)
            except Exception as task_error:
                logger.error(f"Failed to process upload {upload.id}: {task_error}")


class AIReplyListView(generics.ListAPIView):
    """List AI replies for the current user"""
    serializer_class = AIReplySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get replies from last 45 days, ordered by newest first"""
        since = timezone.now() - timedelta(days=45)
        return AIReply.objects.filter(
            user=self.request.user, 
            created_at__gte=since
        ).order_by('-created_at')  # Newest replies first


class AIReplyFeedbackView(generics.CreateAPIView):
    """Handle feedback on AI replies"""
    serializer_class = AIReplyFeedbackSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """Save feedback with user"""
        serializer.save(user=self.request.user)
