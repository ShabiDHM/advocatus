# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - SAAS VECTOR STORE V32.0 (STRICT CASE-ISOLATION & DETERMINISTIC HYBRID LEGAL RETRIEVAL)

import os
import time
import logging
import json
import re
from typing import List, Dict, Any, Sequence, Optional
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)


def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    return {
        k: (v if isinstance(v, (str, int, float, bool)) else json.dumps(v, ensure_ascii=False))
        for k, v in metadata.items()
    }


def _get_db():
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    return MongoClient(uri)[db_name]


def get_global_collection(): 
    return None 


def query_global_knowledge_base(query_text: str, n_results: int = 16, **kwargs) -> List[Dict[str, Any]]:
    """
    KËRKIM HIBRID NË DITURINË GLOBALE:
    Kombinon Kërkimin Vektorial Semantik me Kërkimin e Drejtpërdrejtë të Neneve dhe Precedentëve të Gjykatës Supreme.
    """
    from . import embedding_service
    db = _get_db()
    coll = db["legal_knowledge_base"]
    raw_results = []
    seen_ids = set()

    # 1. KËRKIM I DREJTPËRDREJTË PËR NENE APO PRECEDENTË TË PËRMENDUR NË QUERY
    article_matches = re.findall(r'\b(?:Neni|Nenit|Nenin)\s*(\d+)\b', query_text, re.IGNORECASE)
    case_law_matches = re.findall(r'\b(?:PML|Rev|AC|CA|A)\.?\s*Nr\.?\s*(\d+/\d+)\b', query_text, re.IGNORECASE)

    direct_queries = []
    if article_matches:
        for art_num in article_matches:
            direct_queries.append({"article_number": str(art_num)})
            direct_queries.append({"article_number": int(art_num) if art_num.isdigit() else str(art_num)})
            direct_queries.append({"title": {"$regex": f"Neni\\s+{art_num}\\b", "$options": "i"}})

    if case_law_matches:
        for cl_num in case_law_matches:
            direct_queries.append({"title": {"$regex": cl_num, "$options": "i"}})
            direct_queries.append({"text": {"$regex": cl_num, "$options": "i"}})

    if direct_queries:
        try:
            exact_docs = list(coll.find({"$or": direct_queries}).limit(8))
            for doc in exact_docs:
                d_id = str(doc.get("_id", ""))
                if d_id not in seen_ids:
                    seen_ids.add(d_id)
                    raw_results.append(doc)
        except Exception as ex:
            logger.warning(f"Direct statute search fallback error: {ex}")

    # 2. KËRKIMI VEKTORIAL SEMANTIK NË MONGODB ATLAS
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

    # 3. TEXT / KEYWORD SEARCH FALLBACK NËSE VEKTORËT DËSHTOJNË
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

    # 4. FORMATIMI DHE STRUKTURIMI PËR PROMPT
    formatted_results = []
    for r in raw_results[:n_results]:
        law_title = r.get("law_title") or r.get("title") or "Dokument Juridik"
        article_num = str(r.get("article_number", ""))
        is_article = r.get("is_article", False)
        is_case_law = r.get("is_case_law", False) or "pml" in law_title.lower() or "rev" in law_title.lower() or "supreme" in law_title.lower()

        if is_case_law:
            source_tag = f"🔨 Praktika Gjyqësore & Vendim Parimor i Gjykatës Supreme: {law_title}"
        elif is_article:
            art_label = "Neni " if article_num != "0" else "Preambula"
            art_suffix = article_num if article_num != "0" else ""
            source_tag = f"⚖️ Baza Statutare: {law_title}, {art_label}{art_suffix}"
        else:
            section_label = article_num if article_num else "Seksioni"
            source_tag = f"📚 Doktrina dhe Komentari Zyrtar ({law_title}), {section_label}"

        formatted_results.append({
            "text": (r.get("text") or r.get("content") or "").strip(), 
            "source": source_tag, 
            "chunk_id": str(r.get("_id", ""))
        })

    return formatted_results


