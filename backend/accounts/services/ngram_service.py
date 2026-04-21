"""
N-gram Blocking Service
Prevents semantic repetition by blocking trigrams that have been used recently
"""

from datetime import timedelta
from django.utils import timezone
from accounts.models import NgramLog
import re

BLOCK_WINDOW_DAYS = 45

def extract_ngrams(text: str) -> dict:
    """Extract all bigrams and trigrams from text"""
    # Clean and tokenize - keep only lowercase letters
    words = re.findall(r'\b[a-z]+\b', text.lower())

    bigrams = [
        f"{words[i]} {words[i+1]}"
        for i in range(len(words)-1)
    ]
    trigrams = [
        f"{words[i]} {words[i+1]} {words[i+2]}"
        for i in range(len(words)-2)
    ]
    return {"bigrams": bigrams, "trigrams": trigrams}

def check_ngrams(user_id: str, text: str) -> dict:
    """
    Returns dict with:
    - passed: bool
    - violations: list of offending ngrams
    """
    cutoff = timezone.now() - timedelta(days=BLOCK_WINDOW_DAYS)
    ngrams = extract_ngrams(text)

    # Only block on trigram matches (bigrams too common)
    existing = NgramLog.objects.filter(
        user_id=user_id,
        ngram__in=ngrams["trigrams"],
        ngram_type="trigram",
        used_at__gte=cutoff
    ).values_list('ngram', flat=True)

    violations = list(existing)
    return {
        "passed": len(violations) == 0,
        "violations": violations
    }

def log_ngrams(user_id: str, text: str):
    """Store all ngrams from an approved response"""
    ngrams = extract_ngrams(text)
    cutoff = timezone.now() - timedelta(days=BLOCK_WINDOW_DAYS)

    # Clean old entries first
    NgramLog.objects.filter(
        user_id=user_id,
        used_at__lt=cutoff
    ).delete()

    # Batch insert new ones
    NgramLog.objects.bulk_create([
        NgramLog(
            user_id=user_id,
            ngram=ng,
            ngram_type="bigram"
        ) for ng in ngrams["bigrams"]
    ] + [
        NgramLog(
            user_id=user_id,
            ngram=ng,
            ngram_type="trigram"
        ) for ng in ngrams["trigrams"]
    ], ignore_conflicts=True)