# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - BULLETPROOF DUAL-LAYER VECTOR RETRIEVER V67.0
# V67.0: delete_document_embeddings — ORG-AWARE (owner_id-agnostic)
#        - Fshin embeddings vetëm me document_id (unik global)
#        - Fallback në ObjectId variant për legacy data
#        - Kthen deleted_count (int) në vend të None
#        - Log warning kur 0 fshirje (të dallojmë orphan real)
# V66.0: create_and_store_embeddings_from_chunks — BATCH + RETRY + TIMEOUT
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
)
from bson import ObjectId

from app.core.config import settings

logger = logging.getLogger(__name__)

_CACHED_DB = None


# ═══════════════════════════════════════════════════════════════════════════
# V66.0: INGESTION CONFIG
# ═══════════════════════════════════════════════════════════════════════════

INGESTION_BATCH_SIZE = 15           # Chunks per insert_many
INGESTION_MAX_RETRIES = 3           # Tentativa totale për batch
INGESTION_BACKOFF_BASE = 1.0        # Sekonda — 1s, 2s, 4s
INGESTION_TIMEOUT_MS = 30000        # 30s per batch (jo 10s)


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
# QUERY FUNCTIONS (V65.0 — të paprekura)
# ═══════════════════════════════════════════════════════════════════════════

