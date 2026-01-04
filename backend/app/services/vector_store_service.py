# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - VECTOR STORE V12.0 (CONTEXT AWARENESS FIX)
# 1. ADDED: Support for 'document_ids' filtering in query_private_diary.
# 2. FIX: Implemented complex ChromaDB '$and' / '$in' filtering logic.

from __future__ import annotations
import os
import time
import logging
from typing import List, Dict, Optional, Any, Sequence, cast
import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.types import Metadata, Where

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))

KB_COLLECTION_NAME = "legal_knowledge_base"

_client: Optional[ClientAPI] = None
_kb_collection: Optional[Collection] = None

_active_user_collections: Dict[str, Collection] = {}

VECTOR_WRITE_BATCH_SIZE = 64

def connect_chroma_db():
    global _client, _kb_collection
    if _client and _kb_collection: return

    retries = 5
    while retries > 0:
        try:
            if not _client:
                _client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
                try:
                    _client.heartbeat()
                except Exception:
                    pass # Continue if heartbeat fails but client is created
            
            if not _kb_collection:
                _kb_collection = _client.get_or_create_collection(name=KB_COLLECTION_NAME)
            
            logger.info("✅ Connected to ChromaDB & Public Library.")
            return
        except Exception as e:
            retries -= 1
            logger.warning(f"ChromaDB connection error: {e}. Retrying... ({retries} left)")
            time.sleep(5)
            
    logger.critical("❌ Failed to connect to ChromaDB.")

def get_client() -> ClientAPI:
    if _client is None: connect_chroma_db()
    return _client # type: ignore

def get_kb_collection() -> Collection:
    if _kb_collection is None: connect_chroma_db()
    return _kb_collection # type: ignore

def get_private_collection(user_id: str) -> Collection:
    if not user_id:
        raise ValueError("User ID is required for Vector Access.")
        
    if user_id in _active_user_collections:
        return _active_user_collections[user_id]
    
    client = get_client()
    collection_name = f"user_{user_id}"
    
    collection = client.get_or_create_collection(name=collection_name)
    _active_user_collections[user_id] = collection
    return collection

def create_and_store_embeddings_from_chunks(
    user_id: str, document_id: str, case_id: str, file_name: str, 
    chunks: List[str], metadatas: Sequence[Dict[str, Any]]
) -> bool:
    from . import embedding_service
    
    try:
        collection = get_private_collection(user_id)
    except Exception as e:
        logger.error(f"Failed to access private collection for user {user_id}: {e}")
        return False
    
    embeddings = []
    processed_chunks = []
    source_tag = f"[[BURIMI: {file_name}]] "
    
    for i, chunk in enumerate(chunks):
        tagged_chunk = f"{source_tag}{chunk}"
        processed_chunks.append(tagged_chunk)
        emb = embedding_service.generate_embedding(tagged_chunk, language=metadatas[i].get('language'))
        if emb: embeddings.append(emb)
    
    if not embeddings: return False
    
    ids = [f"{document_id}_{int(time.time())}_{i}" for i in range(len(processed_chunks))]
    
    sanitized_metadatas = []
    for meta in metadatas:
        sanitized_meta = {k: ", ".join(map(str, v)) if isinstance(v, list) else v for k, v in meta.items()}
        sanitized_metadatas.append(sanitized_meta)

    final_metadatas = [{
        **meta, 'source_document_id': str(document_id), 'case_id': str(case_id), 
        'file_name': file_name, 'owner_id': str(user_id)
    } for meta in sanitized_metadatas]
    
    try:
        collection.add(embeddings=embeddings, documents=processed_chunks, metadatas=final_metadatas, ids=ids) # type: ignore
        return True
    except Exception as e:
        logger.error(f"Batch Add Failed for User {user_id}: {e}", exc_info=True)
        return False

# --- AGENTIC TOOLS ---

