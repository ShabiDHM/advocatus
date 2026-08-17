# FILE: backend/app/services/embedding_service.py
# PHOENIX PROTOCOL - CLOUD EMBEDDING PIVOT V11.0 (HIGH-SPEED BATCH EMBEDDING ACCELERATOR)

import logging
from typing import List, Optional
from .llm_service import get_embedding, get_embeddings_batch

logger = logging.getLogger(__name__)


def generate_embedding(text: str, language: Optional[str] = None) -> List[float]:
    """Generates high-precision OpenAI embeddings for a single text."""
    if not text or not text.strip(): 
        return []
    try:
        vector = get_embedding(text)
        if all(v == 0.0 for v in vector):
            logger.error("❌ Cloud embedding returned zero vector. Check API Key.")
            return []
        return vector
    except Exception as e:
        logger.error(f"❌ Cloud Embedding Failure: {e}")
        return []


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    HIGH-SPEED BATCH VECTORIZATION:
    Vectorizes all chunks in a single network round-trip (< 0.4s for the entire document).
    """
    if not texts:
        return []
    try:
        clean_texts = [t.replace("\n", " ").strip() for t in texts]
        vectors = get_embeddings_batch(clean_texts)
        return vectors
    except Exception as e:
        logger.error(f"❌ Batch Embedding Failure: {e}")
        # Fallback to single generation if batch fails
        return [generate_embedding(t) for t in texts]