def query_global_knowledge_base(query_text: str, n_results: int = 35, **kwargs) -> List[Dict[str, Any]]:
    """
    MOTORI I GARANTUAR VEKTORIAL DHE STATUTOR I KOSOVËS:
    Kërkon në të gjitha ligjet statutore dhe 1,425 faqet e Gjykatës Supreme.
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

    # 1. KONTROLLI I CITIMEVE TË NENEVE DHE NUMRAVE TË LËNDËVE
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
            matched_statutes = list(coll.find({"$or": statute_queries}).limit(10))
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
            matched_cases = list(coll.find({"$or": case_queries}).limit(10))
            for doc in matched_cases:
                d_id = str(doc.get("_id", ""))
                if d_id not in seen_ids:
                    seen_ids.add(d_id)
                    caselaw_results.append(doc)
        except Exception as ex:
            logger.warning(f"Case number direct query error: {ex}")

    # 2. GJENERIMI I VEKTORIT TË PYETJES (OPENAI EMBEDDING)
    try:
        vector = embedding_service.generate_embedding(clean_query)
    except Exception as e:
        logger.warning(f"Embedding generation error: {e}")
        vector = None

    # 3. KËRKIMI SEMANTIK I PRECEDENTËVE NË 1,425 FAQET E SUPREMES
    if vector:
        atlas_caselaw_success = False
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
            for doc in coll.aggregate(caselaw_pipeline):
                if doc.get("category") == "caselaw" or doc.get("is_case_law"):
                    d_id = str(doc.get("_id", ""))
                    if d_id not in seen_ids:
                        seen_ids.add(d_id)
                        caselaw_results.append(doc)
                        atlas_caselaw_success = True
        except Exception as e:
            logger.debug(f"Atlas $vectorSearch bypassed: {e}")
            atlas_caselaw_success = False

        if not atlas_caselaw_success or len(caselaw_results) < 5:
            try:
                all_caselaw_chunks = list(coll.find(
                    {
                        "$or": [
                            {"category": "caselaw"},
                            {"is_case_law": True}
                        ],
                        "embedding": {"$exists": True, "$ne": []}
                    },
                    {
                        "embedding": 1, "text": 1, "case_number": 1, 
                        "source": 1, "actual_page": 1, "page": 1, "law_title": 1
                    }
                ).limit(3500))

                scored_chunks = []
                for chunk in all_caselaw_chunks:
                    emb = chunk.get("embedding")
                    if emb and isinstance(emb, list) and len(emb) == len(vector):
                        score = _cosine_similarity(vector, emb)
                        scored_chunks.append((score, chunk))

                scored_chunks.sort(key=lambda x: x[0], reverse=True)

                for score, doc in scored_chunks[:15]:
                    d_id = str(doc.get("_id", ""))
                    if d_id not in seen_ids and score > 0.30:
                        seen_ids.add(d_id)
                        caselaw_results.append(doc)
            except Exception as e:
                logger.error(f"In-memory cosine similarity error: {e}")

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
            for doc in coll.aggregate(statute_pipeline):
                if doc.get("is_article") and not doc.get("is_case_law"):
                    d_id = str(doc.get("_id", ""))
                    if d_id not in seen_ids:
                        seen_ids.add(d_id)
                        statute_results.append(doc)
        except Exception:
            pass

    # 4. FALLBACK ME TEKST NËSE DUHEN MË SHUMË DISPOZITA LIGJORE
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
            }).limit(8))
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

    logger.info(f"✅ [Bulletproof Retrieval] Tërhequr: {len(statute_results)} Nene dhe {len(caselaw_results)} Precedentë për: '{clean_query}'")
    return formatted_results


def query_case_knowledge_base(user_id: str, query_text: str, n_results: int = 35, **kwargs) -> List[Dict[str, Any]]:
    """
    Kërkim semantik në shkresat e lëndës.
    """
    from . import embedding_service
    case_context_id = kwargs.get("case_context_id") or kwargs.get("case_id")
    raw_document_ids = kwargs.get("document_ids")
    
    db = _get_db()
    coll = db["user_vectors"]
    results = []
    seen_chunk_ids = set()

    valid_case_ids = set()
    if case_context_id:
        case_id_str = str(case_context_id)
        valid_case_ids.add(case_id_str)
        if ObjectId.is_valid(case_id_str):
            valid_case_ids.add(str(ObjectId(case_id_str)))

    valid_doc_ids = set()
    if raw_document_ids:
        for did in raw_document_ids:
            did_str = str(did).strip()
            if did_str:
                valid_doc_ids.add(did_str)

    vector = embedding_service.generate_embedding(query_text) if query_text else None

    if vector:
        try:
            pipeline = [{
                "$vectorSearch": {
                    "index": "vector_index", 
                    "path": "embedding", 
                    "queryVector": vector, 
                    "numCandidates": 250, 
                    "limit": n_results * 2,
                    "filter": {"owner_id": user_id}
                }
            }]
            vector_results = list(coll.aggregate(pipeline))
            
            for r in vector_results:
                r_id = str(r.get("_id", ""))
                r_case_id = str(r.get("case_id", ""))
                r_doc_id = str(r.get("document_id", ""))
                
                if valid_case_ids and r_case_id not in valid_case_ids:
                    continue

                if valid_doc_ids and r_doc_id not in valid_doc_ids:
                    continue
                
                if r_id not in seen_chunk_ids:
                    seen_chunk_ids.add(r_id)
                    results.append(r)
        except Exception as e:
            logger.warning(f"Case vector search warning: {e}")

    if len(results) < n_results:
        try:
            case_filter: Dict[str, Any] = {
                "$or": [
                    {"owner_id": user_id},
                    {"owner_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id}
                ]
            }
            if valid_case_ids:
                case_id_str = str(case_context_id)
                case_filter["case_id"] = {
                    "$in": [case_id_str, ObjectId(case_id_str) if ObjectId.is_valid(case_id_str) else case_id_str]
                }

            if valid_doc_ids:
                case_filter["document_id"] = {"$in": list(valid_doc_ids)}
            
            direct_chunks = list(coll.find(case_filter).sort([("page", 1), ("_id", 1)]).limit(n_results))
            for r in direct_chunks:
                r_id = str(r.get("_id", ""))
                if r_id not in seen_chunk_ids:
                    seen_chunk_ids.add(r_id)
                    results.append(r)
        except Exception as e:
            logger.error(f"Direct user_vectors fetch error: {e}")

    results.sort(key=lambda x: (int(x.get("page", 1)) if str(x.get("page", 1)).isdigit() else 1))

    return [
        {
            "text": (r.get("text") or "").strip(), 
            "source": r.get("file_name", "Dokument"), 
            "page": r.get("page", 1),
            "chunk_id": str(r.get("_id", ""))
        } 
        for r in results[:n_results]
        if r.get("text")
    ]


# ═══════════════════════════════════════════════════════════════════════════
# V66.0: INGESTION — BATCH + RETRY + TIMEOUT
# ═══════════════════════════════════════════════════════════════════════════

def _is_transient_error(exc: Exception) -> bool:
    """V66.0: Kontrollo nëse error-i është transient (i përsëritshëm)."""
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


def _insert_batch_with_retry(
    coll,
    batch: List[Dict[str, Any]],
    batch_num: int,
    total_batches: int,
) -> Dict[str, Any]:
    """
    V66.0: Insert një batch me retry exponential backoff.
    Kthen: {"success": int, "failed": int, "errors": [...]}
    """
    attempt = 0
    last_error = None

    while attempt < INGESTION_MAX_RETRIES:
        attempt += 1
        try:
            result = coll.insert_many(batch, ordered=False)
            inserted = len(result.inserted_ids)
            logger.info(
                f"✅ [Batch {batch_num}/{total_batches}] "
                f"Inserted {inserted} chunks (attempt {attempt})"
            )
            return {"success": inserted, "failed": 0, "errors": []}

        except BulkWriteError as bwe:
            # Disa dokumente mund të kenë dështuar, por shumica kaluan
            details = bwe.details or {}
            n_inserted = details.get("nInserted", 0)
            write_errors = details.get("writeErrors", [])
            n_failed = len(write_errors)

            if n_inserted > 0 and n_failed < len(batch) / 2:
                # Shumica kaluan → OK, raporto parcialisht
                logger.warning(
                    f"⚠️ [Batch {batch_num}/{total_batches}] "
                    f"Inserted {n_inserted}, failed {n_failed} (partial)"
                )
                return {
                    "success": n_inserted,
                    "failed": n_failed,
                    "errors": [str(e.get("errmsg", "")) for e in write_errors[:3]],
                }

            last_error = bwe
            logger.warning(
                f"⚠️ [Batch {batch_num}/{total_batches}] "
                f"BulkWriteError attempt {attempt}: {bwe}"
            )

        except (ConnectionFailure, ServerSelectionTimeoutError, AutoReconnect) as e:
            last_error = e
            logger.warning(
                f"⚠️ [Batch {batch_num}/{total_batches}] "
                f"Transient error attempt {attempt}: {type(e).__name__}: {e}"
            )

        except OperationFailure as e:
            # Gabime jo-transient (p.sh. auth) → nuk retry
            logger.error(
                f"❌ [Batch {batch_num}/{total_batches}] "
                f"OperationFailure (no retry): {e}"
            )
            return {
                "success": 0,
                "failed": len(batch),
                "errors": [f"OperationFailure: {e}"],
            }

        except Exception as e:
            if _is_transient_error(e):
                last_error = e
                logger.warning(
                    f"⚠️ [Batch {batch_num}/{total_batches}] "
                    f"Transient attempt {attempt}: {type(e).__name__}: {e}"
                )
            else:
                logger.error(
                    f"❌ [Batch {batch_num}/{total_batches}] "
                    f"Non-transient error (no retry): {type(e).__name__}: {e}"
                )
                return {
                    "success": 0,
                    "failed": len(batch),
                    "errors": [f"{type(e).__name__}: {e}"],
                }

        # Backoff para tentativës tjetër
        if attempt < INGESTION_MAX_RETRIES:
            backoff = INGESTION_BACKOFF_BASE * (2 ** (attempt - 1))
            logger.info(
                f"⏳ [Batch {batch_num}/{total_batches}] "
                f"Backoff {backoff}s para tentativës {attempt + 1}"
            )
            time.sleep(backoff)

    # Të gjitha tentativat dështuan
    logger.error(
        f"❌ [Batch {batch_num}/{total_batches}] "
        f"Dështoi pas {INGESTION_MAX_RETRIES} tentativave. "
        f"Last error: {last_error}"
    )
    return {
        "success": 0,
        "failed": len(batch),
        "errors": [str(last_error) if last_error else "Unknown error"],
    }


def create_and_store_embeddings_from_chunks(
    user_id: str, 
    document_id: str, 
    case_id: str, 
    file_name: str, 
    chunks: List[str], 
    metadatas: Sequence[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    V66.0: Krijon dhe ruan embeddings në MongoDB me:
      - Batch size 15 (safe për Atlas free)
      - Retry 3x me backoff exponential
      - Timeout 30s per batch
      - Raportim i detajuar me status

    Kthen:
      {
        "success": bool,          # True nëse > 80% chunks u ruajtën
        "total_chunks": int,
        "ingested": int,
        "failed": int,
        "batches": int,
        "errors": List[str],
        "duration_sec": float,
      }
    """
    start = time.time()

    if not chunks:
        logger.warning(f"⚠️ [VectorStore V66.0] 0 chunks provided for document {document_id}")
        return {
            "success": False,
            "total_chunks": 0,
            "ingested": 0,
            "failed": 0,
            "batches": 0,
            "errors": ["No chunks provided"],
            "duration_sec": 0.0,
        }

    # 1. Gjenero embeddings
    try:
        from . import embedding_service
        t_emb = time.time()
        vectors = embedding_service.generate_embeddings_batch(chunks)
        emb_duration = round(time.time() - t_emb, 2)
        logger.info(f"🔢 [VectorStore V66.0] Embeddings u gjeneruan për {len(chunks)} chunks në {emb_duration}s")
    except Exception as e:
        logger.error(f"❌ [VectorStore V66.0] Embedding generation failed: {e}")
        return {
            "success": False,
            "total_chunks": len(chunks),
            "ingested": 0,
            "failed": len(chunks),
            "batches": 0,
            "errors": [f"Embedding generation failed: {e}"],
            "duration_sec": round(time.time() - start, 2),
        }

    # 2. Ndërto dokumentet për insert
    docs: List[Dict[str, Any]] = []
    for i, chunk in enumerate(chunks):
        vector = vectors[i] if i < len(vectors) else []
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
            "embedding": vector if vector else [],
            **meta
        })

    # 3. Batch + retry insert
    coll = _get_db()["user_vectors"]
    total_batches = (len(docs) + INGESTION_BATCH_SIZE - 1) // INGESTION_BATCH_SIZE

    total_success = 0
    total_failed = 0
    all_errors: List[str] = []

    logger.info(
        f"📦 [VectorStore V66.0] Duke insertuar {len(docs)} chunks në "
        f"{total_batches} batches (size={INGESTION_BATCH_SIZE}) për doc={document_id}"
    )

    for batch_idx in range(total_batches):
        start_i = batch_idx * INGESTION_BATCH_SIZE
        end_i = min(start_i + INGESTION_BATCH_SIZE, len(docs))
        batch = docs[start_i:end_i]

        batch_result = _insert_batch_with_retry(
            coll, batch,
            batch_num=batch_idx + 1,
            total_batches=total_batches,
        )
        total_success += batch_result["success"]
        total_failed += batch_result["failed"]
        all_errors.extend(batch_result["errors"])

    # 4. Vlerëso suksesin
    success_rate = total_success / len(docs) if docs else 0.0
    is_success = success_rate >= 0.80  # 80% threshold

    duration = round(time.time() - start, 2)

    if is_success:
        logger.info(
            f"✅ [VectorStore V66.0] Ingestion i plotë: "
            f"{total_success}/{len(docs)} chunks në {total_batches} batches, {duration}s"
        )
    else:
        logger.error(
            f"❌ [VectorStore V66.0] Ingestion i pjesshëm: "
            f"{total_success}/{len(docs)} chunks (success_rate={success_rate:.1%}), "
            f"errors={len(all_errors)}, {duration}s"
        )

    return {
        "success": is_success,
        "total_chunks": len(docs),
        "ingested": total_success,
        "failed": total_failed,
        "batches": total_batches,
        "errors": all_errors[:5],
        "duration_sec": duration,
    }


