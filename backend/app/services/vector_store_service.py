# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - VECTOR STORE V10.0 (MULTI-TENANT "APARTMENTS")
# 1. ARCHITECTURE: Replaced single user collection with dynamic 'user_{id}' collections.
# 2. LOGIC: Added 'query_mixed_intelligence' for Dual-Brain RAG (Private + Public).
# 3. SECURITY: Strict Data Isolation. User A cannot technically access User B's embeddings.

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

# Cache for active user collections to reduce API calls
# Key: user_id, Value: Collection Object
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
                _client.heartbeat()
            
            # Public Library is static
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

# --- MULTI-TENANT ACCESSORS ---

def get_private_collection(user_id: str) -> Collection:
    """
    Retrieves (or creates) the isolated collection for a specific user.
    Naming Convention: 'user_{user_id}'
    """
    if not user_id:
        raise ValueError("User ID is required for Vector Access.")
        
    # Check memory cache first
    if user_id in _active_user_collections:
        return _active_user_collections[user_id]
    
    client = get_client()
    collection_name = f"user_{user_id}"
    
    # Get or Create
    collection = client.get_or_create_collection(name=collection_name)
    _active_user_collections[user_id] = collection
    return collection

# --- INGESTION (PRIVATE APARTMENT) ---

def create_and_store_embeddings_from_chunks(
    user_id: str, # <--- NEW: Required param
    document_id: str, 
    case_id: str, 
    file_name: str, 
    chunks: List[str], 
    metadatas: Sequence[Dict[str, Any]]
) -> bool:
    from . import embedding_service
    
    # 1. Access Private Collection
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
    
    # Sanitize Metadata (Prevent ChromaDB List Crash)
    sanitized_metadatas = []
    for meta in metadatas:
        sanitized_meta = {}
        for key, value in meta.items():
            if isinstance(value, list):
                sanitized_meta[key] = ", ".join(map(str, value))
            else:
                sanitized_meta[key] = value
        sanitized_metadatas.append(sanitized_meta)

    # Attach structural metadata
    final_metadatas = [{
        **meta, 
        'source_document_id': str(document_id), 
        'case_id': str(case_id), 
        'file_name': file_name,
        'owner_id': str(user_id) # Redundant but safe
    } for meta in sanitized_metadatas] # type: ignore
    
    try:
        collection.add(embeddings=embeddings, documents=processed_chunks, metadatas=final_metadatas, ids=ids) # type: ignore
        return True
    except Exception as e:
        logger.error(f"Batch Add Failed for User {user_id}: {e}", exc_info=True)
        return False

# --- INTELLIGENCE (THE DUAL BRAIN) ---

def query_mixed_intelligence(
    user_id: str,
    query_text: str,
    n_results: int = 10,
    case_context_id: Optional[str] = None # Optional: Filter private data by case/project
) -> List[Dict[str, Any]]:
    """
    THE SUPER-FUNCTION:
    Queries BOTH the Private User Data AND the Public Legal Library.
    Returns a merged list of contexts.
    """
    from . import embedding_service
    embedding = embedding_service.generate_embedding(query_text)
    if not embedding: return []

    combined_results = []

    # 1. Query Private Diary (User Data)
    try:
        user_coll = get_private_collection(user_id)
        
        # Filter by case if provided (Context Switcher logic)
        where_filter = {}
        if case_context_id and case_context_id != "general":
             # Support filtering by Case/Project OR specific Document
             # This simple logic assumes case_context_id matches 'case_id' metadata
             # For advanced doc filtering, we'd need more logic, but this covers the Project/Case pivot.
             where_filter = {"case_id": {"$eq": str(case_context_id)}}
        
        private_res = user_coll.query(
            query_embeddings=[embedding],
            n_results=n_results,
            where=where_filter if where_filter else None # type: ignore
        )
        
        if private_res and private_res['documents'] and private_res['documents'][0]:
            docs = private_res['documents'][0]
            metas = private_res['metadatas'][0] if private_res['metadatas'] else [{}] * len(docs) # type: ignore
            
            for d, m in zip(docs, metas):
                combined_results.append({
                    "text": d,
                    "source": (m or {}).get("file_name", "Dokument Privat"),
                    "type": "PRIVATE_DATA"
                })
    except Exception as e:
        logger.warning(f"Private Query failed for {user_id}: {e}")

    # 2. Query Public Library (Laws)
    try:
        kb_res = get_kb_collection().query(
            query_embeddings=[embedding],
            n_results=5, # Get top 5 laws
            where={"jurisdiction": {"$eq": 'ks'}} # type: ignore
        )
        
        if kb_res and kb_res['documents'] and kb_res['documents'][0]:
            docs = kb_res['documents'][0]
            metas = kb_res['metadatas'][0] if kb_res['metadatas'] else [{}] * len(docs) # type: ignore
            
            for d, m in zip(docs, metas):
                combined_results.append({
                    "text": d,
                    "source": (m or {}).get("source", "Ligj"),
                    "type": "PUBLIC_LAW"
                })
    except Exception as e:
        logger.warning(f"Public KB Query failed: {e}")

    return combined_results

# --- CLEANUP ---

def delete_user_collection(user_id: str):
    """
    Deletes the ENTIRE private collection for a user.
    Used when deleting account.
    """
    client = get_client()
    try:
        client.delete_collection(name=f"user_{user_id}")
        if user_id in _active_user_collections:
            del _active_user_collections[user_id]
        logger.info(f"🗑️ Deleted Collection for User: {user_id}")
    except Exception as e:
        logger.warning(f"Failed to delete user collection: {e}")

def delete_document_embeddings(user_id: str, document_id: str):
    """
    Deletes vectors for a specific document from the user's collection.
    """
    try: 
        coll = get_private_collection(user_id)
        coll.delete(where={"source_document_id": str(document_id)})
        logger.info(f"🗑️ Deleted Vectors for Doc: {document_id} (User: {user_id})")
    except Exception as e: 
        logger.warning(f"Failed to delete vectors: {e}")