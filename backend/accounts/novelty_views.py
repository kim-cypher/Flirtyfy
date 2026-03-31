from accounts.novelty_models import AIReplyFeedback
from accounts.serializers import AIReplyFeedbackSerializer
from rest_framework import permissions
class AIReplyFeedbackView(generics.CreateAPIView):
    serializer_class = AIReplyFeedbackSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
import logging
logger = logging.getLogger(__name__)
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.novelty_models import ConversationUpload, AIReply
from accounts.serializers import ConversationUploadSerializer, AIReplySerializer
from accounts.tasks import process_upload_task
from django.utils import timezone
from datetime import timedelta

class ConversationUploadView(generics.CreateAPIView):
        # Simple in-memory rate limiting (production: use Redis or cache backend)
        from django.core.cache import cache
        RATE_LIMIT = 10  # max uploads per 5 minutes
        RATE_PERIOD = 300  # seconds

        def create(self, request, *args, **kwargs):
            user_id = request.user.id
            key = f"chat_upload_rate_{user_id}"
            count = self.cache.get(key, 0)
            if count >= self.RATE_LIMIT:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                return Response({"detail": "Rate limit exceeded. Please wait before uploading more chats."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            self.cache.set(key, count + 1, timeout=self.RATE_PERIOD)
            # Abuse prevention: track repeated prohibited/abusive triggers
            abuse_key = f"chat_abuse_{user_id}"
            abuse_count = self.cache.get(abuse_key, 0)
            if abuse_count >= 5:
                logger.warning(f"User {user_id} temporarily banned for repeated abuse triggers.")
                return Response({"detail": "You have been temporarily blocked due to repeated abusive or prohibited content."}, status=status.HTTP_403_FORBIDDEN)
            return super().create(request, *args, **kwargs)
    serializer_class = ConversationUploadSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        upload = serializer.save(user=self.request.user)
        logger.info(f"Conversation uploaded by user {self.request.user.id}, upload id {upload.id}")
        process_upload_task.delay(upload.id)

class AIReplyListView(generics.ListAPIView):
    serializer_class = AIReplySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        since = timezone.now() - timedelta(days=45)
        return AIReply.objects.filter(user=self.request.user, created_at__gte=since)
