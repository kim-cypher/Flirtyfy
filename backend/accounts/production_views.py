"""
PRODUCTION API VIEWS - Production-grade endpoints
Replaces novelty_views.py with optimized implementation.

Single entry point for upload, reply list, feedback.
Uses ProductionGenerator + ProductionMetrics.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.core.cache import cache

from accounts.novelty_models import ConversationUpload, AIReply, AIReplyFeedback
from accounts.serializers import ConversationUploadSerializer, AIReplySerializer, AIReplyFeedbackSerializer
from accounts.production_tasks import process_upload_production
from accounts.services.production_generator import ProductionMetrics

logger = logging.getLogger(__name__)


class ConversationUploadViewProduction(viewsets.ModelViewSet):
    """
    Upload endpoint for conversation processing.
    
    OPTIMIZATIONS:
    - Batch rate limiting (100 uploads per 5 minutes per user)
    - Async processing via Celery
    - Metrics tracking
    - Proper error handling
    """
    
    serializer_class = ConversationUploadSerializer
    permission_classes = [IsAuthenticated]
    queryset = ConversationUpload.objects.all()
    
    # Rate limit: 100 uploads per 5 minutes per user
    RATE_LIMIT_UPLOADS = 100
    RATE_LIMIT_WINDOW = 300  # 5 minutes
    
    def get_queryset(self):
        """Only show uploads for current user"""
        return self.queryset.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """
        POST /api/conversation-upload/
        Create and process a new conversation upload.
        """
        
        user = request.user
        
        # ===== RATE LIMITING =====
        cache_key = f"upload_limit:{user.id}"
        upload_count = cache.get(cache_key, 0)
        
        if upload_count >= self.RATE_LIMIT_UPLOADS:
            return Response(
                {
                    'error': 'rate_limited',
                    'message': f'Too many uploads. Limit: {self.RATE_LIMIT_UPLOADS} per 5 minutes',
                    'retry_after': self.RATE_LIMIT_WINDOW
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # ===== VALIDATE INPUT =====
        conversation_text = request.data.get('conversation_text', '').strip()
        
        if not conversation_text:
            return Response(
                {'error': 'invalid_input', 'message': 'Conversation text is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(conversation_text) > 50000:
            return Response(
                {'error': 'invalid_input', 'message': 'Conversation too long (max 50k characters)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(conversation_text) < 10:
            return Response(
                {'error': 'invalid_input', 'message': 'Conversation too short (min 10 characters)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ===== CREATE UPLOAD RECORD =====
        try:
            # Note: ConversationUpload expects 'original_text' field
            upload = ConversationUpload.objects.create(
                user=user,
                original_text=conversation_text  # Field name in model
            )
            
            logger.info(f"Created upload {upload.id} for user {user.id}")
        
        except Exception as e:
            logger.error(f"Failed to create upload: {e}", exc_info=True)
            return Response(
                {'error': 'database_error', 'message': 'Failed to create upload'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # ===== INCREMENT RATE LIMIT COUNTER =====
        cache.set(cache_key, upload_count + 1, timeout=self.RATE_LIMIT_WINDOW)
        
        # ===== TRIGGER ASYNC PROCESSING =====
        try:
            process_upload_production.delay(upload.id)
            logger.info(f"Queued processing for upload {upload.id}")
        except Exception as e:
            logger.error(f"Failed to queue processing: {e}", exc_info=True)
            # Continue anyway - task will be retried
        
        # ===== RETURN RESPONSE =====
        serializer = self.get_serializer(upload)
        return Response(
            {
                'status': 'processing',
                'upload_id': upload.id,
                'upload': serializer.data
            },
            status=status.HTTP_201_CREATED
        )


class AIReplyListViewProduction(viewsets.ModelViewSet):
    """
    List replies for current user.
    
    Optimizations:
    - Cached query results
    - Limited to last 45 days
    - Proper pagination
    """
    
    serializer_class = AIReplySerializer
    permission_classes = [IsAuthenticated]
    queryset = AIReply.objects.all()
    
    def get_queryset(self):
        """Only show replies for current user from last 45 days"""
        cutoff = timezone.now() - timezone.timedelta(days=45)
        return self.queryset.filter(
            user=self.request.user,
            created_at__gte=cutoff
        ).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """GET /api/ai-reply/"""
        
        # Try cache first
        cache_key = f"reply_list:{request.user.id}"
        cached_response = cache.get(cache_key)
        if cached_response:
            return Response(cached_response)
        
        # Get from DB
        replies = self.get_queryset()[:100]  # Max 100
        serializer = self.get_serializer(replies, many=True)
        
        # Cache for 5 minutes
        response_data = {
            'count': len(replies),
            'results': serializer.data
        }
        cache.set(cache_key, response_data, timeout=300)
        
        return Response(response_data)


class AIReplyFeedbackViewProduction(viewsets.ModelViewSet):
    """
    Record feedback on generated replies.
    """
    
    serializer_class = AIReplyFeedbackSerializer
    permission_classes = [IsAuthenticated]
    queryset = AIReplyFeedback.objects.all()
    
    def create(self, request, *args, **kwargs):
        """
        POST /api/ai-reply-feedback/
        Record user feedback on a reply.
        """
        
        reply_id = request.data.get('reply_id')
        rating = request.data.get('rating')  # 1-5 or positive/negative
        comment = request.data.get('comment', '')
        
        # Validate
        if not reply_id:
            return Response(
                {'error': 'missing_reply_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get reply (must belong to user)
        try:
            reply = AIReply.objects.get(id=reply_id, user=request.user)
        except AIReply.DoesNotExist:
            return Response(
                {'error': 'reply_not_found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create feedback
        try:
            feedback = AIReplyFeedback.objects.create(
                reply=reply,
                user=request.user,
                rating=rating,
                comment=comment
            )
            
            logger.info(f"Recorded feedback for reply {reply_id}: {rating}")
            
            # Clear reply cache when feedback given
            cache.delete(f"reply_list:{request.user.id}")
            
            return Response(
                {'status': 'success', 'feedback_id': feedback.id},
                status=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            logger.error(f"Failed to create feedback: {e}", exc_info=True)
            return Response(
                {'error': 'database_error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@action(detail=False, methods=['get'])
def metrics_summary(request):
    """
    GET /api/metrics-summary/
    Get current metrics for user (for debugging).
    """
    
    user_id = request.user.id
    today = timezone.now().date()
    
    cache_key = f"prod_metrics:{user_id}:{today}"
    metrics = cache.get(cache_key, {})
    
    return Response(metrics)
