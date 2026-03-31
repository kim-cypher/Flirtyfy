import openai
from pgvector.django import L2Distance
from .novelty import normalize_text, fingerprint_text

def get_embedding(text):
    response = openai.Embedding.create(
        input=[text],
        model='text-embedding-ada-002'
    )
    return response['data'][0]['embedding']

def semantic_similar_replies(user, embedding, since, threshold=0.85):
    from accounts.novelty_models import AIReply
    return AIReply.objects.filter(
        user=user,
        created_at__gte=since
    ).annotate(
        sim=L2Distance('embedding', embedding)
    ).filter(sim__lte=1-threshold).order_by('sim')

def lexical_similar_replies(user, normalized_text, since, threshold=0.8):
    from accounts.novelty_models import AIReply
    return AIReply.objects.filter(
        user=user,
        created_at__gte=since,
        normalized_text__trigram_similar=normalized_text
    )
