"""
In-app notifications — not email. Frontend polls GET /api/notifications/.
"""
import logging

logger = logging.getLogger(__name__)


def create_notification(user, type_, title, body):
    from accounts.models import Notification
    notif = Notification.objects.create(user=user, type=type_, title=title, body=body)
    logger.info(f"Notification created — user:{user.id} type:{type_}")
    return notif
