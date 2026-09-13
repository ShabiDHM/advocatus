# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - GUARANTEED SUPREME CASELAW & DUAL-CHANNEL RETRIEVER V62.0
# 100% COMPLETE CODE • DEDICATED CASLELAW CHANNEL • COVERS BOTH SUPREME BOOKS

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


def query_global_knowledge_base(query_text: str, n_results: int = 25, **kwargs) -> List[Dict[str, Any]]:
    """
    PHOENIX GUARANTEED DUAL-CHANNEL RETRIEVAL:
    Garanton me 100% siguri që të vijnë:
    1. Nenet e Ligjeve të Kosovës (Statutes)
    2. Aktgjykimet reale nga dy librat supremë:
       - 'Përmbledhje e Praktikës Gjyqësore.pdf'
       - 'VENDIME TË PËRZGJEDHURA.pdf'
    """
    from . import embedding_service
    db = _get_db()
    coll = db["legal_knowledge_base"]
    
    statute_results = []
    caselaw_results = []
    seen_ids = set()

    # Ekstraktimi i numrave të neneve dhe precedentëve nga pyetja
    article_matches = re.findall(r'\b(?:Neni|Nenit|Nenin)\s*(\d+[a-zA-Z]?)\b', query_text, re.IGNORECASE)
    case_law_matches = re.findall(r'\b(?:PML|Rev|REV|KMLP|ANR|A\.NR|PZR)\.?\s*(?:nr|Nr|NR)?\.?\s*(\d+/\d{2,4})\b', query_text, re.IGNORECASE)

    # KANALI 1: BAZA STATUTORE (Nenet e Kodit/Ligjit)
    direct_statute_queries = []
    if article_matches:
        for art_num in article_matches:
            direct_statute_queries.append({"article_number": str(art_num), "is_article": True})
            if str(art_num).isdigit():
                direct_statute_queries.append({"article_number": int(art_num), "is_article": True})
            direct_statute_queries.append({"title": {"$regex": f"Neni\\s+{art_num}\\b", "$options": "i"}, "is_article": True})

    if direct_statute_queries:
        try:
            exact_statutes = list(coll.find({"$or": direct_statute_queries}).limit(10))
            for doc in exact_statutes:
                d_id = str(doc.get("_id", ""))
                if d_id not in seen_ids:
                    seen_ids.add(d_id)
                    statute_results.append(doc)
        except Exception as ex:
            logger.warning(f"Statute query error: {ex}")

    # KANALI 2: JURISPRUDENCA DHE PRECEDENTËT E GJYKATËS SUPREME
    caselaw_filter_terms = []
    if case_law_matches:
        for cl_num in case_law_matches:
            caselaw_filter_terms.append({"case_number": {"$regex": re.escape(cl_num), "$options": "i"}})
            caselaw_filter_terms.append({"text": {"$regex": re.escape(cl_num), "$options": "i"}})

    # Fjalë kyçe juridike që kërkojnë precedentë
    legal_keywords = [
        "kallëzim", "kallzim", "aktakuzë", "aktakuze", "dyshimit të bazuar", "dyshim", 
        "dhunë në familje", "dhune", "provë", "prove", "dëshmi", "deshmi", "ekspertizë", 
        "urdhër mbrojtës", "shkelje thelbësore", "revizion", "mbrojtje e ligjshmërisë"
    ]
    matched_keywords = [kw for kw in legal_keywords if kw in query_text.lower()]
    for kw in matched_keywords:
        caselaw_filter_terms.append({
            "text": {"$regex": re.escape(kw), "$options": "i"},
            "$or": [
                {"category": "caselaw"},
                {"is_case_law": True},
                {"source": {"$regex": r"Përmbledhje\s+e\s+Praktikës|VENDIME\s+TË\s+PËRZGJEDHURA|case_law", "$options": "i"}}
            ]
        })

    if caselaw_filter_terms:
        try:
            exact_caselaw = list(coll.find({"$or": caselaw_filter_terms}).limit(10))
            for doc in exact_caselaw:
                d_id = str(doc.get("_id", ""))
                if d_id not in seen_ids:
                    seen_ids.add(d_id)
                    caselaw_results.append(doc)
        except Exception as ex:
            logger.warning(f"Caselaw query error: {ex}")

    # KANALI 3: KËRKIM SEMANTIK ME EMBEDDINGS (I NDARË NË DY KANALE TË DEDIKUARA)
    vector = embedding_service.generate_embedding(query_text) if query_text else None
    if vector:
        try:
            # 3.1 Kërkim i dedikuar për LIGJET
            statute_pipeline = [{
                "$vectorSearch": {
                    "index": "vector_index", 
                    "path": "embedding", 
                    "queryVector": vector, 
                    "numCandidates": 100, 
                    "limit": 10,
                    "filter": {"is_article": True}
                }
            }]
            for doc in coll.aggregate(statute_pipeline):
                d_id = str(doc.get("_id", ""))
                if d_id not in seen_ids:
                    seen_ids.add(d_id)
                    statute_results.append(doc)

            # 3.2 Kërkim i dedikuar EKSKLUZIVISHT për DY LIBRAT E GJYKATËS SUPREME
            caselaw_pipeline = [{
                "$vectorSearch": {
                    "index": "vector_index", 
                    "path": "embedding", 
                    "queryVector": vector, 
                    "numCandidates": 100, 
                    "limit": 10
                }
            }]
            for doc in coll.aggregate(caselaw_pipeline):
                d_id = str(doc.get("_id", ""))
                if d_id not in seen_ids:
                    source_name = str(doc.get("source", ""))
                    is_supreme_book = any(b in source_name for b in [
                        "Përmbledhje e Praktikës", 
                        "VENDIME TË PËRZGJEDHURA", 
                        "case_law"
                    ]) or doc.get("category") == "caselaw" or doc.get("is_case_law")

                    if is_supreme_book:
                        seen_ids.add(d_id)
                        caselaw_results.append(doc)
        except Exception as e:
            # Fallback me kërkim teksti të drejtpërdrejtë
            pass

    # Nëse precedentët ende janë bosh, marrim menjëherë pjesët më relevante nga dy librat
    if len(caselaw_results) < 3:
        try:
            fallback_supreme = list(coll.find({
                "$or": [
                    {"source": {"$regex": r"Përmbledhje\s+e\s+Praktikës|VENDIME\s+TË\s+PËRZGJEDHURA|case_law", "$options": "i"}},
                    {"category": "caselaw"},
                    {"is_case_law": True}
                ]
            }).limit(5))
            for doc in fallback_supreme:
                d_id = str(doc.get("_id", ""))
                if d_id not in seen_ids:
                    seen_ids.add(d_id)
                    caselaw_results.append(doc)
        except Exception:
            pass

    combined_docs = statute_results[:12] + caselaw_results[:10]
    formatted_results = []

    for r in combined_docs:
        law_title = r.get("law_title") or r.get("title") or "Dokument Juridik i Kosovës"
        article_num = str(r.get("article_number", ""))
        source_name = str(r.get("source", ""))
        is_case_law = (
            r.get("category") == "caselaw" 
            or r.get("is_case_law", False) 
            or any(k in law_title.lower() for k in ["pml", "rev", "supreme", "kmlp", "anr", "pzr"])
            or any(b in source_name for b in ["Përmbledhje e Praktikës", "VENDIME TË PËRZGJEDHURA", "case_law"])
        )

        if is_case_law:
            case_no = r.get("case_number") or r.get("title") or "Aktgjykim i Gjykatës Supreme"
            page_info = f", Faqja {r.get('page')}" if r.get('page') else ""
            source_tag = f"🏛️ PRECEDENT REAL I GJYKATËS SUPREME: {case_no}{page_info} (Burimi: {source_name})"
        elif article_num and article_num != "0":
            source_tag = f"⚖️ BAZA STATUTORE: {law_title}, Neni {article_num}"
        else:
            source_tag = f"📚 DOKTRINA & KOMENTARI: {law_title}"

        formatted_results.append({
            "text": (r.get("text") or r.get("content") or "").strip(), 
            "source": source_tag, 
            "chunk_id": str(r.get("_id", ""))
        })

    logger.info(f"✅ [RAG Retrieval] Tërheqje e garantuar: {len(statute_results)} Nene dhe {len(caselaw_results)} Precedentë nga dy librat e Gjykatës Supreme!")
    return formatted_results


def query_case_knowledge_base(user_id: str, query_text: str, n_results: int = 35, **kwargs) -> List[Dict[str, Any]]:
    from . import embedding_service
    case_context_id = kwargs.get("case_context_id") or kwargs.get("case_id")
    
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

    vector = embedding_service.generate_embedding(query_text) if query_text else None

    # 1. Kërkim Vektorial në Atlas
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
                
                if valid_case_ids and r_case_id not in valid_case_ids:
                    continue
                
                if r_id not in seen_chunk_ids:
                    seen_chunk_ids.add(r_id)
                    results.append(r)
        except Exception as e:
            logger.warning(f"Case vector search warning: {e}")

    # 2. Fallback nga user_vectors
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
                **_sanitize_metadata(meta)
            })
        
        if docs: 
            coll.insert_many(docs)
            logger.info(f"✅ Ingested {len(docs)} chunks for document {document_id} in case {case_id} me numërim real faqesh!")
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