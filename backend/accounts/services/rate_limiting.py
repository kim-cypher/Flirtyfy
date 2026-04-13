"""
Rate limiting implementation for production.
Prevents abuse and ensures fair resource distribution.
"""

import time
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


class RateLimitKey:
    """Generate rate limit keys."""
    
    @staticmethod
    def user_upload(user_id):
        """Rate limit key for file uploads per user."""
        return f'ratelimit:upload:{user_id}'
    
    @staticmethod
    def user_api(user_id):
        """Rate limit key for general API calls per user."""
        return f'ratelimit:api:{user_id}'
    
    @staticmethod
    def ip_api(ip_address):
        """Rate limit key for API calls per IP address."""
        return f'ratelimit:ip:{ip_address}'
    
    @staticmethod
    def user_retrieval(user_id):
        """Rate limit key for data retrieval per user."""
        return f'ratelimit:retrieval:{user_id}'


class SlidingWindowRateLimiter:
    """
    Implements sliding window rate limiting algorithm.
    More accurate than fixed window.
    """
    
    @staticmethod
    def is_allowed(key, limit, window_seconds=60):
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Unique identifier (user_id, IP, etc)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            (allowed: bool, remaining: int, reset_at: int)
        """
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        try:
            # Get request count for this window
            request_count = cache.get(key, 0)
            
            if request_count >= limit:
                # Exceeded limit
                reset_at = cache.ttl(key) if hasattr(cache, 'ttl') else current_time + window_seconds
                return False, 0, reset_at
            
            # Increment counter and set expiry
            cache.set(key, request_count + 1, window_seconds)
            
            remaining = max(0, limit - request_count - 1)
            reset_at = current_time + window_seconds
            
            return True, remaining, reset_at
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Fail open - allow if cache is down
            return True, limit, current_time + window_seconds


def rate_limit_by_user(limit_per_minute=1):
    """
    Decorator to rate limit by user.
    
    Usage:
        @rate_limit_by_user(limit_per_minute=1)
        def upload_endpoint(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            user_id = request.user.id
            key = RateLimitKey.user_upload(user_id)
            
            allowed, remaining, reset_at = SlidingWindowRateLimiter.is_allowed(
                key, limit_per_minute, window_seconds=60
            )
            
            if not allowed:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                return Response(
                    {
                        'error': 'Rate limit exceeded',
                        'retry_after': reset_at,
                        'limit': limit_per_minute,
                        'window': '1 minute'
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={
                        'Retry-After': str(reset_at - int(time.time())),
                        'X-RateLimit-Limit': str(limit_per_minute),
                        'X-RateLimit-Remaining': '0',
                        'X-RateLimit-Reset': str(reset_at),
                    }
                )
            
            # Add rate limit headers to response
            response = view_func(request, *args, **kwargs)
            response['X-RateLimit-Limit'] = str(limit_per_minute)
            response['X-RateLimit-Remaining'] = str(remaining)
            response['X-RateLimit-Reset'] = str(reset_at)
            
            return response
        
        return wrapper
    return decorator


def rate_limit_by_ip(limit_per_hour=100):
    """
    Decorator to rate limit by IP address.
    Prevents distributed attacks.
    
    Usage:
        @rate_limit_by_ip(limit_per_hour=100)
        def api_endpoint(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR', 'unknown')
            
            key = RateLimitKey.ip_api(ip)
            
            allowed, remaining, reset_at = SlidingWindowRateLimiter.is_allowed(
                key, limit_per_hour, window_seconds=3600
            )
            
            if not allowed:
                logger.warning(f"IP rate limit exceeded: {ip}")
                return Response(
                    {
                        'error': 'Rate limit exceeded (IP)',
                        'retry_after': reset_at,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={
                        'Retry-After': str(reset_at - int(time.time())),
                    }
                )
            
            response = view_func(request, *args, **kwargs)
            return response
        
        return wrapper
    return decorator


class RateLimitService:
    """Service for rate limiting operations."""
    
    @staticmethod
    def check_upload_limit(user_id, limit_per_minute=1):
        """Check if user can upload."""
        key = RateLimitKey.user_upload(user_id)
        allowed, remaining, reset_at = SlidingWindowRateLimiter.is_allowed(
            key, limit_per_minute, window_seconds=60
        )
        return allowed, remaining, reset_at
    
    @staticmethod
    def check_api_limit(user_id, limit_per_hour=1000):
        """Check if user can make API calls."""
        key = RateLimitKey.user_api(user_id)
        allowed, remaining, reset_at = SlidingWindowRateLimiter.is_allowed(
            key, limit_per_hour, window_seconds=3600
        )
        return allowed, remaining, reset_at
    
    @staticmethod
    def get_user_reset_time(user_id):
        """Get when user's rate limit resets."""
        try:
            key = RateLimitKey.user_upload(user_id)
            return cache.ttl(key) if hasattr(cache, 'ttl') else None
        except Exception as e:
            logger.error(f"Failed to get reset time: {e}")
            return None
    
    @staticmethod
    def reset_user_limit(user_id):
        """Manually reset user's rate limit (admin action)."""
        keys = [
            RateLimitKey.user_upload(user_id),
            RateLimitKey.user_api(user_id),
            RateLimitKey.user_retrieval(user_id),
        ]
        try:
            cache.delete_many(keys)
            logger.info(f"Reset rate limits for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to reset rate limits: {e}")