def query_case_knowledge_base(user_id: str, query_text: str, n_results: int = 30, **kwargs) -> List[Dict[str, Any]]:
    """
    KËRKIMI SHUTERUES I IZOLUAR PËR LËNDËN (STRICT CASE-LEVEL RETRIEVAL):
    Garanton që asnjë dokument i një lënde tjetër nuk përzihet në kërkim.
    """
    from . import embedding_service
    case_context_id = kwargs.get("case_context_id") or kwargs.get("case_id")
    
    db = _get_db()
    coll = db["user_vectors"]
    results = []
    seen_chunk_ids = set()

    # NDËRTIMI I FILTRIT TË BLINDUAR PËR CASE_ID DHE OWNER_ID
    case_filter: Dict[str, Any] = {"owner_id": user_id}
    if case_context_id:
        case_id_str = str(case_context_id)
        case_filter["$or"] = [
            {"case_id": case_id_str},
            {"case_id": ObjectId(case_id_str) if ObjectId.is_valid(case_id_str) else case_id_str}
        ]

    vector = embedding_service.generate_embedding(query_text) if query_text else None

    # 1. KËRKIMI ME VEKTORË NË ATLAS ME FILTER TË PLOTË CASE_ID
    if vector:
        try:
            vector_filter: Dict[str, Any] = {"owner_id": user_id}
            if case_context_id:
                vector_filter["case_id"] = str(case_context_id)

            pipeline = [{
                "$vectorSearch": {
                    "index": "vector_index", 
                    "path": "embedding", 
                    "queryVector": vector, 
                    "numCandidates": 160, 
                    "limit": n_results, 
                    "filter": vector_filter
                }
            }]
            vector_results = list(coll.aggregate(pipeline))
            for r in vector_results:
                r_id = str(r.get("_id", ""))
                if r_id not in seen_chunk_ids:
                    seen_chunk_ids.add(r_id)
                    results.append(r)
        except Exception as e:
            logger.warning(f"Case vector search error: {e}")

    # 2. NËSE VEKTORËT NUK KTHYEN MJAFTUESHËM, TËRHEQ TË GJITHA PJESËZAT E KËTIJ RASTI NGA USER_VECTORS
    if len(results) < n_results:
        try:
            direct_chunks = list(coll.find(case_filter).limit(n_results))
            for r in direct_chunks:
                r_id = str(r.get("_id", ""))
                if r_id not in seen_chunk_ids:
                    seen_chunk_ids.add(r_id)
                    results.append(r)
        except Exception as e:
            logger.error(f"Direct user_vectors fetch error: {e}")

    # 3. NËSE EDHE USER_VECTORS ËSHTË BOSH, LEXO DREJTPËRDREJT NGA TABELA E DOKUMENTEVE (FALLBACK)
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
                text_content = (doc.get("extracted_text") or doc.get("summary") or "").strip()
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
        for r in results
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
                "owner_id": user_id, 
                "document_id": str(document_id), 
                "case_id": str(case_id), 
                "file_name": file_name,
                "text": chunk, 
                "embedding": vector if vector else [], 
                **_sanitize_metadata(meta)
            })
        
        if docs: 
            coll.insert_many(docs)
            logger.info(f"✅ SaaS Ingested {len(docs)} chunks for document {document_id} in case {case_id}!")
            return True
        return False
            
    except Exception as e:
        logger.error(f"SaaS Ingestion Failed: {e}")
        return False


def delete_document_embeddings(user_id: str, document_id: str):
    try: 
        _get_db()["user_vectors"].delete_many({"document_id": str(document_id), "owner_id": user_id})
    except Exception: 
        pass


def copy_document_embeddings(source_document_id: str, target_document_id: str, target_user_id: str, target_case_id: str):
    try:
        db = _get_db()
        existing = list(db["user_vectors"].find({"document_id": str(source_document_id)}))
        for doc in existing:
            doc.pop("_id", None)
            doc.update({
                "document_id": str(target_document_id), 
                "owner_id": target_user_id, 
                "case_id": str(target_case_id)
            })
        if existing: 
            db["user_vectors"].insert_many(existing)
    except Exception: 
        pass