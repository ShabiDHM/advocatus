# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - SAAS VECTOR STORE V55.0 (SINGLETON DB POOL & KOSOVO-WIDE COURT MATCHER)

import os
import time
import logging
import json
import re
from typing import List, Dict, Any, Sequence, Optional
from pymongo import MongoClient
from bson import ObjectId

from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache për lidhjen e MongoDB për të mos hapur qindra lidhje paralele
_CACHED_DB = None


def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    return {
        k: (v if isinstance(v, (str, int, float, bool)) else json.dumps(v, ensure_ascii=False))
        for k, v in metadata.items()
    }


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


def get_global_collection(): 
    return None 


def query_global_knowledge_base(query_text: str, n_results: int = 20, **kwargs) -> List[Dict[str, Any]]:
    """
    Kërkim hibrid në Bazën Globale të Ligjeve, Neneve dhe Vendimeve të Gjykatës Supreme.
    """
    from . import embedding_service
    db = _get_db()
    coll = db["legal_knowledge_base"]
    raw_results = []
    seen_ids = set()

    # 1. KËRKIM I DREJTPËRDREJTË STATUTOR & PRECEDENTËSH (PHOENIX FIX: Përfshin KE, PA1, PML, Rev, etj.)
    article_matches = re.findall(r'\b(?:Neni|Nenit|Nenin)\s*(\d+[a-zA-Z]?)\b', query_text, re.IGNORECASE)
    case_law_matches = re.findall(r'\b(?:PML|Rev|AC|CA|A|PA1|PKR|KE|P|C|Cn)\.?\s*(?:nr|Nr|NR)?\.?\s*(\d+/\d{2,4})\b', query_text, re.IGNORECASE)

    direct_queries = []
    if article_matches:
        for art_num in article_matches:
            direct_queries.append({"article_number": str(art_num)})
            if str(art_num).isdigit():
                direct_queries.append({"article_number": int(art_num)})
            direct_queries.append({"title": {"$regex": f"Neni\\s+{art_num}\\b", "$options": "i"}})

    if case_law_matches:
        for cl_num in case_law_matches:
            direct_queries.append({"title": {"$regex": cl_num, "$options": "i"}})
            direct_queries.append({"text": {"$regex": cl_num, "$options": "i"}})
            direct_queries.append({"law_title": {"$regex": cl_num, "$options": "i"}})

    if direct_queries:
        try:
            exact_docs = list(coll.find({"$or": direct_queries}).limit(10))
            for doc in exact_docs:
                d_id = str(doc.get("_id", ""))
                if d_id not in seen_ids:
                    seen_ids.add(d_id)
                    raw_results.append(doc)
        except Exception as ex:
            logger.warning(f"Direct statute search fallback error: {ex}")

    # 2. KËRKIMI VEKTORIAL SEMANTIK ($vectorSearch)
    vector = embedding_service.generate_embedding(query_text) if query_text else None
    if vector:
        try:
            pipeline = [{
                "$vectorSearch": {
                    "index": "vector_index", 
                    "path": "embedding", 
                    "queryVector": vector, 
                    "numCandidates": 150, 
                    "limit": n_results
                }
            }]
            vector_docs = list(coll.aggregate(pipeline))
            for doc in vector_docs:
                d_id = str(doc.get("_id", ""))
                if d_id not in seen_ids:
                    seen_ids.add(d_id)
                    raw_results.append(doc)
        except Exception as e:
            logger.warning(f"Global Vector Search failed, running text fallback: {e}")

    # 3. TEXT SEARCH FALLBACK
    if len(raw_results) < n_results:
        try:
            clean_q = re.sub(r'[^\w\s]', ' ', query_text).strip()
            if clean_q:
                text_docs = list(coll.find({"$text": {"$search": clean_q}}).limit(n_results - len(raw_results)))
                for doc in text_docs:
                    d_id = str(doc.get("_id", ""))
                    if d_id not in seen_ids:
                        seen_ids.add(d_id)
                        raw_results.append(doc)
        except Exception:
            pass

    # 4. FORMATIMI DOKTRINAR I REZULTATEVE
    formatted_results = []
    for r in raw_results[:n_results]:
        law_title = r.get("law_title") or r.get("title") or "Dokument Juridik i Kosovës"
        article_num = str(r.get("article_number", ""))
        is_article = r.get("is_article", False)
        is_case_law = r.get("is_case_law", False) or any(k in law_title.lower() for k in ["pml", "rev", "supreme", "kushtetuese", "apelit", "ke."])

        if is_case_law:
            source_tag = f"🔨 Praktika Gjyqësore & Vendim Parimor (Gjykata Supreme e Kosovës): {law_title}"
        elif is_article:
            art_label = "Neni " if article_num != "0" else "Preambula"
            art_suffix = article_num if article_num != "0" else ""
            source_tag = f"⚖️ Baza Statutare: {law_title}, {art_label}{art_suffix}"
        else:
            section_label = f"Neni {article_num}" if article_num else "Seksioni"
            source_tag = f"📚 Doktrina dhe Komentari Zyrtar ({law_title}), {section_label}"

        formatted_results.append({
            "text": (r.get("text") or r.get("content") or "").strip(), 
            "source": source_tag, 
            "chunk_id": str(r.get("_id", ""))
        })

    return formatted_results