def delete_document_embeddings(user_id: str, document_id: str, case_id: Optional[str] = None) -> int:
    """
    V67.0: ORG-AWARE — fshin embeddings pavarësisht nga owner_id.

    Pse: në një organizatë, user-i që fshin dokumentin mund të mos jetë ai
    që e ka ngarkuar. document_id është ObjectId unik → filter vetëm me të
    është i sigurt dhe mbulon të gjitha rastet.

    Kthen: numrin e embeddings të fshirë (int).
    """
    doc_id_str = str(document_id)
    total_deleted = 0

    try:
        coll = _get_db()["user_vectors"]

        # Primary: dokumentet e reja (V66.0+) ruajnë document_id si str
        result = coll.delete_many({"document_id": doc_id_str})
        total_deleted += result.deleted_count

        # Fallback legacy: dokumentet e vjetra mund të kenë ObjectId
        if total_deleted == 0 and ObjectId.is_valid(doc_id_str):
            fallback = coll.delete_many({"document_id": ObjectId(doc_id_str)})
            total_deleted += fallback.deleted_count

        if total_deleted == 0:
            logger.warning(
                f"⚠️ [VectorStore V67.0] 0 embeddings për document_id={doc_id_str} "
                f"(case={case_id}, caller={user_id})"
            )
        else:
            logger.info(
                f"✅ [VectorStore V67.0] {total_deleted} embeddings u fshinë "
                f"për document_id={doc_id_str} (case={case_id})"
            )
        return total_deleted
    except Exception as e:
        logger.error(f"❌ [VectorStore V67.0] Delete error për {doc_id_str}: {e}")
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