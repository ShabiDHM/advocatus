# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - BULLETPROOF DUAL-LAYER VECTOR RETRIEVER V68.5
# V68.5: EMPTY EMBEDDING HARDENING — create_and_store_embeddings_from_chunks
#        tani skip chunks me embedding bosh. Nëse të gjitha bosh → kthe
#        success=False (nuk ruan dokumente pa vektor që mbushin Mongo
#        dhe nuk gjenden nga RAG chat).
# V68.4: ORG-AWARE — hequr filtri Python owner_id.
# V68.3: Skip embedding fetch për case të vegjël (<500 chunks).
# V68.2: Query VETËM me case_id.
# V68.1: Reduktuar fetch limits.
# V68.0: Skip $vectorSearch për case të vegjël.
# V67.0: delete_document_embeddings — ORG-AWARE.
# V66.0: BATCH + RETRY + TIMEOUT.
# V65.0: Optional document filter.

import os
import time
import logging
import json
import re
import math
from typing import List, Dict, Any, Sequence, Optional
from pymongo import MongoClient
from pymongo.errors import (
    BulkWriteError,
    OperationFailure,
    ConnectionFailure,
    ServerSelectionTimeoutError,
    AutoReconnect,
    ExecutionTimeout,
)
from bson import ObjectId

from app.core.config import settings

logger = logging.getLogger(__name__)

_CACHED_DB = None


# ═══════════════════════════════════════════════════════════════════════════
# V66.0: INGESTION CONFIG
# ═══════════════════════════════════════════════════════════════════════════

INGESTION_BATCH_SIZE = 15
INGESTION_MAX_RETRIES = 3
INGESTION_BACKOFF_BASE = 1.0
INGESTION_TIMEOUT_MS = 30000


CASE_NO_PATTERN = re.compile(
    r'\b(?:PA1|PKR|PML|REV|Rev|KMLP|ANR|A\.NR|PZR|CP|P|AC|PN|KP)\.?\s*(?:nr|Nr|NR)?\.?\s*(\d+[\w\/\.\-]*)',
    re.IGNORECASE
)
ARTICLE_EXTRACT_PATTERN = re.compile(
    r'\b(?:Neni|Nenit|Nenin|Artikulli|Art\.?)\s*(\d+[a-zA-Z]?)\b',
    re.IGNORECASE
)

ALBANIAN_STOP_WORDS = {
    "i", "e", "të", "te", "së", "se", "më", "me", "në", "ne", "nga", "për", "per",
    "ndaj", "tek", "ku", "ka", "pa", "brenda", "para", "pas", "si", "ose", "dhe",
    "po", "jo", "një", "nje", "çdo", "cdo", "këtë", "kete", "atij", "asaj", "keta",
    "keto", "derisa", "nuk", "eshte", "është", "jane", "janë"
}


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Llogaritje me shpejtësi të lartë e ngjashmërisë kosinusike."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a, b in zip(vec1, vec2)))
    norm_b = math.sqrt(sum(b * b for a, b in zip(vec1, vec2)))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def _get_db():
    global _CACHED_DB
    if _CACHED_DB is not None:
        return _CACHED_DB

    try:
        from app.core.db import get_db_instance
        _CACHED_DB = get_db_instance()
        return _CACHED_DB
    except Exception:
        uri = settings.DATABASE_URI or os.getenv("DATABASE_URI")
        db_name = settings.MONGO_DB_NAME or os.getenv("MONGO_DB_NAME", "advocatus_db")
        if not uri:
            logger.error("❌ DATABASE_URI is empty in vector_store_service._get_db()")
            raise ValueError("DATABASE_URI is not configured.")
        _CACHED_DB = MongoClient(uri)[db_name]
        return _CACHED_DB


