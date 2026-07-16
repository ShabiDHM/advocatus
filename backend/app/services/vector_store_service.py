# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - SAAS VECTOR STORE V23.0 (MONGO ATLAS PIVOT)
# 1. REMOVED: All ChromaDB dependencies.
# 2. ADDED: MongoDB Atlas Vector Search logic for permanent persistence.

import os, time, logging, json
from typing import List, Dict, Any, Sequence
from pymongo import MongoClient

logger = logging.getLogger(__name__)

def _get_db():
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    return MongoClient(uri)[db_name]

def query_global_knowledge_base(query_text: str, n_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
    from . import embedding_service
    vector = embedding_service.generate_embedding(query_text)
    if not vector: return []
    try:
        coll = _get_db()["legal_knowledge_base"]
        # Standard Atlas Vector Search Pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index", 
                    "path": "embedding",
                    "queryVector": vector,
                    "numCandidates": 100,
                    "limit": n_results
                }
            }
        ]
        results = list(coll.aggregate(pipeline))
        return [{"text": r.get("text", ""), "source": r.get("law_title", "Ligji"), "chunk_id": str(r.get("_id"))} for r in results]
    except Exception as e:
        logger.error(f"SaaS Global Query Failed: {e}")
        return []

def query_case_knowledge_base(user_id: str, query_text: str, n_results: int = 15, **kwargs) -> List[Dict[str, Any]]:
    from . import embedding_service
    vector = embedding_service.generate_embedding(query_text)
    if not vector: return []
    try:
        coll = _get_db()["user_vectors"]
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": vector,
                    "numCandidates": 100,
                    "limit": n_results,
                    "filter": {"owner_id": user_id} # SaaS Multitenancy
                }
            }
        ]
        results = list(coll.aggregate(pipeline))
        return [{"text": r["text"], "source": r.get("file_name", "Doc"), "page": r.get("page", "N/A")} for r in results]
    except Exception as e:
        logger.error(f"SaaS Case Query Failed: {e}")
        return []

def create_and_store_embeddings_from_chunks(uid: str, did: str, cid: str, fname: str, chunks: List[str], metas: Sequence[Dict[str, Any]]) -> bool:
    from . import embedding_service
    try:
        coll = _get_db()["user_vectors"]
        docs = []
        for i, chunk in enumerate(chunks):
            vector = embedding_service.generate_embedding(chunk)
            if vector:
                docs.append({
                    "owner_id": uid, "document_id": did, "case_id": cid, "file_name": fname,
                    "text": chunk, "embedding": vector, **metas[i]
                })
        if docs: coll.insert_many(docs)
        return True
    except Exception as e:
        logger.error(f"SaaS Ingestion Failed: {e}")
        return False

def delete_document_embeddings(uid: str, did: str):
    _get_db()["user_vectors"].delete_many({"document_id": did, "owner_id": uid})

def copy_document_embeddings(sid: str, tid: str, tuid: str, tcid: str):
    db = _get_db()
    existing = list(db["user_vectors"].find({"document_id": sid}))
    for doc in existing:
        doc.pop("_id", None)
        doc.update({"document_id": tid, "owner_id": tuid, "case_id": tcid})
    if existing: db["user_vectors"].insert_many(existing)

def get_global_collection(): return None # Stub to prevent import crashes