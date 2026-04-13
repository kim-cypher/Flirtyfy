"""
Caching utilities and decorators for production optimization.
Reduces database hits and AI API calls dramatically.
"""

import hashlib
import json
from functools import wraps
from django.core.cache import cache
from django.utils.encoding import force_bytes
import logging

logger = logging.getLogger(__name__)


class CacheKey:
    """Generate cache keys for different data types."""
    
    @staticmethod
    def user_profile(user_id):
        """Cache key for user profile."""
        return f'user_profile:{user_id}'
    
    @staticmethod
    def user_conversations(user_id, page=1):
        """Cache key for user's conversations list."""
        return f'user_conversations:{user_id}:page_{page}'
    
    @staticmethod
    def ai_response(conversation_hash):
        """Cache key for AI response (checks if conversation already processed)."""
        return f'ai_response:{conversation_hash}'
    
    @staticmethod
    def conversation_replies(conversation_id):
        """Cache key for replies to a specific conversation."""
        return f'conversation_replies:{conversation_id}'
    
    @staticmethod
    def similarity_check(fingerprint):
        """Cache key for similarity check results."""
        return f'similarity:{fingerprint}'
    
    @staticmethod
    def user_stats(user_id):
        """Cache key for user statistics."""
        return f'user_stats:{user_id}'
    
    @staticmethod
    def system_status():
        """Cache key for system wide status."""
        return 'system:status'


def generate_conversation_hash(conversation_text):
    """
    Generate a hash of conversation text for cache lookups.
    Used to detect if same conversation was already processed.
    """
    return hashlib.sha256(force_bytes(conversation_text)).hexdigest()


def cache_response(timeout=300, key_func=None):
    """
    Decorator to cache view responses.
    
    Usage:
        @cache_response(timeout=600)  # Cache for 10 minutes
        def my_view(request):
            return Response(data)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(request, *args, **kwargs)
            else:
                # Default: use URL + user ID
                user_id = request.user.id if request.user.is_authenticated else 'anon'
                cache_key = f"{request.path}:{user_id}"
            
            # Try to get from cache
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached
            
            # Not in cache, execute view
            response = view_func(request, *args, **kwargs)
            
            # Cache the response
            try:
                cache.set(cache_key, response, timeout)
                logger.debug(f"Cached response for {cache_key} ({timeout}s)")
            except Exception as e:
                logger.warning(f"Failed to cache {cache_key}: {e}")
            
            return response
        
        return wrapper
    return decorator


def invalidate_user_cache(user_id):
    """
    Invalidate all cache entries for a specific user.
    Called after user profile updates.
    """
    keys_to_delete = [
        CacheKey.user_profile(user_id),
        CacheKey.user_stats(user_id),
    ]
    
    try:
        cache.delete_many(keys_to_delete)
        logger.info(f"Invalidated cache for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to invalidate user cache: {e}")


def invalidate_conversation_cache(user_id, conversation_id=None):
    """
    Invalidate cache for user's conversations.
    Called after new conversation or reply.
    """
    try:
        # Delete paginated conversation lists
        for page in range(1, 10):  # Delete first 10 pages
            cache.delete(CacheKey.user_conversations(user_id, page))
        
        if conversation_id:
            cache.delete(CacheKey.conversation_replies(conversation_id))
        
        logger.info(f"Invalidated conversation cache for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to invalidate conversation cache: {e}")


def get_or_compute(cache_key, compute_func, timeout=300, *args, **kwargs):
    """
    Get value from cache or compute if not exists.
    Generic cache-aside pattern.
    
    Usage:
        data = get_or_compute(
            cache_key='user_stats:123',
            compute_func=fetch_user_stats,
            timeout=600,
            user_id=123
        )
    """
    # Try to get from cache
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug(f"Get-or-compute cache hit: {cache_key}")
        return cached
    
    # Compute value
    logger.debug(f"Get-or-compute cache miss: {cache_key}, computing...")
    value = compute_func(*args, **kwargs)
    
    # Store in cache
    try:
        cache.set(cache_key, value, timeout)
        logger.debug(f"Computed and cached {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to cache computed value {cache_key}: {e}")
    
    return value


def batch_cache_get(keys):
    """
    Get multiple keys from cache at once.
    More efficient than individual gets.
    
    Usage:
        results = batch_cache_get(['key1', 'key2', 'key3'])
    """
    try:
        return cache.get_many(keys)
    except Exception as e:
        logger.error(f"Failed to batch get cache: {e}")
        return {}


def batch_cache_set(data_dict, timeout=300):
    """
    Set multiple keys in cache at once.
    More efficient than individual sets.
    
    Usage:
        batch_cache_set({'key1': val1, 'key2': val2}, timeout=600)
    """
    try:
        cache.set_many(data_dict, timeout)
        logger.debug(f"Batch cached {len(data_dict)} entries")
    except Exception as e:
        logger.error(f"Failed to batch set cache: {e}")


class CachingService:
    """Service class for cache operations."""
    
    @staticmethod
    def cache_ai_response(conversation_id, response_text, timeout=3600):
        """Cache an AI response (1 hour TTL)."""
        key = CacheKey.ai_response(generate_conversation_hash(response_text))
        try:
            cache.set(key, {
                'response': response_text,
                'conversation_id': conversation_id,
            }, timeout)
        except Exception as e:
            logger.error(f"Failed to cache AI response: {e}")
    
    @staticmethod
    def get_cached_response(conversation_text):
        """Get cached response if one exists for this conversation."""
        key = CacheKey.ai_response(generate_conversation_hash(conversation_text))
        return cache.get(key)
    
    @staticmethod
    def cache_similarity_results(fingerprint, results, timeout=3600):
        """Cache similarity check results."""
        key = CacheKey.similarity_check(fingerprint)
        try:
            cache.set(key, results, timeout)
        except Exception as e:
            logger.error(f"Failed to cache similarity results: {e}")
    
    @staticmethod
    def get_similarity_results(fingerprint):
        """Get cached similarity results."""
        key = CacheKey.similarity_check(fingerprint)
        return cache.get(key)
    
    @staticmethod
    def clear_all():
        """Clear entire cache (use cautiously)."""
        try:
            cache.clear()
            logger.warning("Cache completely cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
