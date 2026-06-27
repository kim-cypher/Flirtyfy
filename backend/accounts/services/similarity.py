from datetime import timedelta


def get_embedding(text):
    """
    Generate an embedding vector for text using OpenAI text-embedding-3-small.
    Used by the Celery background task for Layer 3 semantic dedup.
    """
    from accounts.openai_service import get_openai_client
    try:
        client = get_openai_client()
        response = client.embeddings.create(
            input=text,
            model='text-embedding-3-small',
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def semantic_similar_replies(user, embedding, since, threshold=0.88):
    """
    Find semantically similar past replies using pgvector cosine distance.
    Called by tasks.generate_and_store_embedding (Layer 3, async) and by
    dedup.dedupe_semantic (synchronous, real-time check).

    threshold=0.88 means 88% similarity → flag as duplicate.
    Lower value = stricter (fewer false negatives).

    Uses CosineDistance, not L2Distance — the (1 - threshold) conversion
    below is only mathematically valid for cosine distance (similarity =
    1 - distance). L2/Euclidean distance has a different, magnitude-dependent
    range, so applying this same formula to it would silently never match.
    """
    from accounts.novelty_models import AIReply
    from pgvector.django import CosineDistance

    if embedding is None:
        return AIReply.objects.none()

    return (
        AIReply.objects.filter(
            user=user,
            created_at__gte=since,
            embedding__isnull=False,
        )
        .annotate(distance=CosineDistance('embedding', embedding))
        .filter(distance__lt=(1 - threshold))
        .order_by('distance')
    )