def query_private_diary(
    user_id: str, 
    query_text: str, 
    n_results: int = 7, 
    case_context_id: Optional[str] = None,
    document_ids: Optional[List[str]] = None # PHOENIX: Added filtering parameter
) -> List[Dict[str, Any]]:
    from . import embedding_service
    embedding = embedding_service.generate_embedding(query_text)
    if not embedding: return []

    try:
        user_coll = get_private_collection(user_id)
        
        # PHOENIX: Advanced Filtering Logic
        where_conditions = []
        
        # 1. Case Context Filter
        if case_context_id and case_context_id != "general":
             where_conditions.append({"case_id": {"$eq": str(case_context_id)}})
        
        # 2. Document Specific Filter
        if document_ids:
            if len(document_ids) == 1:
                where_conditions.append({"source_document_id": {"$eq": document_ids[0]}})
            else:
                where_conditions.append({"source_document_id": {"$in": document_ids}})
        
        # 3. Construct Final Where Clause
        where_filter: Optional[Dict[str, Any]] = None
        if len(where_conditions) > 1:
            where_filter = {"$and": where_conditions}
        elif len(where_conditions) == 1:
            where_filter = where_conditions[0]
        else:
            where_filter = None # Search everything if no filters
        
        private_res = user_coll.query(
            query_embeddings=[embedding], n_results=n_results, where=where_filter # type: ignore
        )
        
        results = []
        if private_res and (doc_lists := private_res.get('documents')) and doc_lists and (docs := doc_lists[0]):
            meta_lists = private_res.get('metadatas', [[]])
            metas = meta_lists[0] if meta_lists and meta_lists[0] else []
            for d, m in zip(docs, metas):
                results.append({"text": d, "source": (m or {}).get("file_name", "Dokument Privat"), "type": "PRIVATE_DATA"})
        return results
    except Exception as e:
        logger.warning(f"Agent Tool (Private Diary) failed for {user_id}: {e}")
        return []

def query_public_library(
    query_text: str, n_results: int = 3, jurisdiction: str = 'ks'
) -> List[Dict[str, Any]]:
    from . import embedding_service
    embedding = embedding_service.generate_embedding(query_text)
    if not embedding: return []

    try:
        kb_res = get_kb_collection().query(
            query_embeddings=[embedding], n_results=n_results, where={"jurisdiction": {"$eq": jurisdiction}} # type: ignore
        )
        
        results = []
        if kb_res and (doc_lists := kb_res.get('documents')) and doc_lists and (docs := doc_lists[0]):
            meta_lists = kb_res.get('metadatas', [[]])
            metas = meta_lists[0] if meta_lists and meta_lists[0] else []
            for d, m in zip(docs, metas):
                results.append({"text": d, "source": (m or {}).get("source", "Ligj"), "type": "PUBLIC_LAW"})
        return results
    except Exception as e:
        logger.warning(f"Agent Tool (Public Library) failed: {e}")
        return []

# --- LEGACY FUNCTION ---
def query_mixed_intelligence(
    user_id: str, query_text: str, n_results: int = 10, case_context_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    private_results = query_private_diary(user_id, query_text, n_results, case_context_id)
    public_results = query_public_library(query_text, 5)
    return private_results + public_results

# --- CLEANUP ---
def delete_user_collection(user_id: str):
    client = get_client()
    try:
        client.delete_collection(name=f"user_{user_id}")
        if user_id in _active_user_collections: del _active_user_collections[user_id]
        logger.info(f"🗑️ Deleted Collection for User: {user_id}")
    except Exception as e:
        logger.warning(f"Failed to delete user collection: {e}")

def delete_document_embeddings(user_id: str, document_id: str):
    try: 
        coll = get_private_collection(user_id)
        coll.delete(where={"source_document_id": str(document_id)})
        logger.info(f"🗑️ Deleted Vectors for Doc: {document_id} (User: {user_id})")
    except Exception as e: 
        logger.warning(f"Failed to delete vectors: {e}")