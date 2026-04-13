"""
Health check endpoints for monitoring system status.
Critical for Docker health probes and load balancer checks.
"""

from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.views.decorators.http import require_http_methods
import redis
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def health_basic(request):
    """
    Basic health check - lightweight, fast response.
    Used by load balancers for quick checks.
    """
    return JsonResponse({
        'status': 'ok',
        'environment': 'production'
    }, status=200)


@require_http_methods(["GET"])
def health_detailed(request):
    """
    Detailed health check including database and cache.
    Used for comprehensive monitoring.
    """
    health_status = {
        'status': 'ok',
        'components': {}
    }

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['components']['database'] = {'status': 'ok'}
    except Exception as e:
        health_status['components']['database'] = {
            'status': 'error',
            'error': str(e)
        }
        health_status['status'] = 'degraded'
        logger.error(f"Database health check failed: {e}")

    # Check Redis
    try:
        cache.set('health_check', 'ok', 1)
        if cache.get('health_check') == 'ok':
            health_status['components']['cache'] = {'status': 'ok'}
        else:
            raise Exception("Cache read-write failed")
    except Exception as e:
        health_status['components']['cache'] = {
            'status': 'error',
            'error': str(e)
        }
        health_status['status'] = 'degraded'
        logger.error(f"Cache health check failed: {e}")

    # Check Celery
    try:
        from celery.result import AsyncResult
        from flirty_backend.celery import app as celery_app
        
        # Simple ping task
        result = celery_app.control.inspect().ping()
        if result:
            health_status['components']['celery'] = {'status': 'ok', 'workers': len(result)}
        else:
            raise Exception("No Celery workers responding")
    except Exception as e:
        health_status['components']['celery'] = {
            'status': 'warning',
            'error': str(e)
        }
        logger.warning(f"Celery health check failed: {e}")

    http_status = 200 if health_status['status'] == 'ok' else 503
    return JsonResponse(health_status, status=http_status)


@require_http_methods(["GET"])
def metrics(request):
    """
    Prometheus metrics endpoint.
    Exposed for Prometheus scraping.
    """
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        # Get metrics from database
        from accounts.models import User, ConversationUpload, AIReply
        
        # Count total users
        total_users = User.objects.count()
        
        # Count active users (logged in last 24 hours)
        active_threshold = timezone.now() - timedelta(hours=24)
        active_users = User.objects.filter(last_login__gte=active_threshold).count()
        
        # Count conversations (last hour)
        hour_ago = timezone.now() - timedelta(hours=1)
        conversations_last_hour = ConversationUpload.objects.filter(
            created_at__gte=hour_ago
        ).count()
        
        # Count responses
        responses_last_hour = AIReply.objects.filter(
            created_at__gte=hour_ago
        ).count()
        
        # Average response time
        responses_sample = AIReply.objects.filter(
            created_at__gte=hour_ago
        ).values_list('created_at')
        
        metrics_text = f"""# HELP flirty_total_users Total registered users
# TYPE flirty_total_users gauge
flirty_total_users {total_users}

# HELP flirty_active_users Active users (24h)
# TYPE flirty_active_users gauge
flirty_active_users {active_users}

# HELP flirty_conversations_last_hour Conversations in last hour
# TYPE flirty_conversations_last_hour gauge
flirty_conversations_last_hour {conversations_last_hour}

# HELP flirty_responses_last_hour AI responses in last hour
# TYPE flirty_responses_last_hour gauge
flirty_responses_last_hour {responses_last_hour}
"""
        
        return JsonResponse(
            {'text': metrics_text},
            content_type='text/plain',
            status=200
        )
    except Exception as e:
        logger.error(f"Metrics endpoint error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
def cache_clear(request):
    """
    Admin endpoint to clear cache manually.
    Requires authentication.
    """
    from django.contrib.auth.decorators import login_required
    
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        cache.clear()
        return JsonResponse({
            'status': 'ok',
            'message': 'Cache cleared successfully'
        })
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def check_system_resources(request):
    """
    Check system resource usage (CPU, memory, disk).
    Used for auto-scaling decisions.
    """
    import psutil
    import json
    
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        resources = {
            'cpu': {
                'percent': cpu_percent,
                'threshold_warning': 70,
                'threshold_critical': 90,
            },
            'memory': {
                'percent': memory.percent,
                'threshold_warning': 80,
                'threshold_critical': 95,
            },
            'disk': {
                'percent': disk.percent,
                'threshold_warning': 80,
                'threshold_critical': 95,
            }
        }
        
        # Determine overall status
        status = 'ok'
        if (cpu_percent > 90 or memory.percent > 95 or disk.percent > 95):
            status = 'critical'
        elif (cpu_percent > 70 or memory.percent > 80 or disk.percent > 80):
            status = 'warning'
        
        resources['status'] = status
        
        http_status = 200 if status == 'ok' else 503 if status == 'critical' else 200
        return JsonResponse(resources, status=http_status)
    except Exception as e:
        logger.error(f"Resource check error: {e}")
        return JsonResponse({'error': str(e)}, status=500)
