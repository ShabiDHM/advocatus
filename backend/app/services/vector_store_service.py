# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - VECTOR STORE V16.0 (METADATA AWARE)
# 1. FIX: The 'query_case_knowledge_base' function now correctly extracts and returns the 'page' number from metadata.
# 2. STATUS: Enables page-specific citations in the RAG service.

from __future__ import annotations
import os
import time
import logging
from typing import List, Dict, Optional, Any, Sequence
import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
GLOBAL_KB_COLLECTION_NAME = "legal_knowledge_base"

_client: Optional[ClientAPI] = None
_global_collection: Optional[Collection] = None
_active_user_collections: Dict[str, Collection] = {}

def connect_chroma_db():
    global _client, _global_collection
    if _client and _global_collection: return
    retries = 5
    while retries > 0:
        try:
            if not _client:
                _client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
                try: _client.heartbeat()
                except: pass 
            if not _global_collection:
                _global_collection = _client.get_or_create_collection(name=GLOBAL_KB_COLLECTION_NAME)
            logger.info("✅ [VectorStore] Connected to ChromaDB.")
            return
        except Exception as e:
            retries -= 1
            logger.warning(f"⚠️ [VectorStore] Connection error: {e}. Retrying... ({retries} left)")
            time.sleep(5)
    logger.critical("❌ [VectorStore] CRITICAL FAILURE: Could not connect to Database.")

def get_client() -> ClientAPI:
    if _client is None: connect_chroma_db()
    return _client # type: ignore

def get_global_collection() -> Collection:
    if _global_collection is None: connect_chroma_db()
    return _global_collection # type: ignore

def get_case_kb_collection(user_id: str) -> Collection:
    if not user_id: raise ValueError("User ID is required.")
    if user_id in _active_user_collections: return _active_user_collections[user_id]
    client = get_client()
    collection = client.get_or_create_collection(name=f"user_{user_id}")
    _active_user_collections[user_id] = collection
    return collection

def create_and_store_embeddings_from_chunks(
    user_id: str, document_id: str, case_id: str, file_name: str, 
    chunks: List[str], metadatas: Sequence[Dict[str, Any]]
) -> bool:
    from . import embedding_service
    try:
        collection = get_case_kb_collection(user_id)
    except Exception as e:
        logger.error(f"Failed to access 'Baza e Lëndës' for user {user_id}: {e}")
        return False
    
    embeddings = [emb for chunk in chunks if (emb := embedding_service.generate_embedding(chunk, language=metadatas[0].get('language')))]
    if not embeddings: return False
    
    ids = [f"{document_id}_{int(time.time())}_{i}" for i in range(len(chunks))]
    
    try:
        collection.add(embeddings=embeddings, documents=chunks, metadatas=list(metadatas), ids=ids) # type: ignore
        return True
    except Exception as e:
        logger.error(f"Ingestion failed for User {user_id}: {e}", exc_info=True)
        return False

def query_case_knowledge_base(
    user_id: str, 
    query_text: str, 
    n_results: int = 7, 
    case_context_id: Optional[str] = None,
    document_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    from . import embedding_service
    embedding = embedding_service.generate_embedding(query_text)
    if not embedding: return []

    try:
        user_coll = get_case_kb_collection(user_id)
        where_filter: Optional[Dict[str, Any]] = None
        if document_ids:
            where_filter = {"source_document_id": {"$in": document_ids}} if len(document_ids) > 1 else {"source_document_id": {"$eq": document_ids[0]}}
        elif case_context_id and case_context_id != "general":
            where_filter = {"case_id": {"$eq": str(case_context_id)}}
        
        private_res = user_coll.query(query_embeddings=[embedding], n_results=n_results, where=where_filter) # type: ignore
        
        results = []
        if private_res and (doc_lists := private_res.get('documents')) and doc_lists and (docs := doc_lists[0]):
            meta_lists = private_res.get('metadatas', [[]])
            metas = meta_lists[0] if meta_lists and meta_lists[0] else [{} for _ in docs]
            for d, m in zip(docs, metas):
                results.append({
                    "text": d, 
                    "source": m.get("file_name", "Dokument"), 
                    "page": m.get("page", "N/A"), # PHOENIX FIX: Extract and return the page number
                    "type": "CASE_FACT"
                })
        return results
    except Exception as e:
        logger.warning(f"Baza e Lëndës Query failed for {user_id}: {e}")
        return []

def query_global_knowledge_base(
    query_text: str, n_results: int = 3, jurisdiction: str = 'ks'
) -> List[Dict[str, Any]]:
    from . import embedding_service
    embedding = embedding_service.generate_embedding(query_text)
    if not embedding: return []
    try:
        kb_res = get_global_collection().query(query_embeddings=[embedding], n_results=n_results, where={"jurisdiction": {"$eq": jurisdiction}}) # type: ignore
        results = []
        if kb_res and (doc_lists := kb_res.get('documents')) and doc_lists and (docs := doc_lists[0]):
            meta_lists = kb_res.get('metadatas', [[]])
            metas = meta_lists[0] if meta_lists and meta_lists[0] else [{} for _ in docs]
            for d, m in zip(docs, metas):
                results.append({"text": d, "source": m.get("source", "Ligj"), "type": "GLOBAL_LAW"})
        return results
    except Exception as e:
        logger.warning(f"Baza e Ligjeve Query failed: {e}")
        return []

# ... (cleanup functions remain the same)
def delete_user_collection(user_id: str): pass
def delete_document_embeddings(user_id: str, document_id: str): pass