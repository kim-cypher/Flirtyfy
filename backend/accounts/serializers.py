import socket

from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.core.exceptions import MultipleObjectsReturned
from datetime import date

from .models import UserProfile


# Well-known disposable/temporary email providers — the cheap route to
# farming free clicks with throwaway accounts.
_DISPOSABLE_DOMAINS = frozenset([
    'mailinator.com', 'guerrillamail.com', '10minutemail.com', 'tempmail.com',
    'temp-mail.org', 'yopmail.com', 'trashmail.com', 'sharklasers.com',
    'getnada.com', 'maildrop.cc', 'dispostable.com', 'fakeinbox.com',
    'mintemail.com', 'throwawaymail.com', 'mailnesia.com', 'tempail.com',
    'moakt.com', 'emailondeck.com', 'mohmal.com', 'tmpmail.net',
    'burnermail.io', 'mytemp.email', 'tempinbox.com', 'spam4.me',
])


def _email_domain_resolves(domain: str) -> bool:
    """True if the email's domain actually exists in DNS. Catches typo'd and
    fabricated domains ('user@asdfgh.xyz'). On DNS infrastructure errors we
    let the user through — never block a real signup on our own hiccup."""
    try:
        socket.getaddrinfo(domain, None)
        return True
    except socket.gaierror:
        return False
    except Exception:
        return True


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration with age verification"""
    password = serializers.CharField(write_only=True)
    confirmPassword = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    date_of_birth = serializers.DateField()
    referral_code = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'password', 'confirmPassword', 'date_of_birth', 'referral_code']

    def validate(self, data):
        """Validate passwords match and user is 18+"""
        if data['password'] != data['confirmPassword']:
            raise serializers.ValidationError({
                "password": ["Passwords do not match."]
            })


        try:
            password_validation.validate_password(data['password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        # Normalize email
        email = (data.get('email') or '').strip().lower()
        data['email'] = email


        # Check if email already exists (case-insensitive)
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({
                "email": ["A user with this email already exists."]
            })

        # Email must look real: no disposable providers, and the domain must
        # actually exist in DNS. (Format is already enforced by EmailField.)
        domain = email.rsplit('@', 1)[-1]
        if domain in _DISPOSABLE_DOMAINS:
            raise serializers.ValidationError({
                "email": "Disposable email addresses are not allowed — please use your real email."
            })
        if not _email_domain_resolves(domain):
            raise serializers.ValidationError({
                "email": "This email domain does not exist — please check for typos."
            })

        # Check age is 18+
        date_of_birth = data.get('date_of_birth')
        today = date.today()
        age = today.year - date_of_birth.year
        if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
            age -= 1

        if age < 18:
            raise serializers.ValidationError({
                "date_of_birth": ["You must be at least 18 years old to use Flirtyfy. This app contains adult conversations."]
            })

        return data

    def create(self, validated_data):
        """Create user and associated profile"""
        date_of_birth = validated_data.pop('date_of_birth')
        validated_data.pop('confirmPassword')
        referral_code = validated_data.pop('referral_code', '')

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

            # Invalid/blank codes are silently ignored — referral is a bonus,
            # never a reason to block signup.
            if referral_code:
                from .services.credits import apply_referral
                apply_referral(user, referral_code)

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
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password.")
        except MultipleObjectsReturned:
            # If multiple users with same email exist (legacy data), use the most recent one
            user = User.objects.filter(email__iexact=email).order_by('-date_joined').first()
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


class PasswordResetSerializer(serializers.Serializer):
    """
    No-email-link reset flow: an account is identified by (email, first_name)
    together — first names alone are not unique, but combined with the email
    they always pin down exactly one account. On match, the password is reset
    immediately.
    """
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    new_password = serializers.CharField(write_only=True)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError({
                "new_password": ["Passwords do not match."]
            })

        try:
            password_validation.validate_password(data['new_password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})

        user = User.objects.filter(
            email__iexact=data['email'].strip(),
            first_name__iexact=data['first_name'].strip(),
        ).first()
        if not user:
            raise serializers.ValidationError({
                "non_field_errors": ["We couldn't find an account matching that email and first name."]
            })

        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


