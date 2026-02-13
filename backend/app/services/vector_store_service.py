# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - VECTOR STORE V16.5 (TYPE SAFETY + METADATA SANITIZATION)
# 1. FIX: Recursive sanitization of metadata – converts dict → JSON, list → JSON.
# 2. FIX: Explicit None handling in copy_document_embeddings (Pylance).
# 3. STATUS: Full ChromaDB compatibility, 100% type‑checked.

from __future__ import annotations
import os
import time
import logging
import json
from typing import List, Dict, Optional, Any, Sequence, Union
import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

logger = logging.getLogger(__name__)

CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
GLOBAL_KB_COLLECTION_NAME = "legal_knowledge_base"

_client: Optional[ClientAPI] = None
_global_collection: Optional[Collection] = None
_active_user_collections: Dict[str, Collection] = {}

# --- PHOENIX: Robust metadata sanitizer for ChromaDB ---
def _sanitize_metadata_value(value: Any) -> Union[str, int, float, bool, None]:
    """
    Recursively convert any value into a ChromaDB‑compatible type.
    Allowed: str, int, float, bool, None.
    Dict → JSON string, List → JSON string.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)
    if isinstance(value, list):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            try:
                return ", ".join(str(v) for v in value)
            except Exception:
                return str(value)
    try:
        return str(value)
    except Exception:
        return ""

def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Apply _sanitize_metadata_value to every field."""
    sanitized = {}
    for k, v in metadata.items():
        sanitized[k] = _sanitize_metadata_value(v)
    return sanitized

# --- Connection management ---
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
    return _client  # type: ignore

def get_global_collection() -> Collection:
    if _global_collection is None: connect_chroma_db()
    return _global_collection  # type: ignore

def get_case_kb_collection(user_id: str) -> Collection:
    if not user_id: raise ValueError("User ID is required.")
    if user_id in _active_user_collections: return _active_user_collections[user_id]
    client = get_client()
    collection = client.get_or_create_collection(name=f"user_{user_id}")
    _active_user_collections[user_id] = collection
    return collection

# --- Ingestion with metadata sanitization ---
def create_and_store_embeddings_from_chunks(
    user_id: str, 
    document_id: str, 
    case_id: str, 
    file_name: str, 
    chunks: List[str], 
    metadatas: Sequence[Dict[str, Any]]
) -> bool:
    from . import embedding_service
    try:
        collection = get_case_kb_collection(user_id)
    except Exception as e:
        logger.error(f"Failed to access 'Baza e Lëndës' for user {user_id}: {e}")
        return False

    embeddings = []
    valid_chunks = []
    valid_metadatas = []
    
    for i, chunk in enumerate(chunks):
        emb = embedding_service.generate_embedding(chunk, language=metadatas[i].get('language'))
        if emb:
            embeddings.append(emb)
            valid_chunks.append(chunk)
            
            # Sanitize metadata
            raw_meta = dict(metadatas[i])
            raw_meta['source_document_id'] = str(document_id)
            raw_meta['case_id'] = str(case_id)
            raw_meta['file_name'] = file_name
            raw_meta['owner_id'] = str(user_id)
            raw_meta['kb_type'] = 'CASE_FACT'
            
            sanitized_meta = _sanitize_metadata(raw_meta)
            valid_metadatas.append(sanitized_meta)
        else:
            logger.warning(f"Skipping chunk {i} for doc {document_id}: embedding failed.")

    if not embeddings:
        return False

    ids = [f"{document_id}_{int(time.time())}_{i}" for i in range(len(valid_chunks))]
    try:
        collection.add(
            embeddings=embeddings, 
            documents=valid_chunks, 
            metadatas=valid_metadatas, 
            ids=ids
        )  # type: ignore
        logger.info(f"✅ Stored {len(valid_chunks)} chunks for document {document_id}")
        return True
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        return False

