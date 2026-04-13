import json
from .novelty import normalize_text, fingerprint_text


def get_embedding(text):
    """
    Get embedding for text using OpenAI API.
    Returns a vector suitable for pgvector storage.
    """
    from accounts.openai_service import get_openai_client
    
    try:
        client = get_openai_client()
        response = client.embeddings.create(
            input=text,
            model='text-embedding-3-small'
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def semantic_similar_replies(user, embedding, since, threshold=0.95):
    """
    Find semantically similar replies using embeddings with pgvector.
    Uses L2 distance to find similar vectors.
    VERY STRICT threshold (0.95) to only allow truly diverse responses.
    """
    from accounts.novelty_models import AIReply
    from django.db.models import F, FloatField
    from pgvector.django import L2Distance
    
    if embedding is None:
        return AIReply.objects.none()
    
    # Find replies within threshold using L2 distance
    similar_replies = AIReply.objects.filter(
        user=user,
        created_at__gte=since,
        embedding__isnull=False
    ).annotate(
        distance=L2Distance('embedding', embedding)
    ).filter(
        distance__lt=(1 - threshold)  # L2 distance is inverse of similarity
    ).order_by('distance')
    
    return similar_replies


def lexical_similar_replies(user, normalized_text, since, threshold=0.95):
    """
    Find lexically similar replies using text similarity.
    Compares normalized text fields.
    VERY STRICT threshold (0.95) to catch near-identical text.
    """
    from accounts.novelty_models import AIReply
    from difflib import SequenceMatcher
    
    # Get all recent replies and compare in Python
    recent_replies = AIReply.objects.filter(
        user=user,
        created_at__gte=since
    )
    
    similar_ids = []
    for reply in recent_replies:
        if reply.normalized_text:
            ratio = SequenceMatcher(None, normalized_text, reply.normalized_text).ratio()
            if ratio >= threshold:
                similar_ids.append(reply.id)
    
    return AIReply.objects.filter(id__in=similar_ids)
