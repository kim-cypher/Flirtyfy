from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.novelty_models import ConversationUpload, AIReply
from accounts.serializers import ConversationUploadSerializer, AIReplySerializer
from accounts.tasks import process_upload_task
from django.utils import timezone
from datetime import timedelta

class ConversationUploadView(generics.CreateAPIView):
    serializer_class = ConversationUploadSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        upload = serializer.save(user=self.request.user)
        process_upload_task.delay(upload.id)

class AIReplyListView(generics.ListAPIView):
    serializer_class = AIReplySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        since = timezone.now() - timedelta(days=45)
        return AIReply.objects.filter(user=self.request.user, created_at__gte=since)
