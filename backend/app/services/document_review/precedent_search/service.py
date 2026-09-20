# FILE: backend/app/services/document_review/precedent_search/service.py
# PHOENIX PROTOCOL - PRECEDENT SEARCH SERVICE V2.2
# V2.2: _cli_test() shfaq topic_label + rerank_score (Shtresa 2.1).
# V2.1: Filtrim me rerank_score >= PRECEDENT_RERANK_MIN_SCORE.
# V2.0: Hybrid (Atlas + MongoDB text + RRF) + DeepSeek rerank.

import logging
from typing import List, Dict, Any

from app.services.embedding_service import generate_embedding

from .config import (
    PRECEDENT_SIMILARITY_THRESHOLD,
    PRECEDENT_TOP_K,
    PRECEDENT_USE_HYBRID,
    PRECEDENT_CANDIDATES,
    PRECEDENT_RRF_K,
    PRECEDENT_RERANKER,
    PRECEDENT_RERANK_MIN_SCORE,
)
from .helpers import is_real_case_number, format_result
from .searchers import (
    search_atlas,
    search_mongo_text,
    search_fallback,
    rrf_fusion,
)
from .rerank import rerank_deepseek

logger = logging.getLogger(__name__)


# ===========================================================================
# PUBLIC API
# ===========================================================================

def search_relevant_precedents(
    db,
    query_text: str,
    top_k: int = PRECEDENT_TOP_K,
    threshold: float = PRECEDENT_SIMILARITY_THRESHOLD,
) -> List[Dict[str, Any]]:
    """
    V2.2: Hybrid (Atlas + MongoDB text + RRF) + DeepSeek rerank + topic enrichment.

    Rrjedha:
      1. Embedding query
      2. Kandidatet: hybrid ose vector-only ose fallback
      3. Filtrim: _is_real_case_number + cosine threshold (VETEM per cosine)
      4. Dedup sipas case_number
      5. Rerank me DeepSeek
      6. Filtrim me rerank_score >= PRECEDENT_RERANK_MIN_SCORE
      7. Format + log
    """
    if not query_text or not query_text.strip():
        logger.warning("[PRECEDENT] Query bosh - kthim []")
        return []

    if db is None:
        logger.error("[PRECEDENT] db=None - kthim []")
        return []

    # 1. Embedding
    try:
        query_vector = generate_embedding(query_text)
    except Exception as e:
        logger.error(f"[PRECEDENT] Embedding deshtoi: {e}")
        return []

    if not query_vector:
        logger.error("[PRECEDENT] Embedding bosh - kthim []")
        return []

    # 2. Kandidatet
    strategy = "vector_only"
    candidates: List[Dict[str, Any]] = []

    if PRECEDENT_USE_HYBRID:
        vector_results = search_atlas(db, query_vector, limit=PRECEDENT_CANDIDATES)
        text_results = search_mongo_text(db, query_text, limit=PRECEDENT_CANDIDATES)

        if not vector_results and not text_results:
            logger.warning("[PRECEDENT] Hybrid bosh - fallback cosine")
            candidates = search_fallback(db, query_vector, limit=PRECEDENT_CANDIDATES)
            strategy = "fallback_cosine"
        elif not text_results:
            candidates = vector_results
            strategy = "vector_only"
        elif not vector_results:
            candidates = text_results
            strategy = "text_only"
        else:
            candidates = rrf_fusion(vector_results, text_results, k=PRECEDENT_RRF_K)
            strategy = "hybrid"
    else:
        vector_results = search_atlas(db, query_vector, limit=PRECEDENT_CANDIDATES)
        if not vector_results:
            candidates = search_fallback(db, query_vector, limit=PRECEDENT_CANDIDATES)
            strategy = "fallback_cosine"
        else:
            candidates = vector_results
            strategy = "vector_only"

    if not candidates:
        logger.warning(
            f"[PRECEDENT] Asnje kandidat (strategjia={strategy}). Kthim []"
        )
        return []

    # 3. Filtrim + threshold (VETEM per cosine)
    filtered_for_dedup: List[Dict[str, Any]] = []
    for doc in candidates:
        cn = str(doc.get("case_number") or doc.get("title") or "").strip()
        if not is_real_case_number(cn):
            continue

        cosine = doc.get("similarity")
        if cosine is not None and float(cosine) < threshold:
            continue

        filtered_for_dedup.append(doc)

    if not filtered_for_dedup:
        logger.info(
            f"[PRECEDENT] 0 kandidate pas filtrit (strategjia={strategy})"
        )
        return []

    # 4. Dedup
    seen: Dict[str, Dict[str, Any]] = {}
    for doc in filtered_for_dedup:
        cn = str(doc.get("case_number") or doc.get("title") or "").strip()
        prev = seen.get(cn)
        if prev is None:
            seen[cn] = doc
            continue
        prev_key = (
            prev.get("similarity", 0) or 0,
            prev.get("rrf_score", 0) or 0,
        )
        new_key = (
            doc.get("similarity", 0) or 0,
            doc.get("rrf_score", 0) or 0,
        )
        if new_key > prev_key:
            seen[cn] = doc

    deduped = list(seen.values())

    # 5. Rerank
    reranked = False
    if PRECEDENT_RERANKER == "deepseek" and len(deduped) > 0:
        reranked_docs = rerank_deepseek(query_text, deduped, top_n=top_k * 2)
        reranked = True

        final_docs = [
            d for d in reranked_docs
            if d.get("rerank_score", 0.0) >= PRECEDENT_RERANK_MIN_SCORE
        ]

        if not final_docs and reranked_docs:
            logger.info(
                f"[RERANK] Asnje kandidat me score >= "
                f"{PRECEDENT_RERANK_MIN_SCORE}. Marr top 3 si fallback."
            )
            final_docs = reranked_docs[:3]
    else:
        final_docs = deduped[:top_k]

    final_docs = final_docs[:top_k]

    # 6. Format
    formatted: List[Dict[str, Any]] = []
    for doc in final_docs:
        formatted.append(format_result(
            doc,
            cosine_sim=doc.get("similarity"),
            rerank_score=doc.get("rerank_score"),
            rrf_score=doc.get("rrf_score"),
            search_source=doc.get("_search_source"),
        ))

    # 7. Log
    logger.info(
        f"[PRECEDENT] Strategjia={strategy}, "
        f"reranked={reranked}, "
        f"kandidate={len(candidates)}, "
        f"pas_threshold={len(filtered_for_dedup)}, "
        f"dedup={len(deduped)}, "
        f"final={len(formatted)} "
        f"(min_rerank_score={PRECEDENT_RERANK_MIN_SCORE})"
    )
    for i, p in enumerate(formatted, 1):
        rs = p.get("rerank_score", "-")
        sim = p.get("similarity", 0)
        src = p.get("search_source", "-")
        topic = p.get("topic_label", "-")
        logger.info(
            f"  {i}. [{p['case_number']}] "
            f"sim={sim:.4f} "
            f"rerank={rs} src={src} "
            f"tema={topic} "
            f"page={p['page']}"
        )

    if not formatted:
        logger.info(
            f"[PRECEDENT] Asnje precedent i mjaftueshem - "
            f"raporti do te shkruaje frazen standarde"
        )

    return formatted


