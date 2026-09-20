# FILE: backend/app/services/document_review/precedent_search/searchers.py
# PHOENIX PROTOCOL - PRECEDENT SEARCHERS V2.2
# V2.2: Projections shtojne topic_id, topic_label, topic_keywords.
# V2.1: I njejti.
# V2.0: 3 motoret: Atlas vector, MongoDB text, fallback cosine. + RRF fusion.

import logging
from typing import List, Dict, Any

from .config import (
    LEGAL_KB_COLLECTION,
    ATLAS_VECTOR_INDEX,
    PRECEDENT_CANDIDATES,
    PRECEDENT_RRF_K,
    PRECEDENT_FALLBACK_SCAN_LIMIT,
    PRECEDENT_FALLBACK_BATCH_SIZE,
)
from .helpers import cosine_similarity

logger = logging.getLogger(__name__)


# ===========================================================================
# ATLAS VECTOR
# ===========================================================================

def search_atlas(
    db,
    query_vector: List[float],
    limit: int = PRECEDENT_CANDIDATES,
) -> List[Dict[str, Any]]:
    """Atlas $vectorSearch (pa filter ne stage, filtrim pas me $match)."""
    try:
        coll = db[LEGAL_KB_COLLECTION]
        pipeline = [
            {
                "$vectorSearch": {
                    "index": ATLAS_VECTOR_INDEX,
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": max(300, limit * 3),
                    "limit": limit,
                }
            },
            {"$addFields": {"similarity": {"$meta": "vectorSearchScore"}}},
            {
                "$match": {
                    "$or": [
                        {"category": "caselaw"},
                        {"is_case_law": True},
                    ]
                }
            },
            {"$project": {"embedding": 0}},
            {"$limit": limit},
        ]
        results = list(coll.aggregate(pipeline))
        logger.info(
            f"✅ [PRECEDENT] Atlas $vectorSearch ktheu {len(results)} kandidate"
        )
        return results
    except Exception as e:
        logger.warning(f"⚠️ [PRECEDENT] Atlas $vectorSearch deshtoi: {e}")
        return []


# ===========================================================================
# MONGODB TEXT
# ===========================================================================

def search_mongo_text(
    db,
    query_text: str,
    limit: int = PRECEDENT_CANDIDATES,
) -> List[Dict[str, Any]]:
    """MongoDB $text (index ekziston: text_text_title_text_law_title_text)."""
    if not query_text or not query_text.strip():
        return []

    try:
        coll = db[LEGAL_KB_COLLECTION]
        cursor = coll.find(
            {
                "$text": {"$search": query_text},
                "category": "caselaw",
            },
            {
                "text_score": {"$meta": "textScore"},
                "text": 1, "case_number": 1, "source": 1,
                "actual_page": 1, "page": 1, "chunk_id": 1,
                "_id": 1, "law_title": 1, "title": 1,
                # V2.2: topic fields
                "topic_id": 1, "topic_label": 1, "topic_keywords": 1,
            },
        ).sort([("text_score", {"$meta": "textScore"})]).limit(limit)

        results = list(cursor)
        logger.info(
            f"✅ [PRECEDENT] MongoDB $text ktheu {len(results)} kandidate"
        )
        return results
    except Exception as e:
        logger.warning(f"⚠️ [PRECEDENT] MongoDB $text deshtoi: {e}")
        return []


# ===========================================================================
# FALLBACK COSINE
# ===========================================================================

def search_fallback(
    db,
    query_vector: List[float],
    limit: int = PRECEDENT_CANDIDATES,
) -> List[Dict[str, Any]]:
    """Cosine manuale ne Python (nese Atlas + Text te dy deshtojne)."""
    try:
        coll = db[LEGAL_KB_COLLECTION]
        cursor = coll.find(
            {
                "$or": [
                    {"category": "caselaw"},
                    {"is_case_law": True},
                ],
                "embedding": {"$exists": True, "$ne": []},
            },
            {
                "embedding": 1, "text": 1, "case_number": 1, "title": 1,
                "source": 1, "actual_page": 1, "page": 1, "chunk_id": 1,
                "_id": 1, "law_title": 1,
                # V2.2: topic fields
                "topic_id": 1, "topic_label": 1, "topic_keywords": 1,
            },
        ).limit(PRECEDENT_FALLBACK_SCAN_LIMIT)

        cursor = cursor.batch_size(PRECEDENT_FALLBACK_BATCH_SIZE)
        cursor = cursor.max_time_ms(30000)

        scored: List[Dict[str, Any]] = []
        for doc in cursor:
            emb = doc.get("embedding")
            if not emb or not isinstance(emb, list):
                continue
            if len(emb) != len(query_vector):
                continue
            sim = cosine_similarity(query_vector, emb)
            doc["similarity"] = sim
            scored.append(doc)

        scored.sort(key=lambda d: -d["similarity"])

        if scored:
            logger.info(
                f"✅ [PRECEDENT] Fallback cosine skanoi {len(scored)} chunks, "
                f"top similarity={scored[0]['similarity']:.4f}"
            )
        return scored[:limit]
    except Exception as e:
        logger.error(f"❌ [PRECEDENT] Fallback cosine deshtoi: {e}")
        return []


# ===========================================================================
# RRF FUSION
# ===========================================================================

def rrf_fusion(
    vector_results: List[Dict[str, Any]],
    text_results: List[Dict[str, Any]],
    k: int = PRECEDENT_RRF_K,
) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion.

    score(d) = sum over rankings R of 1 / (k + rank_R(d))
    Dokumentet qe shfaqen ne te dyja ranking-et marrin score me te larte.
    """
    scores: Dict[str, float] = {}
    docs_by_id: Dict[str, Dict[str, Any]] = {}
    sources: Dict[str, set] = {}

    def _doc_id(d: Dict[str, Any]) -> str:
        return str(d.get("_id") or d.get("chunk_id") or id(d))

    for rank, doc in enumerate(vector_results, 1):
        did = _doc_id(doc)
        scores[did] = scores.get(did, 0.0) + 1.0 / (k + rank)
        sources.setdefault(did, set()).add("vector")
        if did not in docs_by_id:
            docs_by_id[did] = doc

    for rank, doc in enumerate(text_results, 1):
        did = _doc_id(doc)
        scores[did] = scores.get(did, 0.0) + 1.0 / (k + rank)
        sources.setdefault(did, set()).add("text")
        if did not in docs_by_id:
            docs_by_id[did] = doc

    sorted_ids = sorted(scores.keys(), key=lambda x: -scores[x])

    fused: List[Dict[str, Any]] = []
    for did in sorted_ids:
        doc = docs_by_id[did]
        doc["rrf_score"] = scores[did]
        src = sources.get(did, set())
        doc["_search_source"] = (
            "both" if len(src) >= 2 else (src.pop() if src else "?")
        )
        fused.append(doc)

    logger.info(
        f"✅ [PRECEDENT] RRF fusion: {len(vector_results)} vector + "
        f"{len(text_results)} text = {len(fused)} unike"
    )
    return fused