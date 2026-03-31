import re
import hashlib
import unicodedata

def normalize_text(text):
    text = unicodedata.normalize('NFKC', text)
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[\W_]+', ' ', text)
    return text.strip()

def fingerprint_text(text):
    return hashlib.sha256(normalize_text(text).encode()).hexdigest()
