# FILE: backend/app/services/document_review/precedent_search/service.py
# PHOENIX PROTOCOL - PRECEDENT SEARCH SERVICE V2.6
# V2.6: RERANK SCALE CLARITY — Shtuar _resolve_rerank_min_score() që
#       centralizon logjikën e threshold-it në shkallën 0-10 (DeepSeek).
#       Zëvendëson inline-in `if PRECEDENT_RERANKER == "cohere": min * 10`
#       me thirrje të lexueshme. Zero ndryshim sjelljeje.
# V2.5: CACHE CONSISTENCY FIX — Hequr _set_cache(query, [], top_k) në rrugën
#       e "0 kandidate pas threshold-it".
# V2.4: PERFORMANCE — pre-filter para rerank + cache.
# V2.3: Cohere reranker dispatcher.
# V2.2: _cli_test() shfaq topic_label + rerank_score.
# V2.1: Filtrim me rerank_score >= PRECEDENT_RERANK_MIN_SCORE.
# V2.0: Hybrid (Atlas + MongoDB text + RRF) + DeepSeek rerank.

import hashlib
import json
import logging
from typing import List, Dict, Any, Optional

from app.services.embedding_service import generate_embedding

from .config import (
    PRECEDENT_SIMILARITY_THRESHOLD,
    PRECEDENT_TOP_K,
    PRECEDENT_USE_HYBRID,
    PRECEDENT_CANDIDATES,
    PRECEDENT_RRF_K,
    PRECEDENT_RERANKER,
    PRECEDENT_RERANK_MIN_SCORE,
    PRECEDENT_RERANK_COHERE_MIN_SCORE,
)
from .helpers import is_real_case_number, format_result
from .searchers import (
    search_atlas,
    search_mongo_text,
    search_fallback,
    rrf_fusion,
)
from .rerank import rerank, COHERE_TO_DEEPSEEK_SCALE

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# V2.4: CACHE CONFIG
# ═══════════════════════════════════════════════════════════════════════════

PRECEDENT_CACHE_TTL_SECONDS = 24 * 3600  # 24 orë
PRECEDENT_CACHE_KEY_PREFIX = "precedent_search:v1"
PRECEDENT_CACHE_ENABLED = True

# V2.4: Sa kandidatë dërgohen në rerank (para: pa limit → 50+)
PRECEDENT_RERANK_PRE_FILTER_TOP_N = 20


# ═══════════════════════════════════════════════════════════════════════════
# V2.6: RERANK THRESHOLD RESOLVER
# ═══════════════════════════════════════════════════════════════════════════

def _resolve_rerank_min_score() -> float:
    """
    V2.6: Kthen threshold-in e rerank-ut në shkallën e unifikuar 0-10
    (DeepSeek). Për Cohere, shkallëzohet ×COHERE_TO_DEEPSEEK_SCALE pasi
    rerank_cohere() e ka tashmë të shkallëzuar `rerank_score` në 0-10.
    """
    if PRECEDENT_RERANKER == "cohere":
        return PRECEDENT_RERANK_COHERE_MIN_SCORE * COHERE_TO_DEEPSEEK_SCALE
    return PRECEDENT_RERANK_MIN_SCORE


# ═══════════════════════════════════════════════════════════════════════════
# V2.4: CACHE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _make_cache_key(query_text: str, top_k: int) -> str:
    """V2.4: Çelës deterministik sipas query + top_k."""
    normalized = " ".join(query_text.strip().lower().split())
    digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()[:16]
    return f"{PRECEDENT_CACHE_KEY_PREFIX}:{digest}:{top_k}"


def _get_cache(query_text: str, top_k: int) -> Optional[List[Dict[str, Any]]]:
    """V2.4: Lexon rezultatin nga Redis (me timeout 0.3s, fail-open)."""
    if not PRECEDENT_CACHE_ENABLED:
        return None

    try:
        import redis
        from app.core.config import settings

        client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=0.3,
            socket_connect_timeout=0.3,
        )
        key = _make_cache_key(query_text, top_k)
        raw = client.get(key)
        client.close()

        if not raw:
            return None

        data = json.loads(raw)
        if isinstance(data, list):
            logger.info(f"⚡ [PRECEDENT CACHE] HIT — {len(data)} rezultate (key={key})")
            return data
        return None
    except Exception as e:
        logger.warning(f"⚠️ [PRECEDENT CACHE] Get failed: {e}")
        return None


