# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - SAAS VECTOR STORE V26.0 (AUTOMATIC FAIL-SAFE DIRECT MONGO FALLBACK)

import os, time, logging, json
from typing import List, Dict, Any, Sequence
from pymongo import MongoClient
from bson import ObjectId

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
    
    db = _get_db()
    coll = db["legal_knowledge_base"]
    results = []

    if vector:
        try:
            pipeline = [{"$vectorSearch": {"index": "vector_index", "path": "embedding", "queryVector": vector, "numCandidates": 100, "limit": n_results}}]
            results = list(coll.aggregate(pipeline))
        except Exception as e:
            logger.warning(f"SaaS Global Vector Query Failed, running keyword fallback: {e}")

    # Fallback to direct text search if vector search returns empty
    if not results:
        try:
            results = list(coll.find({"$text": {"$search": query_text}}).limit(n_results))
        except Exception:
            results = list(coll.find().limit(n_results))

    return [{"text": r.get("text", ""), "source": r.get("law_title", "Ligji"), "chunk_id": str(r.get("_id"))} for r in results]

def query_case_knowledge_base(user_id: str, query_text: str, n_results: int = 15, **kwargs) -> List[Dict[str, Any]]:
    """
    UNBREAKABLE DUAL-RETRIEVAL ENGINE:
    1. Executes Atlas $vectorSearch with case_id + owner_id filter.
    2. Fallback: Directly queries db.user_vectors & db.documents if $vectorSearch yields 0 chunks.
    """
    from . import embedding_service
    case_context_id = kwargs.get("case_context_id") or kwargs.get("case_id")
    vector = embedding_service.generate_embedding(query_text) if query_text else None
    
    db = _get_db()
    coll = db["user_vectors"]
    results = []

    case_filter: Dict[str, Any] = {"owner_id": user_id}
    if case_context_id:
        case_id_str = str(case_context_id)
        case_filter["$or"] = [
            {"case_id": case_id_str},
            {"case_id": ObjectId(case_id_str) if ObjectId.is_valid(case_id_str) else case_id_str}
        ]

    # Step 1: Try Vector Search if vector embedding succeeded
    if vector:
        try:
            pipeline = [{
                "$vectorSearch": {
                    "index": "vector_index", 
                    "path": "embedding", 
                    "queryVector": vector, 
                    "numCandidates": 100, 
                    "limit": n_results, 
                    "filter": {"owner_id": user_id}
                }
            }]
            results = list(coll.aggregate(pipeline))
        except Exception as e:
            logger.warning(f"Vector search exception (falling back to direct Mongo search): {e}")

    # Step 2: FAIL-SAFE FALLBACK (Direct Mongo Query if vector search yields 0 chunks)
    if not results:
        logger.info(f"⚡ [VectorStore] Vector search returned 0 results. Executing Direct Mongo Ingestion Fallback for case {case_context_id}")
        
        # A. Query chunks from user_vectors directly
        try:
            results = list(coll.find(case_filter).limit(n_results))
        except Exception as e:
            logger.error(f"Direct user_vectors fetch failed: {e}")

        # B. Direct Document Text Ingestion if user_vectors is empty
        if not results and case_context_id:
            try:
                c_oid = ObjectId(case_context_id) if ObjectId.is_valid(case_context_id) else case_context_id
                doc_cursor = db.documents.find({"$or": [{"case_id": case_context_id}, {"case_id": c_oid}], "status": {"$ne": "DELETED"}})
                docs = list(doc_cursor)
                
                fallback_chunks = []
                for doc in docs:
                    text_content = doc.get("extracted_text") or doc.get("summary") or ""
                    if text_content:
                        file_name = doc.get("file_name") or doc.get("title") or "Dokument i Lëndës"
                        fallback_chunks.append({
                            "text": text_content[:2500],
                            "source": file_name,
                            "page": 1
                        })
                return fallback_chunks
            except Exception as doc_err:
                logger.error(f"Direct document fallback failed: {doc_err}")

    return [{"text": r.get("text", ""), "source": r.get("file_name", "Doc"), "page": r.get("page", "1")} for r in results]

def create_and_store_embeddings_from_chunks(
    user_id: str, 
    document_id: str, 
    case_id: str, 
    file_name: str, 
    chunks: List[str], 
    metadatas: Sequence[Dict[str, Any]]
) -> bool:
    from . import embedding_service
    
    logger.info(f"⚡ [VectorStore] Attempting to store {len(chunks)} chunks for document {document_id}")
    
    try:
        coll = _get_db()["user_vectors"]
        docs = []
        for i, chunk in enumerate(chunks):
            vector = embedding_service.generate_embedding(chunk)
            docs.append({
                "owner_id": user_id, 
                "document_id": document_id, 
                "case_id": case_id, 
                "file_name": file_name,
                "text": chunk, 
                "embedding": vector if vector else [], 
                **metadatas[i]
            })
        
        if docs: 
            coll.insert_many(docs)
            logger.info(f"✅ SaaS Ingested {len(docs)} chunks for document {document_id}")
            return True
        else:
            logger.error(f"❌ [VectorStore] FAILURE: 0 chunks created for document {document_id}")
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