# ═══════════════════════════════════════════════════════════════════════════
# QUERY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def query_global_knowledge_base(query_text: str, n_results: int = 35, **kwargs) -> List[Dict[str, Any]]:
    """
    MOTORI I GARANTUAR VEKTORIAL DHE STATUTOR I KOSOVËS.

    V68.3: Skip caselaw fetch nëse $vectorSearch funksionon.
    """
    from . import embedding_service
    db = _get_db()
    coll = db["legal_knowledge_base"]

    clean_query = query_text.strip()
    if not clean_query:
        return []

    statute_results = []
    caselaw_results = []
    seen_ids = set()

    article_matches = ARTICLE_EXTRACT_PATTERN.findall(clean_query)
    case_matches = CASE_NO_PATTERN.findall(clean_query)

    if article_matches:
        statute_queries = []
        for art in article_matches:
            statute_queries.append({"article_number": str(art), "is_article": True})
            if str(art).isdigit():
                statute_queries.append({"article_number": int(art), "is_article": True})
            statute_queries.append({"title": {"$regex": rf"Neni\s+{art}\b", "$options": "i"}, "is_article": True})

        try:
            matched_statutes = list(coll.find({"$or": statute_queries}).limit(10).max_time_ms(5000))
            for doc in matched_statutes:
                d_id = str(doc.get("_id", ""))
                if d_id not in seen_ids:
                    seen_ids.add(d_id)
                    statute_results.append(doc)
        except Exception as ex:
            logger.warning(f"Statute extraction query error: {ex}")

    if case_matches:
        case_queries = []
        for c_no in case_matches:
            escaped = re.escape(c_no)
            case_queries.append({"case_number": {"$regex": escaped, "$options": "i"}})
            case_queries.append({"text": {"$regex": escaped, "$options": "i"}})

        try:
            matched_cases = list(coll.find({"$or": case_queries}).limit(10).max_time_ms(5000))
            for doc in matched_cases:
                d_id = str(doc.get("_id", ""))
                if d_id not in seen_ids:
                    seen_ids.add(d_id)
                    caselaw_results.append(doc)
        except Exception as ex:
            logger.warning(f"Case number direct query error: {ex}")

    try:
        vector = embedding_service.generate_embedding(clean_query)
    except Exception as e:
        logger.warning(f"Embedding generation error: {e}")
        vector = None

    if vector:
        try:
            caselaw_pipeline = [{
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": vector,
                    "numCandidates": 200,
                    "limit": 15
                }
            }]
            for doc in coll.aggregate(caselaw_pipeline, maxTimeMS=8000):
                if doc.get("category") == "caselaw" or doc.get("is_case_law"):
                    d_id = str(doc.get("_id", ""))
                    if d_id not in seen_ids:
                        seen_ids.add(d_id)
                        caselaw_results.append(doc)
        except Exception as e:
            logger.warning(f"$vectorSearch caselaw error: {e}")

        try:
            statute_pipeline = [{
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": vector,
                    "numCandidates": 150,
                    "limit": 10
                }
            }]
            for doc in coll.aggregate(statute_pipeline, maxTimeMS=8000):
                if doc.get("is_article") and not doc.get("is_case_law"):
                    d_id = str(doc.get("_id", ""))
                    if d_id not in seen_ids:
                        seen_ids.add(d_id)
                        statute_results.append(doc)
        except Exception as e:
            logger.debug(f"$vectorSearch statute error: {e}")

    query_tokens = [
        re.escape(w.strip()) for w in re.findall(r'\w+', clean_query)
        if len(w.strip()) >= 3 and w.lower() not in ALBANIAN_STOP_WORDS
    ]

    if query_tokens and len(statute_results) < 5:
        token_or_clauses = [{"text": {"$regex": tok, "$options": "i"}} for tok in query_tokens[:4]]
        try:
            text_statutes = list(coll.find({
                "is_article": True,
                "$or": token_or_clauses
            }).limit(8).max_time_ms(5000))
            for doc in text_statutes:
                d_id = str(doc.get("_id", ""))
                if d_id not in seen_ids:
                    seen_ids.add(d_id)
                    statute_results.append(doc)
        except Exception as ex:
            logger.warning(f"Text statute query error: {ex}")

    combined_docs = statute_results[:12] + caselaw_results[:12]
    formatted_results = []

    for r in combined_docs:
        law_title = r.get("law_title") or r.get("title") or "Dokument Juridik i Kosovës"
        article_num = str(r.get("article_number", ""))
        source_name = str(r.get("source", ""))
        is_case_law = (
            r.get("category") == "caselaw"
            or r.get("is_case_law", False)
            or any(b in source_name.lower() for b in ["praktikës", "praktikes", "vendime", "case_law", "supreme"])
        )

        real_page = r.get("actual_page") or r.get("page") or 1

        if is_case_law:
            case_no = r.get("case_number") or r.get("title") or "Aktgjykim i Gjykatës Supreme"
            source_tag = f"🏛️ PRECEDENT REAL I GJYKATËS SUPREME: {case_no}, Faqja {real_page} (Burimi: {source_name})"
        elif article_num and article_num != "0":
            source_tag = f"⚖️ BAZA STATUTORE: {law_title}, Neni {article_num}"
        else:
            source_tag = f"📚 DOKTRINA & KOMENTARI: {law_title}"

        formatted_results.append({
            "text": (r.get("text") or r.get("content") or "").strip(),
            "source": source_tag,
            "page": real_page,
            "law_title": law_title,
            "case_number": r.get("case_number", "Aktgjykim"),
            "article_number": article_num,
            "chunk_id": str(r.get("_id", ""))
        })

    logger.info(f"✅ [Bulletproof Retrieval V68.5] Tërhequr: {len(statute_results)} Nene dhe {len(caselaw_results)} Precedentë për: '{clean_query}'")
    return formatted_results


