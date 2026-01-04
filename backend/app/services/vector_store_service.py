# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - VECTOR STORE V13.0 (END-TO-END ARCHITECTURE)
# 1. REFACTOR: Renamed functions to 'query_case_knowledge_base' and 'query_global_knowledge_base'.
# 2. LOGIC: Enforced strict boundary between Private User Data (Facts) and Public Legal Data (Law).
# 3. FILTERS: Preserved robust 'document_ids' filtering for Case KB.

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

# THE GLOBAL KNOWLEDGE BASE (Shared, Read-Only for Users)
GLOBAL_KB_COLLECTION_NAME = "legal_knowledge_base"

_client: Optional[ClientAPI] = None
_global_collection: Optional[Collection] = None

# Cache for Active Case Knowledge Bases (User Collections)
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
            
            logger.info("✅ Connected to ChromaDB. Global & Case Knowledge Bases ready.")
            return
        except Exception as e:
            retries -= 1
            logger.warning(f"ChromaDB connection error: {e}. Retrying... ({retries} left)")
            time.sleep(5)
            
    logger.critical("❌ Failed to connect to ChromaDB.")

def get_client() -> ClientAPI:
    if _client is None: connect_chroma_db()
    return _client # type: ignore

# --- GLOBAL KNOWLEDGE BASE ACCESS (LAW) ---
def get_global_collection() -> Collection:
    if _global_collection is None: connect_chroma_db()
    return _global_collection # type: ignore

# --- CASE KNOWLEDGE BASE ACCESS (FACTS) ---
def get_case_kb_collection(user_id: str) -> Collection:
    """
    Retrieves the Private Collection for a specific user (The Case Knowledge Base storage).
    """
    if not user_id:
        raise ValueError("User ID is required to access Case Knowledge Base.")
        
    if user_id in _active_user_collections:
        return _active_user_collections[user_id]
    
    client = get_client()
    # PHOENIX: Each user gets a dedicated collection for their cases
    collection_name = f"user_{user_id}"
    
    collection = client.get_or_create_collection(name=collection_name)
    _active_user_collections[user_id] = collection
    return collection

# --- INGESTION (WRITING TO CASE KB) ---
def create_and_store_embeddings_from_chunks(
    user_id: str, document_id: str, case_id: str, file_name: str, 
    chunks: List[str], metadatas: Sequence[Dict[str, Any]]
) -> bool:
    """
    Writes new facts into the Case Knowledge Base.
    """
    from . import embedding_service
    
    try:
        collection = get_case_kb_collection(user_id)
    except Exception as e:
        logger.error(f"Failed to access Case KB for user {user_id}: {e}")
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
        # Flatten lists for metadata compliance
        sanitized_meta = {k: ", ".join(map(str, v)) if isinstance(v, list) else v for k, v in meta.items()}
        sanitized_metadatas.append(sanitized_meta)

    # STRICT METADATA: Ensures this data belongs to specific Case and Document
    final_metadatas = [{
        **meta, 
        'source_document_id': str(document_id), 
        'case_id': str(case_id), 
        'file_name': file_name, 
        'owner_id': str(user_id),
        'kb_type': 'CASE_FACT' # Explicit Type Tag
    } for meta in sanitized_metadatas]
    
    try:
        collection.add(embeddings=embeddings, documents=processed_chunks, metadatas=final_metadatas, ids=ids) # type: ignore
        return True
    except Exception as e:
        logger.error(f"Ingestion failed for User {user_id}: {e}", exc_info=True)
        return False

# --- RETRIEVAL (READING) ---

def query_case_knowledge_base(
    user_id: str, 
    query_text: str, 
    n_results: int = 7, 
    case_context_id: Optional[str] = None,
    document_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    SEARCH THE FACTS (Private Case Data).
    Strictly filters by Case ID and optional Document IDs.
    """
    from . import embedding_service
    embedding = embedding_service.generate_embedding(query_text)
    if not embedding: return []

    try:
        user_coll = get_case_kb_collection(user_id)
        
        # --- PHOENIX FILTERING LOGIC ---
        where_conditions = []
        
        # 1. Scope: Specific Case
        if case_context_id and case_context_id != "general":
             where_conditions.append({"case_id": {"$eq": str(case_context_id)}})
        
        # 2. Scope: Specific Documents (User Selection)
        if document_ids:
            if len(document_ids) == 1:
                where_conditions.append({"source_document_id": {"$eq": document_ids[0]}})
            else:
                where_conditions.append({"source_document_id": {"$in": document_ids}})
        
        # 3. Construct Filter
        where_filter: Optional[Dict[str, Any]] = None
        if len(where_conditions) > 1:
            where_filter = {"$and": where_conditions}
        elif len(where_conditions) == 1:
            where_filter = where_conditions[0]
        
        private_res = user_coll.query(
            query_embeddings=[embedding], n_results=n_results, where=where_filter # type: ignore
        )
        
        results = []
        if private_res and (doc_lists := private_res.get('documents')) and doc_lists and (docs := doc_lists[0]):
            meta_lists = private_res.get('metadatas', [[]])
            metas = meta_lists[0] if meta_lists and meta_lists[0] else []
            for d, m in zip(docs, metas):
                results.append({
                    "text": d, 
                    "source": (m or {}).get("file_name", "Dokument Case KB"), 
                    "type": "CASE_FACT"
                })
        return results
    except Exception as e:
        logger.warning(f"Case KB Query failed for {user_id}: {e}")
        return []

def query_global_knowledge_base(
    query_text: str, n_results: int = 3, jurisdiction: str = 'ks'
) -> List[Dict[str, Any]]:
    """
    SEARCH THE LAW (Public Global Data).
    """
    from . import embedding_service
    embedding = embedding_service.generate_embedding(query_text)
    if not embedding: return []

    try:
        kb_res = get_global_collection().query(
            query_embeddings=[embedding], n_results=n_results, where={"jurisdiction": {"$eq": jurisdiction}} # type: ignore
        )
        
        results = []
        if kb_res and (doc_lists := kb_res.get('documents')) and doc_lists and (docs := doc_lists[0]):
            meta_lists = kb_res.get('metadatas', [[]])
            metas = meta_lists[0] if meta_lists and meta_lists[0] else []
            for d, m in zip(docs, metas):
                results.append({
                    "text": d, 
                    "source": (m or {}).get("source", "Ligj"), 
                    "type": "GLOBAL_LAW"
                })
        return results
    except Exception as e:
        logger.warning(f"Global KB Query failed: {e}")
        return []

# --- CLEANUP ---
def delete_user_collection(user_id: str):
    client = get_client()
    try:
        client.delete_collection(name=f"user_{user_id}")
        if user_id in _active_user_collections: del _active_user_collections[user_id]
        logger.info(f"🗑️ Deleted Case KB for User: {user_id}")
    except Exception as e:
        logger.warning(f"Failed to delete user collection: {e}")

def delete_document_embeddings(user_id: str, document_id: str):
    try: 
        coll = get_case_kb_collection(user_id)
        coll.delete(where={"source_document_id": str(document_id)})
        logger.info(f"🗑️ Deleted Vectors for Doc: {document_id} (User: {user_id})")
    except Exception as e: 
        logger.warning(f"Failed to delete vectors: {e}")