def query_case_knowledge_base(user_id: str, query_text: str, n_results: int = 35, **kwargs) -> List[Dict[str, Any]]:
    """
    Kërkim i thellë dhe i izoluar hermetikisht në dokumentet e fashikullit të lëndës.
    """
    from . import embedding_service
    case_context_id = kwargs.get("case_context_id") or kwargs.get("case_id")
    
    db = _get_db()
    coll = db["user_vectors"]
    results = []
    seen_chunk_ids = set()

    # Përgatitja e filtrave të sigurt të lëndës
    valid_case_ids = set()
    if case_context_id:
        case_id_str = str(case_context_id)
        valid_case_ids.add(case_id_str)
        if ObjectId.is_valid(case_id_str):
            valid_case_ids.add(str(ObjectId(case_id_str)))

    vector = embedding_service.generate_embedding(query_text) if query_text else None

    # 1. KËRKIMI VEKTORIAL ME FILTRIM TË OWNER_ID
    if vector:
        try:
            pipeline = [{
                "$vectorSearch": {
                    "index": "vector_index", 
                    "path": "embedding", 
                    "queryVector": vector, 
                    "numCandidates": 200, 
                    "limit": n_results * 2,
                    "filter": {"owner_id": user_id}
                }
            }]
            vector_results = list(coll.aggregate(pipeline))
            
            for r in vector_results:
                r_id = str(r.get("_id", ""))
                r_case_id = str(r.get("case_id", ""))
                
                if valid_case_ids and r_case_id not in valid_case_ids:
                    continue
                
                if r_id not in seen_chunk_ids:
                    seen_chunk_ids.add(r_id)
                    results.append(r)
                    
        except Exception as e:
            logger.warning(f"Case vector search warning: {e}")

    # 2. FALLBACK DIREKT NGA USER_VECTORS
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
            
            direct_chunks = list(coll.find(case_filter).limit(n_results))
            for r in direct_chunks:
                r_id = str(r.get("_id", ""))
                if r_id not in seen_chunk_ids:
                    seen_chunk_ids.add(r_id)
                    results.append(r)
        except Exception as e:
            logger.error(f"Direct user_vectors fetch error: {e}")

    # 3. FALLBACK DIREKT NGA TABELA E DOKUMENTEVE (DOKUMENTET E PLOTA)
    if not results and case_context_id:
        try:
            c_oid = ObjectId(case_context_id) if ObjectId.is_valid(case_context_id) else case_context_id
            doc_cursor = db.documents.find({
                "$or": [{"case_id": str(case_context_id)}, {"case_id": c_oid}], 
                "status": {"$ne": "DELETED"}
            })
            docs = list(doc_cursor)
            
            fallback_chunks = []
            for doc in docs:
                text_content = (doc.get("content") or doc.get("extracted_text") or doc.get("text") or doc.get("summary") or "").strip()
                if text_content and text_content != "Sinteza...":
                    file_name = doc.get("file_name") or doc.get("title") or "Dokument i Lëndës"
                    fallback_chunks.append({
                        "text": text_content,
                        "source": file_name,
                        "page": 1
                    })
            return fallback_chunks
        except Exception as doc_err:
            logger.error(f"Direct document fallback error: {doc_err}")

    return [
        {
            "text": (r.get("text") or "").strip(), 
            "source": r.get("file_name", "Dokument"), 
            "page": r.get("page", 1)
        } 
        for r in results[:n_results]
        if r.get("text")
    ]


def create_and_store_embeddings_from_chunks(
    user_id: str, 
    document_id: str, 
    case_id: str, 
    file_name: str, 
    chunks: List[str], 
    metadatas: Sequence[Dict[str, Any]]
) -> bool:
    from . import embedding_service
    
    if not chunks:
        logger.warning(f"⚠️ [VectorStore] 0 chunks provided for document {document_id}")
        return False

    try:
        vectors = embedding_service.generate_embeddings_batch(chunks)
        
        coll = _get_db()["user_vectors"]
        docs = []
        for i, chunk in enumerate(chunks):
            vector = vectors[i] if i < len(vectors) else []
            meta = metadatas[i] if i < len(metadatas) else {}
            docs.append({
                "owner_id": str(user_id), 
                "document_id": str(document_id), 
                "case_id": str(case_id), 
                "file_name": file_name,
                "text": chunk, 
                "embedding": vector if vector else [], 
                **_sanitize_metadata(meta)
            })
        
        if docs: 
            coll.insert_many(docs)
            logger.info(f"✅ Ingested {len(docs)} chunks for document {document_id} in case {case_id}!")
            return True
        return False
            
    except Exception as e:
        logger.error(f"❌ Ingestion Failed: {e}")
        return False


def delete_document_embeddings(user_id: str, document_id: str):
    try: 
        _get_db()["user_vectors"].delete_many({
            "document_id": str(document_id), 
            "$or": [
                {"owner_id": str(user_id)},
                {"owner_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else str(user_id)}
            ]
        })
    except Exception as e: 
        logger.warning(f"⚠️ Delete embeddings error: {e}")


def copy_document_embeddings(source_document_id: str, target_document_id: str, target_user_id: str, target_case_id: str):
    try:
        db = _get_db()
        existing = list(db["user_vectors"].find({"document_id": str(source_document_id)}))
        
        if not existing:
            logger.warning(f"⚠️ No embeddings found for source document {source_document_id}")
            return
        
        for doc in existing:
            doc.pop("_id", None)
            doc.update({
                "document_id": str(target_document_id), 
                "owner_id": str(target_user_id), 
                "case_id": str(target_case_id)
            })
        
        db["user_vectors"].insert_many(existing)
        logger.info(f"✅ Copied {len(existing)} embeddings from {source_document_id} to {target_document_id}")
    except Exception as e:
        logger.error(f"❌ Failed to copy document embeddings: {e}")