def query_case_knowledge_base(user_id: str, query_text: str, n_results: int = 35, **kwargs) -> List[Dict[str, Any]]:
    """
    V68.4: ORG-AWARE — filtro vetëm me case_id + document_id.
    Aksesi në case verifikohet nga router (chat_service / case_analysis_router)
    përmes case_service.get_case_for_user. Nuk filtrohet më me owner_id.
    """
    from . import embedding_service
    case_context_id = kwargs.get("case_context_id") or kwargs.get("case_id")
    raw_document_ids = kwargs.get("document_ids")

    db = _get_db()
    coll = db["user_vectors"]
    results = []
    seen_chunk_ids = set()

    case_id_variants: List[Any] = []
    if case_context_id:
        case_id_str = str(case_context_id)
        case_id_variants.append(case_id_str)
        if ObjectId.is_valid(case_id_str):
            case_id_variants.append(ObjectId(case_id_str))

    if not case_id_variants:
        return []

    case_chunk_count = 0
    try:
        case_chunk_count = coll.count_documents({
            "case_id": {"$in": case_id_variants}
        })
    except Exception as e:
        logger.warning(f"Count chunks error: {e}")
        case_chunk_count = 9999

    logger.info(
        f"⚡ [V68.5] Direct mode për case (n={case_chunk_count} chunks) — "
        f"fetch text-only, PA owner filter (org-aware)"
    )

    try:
        base_filter: Dict[str, Any] = {
            "case_id": {"$in": case_id_variants}
        }

        if raw_document_ids:
            valid_doc_ids = [str(d).strip() for d in raw_document_ids if str(d).strip()]
            if valid_doc_ids:
                base_filter["document_id"] = {"$in": valid_doc_ids}

        projection = {
            "_id": 1,
            "text": 1,
            "file_name": 1,
            "page": 1,
            "owner_id": 1,
            "document_id": 1,
        }

        fetch_limit = min(max(case_chunk_count + 50, 200), 500)

        cursor = coll.find(
            base_filter,
            projection
        ).sort([("page", 1), ("_id", 1)]).limit(fetch_limit).max_time_ms(5000)

        for r in cursor:
            r_id = str(r.get("_id", ""))
            if r_id not in seen_chunk_ids:
                seen_chunk_ids.add(r_id)
                results.append(r)
                if len(results) >= n_results:
                    break

        logger.info(
            f"✅ [V68.5] Fetch OK: {len(results)} chunks (nga {case_chunk_count} total, "
            f"limit={fetch_limit})"
        )

    except ExecutionTimeout as e:
        logger.warning(
            f"⏱️ [V68.5] Fetch timeout (5s) — shard i ngadaltë. "
            f"Kthim rezultat i pjesshëm: {len(results)} chunks. Err: {e}"
        )
    except Exception as e:
        logger.warning(f"⚠️ [V68.5] Fetch error: {e}")

    if not results and case_chunk_count > 0:
        logger.warning("⚠️ [V68.5] Fetch kryesor dështoi — provo minimal fallback...")
        try:
            minimal_filter = {"case_id": {"$in": case_id_variants}}
            for r in coll.find(minimal_filter, {"text": 1, "file_name": 1, "page": 1, "_id": 1}).limit(50).max_time_ms(3000):
                r_id = str(r.get("_id", ""))
                if r_id not in seen_chunk_ids:
                    seen_chunk_ids.add(r_id)
                    results.append(r)
                    if len(results) >= min(n_results, 20):
                        break
            logger.info(f"✅ [V68.5] Minimal fallback: {len(results)} chunks")
        except Exception as e2:
            logger.warning(f"⚠️ [V68.5] Minimal fallback dështoi: {e2}")

    results.sort(key=lambda x: (int(x.get("page", 1)) if str(x.get("page", 1)).isdigit() else 1))

    return [
        {
            "text": (r.get("text") or "").strip(),
            "source": r.get("file_name", "Dokument"),
            "page": r.get("page", 1),
            "chunk_id": str(r.get("_id", "")),
        }
        for r in results[:n_results]
        if r.get("text")
    ]


