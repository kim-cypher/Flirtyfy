from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import MultipleObjectsReturned
from datetime import date, datetime
import re

from .models import UserProfile
from .novelty_models import ConversationUpload, AIReply, AIReplyFeedback


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration with age verification"""
    password = serializers.CharField(write_only=True)
    confirmPassword = serializers.CharField(write_only=True)
    date_of_birth = serializers.DateField()

    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'confirmPassword', 'date_of_birth']

    def validate(self, data):
        """Validate passwords match and user is 18+"""
        if data['password'] != data['confirmPassword']:
            raise serializers.ValidationError({
                "password": "Passwords do not match."
            })

        # Check if email already exists
        email = data.get('email')
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({
                "email": "A user with this email already exists."
            })

        # Check age is 18+
        date_of_birth = data.get('date_of_birth')
        today = date.today()
        age = today.year - date_of_birth.year
        if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
            age -= 1

        if age < 18:
            raise serializers.ValidationError({
                "date_of_birth": "You must be at least 18 years old to use Flirty. This app contains adult conversations."
            })

        return data

    def create(self, validated_data):
        """Create user and associated profile"""
        date_of_birth = validated_data.pop('date_of_birth')
        validated_data.pop('confirmPassword')

        with transaction.atomic():
            user = User.objects.create_user(**validated_data)

            # Compute age
            today = date.today()
            age = today.year - date_of_birth.year
            if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
                age -= 1

            # Signal will create a profile; update it (safe whether created or not)
            profile = getattr(user, 'profile', None)
            if profile is None:
                # Fallback — create if signal didn't run for some reason
                UserProfile.objects.create(
                    user=user,
                    age=age,
                    date_of_birth=date_of_birth,
                    age_verified=True
                )
            else:
                profile.age = age
                profile.date_of_birth = date_of_birth
                profile.age_verified = True
                profile.save()

        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login with age verification"""
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        """Validate login credentials and check age verification"""
        email = data.get('email')
        password = data.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password.")
        except MultipleObjectsReturned:
            # If multiple users with same email exist (legacy data), use the most recent one
            user = User.objects.filter(email=email).order_by('-date_joined').first()
            if not user:
                raise serializers.ValidationError("Invalid email or password.")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")

        # Check if user profile exists and age is verified
        try:
            profile = user.profile
            if not profile.age_verified:
                raise serializers.ValidationError("Your age could not be verified. Please contact support.")
            if profile.age < 18:
                raise serializers.ValidationError("This app is restricted to users 18+.")
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError("User profile not found. Please register again.")

        return {'user': user}


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class ConversationUploadSerializer(serializers.ModelSerializer):
    """Serializer for conversation uploads with validation"""
    def validate_original_text(self, value):
        # Enforce length limits
        if not (10 <= len(value.strip()) <= 2000):
            raise serializers.ValidationError("Conversation text must be between 10 and 2000 characters.")
        
        # Disallow dangerous characters (basic injection prevention)
        if re.search(r'[<>\{\}\[\]\\]', value):
            raise serializers.ValidationError("Invalid characters detected in conversation text.")
        
        # Basic profanity filter (expand as needed)
        profanity = [
            r'rape', r'suicide', r'sex with minors', r'sex with children',
            r'violence', r'drugs', r'kill', r'murder'
        ]
        for word in profanity:
            if re.search(word, value, re.IGNORECASE):
                raise serializers.ValidationError("Inappropriate language detected. Please rephrase.")
        
        return value

    class Meta:
        model = ConversationUpload
        fields = ['id', 'original_text', 'created_at']


class AIReplySerializer(serializers.ModelSerializer):
    """Serializer for AI-generated replies"""
    class Meta:
        model = AIReply
        fields = [
            'id', 'original_text', 'normalized_text', 'fingerprint',
            'summary', 'intent', 'created_at', 'expires_at', 'status', 'error'
        ]
        read_only_fields = ['fingerprint', 'normalized_text', 'summary', 'intent', 'created_at', 'status', 'error']


class AIReplyFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for feedback on AI replies"""
    class Meta:
        model = AIReplyFeedback
        fields = ['id', 'user', 'reply', 'reason', 'created_at']
        read_only_fields = ['user', 'created_at']