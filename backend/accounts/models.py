from django.db import models
from django.contrib.auth.models import AbstractUser, User


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