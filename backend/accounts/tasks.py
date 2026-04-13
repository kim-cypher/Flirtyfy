from celery import shared_task
from django.utils import timezone
from accounts.novelty_models import ConversationUpload, AIReply
from accounts.services.ai_generation import generate_reply
from accounts.services.similarity import get_embedding, semantic_similar_replies, lexical_similar_replies
from accounts.services.novelty import normalize_text, fingerprint_text
from accounts.services.utils import summarize_text, classify_intent
from datetime import timedelta

@shared_task(bind=True, max_retries=3)
def process_upload_task(self, upload_id):
    upload = ConversationUpload.objects.get(id=upload_id)
    user = upload.user
    prompt = upload.original_text
    summary = summarize_text(prompt)
    intent = classify_intent(prompt)
    since = timezone.now() - timedelta(days=45)
    memory = AIReply.objects.filter(user=user, created_at__gte=since)
    
    # Try 5 times with increasing temperature and explicit diversity instructions
    for attempt in range(1, 6):  # Attempts 1-5
        candidate = generate_reply(prompt, user=user, context=f"Summarize: {summary}\nIntent: {intent}", attempt_number=attempt)
        norm = normalize_text(candidate)
        fp = fingerprint_text(candidate)
        emb = get_embedding(candidate)
        
        # Check if response is unique against user's history
        if memory.filter(fingerprint=fp).exists():
            continue
        if semantic_similar_replies(user, emb, since).exists():
            continue
        if lexical_similar_replies(user, norm, since).exists():
            continue
        
        # Prune AIReply entries older than 45 days for this user
        AIReply.objects.filter(user=user, created_at__lt=timezone.now() - timedelta(days=45)).delete()
        reply = AIReply.objects.create(
            user=user,
            upload=upload,
            original_text=candidate,
            normalized_text=norm,
            embedding=emb,
            fingerprint=fp,
            summary=summary,
            intent=intent,
            created_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=45),
            status='complete'
        )
        return reply.id
    
    # Fallback: if all 5 attempts are similar, store the last one anyway (status='fallback')
    AIReply.objects.filter(user=user, created_at__lt=timezone.now() - timedelta(days=45)).delete()
    reply = AIReply.objects.create(
        user=user,
        upload=upload,
        original_text=candidate,
        normalized_text=norm,
        embedding=emb,
        fingerprint=fp,
        summary=summary,
        intent=intent,
        created_at=timezone.now(),
        expires_at=timezone.now() + timedelta(days=45),
        status='fallback'
    )
    return reply.id
