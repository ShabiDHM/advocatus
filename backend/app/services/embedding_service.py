# FILE: backend/app/services/embedding_service.py
# PHOENIX PROTOCOL - CLOUD EMBEDDING PIVOT V11.1 (HIGH-SPEED BATCH EMBEDDING ACCELERATOR)
# V11.1: EMBEDDING FAILURE HARDENING —
#        - generate_embedding(): kontroll bosh PARA kontrollit zero-vector;
#          log i saktë ("Embedding bosh" jo "zero vector").
#        - generate_embeddings_batch(): valido gjatësinë e përgjigjes;
#          nëse mospërputhje → fallback një-nga-një. Log warning.
# V11.0: HIGH-SPEED BATCH EMBEDDING ACCELERATOR.

import logging
from typing import List, Optional
from .llm_service import get_embedding, get_embeddings_batch

logger = logging.getLogger(__name__)


def generate_embedding(text: str, language: Optional[str] = None) -> List[float]:
    """
    V11.1: Gjeneron embedding për një tekst të vetëm.

    Kthen [] në dështim ose nëse API kthen vector bosh/zero.
    """
    if not text or not text.strip():
        return []

    try:
        vector = get_embedding(text)

        # V11.1: Kontrollo bosh PARA kontrollit zero-vector
        if not vector:
            logger.warning(
                "⚠️ [Embedding V11.1] Kthim bosh — kontrollo API key, "
                "kuota, ose lidhjen me OpenRouter."
            )
            return []

        # V11.1: Rrallë herë — vetëm nëse API kthen vërtet zero vector
        if all(v == 0.0 for v in vector):
            logger.warning(
                "⚠️ [Embedding V11.1] Zero vector — kontrollo API key."
            )
            return []

        return vector

    except Exception as e:
        logger.warning(f"⚠️ [Embedding V11.1] Dështoi: {e}")
        return []


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    V11.1: Batch vectorization me validim + fallback.

    Nëse batch-i kthen mospërputhje gjatësie (dështim parcial ose total),
    fallback në generate_embedding për çdo tekst.
    """
    if not texts:
        return []

    try:
        clean_texts = [t.replace("\n", " ").strip() for t in texts]
        vectors = get_embeddings_batch(clean_texts)

        # V11.1: Valido gjatësinë
        if not vectors or len(vectors) != len(texts):
            logger.warning(
                f"⚠️ [Batch V11.1] Mospërputhje gjatësie: "
                f"{len(vectors) if vectors else 0} vectors për "
                f"{len(texts)} input — fallback një-nga-një."
            )
            return [generate_embedding(t) for t in texts]

        return vectors

    except Exception as e:
        logger.warning(f"⚠️ [Batch V11.1] Dështoi: {e} — fallback një-nga-një.")
        return [generate_embedding(t) for t in texts]