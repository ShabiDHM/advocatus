# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - SAAS VECTOR STORE V25.1 (TYPO CORRECTED)
# 1. FIX: Aligned 'metadatas' variable name to prevent Pylance undefined error.
# 2. STATUS: Linter clean / Fail-Fast active.

import os, time, logging, json
from typing import List, Dict, Any, Sequence
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# --- UTILITIES ---
def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    return {k: (v if isinstance(v, (str, int, float, bool)) else json.dumps(v, ensure_ascii=False)) for k, v in metadata.items()}

def _get_db():
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    return MongoClient(uri)[db_name]

def get_global_collection(): return None 

def query_global_knowledge_base(query_text: str, n_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
    from . import embedding_service
    vector = embedding_service.generate_embedding(query_text)
    if not vector: return []
    try:
        coll = _get_db()["legal_knowledge_base"]
        pipeline = [{"$vectorSearch": {"index": "vector_index", "path": "embedding", "queryVector": vector, "numCandidates": 100, "limit": n_results}}]
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
        pipeline = [{"$vectorSearch": {"index": "vector_index", "path": "embedding", "queryVector": vector, "numCandidates": 100, "limit": n_results, "filter": {"owner_id": user_id}}}]
        results = list(coll.aggregate(pipeline))
        return [{"text": r["text"], "source": r.get("file_name", "Doc"), "page": r.get("page", "N/A")} for r in results]
    except Exception as e:
        logger.error(f"SaaS Case Query Failed: {e}")
        return []

# PHOENIX SIGNATURE FIX: Aligned parameter names with orchestrator
def create_and_store_embeddings_from_chunks(
    user_id: str, 
    document_id: str, 
    case_id: str, 
    file_name: str, 
    chunks: List[str], 
    metadatas: Sequence[Dict[str, Any]]
) -> bool:
    from . import embedding_service
    
    # Diagnostic Log
    logger.info(f"⚡ [VectorStore] Attempting to store {len(chunks)} chunks for document {document_id}")
    
    try:
        coll = _get_db()["user_vectors"]
        docs = []
        for i, chunk in enumerate(chunks):
            vector = embedding_service.generate_embedding(chunk)
            if vector:
                docs.append({
                    "owner_id": user_id, 
                    "document_id": document_id, 
                    "case_id": case_id, 
                    "file_name": file_name,
                    "text": chunk, 
                    "embedding": vector, 
                    **metadatas[i]  # PHOENIX FIX: Aligned variable name
                })
        
        # PHOENIX FAIL-FAST: Explicitly fail if no vectors were generated
        if docs: 
            coll.insert_many(docs)
            logger.info(f"✅ SaaS Ingested {len(docs)} vectors for document {document_id}")
            return True
        else:
            logger.error(f"❌ [VectorStore] FAILURE: 0 vectors generated. Your OpenRouter key on Render is likely missing or blocked.")
            return False
            
    except Exception as e:
        logger.error(f"SaaS Ingestion Failed: {e}")
        return False

def delete_document_embeddings(user_id: str, document_id: str):
    try: _get_db()["user_vectors"].delete_many({"document_id": document_id, "owner_id": user_id})
    except Exception: pass

def copy_document_embeddings(source_document_id: str, target_document_id: str, target_user_id: str, target_case_id: str):
    try:
        db = _get_db()
        existing = list(db["user_vectors"].find({"document_id": source_document_id}))
        for doc in existing:
            doc.pop("_id", None)
            doc.update({"document_id": target_document_id, "owner_id": target_user_id, "case_id": target_case_id})
        if existing: db["user_vectors"].insert_many(existing)
    except Exception: pass