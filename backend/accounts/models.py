from django.db import models
from django.contrib.auth.models import AbstractUser, User
from django.utils import timezone
import json


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    age = models.IntegerField(default=18, help_text="User must be 18+ to use this app")
    date_of_birth = models.DateField(null=True, blank=True, help_text="Stored for age verification")
    age_verified = models.BooleanField(default=False, help_text="Confirms user is 18+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'


class ConversationLog(models.Model):
    """One record per user conversation session"""
    user_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    reply_count = models.IntegerField(default=0)
    last_question_starter = models.CharField(
        max_length=100, blank=True, null=True
    )

    def __str__(self):
        return f"Conversation {self.id} for user {self.user_id}"


class ResponseLog(models.Model):
    """One record per AI response sent"""
    conversation = models.ForeignKey(
        ConversationLog, on_delete=models.CASCADE,
        related_name='responses'
    )
    reply_number = models.IntegerField()
    response_text = models.TextField()
    structure_used = models.CharField(max_length=1)  # A-G
    tone_used = models.CharField(max_length=20)
    question_starter = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['conversation', 'reply_number']
        ordering = ['reply_number']

    def __str__(self):
        return f"Response {self.reply_number} in conversation {self.conversation.id}"


class NgramLog(models.Model):
    """Stores all bigrams and trigrams used"""
    user_id = models.CharField(max_length=100)
    ngram = models.CharField(max_length=200)
    ngram_type = models.CharField(
        max_length=10,
        choices=[('bigram', 'Bigram'), ('trigram', 'Trigram')]
    )
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user_id', 'ngram']),
            models.Index(fields=['used_at']),
        ]

    def __str__(self):
        return f"{self.ngram_type}: {self.ngram} for user {self.user_id}"


class VocabCooldown(models.Model):
    """Tracks per-word cooldown per user"""
    user_id = models.CharField(max_length=100)
    word = models.CharField(max_length=100)
    last_used_reply = models.IntegerField()

    class Meta:
        unique_together = ['user_id', 'word']

    def __str__(self):
        return f"{self.word} cooldown for user {self.user_id} until reply {self.last_used_reply + 15}"