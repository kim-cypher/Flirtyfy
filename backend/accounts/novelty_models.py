from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField


class ConversationUpload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploads')
    original_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class AIReply(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_replies')
    upload = models.ForeignKey(ConversationUpload, on_delete=models.CASCADE, related_name='replies')
    original_text = models.TextField()
    normalized_text = models.TextField()
    embedding = VectorField(dimensions=1536, null=True, blank=True)  # OpenAI text-embedding-3-small
    fingerprint = models.CharField(max_length=128, db_index=True)
    summary = models.TextField()
    intent = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=32, default='pending', db_index=True)
    error = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['fingerprint']),
            models.Index(fields=['normalized_text']),
        ]


class AIReplyFeedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_feedbacks')
    reply = models.ForeignKey(AIReply, on_delete=models.CASCADE, related_name='feedbacks')
    reason = models.CharField(max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)