# ═══════════════════════════════════════════════════════════════════════════
# V66.0: INGESTION — BATCH + RETRY + TIMEOUT
# ═══════════════════════════════════════════════════════════════════════════

def _is_transient_error(exc: Exception) -> bool:
    if isinstance(exc, (
        ConnectionFailure,
        ServerSelectionTimeoutError,
        AutoReconnect,
    )):
        return True
    err_str = str(exc).lower()
    return any(marker in err_str for marker in [
        "timed out", "timeout", "connection reset",
        "connection refused", "network", "unreachable",
    ])


def _insert_batch_with_retry(coll, batch, batch_num, total_batches):
    attempt = 0
    last_error = None

    while attempt < INGESTION_MAX_RETRIES:
        attempt += 1
        try:
            result = coll.insert_many(batch, ordered=False)
            inserted = len(result.inserted_ids)
            logger.info(f"✅ [Batch {batch_num}/{total_batches}] Inserted {inserted} chunks (attempt {attempt})")
            return {"success": inserted, "failed": 0, "errors": []}
        except BulkWriteError as bwe:
            details = bwe.details or {}
            n_inserted = details.get("nInserted", 0)
            write_errors = details.get("writeErrors", [])
            n_failed = len(write_errors)
            if n_inserted > 0 and n_failed < len(batch) / 2:
                logger.warning(f"⚠️ [Batch {batch_num}/{total_batches}] Inserted {n_inserted}, failed {n_failed} (partial)")
                return {"success": n_inserted, "failed": n_failed, "errors": [str(e.get("errmsg", "")) for e in write_errors[:3]]}
            last_error = bwe
            logger.warning(f"⚠️ [Batch {batch_num}/{total_batches}] BulkWriteError attempt {attempt}: {bwe}")
        except (ConnectionFailure, ServerSelectionTimeoutError, AutoReconnect) as e:
            last_error = e
            logger.warning(f"⚠️ [Batch {batch_num}/{total_batches}] Transient error attempt {attempt}: {type(e).__name__}: {e}")
        except OperationFailure as e:
            logger.error(f"❌ [Batch {batch_num}/{total_batches}] OperationFailure (no retry): {e}")
            return {"success": 0, "failed": len(batch), "errors": [f"OperationFailure: {e}"]}
        except Exception as e:
            if _is_transient_error(e):
                last_error = e
                logger.warning(f"⚠️ [Batch {batch_num}/{total_batches}] Transient attempt {attempt}: {type(e).__name__}: {e}")
            else:
                logger.error(f"❌ [Batch {batch_num}/{total_batches}] Non-transient error (no retry): {type(e).__name__}: {e}")
                return {"success": 0, "failed": len(batch), "errors": [f"{type(e).__name__}: {e}"]}

        if attempt < INGESTION_MAX_RETRIES:
            backoff = INGESTION_BACKOFF_BASE * (2 ** (attempt - 1))
            logger.info(f"⏳ [Batch {batch_num}/{total_batches}] Backoff {backoff}s para tentativës {attempt + 1}")
            time.sleep(backoff)

    logger.error(f"❌ [Batch {batch_num}/{total_batches}] Dështoi pas {INGESTION_MAX_RETRIES} tentativave. Last error: {last_error}")
    return {"success": 0, "failed": len(batch), "errors": [str(last_error) if last_error else "Unknown error"]}


