# FILE: backend/app/services/embedding_service.py
# PHOENIX PROTOCOL - CLOUD EMBEDDING PIVOT V10.0
# STATUS: 100% Independent / 8GB RAM Optimized

import logging
from typing import List, Optional
from .llm_service import get_embedding

logger = logging.getLogger(__name__)

def generate_embedding(text: str, language: Optional[str] = None) -> List[float]:
    """Generates high-precision OpenAI embeddings, bypassing local AI Core."""
    if not text or not text.strip(): return []
    try:
        # Returns 1536-dimensional vector via OpenAI API
        vector = get_embedding(text)
        if all(v == 0.0 for v in vector):
            logger.error("❌ Cloud embedding returned zero vector. Check API Key.")
            return []
        return vector
    except Exception as e:
        logger.error(f"❌ Cloud Embedding Failure: {e}")
        return []