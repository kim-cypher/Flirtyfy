import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounts.novelty_models import AIReply, ConversationUpload
from accounts.services.similarity import get_embedding, semantic_similar_replies

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, ignore_result=True)
def generate_and_store_embedding(self, reply_id: int):
    """
    Layer 3 semantic dedup — runs in background AFTER response is sent to user.
    Zero latency impact. Cost: ~$4.50/month at 700 users × 300 messages/day.

    Steps:
    1. Fetch the saved AIReply.
    2. Generate embedding via text-embedding-3-small.
    3. Check pgvector cosine similarity against user's past 30-day replies.
    4. If too similar (threshold 0.88) → mark status='similar' so future
       generations skip it.
    5. If unique → store embedding for future checks.
    """
    try:
        reply = AIReply.objects.get(id=reply_id)
    except AIReply.DoesNotExist:
        logger.warning(f"generate_and_store_embedding: reply {reply_id} not found")
        return

    if reply.embedding is not None:
        return

    text = reply.original_text if reply.intent_type == 'specific' else reply.normalized_text
    if not text or len(text.strip()) < 5:
        return

    try:
        embedding = get_embedding(text)
    except Exception as e:
        logger.error(f"Embedding generation failed for reply {reply_id}: {e}")
        try:
            self.retry(countdown=30)
        except self.MaxRetriesExceededError:
            pass
        return

    if embedding is None:
        return

    since = timezone.now() - timedelta(days=30)
    similar = semantic_similar_replies(reply.user, embedding, since, threshold=0.88)
    similar = similar.exclude(id=reply_id)

    if similar.exists():
        AIReply.objects.filter(id=reply_id).update(embedding=embedding, status='similar')
        logger.info(f"Reply {reply_id} marked similar (Layer 3) — user {reply.user_id}")
    else:
        AIReply.objects.filter(id=reply_id).update(embedding=embedding)
        logger.debug(f"Reply {reply_id} embedding stored, semantically unique")


@shared_task(ignore_result=True)
def cleanup_expired_replies():
    """
    Daily Celery Beat task — enforces the 30-day retention that
    AIReply.expires_at implies but nothing was actually deleting on.

    Deletes ConversationUpload rows older than 30 days first — its FK from
    AIReply is on_delete=CASCADE, so this also removes their child AIReply
    rows in the same step. Then sweeps any AIReply whose own expires_at has
    already passed, covering rows that could otherwise outlive their upload
    (defensive — in normal operation the two are created together).
    """
    now = timezone.now()
    cutoff = now - timedelta(days=30)

    deleted_uploads, _ = ConversationUpload.objects.filter(created_at__lt=cutoff).delete()
    deleted_replies, _ = AIReply.objects.filter(expires_at__lt=now).delete()

    logger.info(
        f"Cleanup: removed {deleted_uploads} expired ConversationUpload rows "
        f"(cascaded AIReply included) + {deleted_replies} additional expired AIReply rows"
    )
    return {'uploads_deleted': deleted_uploads, 'replies_deleted': deleted_replies}
