"""
Oneiros Utilities - Embedding & Text processing

Functions for string token estimation or text normalization.
"""

import re

def estimate_token_count(text: str) -> int:
    """
    Approximates tokens based on whitespace division (1 token ~ 0.75 words).
    """
    if not text:
        return 0
    words = text.split()
    return int(len(words) * 1.33)

def clean_text_for_embedding(text: str) -> str:
    """
    Normalizes spaces and removes special characters for clean semantic similarity evaluations.
    """
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return re.sub(r'\s+', ' ', text)
