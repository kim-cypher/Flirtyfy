"""
PRODUCTION CELERY TASKS - Async processing for reply generation
Replaces old tasks.py with production-grade implementation.

Single async entry point for all reply generation requests.
Uses ProductionGenerator for core logic.
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from datetime import timedelta

from accounts.novelty_models import ConversationUpload, AIReply, AIReplyFeedback
from accounts.services.production_generator import generate_reply_production, ProductionMetrics
from accounts.services.similarity import get_embedding
from accounts.services.novelty import normalize_text, fingerprint_text

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_upload_production(self, upload_id: int):
    """
    Process a conversation upload asynchronously.
    
    OPTIMIZATIONS:
    - Minimal retries (3 instead of 5)
    - Fast-fail on invalid input
    - Single transaction for DB operations
    - Fallback integrated into generator
    
    Return:
        Dict: {success, reply_id, status, error}
    """
    
    try:
        # Get upload
        upload = ConversationUpload.objects.get(id=upload_id)
        user = upload.user
        
        logger.info(f"Processing upload {upload_id} for user {user.id}")
        
        # ===== GENERATE REPLY =====
        reply_text, metadata = _generate_with_production(
            user.id, 
            upload.original_text  # Use correct model field name
        )
        
        # ===== SAVE REPLY TO DATABASE =====
        with transaction.atomic():
            # Create normalized/fingerprint versions
            norm_text = normalize_text(reply_text)
            fp = fingerprint_text(reply_text)
            
            # Generate embedding (async, can fail gracefully)
            try:
                embedding = get_embedding(reply_text)
            except Exception as e:
                logger.warning(f"Embedding generation failed for user {user.id}: {e}")
                embedding = None
            
            # Extract summary and intent (required fields for AIReply)
            from accounts.services.conversation_parser import ConversationParser
            from accounts.services.tone_intent_classifier import ToneIntentClassifier
            from accounts.services.utils import summarize_text, classify_intent
            
            parser = ConversationParser()
            parsed = parser.parse_conversation(upload.original_text)
            summary = parsed.get('summary', '')[:500]
            
            classifier = ToneIntentClassifier()
            last_msg = parsed.get('last_message', '')
            tone, intent, emotion = classifier.classify(last_msg)
            
            # Create AI reply
            # Note: AIReply.original_text stores the generated reply (confusing field name, but that's the model)
            ai_reply = AIReply.objects.create(
                user=user,
                upload=upload,  # ForeignKey to ConversationUpload
                original_text=reply_text,  # The generated reply goes here
                fingerprint=fp,
                embedding=embedding,
                normalized_text=norm_text,
                summary=summary,
                intent=intent.value if intent else 'unknown',
                status='complete' if metadata['success'] else 'fallback',
                expires_at=timezone.now() + timedelta(days=45),
            )
            
            logger.info(f"Created reply {ai_reply.id} for user {user.id}")
        
        return {
            'success': True,
            'reply_id': ai_reply.id,
            'status': ai_reply.status,
            'tokens': metadata['tokens_input'] + metadata['tokens_output'],
            'latency_ms': metadata.get('latency_ms', 0),
        }
    
    except ConversationUpload.DoesNotExist:
        logger.error(f"Upload {upload_id} not found")
        return {'success': False, 'error': 'upload_not_found'}
    
    except Exception as e:
        logger.error(f"Process upload failed: {e}", exc_info=True)
        
        # Retry with exponential backoff
        retry_count = self.request.retries
        if retry_count < self.max_retries:
            logger.info(f"Retrying upload {upload_id} (attempt {retry_count + 1})")
            raise self.retry(exc=e, countdown=2 ** retry_count)
        
        return {'success': False, 'error': str(e), 'attempts': retry_count + 1}


def _generate_with_production(user_id: int, conversation_text: str) -> tuple:
    """
    Wrapper that calls ProductionGenerator.
    Returns: (reply_text, metadata)
    """
    from accounts.services.production_generator import ProductionGenerator
    
    generator = ProductionGenerator(user_id)
    reply, metadata = generator.generate(conversation_text)
    
    return reply, metadata


# ============================================================================
# DEPRECATED: Old tasks for reference (to be removed after migration)
# ============================================================================

# Old generate_reply_task, validate_and_update_reply, etc. - removed
# Use process_upload_production instead