def _set_cache(query_text: str, top_k: int, results: List[Dict[str, Any]]) -> None:
    """V2.4: Ruan rezultatin në Redis (fail-open, nuk bllokon)."""
    if not PRECEDENT_CACHE_ENABLED:
        return

    try:
        import redis
        from app.core.config import settings

        client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=0.3,
            socket_connect_timeout=0.3,
        )
        key = _make_cache_key(query_text, top_k)
        client.setex(
            key,
            PRECEDENT_CACHE_TTL_SECONDS,
            json.dumps(results, default=str, ensure_ascii=False),
        )
        client.close()
        logger.info(f"💾 [PRECEDENT CACHE] SAVE — {len(results)} rezultate (key={key})")
    except Exception as e:
        logger.warning(f"⚠️ [PRECEDENT CACHE] Set failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def search_relevant_precedents(
    db,
    query_text: str,
    top_k: int = PRECEDENT_TOP_K,
    threshold: float = PRECEDENT_SIMILARITY_THRESHOLD,
) -> List[Dict[str, Any]]:
    """
    V2.6: Hybrid (Atlas + MongoDB text + RRF) + Reranker.

    Rrjedha:
      1. CACHE check — nëse ekziston në Redis, kthe direkt
      2. Embedding query
      3. Kandidatet: hybrid / vector-only / fallback
      4. Filtrim: _is_real_case_number + threshold
      5. Dedup sipas case_number
      6. PRE-FILTER — top 20 sipas RRF/cosine → rerank
      7. Rerank (deepseek | cohere | none)
      8. Filtrim me rerank_score >= _resolve_rerank_min_score()
      9. CACHE save — VETËM nëse ka rezultate
      10. Format + log
    """
    if not query_text or not query_text.strip():
        logger.warning("⚠️ [PRECEDENT] Query bosh - kthim []")
        return []

    if db is None:
        logger.error("❌ [PRECEDENT] db=None - kthim []")
        return []

    # ─── 1. CACHE CHECK ───
    cached = _get_cache(query_text, top_k)
    if cached is not None:
        return cached

    # ─── 2. Embedding ───
    try:
        query_vector = generate_embedding(query_text)
    except Exception as e:
        logger.error(f"❌ [PRECEDENT] Embedding deshtoi: {e}")
        return []

    if not query_vector:
        logger.error("❌ [PRECEDENT] Embedding bosh - kthim []")
        return []

    # ─── 3. Kandidatet ───
    strategy = "vector_only"
    candidates: List[Dict[str, Any]] = []

    if PRECEDENT_USE_HYBRID:
        vector_results = search_atlas(db, query_vector, limit=PRECEDENT_CANDIDATES)
        text_results = search_mongo_text(db, query_text, limit=PRECEDENT_CANDIDATES)

        if not vector_results and not text_results:
            logger.warning("⚠️ [PRECEDENT] Hybrid bosh - fallback cosine")
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
            f"⚠️ [PRECEDENT] Asnje kandidat (strategjia={strategy}). Kthim []"
        )
        return []

    # ─── 4. Filtrim + threshold ───
    filtered_for_dedup: List[Dict[str, Any]] = []
    skipped_no_sim = 0
    for doc in candidates:
        cn = str(doc.get("case_number") or doc.get("title") or "").strip()
        if not is_real_case_number(cn):
            continue

        cosine = doc.get("similarity")
        rrf = doc.get("rrf_score")

        if cosine is not None:
            if float(cosine) < threshold:
                continue
        elif rrf is not None:
            if float(rrf) <= 0:
                continue
        else:
            skipped_no_sim += 1
            continue

        filtered_for_dedup.append(doc)

    if skipped_no_sim > 0:
        logger.info(
            f"ℹ️ [PRECEDENT] Skip {skipped_no_sim} kandidatë pa similarity/RRF"
        )

    if not filtered_for_dedup:
        logger.info(
            f"ℹ️ [PRECEDENT] 0 kandidate pas filtrit (strategjia={strategy})"
        )
        # V2.5: NUK cache-ohet [] — transient dështimi nuk duhet të bllokojë
        # rezultatet e vlefshme për 24 orë.
        return []

    # ─── 5. Dedup ───
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

    # ─── 6. PRE-FILTER para rerank ───
    deduped_sorted = sorted(
        deduped,
        key=lambda d: (
            d.get("rrf_score", 0) or 0,
            d.get("similarity", 0) or 0,
        ),
        reverse=True,
    )

    pre_filter_limit = min(PRECEDENT_RERANK_PRE_FILTER_TOP_N, max(top_k * 2, 10))
    pre_filtered = deduped_sorted[:pre_filter_limit]

    logger.info(
        f"⚡ [PRECEDENT V2.6] Pre-filter: {len(deduped)} → {len(pre_filtered)} "
        f"kandidatë për rerank (limit={pre_filter_limit})"
    )

    # ─── 7. Rerank ───
    reranked = False
    if PRECEDENT_RERANKER in ("deepseek", "cohere") and len(pre_filtered) > 0:
        reranked_docs = rerank(query_text, pre_filtered, top_n=top_k * 2)
        reranked = True

        # V2.6: Threshold i centralizuar (shkallë 0-10)
        min_score = _resolve_rerank_min_score()

        final_docs = [
            d for d in reranked_docs
            if d.get("rerank_score", 0.0) >= min_score
        ]

        if not final_docs and reranked_docs:
            logger.info(
                f"⚠️ [RERANK] Asnje kandidat me score >= "
                f"{min_score:.2f}. Marr top 3 si fallback."
            )
            final_docs = reranked_docs[:3]
    else:
        final_docs = pre_filtered[:top_k]

    final_docs = final_docs[:top_k]

    # ─── 8. Format ───
    formatted: List[Dict[str, Any]] = []
    for doc in final_docs:
        formatted.append(format_result(
            doc,
            cosine_sim=doc.get("similarity"),
            rerank_score=doc.get("rerank_score"),
            rrf_score=doc.get("rrf_score"),
            search_source=doc.get("_search_source"),
        ))

    # ─── 9. CACHE SAVE — VETËM nëse ka rezultate ───
    if formatted:
        _set_cache(query_text, top_k, formatted)

    # ─── 10. Log ───
    logger.info(
        f"🏛️ [PRECEDENT V2.6] Strategjia={strategy}, "
        f"reranker={PRECEDENT_RERANKER}, "
        f"reranked={reranked}, "
        f"kandidate={len(candidates)}, "
        f"pas_threshold={len(filtered_for_dedup)}, "
        f"dedup={len(deduped)}, "
        f"pre_filtered={len(pre_filtered)}, "
        f"final={len(formatted)}"
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
            f"ℹ️ [PRECEDENT] Asnje precedent i mjaftueshem - "
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
    print(f"TEST V2.6 - Query: '{test_query}'")
    print(f"Hybrid: {PRECEDENT_USE_HYBRID}, Reranker: {PRECEDENT_RERANKER}")
    print(f"Threshold: {PRECEDENT_SIMILARITY_THRESHOLD}, Top-K: {PRECEDENT_TOP_K}")
    print(f"Pre-filter top N: {PRECEDENT_RERANK_PRE_FILTER_TOP_N}")
    print(f"Cache: {'ENABLED' if PRECEDENT_CACHE_ENABLED else 'DISABLED'} "
          f"(TTL={PRECEDENT_CACHE_TTL_SECONDS}s)")
    if PRECEDENT_RERANKER == "cohere":
        print(f"Min Cohere score (0-1): {PRECEDENT_RERANK_COHERE_MIN_SCORE}")
        print(f"Min effective (0-10): {_resolve_rerank_min_score():.2f}")
    else:
        print(f"Min DeepSeek score: {PRECEDENT_RERANK_MIN_SCORE}")
    print('=' * 70)

    print("\n[TEST 1] Cold run (nuk ka cache)...")
    results = search_relevant_precedents(db, test_query, top_k=5)
    print(f"\n>>> Rezultatet: {len(results)}")

    print("\n[TEST 2] Warm run (duhet cache HIT)...")
    results2 = search_relevant_precedents(db, test_query, top_k=5)
    print(f"\n>>> Rezultatet: {len(results2)}")

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