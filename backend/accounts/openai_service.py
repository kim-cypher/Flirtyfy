import os
import httpx
from openai import OpenAI

_client = None


def get_openai_client():
    """Lazy-load OpenAI client. Used by similarity.py for embedding generation."""
    global _client
    if _client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        try:
            _client = OpenAI(api_key=api_key, http_client=httpx.Client())
        except Exception:
            _client = OpenAI(api_key=api_key)
    return _client
