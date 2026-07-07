import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounts.novelty_models import AIReply, ConversationUpload

logger = logging.getLogger(__name__)

# NOTE: the old generate_and_store_embedding task (OpenAI embeddings + pgvector,
# "Layer 3") was removed when the app went Anthropic-only. Near-duplicate
# detection now runs synchronously via Postgres pg_trgm — see
# accounts/services/dedup.py::dedupe_similar. No Celery worker is required for
# the similarity checks anymore; Celery remains only for periodic cleanup.


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
