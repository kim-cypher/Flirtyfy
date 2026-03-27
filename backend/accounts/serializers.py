from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile
from datetime import datetime, timedelta
from django.db import transaction
from datetime import date


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['bio', 'avatar', 'age', 'age_verified']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    confirmPassword = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=True)
    date_of_birth = serializers.DateField(required=True, help_text="Format: YYYY-MM-DD")

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirmPassword', 'date_of_birth']

    def validate(self, data):
        """
        Validate passwords match and user is 18+ years old
        """
        # Check passwords match
        if data['password'] != data['confirmPassword']:
            raise serializers.ValidationError({"password": "Passwords must match."})
        
        # Check age is 18+
        date_of_birth = data.get('date_of_birth')
        today = datetime.now().date()
        age = (today - date_of_birth).days // 365
        
        if age < 18:
            raise serializers.ValidationError({
                "date_of_birth": "You must be at least 18 years old to use Flirty. This app contains adult conversations."
            })
        
        return data


    def create(self, validated_data):
        date_of_birth = validated_data.pop('date_of_birth')
        validated_data.pop('confirmPassword')

        with transaction.atomic():
            user = User.objects.create_user(**validated_data)

            # compute age
            today = date.today()
            age = today.year - date_of_birth.year
            if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
                age -= 1
            
            if age < 18:
                raise serializers.ValidationError({
                    "date_of_birth": "You must be at least 18 years old to use Flirty."
                })

            # signal will create a profile; update it (safe whether created or not)
            profile = getattr(user, 'profile', None)
            if profile is None:
                # fallback — create if signal didn't run for some reason
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
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        """
        Validate login credentials and check age verification
        """
        email = data.get('email')
        password = data.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
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