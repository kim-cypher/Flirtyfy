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
    # New fields for button system (LEFT and RIGHT sides)
    conversation_context = models.TextField(null=True, blank=True, help_text="Original pasted conversation (LEFT side)")
    intent_type = models.CharField(
        max_length=10,
        choices=[('specific', 'Specific'), ('button', 'Button')],
        null=True,
        blank=True,
        help_text="Whether response was generated from pasted conversation (specific) or button click (button)"
    )
    button_intent = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Button name if intent_type='button' (e.g., 'morning_flirt', 'sensual')"
    )

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