# ===========================================================================
# CLI TEST
# ===========================================================================

def _cli_test():
    """Test manual: python -m app.services.document_review.precedent_search"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from app.core.db import get_db

    db = get_db()

    test_query = (
        "Urdher Mbrojtjeje Procedure Penale dhune familjare femije mitur kontakt"
    )

    print(f"\n{'=' * 70}")
    print(f"TEST V2.2 - Query: '{test_query}'")
    print(f"Hybrid: {PRECEDENT_USE_HYBRID}, Reranker: {PRECEDENT_RERANKER}")
    print(f"Threshold: {PRECEDENT_SIMILARITY_THRESHOLD}, Top-K: {PRECEDENT_TOP_K}")
    print(f"Min rerank score: {PRECEDENT_RERANK_MIN_SCORE}")
    print('=' * 70)

    results = search_relevant_precedents(db, test_query, top_k=5)
    print(f"\n>>> Rezultatet: {len(results)}")
    for i, r in enumerate(results, 1):
        rs = r.get("rerank_score", "-")
        src = r.get("search_source", "-")
        topic = r.get("topic_label", "-")
        print(f"\n  {i}. [{r['case_number']}] sim={r['similarity']:.4f} "
              f"rerank={rs} src={src}")
        print(f"     Tema: {topic}")
        print(f"     Burimi: {r['source']}, faqe {r['page']}")
        print(f"     Fragment: {r['text_excerpt'][:200]}...")


# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    _cli_test()