# --- Query functions ---
def query_case_knowledge_base(
    user_id: str, 
    query_text: str, 
    n_results: int = 10, 
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
            where_filter = {"source_document_id": {"$eq": document_ids[0]}} if len(document_ids) == 1 else {"source_document_id": {"$in": document_ids}}
        elif case_context_id and case_context_id != "general":
            where_filter = {"case_id": {"$eq": str(case_context_id)}}
        
        private_res = user_coll.query(
            query_embeddings=[embedding], 
            n_results=n_results, 
            where=where_filter
        )  # type: ignore
        results = []
        if private_res and (doc_lists := private_res.get('documents')) and doc_lists and (docs := doc_lists[0]):
            meta_lists = private_res.get('metadatas', [[]])
            metas = meta_lists[0] if meta_lists and meta_lists[0] else [{} for _ in docs]
            for d, m in zip(docs, metas):
                results.append({
                    "text": d,
                    "source": m.get("file_name", "Dokument"),
                    "page": m.get("page", "N/A"),
                    "type": "CASE_FACT"
                })
        return results
    except Exception as e:
        logger.warning(f"Baza e Lëndës Query failed: {e}")
        return []

def query_global_knowledge_base(
    query_text: str, 
    n_results: int = 10, 
    jurisdiction: str = 'ks'
) -> List[Dict[str, Any]]:
    from . import embedding_service
    embedding = embedding_service.generate_embedding(query_text)
    if not embedding: return []
    try:
        kb_res = get_global_collection().query(
            query_embeddings=[embedding], 
            n_results=n_results, 
            where={"jurisdiction": {"$eq": jurisdiction}}
        )  # type: ignore
        results = []
        if kb_res and (doc_lists := kb_res.get('documents')) and doc_lists and (docs := doc_lists[0]):
            meta_lists = kb_res.get('metadatas', [[]])
            metas = meta_lists[0] if meta_lists and meta_lists[0] else [{} for _ in docs]
            for d, m in zip(docs, metas):
                results.append({
                    "text": d,
                    "source": m.get("source", "Ligji përkatës"),
                    "law_title": m.get("law_title"),
                    "article_number": m.get("article_number"),
                    "type": "GLOBAL_LAW"
                })
        return results
    except Exception as e:
        logger.warning(f"Baza e Ligjeve Query failed: {e}")
        return []

def delete_user_collection(user_id: str):
    client = get_client()
    try:
        client.delete_collection(name=f"user_{user_id}")
        if user_id in _active_user_collections: 
            del _active_user_collections[user_id]
    except Exception as e: 
        logger.warning(f"Failed to delete collection: {e}")

def delete_document_embeddings(user_id: str, document_id: str):
    try: 
        coll = get_case_kb_collection(user_id)
        coll.delete(where={"source_document_id": str(document_id)})
        logger.info(f"Deleted embeddings for document {document_id}")
    except Exception as e: 
        logger.warning(f"Failed to delete vectors: {e}")

# --- Optional: Copy embeddings for deduplication ---
def copy_document_embeddings(
    source_document_id: str, 
    target_document_id: str, 
    target_user_id: str, 
    target_case_id: str
):
    """
    Copy all embeddings from source_document to target_document within the same user's collection.
    Required for deduplication optimization.
    """
    try:
        source_coll = get_case_kb_collection(target_user_id)
        results = source_coll.get(where={"source_document_id": str(source_document_id)})
        
        ids = results.get('ids', [])
        documents = results.get('documents')
        metadatas = results.get('metadatas')
        embeddings = results.get('embeddings')
        
        # PHOENIX: Explicit None handling (Pylance safety)
        if documents is None:
            documents = []
        if metadatas is None:
            metadatas = []
        if embeddings is None:
            embeddings = []
        
        if not ids:
            logger.warning(f"No embeddings found for source document {source_document_id}")
            return
        
        new_ids = []
        new_metadatas = []
        for i, meta in enumerate(metadatas):
            new_meta = dict(meta)
            new_meta['source_document_id'] = str(target_document_id)
            new_meta['case_id'] = str(target_case_id)
            new_meta['owner_id'] = str(target_user_id)
            new_id = f"{target_document_id}_copy_{i}_{int(time.time())}"
            new_ids.append(new_id)
            new_metadatas.append(_sanitize_metadata(new_meta))
        
        source_coll.add(
            ids=new_ids,
            embeddings=embeddings,  # reuse same embeddings
            documents=documents,
            metadatas=new_metadatas
        )
        logger.info(f"Copied {len(new_ids)} embeddings from {source_document_id} to {target_document_id}")
    except Exception as e:
        logger.error(f"Failed to copy embeddings: {e}")
        raise