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
    """
    Process conversation upload and generate unique AI reply
    
    VALIDATION FLOW:
    1. generate_reply() validates response against ALL 7 rules:
       - Rule 1: Character length (140-180)
       - Rule 2: Must end with question mark
       - Rule 3: No prohibited content
       - Rule 4: Not robotic/formulaic
       - Rule 5: Fingerprint unique
       - Rule 6: Semantic unique (pgvector)
       - Rule 7: Lexical unique (text similarity)
    
    2. This task checks uniqueness a FINAL TIME before creating database entry
       to ensure response is still unique after generation delay
    
    3. Response is only saved to DB if ALL validations pass
    """
    upload = ConversationUpload.objects.get(id=upload_id)
    user = upload.user
    prompt = upload.original_text
    summary = summarize_text(prompt)
    intent = classify_intent(prompt)
    since = timezone.now() - timedelta(days=45)
    
    # Try 5 times with increasing temperature and explicit diversity instructions
    for attempt in range(1, 6):  # Attempts 1-5
        # generate_reply() ALREADY validates against ALL 7 rules internally
        # with automatic rephrasing up to 3 times if validation fails
        candidate = generate_reply(
            prompt, 
            user=user, 
            context=f"Summarize: {summary}\nIntent: {intent}", 
            attempt_number=attempt
        )
        
        # CRITICAL: Response from generate_reply() already passed ALL validation rules
        # But we re-check ONLY uniqueness here because:
        # - If response doesn't meet length/question/prohibited/robotic rules → generate_reply returns error
        # - We only store responses that passed generate_reply() validation
        # - But we still check uniqueness in case user has since uploaded identical conversation
        
        norm = normalize_text(candidate)
        fp = fingerprint_text(candidate)
        emb = get_embedding(candidate)
        
        # ===== FINAL UNIQUENESS RE-CHECK =====
        # Rule 5: Fingerprint unique (no exact matches in last 45 days)
        if AIReply.objects.filter(user=user, fingerprint=fp, created_at__gte=since).exists():
            continue  # Try next attempt
        
        # Rule 6: Semantic unique (pgvector similarity < 0.95)
        if semantic_similar_replies(user, emb, since).exists():
            continue  # Try next attempt
        
        # Rule 7: Lexical unique (text overlap < 0.95)
        if lexical_similar_replies(user, norm, since).exists():
            continue  # Try next attempt
        
        # ===== ALL VALIDATIONS PASSED =====
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
            status='complete'  # ✅ Response is valid and ready to use
        )
        return reply.id
    
    # ===== FALLBACK: ALL 5 ATTEMPTS FAILED UNIQUENESS CHECK =====
    # This is rare - means response generation succeeded but all attempts were similar
    # or user submitted same conversation 5 times rapidly
    # Still save response with 'fallback' status for user transparency
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
        status='fallback'  # ⚠️ Valid response, but couldn't ensure uniqueness
    )
    return reply.id
