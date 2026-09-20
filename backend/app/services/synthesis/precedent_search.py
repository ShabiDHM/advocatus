# FILE: backend/app/services/synthesis/precedent_search.py
# PHOENIX PROTOCOL - SYNTHESIS PRECEDENT SEARCH WRAPPER V1.0
# Wrapper i hollë që ripërdor paketën document_review.precedent_search.
# Nuk dublon logjikën — thërret search_relevant_precedents (hybrid + rerank).
#
# RREGULLA ABSOLUTE:
#   - Zero njohuri e LLM-se per precedentët - VETEM nga legal_knowledge_base.
#   - I njejti signature i jashtëm: search_synthesis_precedents(db, case_type,
#     extractions) -> List[Dict].

import logging
from typing import List, Dict, Any, Optional

from app.services.document_review.precedent_search import (
    search_relevant_precedents,
    build_precedent_query,
    PRECEDENT_SIMILARITY_THRESHOLD,
    PRECEDENT_TOP_K,
)

logger = logging.getLogger(__name__)


# ===========================================================================
# KONFIGURIMI
# ===========================================================================

# Sa karaktere te tekstit te ekstrakteve perdorim per query (limit)
SYNTHESIS_QUERY_MAX_CHARS = 8000

# Sa karaktere per cdo dokument individual (per te shmangur dominimin)
SYNTHESIS_QUERY_PER_DOC_CHARS = 2000


# ===========================================================================
# QUERY BUILDER PËR SYNTHESIS
# ===========================================================================

def build_synthesis_query(
    case_type: Optional[str],
    extractions: List[Dict[str, Any]],
    max_chars: int = SYNTHESIS_QUERY_MAX_CHARS,
) -> str:
    """
    Nderton query nga case_type + ekstraktet e te gjitha dokumenteve.

    Logjika:
      1. Fillimisht case_type (kontekst procedural)
      2. Bashko tekstin e extractions (deri max_chars)
      3. Kalon ne build_precedent_query qe nxjerr termat tematik/frekuence
    """
    if not extractions and not case_type:
        return ""

    # Bashko tekstin nga te gjitha ekstraktet
    combined = ""
    for ext in extractions:
        text = (
            ext.get("text")
            or ext.get("raw_text")
            or ""
        )[:SYNTHESIS_QUERY_PER_DOC_CHARS]

        if not text:
            continue

        combined += " " + text

        if len(combined) >= max_chars:
            break

    combined = combined[:max_chars]

    # Ripërdor build_precedent_query
    query = build_precedent_query(
        document_type="Case Synthesis",
        file_name="",
        doc_text=combined,
        case_type=case_type,
    )

    logger.info(
        f"🔍 [SYNTH-PRECEDENT] Query built: case_type={case_type or 'N/A'}, "
        f"extractions={len(extractions)}, chars={len(combined)}"
    )
    return query


# ===========================================================================
# PUBLIC API
# ===========================================================================

def search_synthesis_precedents(
    db,
    case_type: Optional[str],
    extractions: List[Dict[str, Any]],
    top_k: int = PRECEDENT_TOP_K,
    threshold: float = PRECEDENT_SIMILARITY_THRESHOLD,
) -> List[Dict[str, Any]]:
    """
    Kerkon precedentet per nje case synthesis.

    Ripërdor search_relevant_precedents nga document_review:
      - Hybrid search (Atlas vector + MongoDB text + RRF)
      - Reranker DeepSeek
      - Enrichment me topic_label

    Return: List[Dict] me {case_number, text_excerpt, page, source,
                            similarity, chunk_id, rerank_score, topic_label}
    """
    if not extractions:
        logger.warning("⚠️ [SYNTH-PRECEDENT] Asnje extraction - kthim []")
        return []

    query = build_synthesis_query(case_type, extractions)
    if not query or len(query.strip()) < 5:
        logger.warning("⚠️ [SYNTH-PRECEDENT] Query bosh - kthim []")
        return []

    try:
        results = search_relevant_precedents(
            db, query, top_k=top_k, threshold=threshold
        )
        logger.info(
            f"🏛️ [SYNTH-PRECEDENT] Kthyer {len(results)} precedente "
            f"per case_type='{case_type or 'N/A'}'"
        )
        return results
    except Exception as e:
        logger.error(f"❌ [SYNTH-PRECEDENT] Deshtoi: {e}")
        return []