def create_and_store_embeddings_from_chunks(
    user_id: str,
    document_id: str,
    case_id: str,
    file_name: str,
    chunks: List[str],
    metadatas: Sequence[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    V68.5: Skip chunks me embedding bosh.

    Nëse të gjitha embedding-et janë bosh → kthe success=False (nuk ruan
    dokumente pa vektor që mbushin Mongo dhe nuk gjenden nga RAG chat).
    """
    start = time.time()

    if not chunks:
        logger.warning(f"⚠️ [VectorStore V68.5] 0 chunks provided for document {document_id}")
        return {"success": False, "total_chunks": 0, "ingested": 0, "failed": 0, "batches": 0, "errors": ["No chunks provided"], "duration_sec": 0.0}

    try:
        from . import embedding_service
        t_emb = time.time()
        vectors = embedding_service.generate_embeddings_batch(chunks)
        emb_duration = round(time.time() - t_emb, 2)
        logger.info(f"🔢 [VectorStore V68.5] Embeddings u gjeneruan për {len(chunks)} chunks në {emb_duration}s")
    except Exception as e:
        logger.error(f"❌ [VectorStore V68.5] Embedding generation failed: {e}")
        return {"success": False, "total_chunks": len(chunks), "ingested": 0, "failed": len(chunks), "batches": 0, "errors": [f"Embedding generation failed: {e}"], "duration_sec": round(time.time() - start, 2)}

    # ───────────────────────────────────────────────────────────────────────
    # V68.5: Ndaj chunks me vektor valid nga ato bosh
    # ───────────────────────────────────────────────────────────────────────
    docs: List[Dict[str, Any]] = []
    skipped_empty = 0
    for i, chunk in enumerate(chunks):
        vector = vectors[i] if i < len(vectors) else []

        if not vector:
            skipped_empty += 1
            continue

        meta = metadatas[i] if i < len(metadatas) else {}

        page_val = meta.get("page")
        if page_val is None:
            page_val = i + 1
        try:
            page_val = int(page_val)
        except Exception:
            page_val = 1

        docs.append({
            "owner_id": str(user_id),
            "document_id": str(document_id),
            "case_id": str(case_id),
            "file_name": file_name,
            "text": chunk,
            "page": page_val,
            "embedding": vector,
            **meta
        })

    if skipped_empty > 0:
        logger.warning(
            f"⚠️ [VectorStore V68.5] Skip {skipped_empty}/{len(chunks)} chunks "
            f"— embedding bosh (dështim i API-t). Dokument={document_id}"
        )

    if not docs:
        logger.error(
            f"❌ [VectorStore V68.5] Të gjitha {len(chunks)} chunks kanë embedding bosh "
            f"— nuk ruhen në Mongo. Dokument={document_id}, kontrollo API key."
        )
        return {
            "success": False,
            "total_chunks": len(chunks),
            "ingested": 0,
            "failed": len(chunks),
            "batches": 0,
            "errors": [f"All {len(chunks)} embeddings empty — kontrollo API key / rate limit"],
            "duration_sec": round(time.time() - start, 2),
        }

    # ───────────────────────────────────────────────────────────────────────
    # Ingestion normal (batch + retry)
    # ───────────────────────────────────────────────────────────────────────
    coll = _get_db()["user_vectors"]
    total_batches = (len(docs) + INGESTION_BATCH_SIZE - 1) // INGESTION_BATCH_SIZE

    total_success = 0
    total_failed = 0
    all_errors: List[str] = []

    logger.info(f"📦 [VectorStore V68.5] Duke insertuar {len(docs)} chunks në {total_batches} batches (size={INGESTION_BATCH_SIZE}) për doc={document_id}")

    for batch_idx in range(total_batches):
        start_i = batch_idx * INGESTION_BATCH_SIZE
        end_i = min(start_i + INGESTION_BATCH_SIZE, len(docs))
        batch = docs[start_i:end_i]

        batch_result = _insert_batch_with_retry(coll, batch, batch_num=batch_idx + 1, total_batches=total_batches)
        total_success += batch_result["success"]
        total_failed += batch_result["failed"]
        all_errors.extend(batch_result["errors"])

    success_rate = total_success / len(docs) if docs else 0.0
    is_success = success_rate >= 0.80

    duration = round(time.time() - start, 2)

    if is_success:
        logger.info(f"✅ [VectorStore V68.5] Ingestion i plotë: {total_success}/{len(docs)} chunks në {total_batches} batches, {duration}s (skip_empty={skipped_empty})")
    else:
        logger.error(f"❌ [VectorStore V68.5] Ingestion i pjesshëm: {total_success}/{len(docs)} chunks (success_rate={success_rate:.1%}), errors={len(all_errors)}, {duration}s")

    return {
        "success": is_success,
        "total_chunks": len(docs),
        "ingested": total_success,
        "failed": total_failed,
        "batches": total_batches,
        "skipped_empty": skipped_empty,
        "errors": all_errors[:5],
        "duration_sec": duration,
    }


def delete_document_embeddings(user_id: str, document_id: str, case_id: Optional[str] = None) -> int:
    """
    V67.0: ORG-AWARE — fshin embeddings pavarësisht nga owner_id.
    """
    doc_id_str = str(document_id)
    total_deleted = 0

    try:
        coll = _get_db()["user_vectors"]

        result = coll.delete_many({"document_id": doc_id_str})
        total_deleted += result.deleted_count

        if total_deleted == 0 and ObjectId.is_valid(doc_id_str):
            fallback = coll.delete_many({"document_id": ObjectId(doc_id_str)})
            total_deleted += fallback.deleted_count

        if total_deleted == 0:
            logger.warning(f"⚠️ [VectorStore V68.5] 0 embeddings për document_id={doc_id_str} (case={case_id}, caller={user_id})")
        else:
            logger.info(f"✅ [VectorStore V68.5] {total_deleted} embeddings u fshinë për document_id={doc_id_str} (case={case_id})")
        return total_deleted
    except Exception as e:
        logger.error(f"❌ [VectorStore V68.5] Delete error për {doc_id_str}: {e}")
        return total_deleted


def copy_document_embeddings(source_document_id: str, target_document_id: str, target_user_id: str, target_case_id: str):
    try:
        db = _get_db()
        existing = list(db["user_vectors"].find({"document_id": str(source_document_id)}))
        if not existing:
            return

        for doc in existing:
            doc.pop("_id", None)
            doc.update({
                "document_id": str(target_document_id),
                "owner_id": str(target_user_id),
                "case_id": str(target_case_id)
            })

        db["user_vectors"].insert_many(existing)
    except Exception as e:
        logger.error(f"❌ Failed to copy document embeddings: {e}")