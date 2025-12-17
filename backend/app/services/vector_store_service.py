# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - VECTOR STORE V9.0 (SOURCE AWARE + FINDINGS REMOVED)
# 1. REMOVED: Findings Collection and all related logic.
# 2. UPGRADE: Source Injection ([[BURIMI: ...]]) for better context distinction.
# 3. STATUS: Optimized for Multi-Document RAG.

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

USER_COLLECTION_NAME = "advocatus_phoenix_documents"
KB_COLLECTION_NAME = "legal_knowledge_base"

_client: Optional[ClientAPI] = None
_user_collection: Optional[Collection] = None
_kb_collection: Optional[Collection] = None

VECTOR_WRITE_BATCH_SIZE = 64

def connect_chroma_db():
    global _client, _user_collection, _kb_collection
    if _user_collection and _kb_collection: return

    retries = 5
    while retries > 0:
        try:
            if not _client:
                _client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
                _client.heartbeat()
            if not _user_collection:
                _user_collection = _client.get_or_create_collection(name=USER_COLLECTION_NAME)
            if not _kb_collection:
                _kb_collection = _client.get_or_create_collection(name=KB_COLLECTION_NAME)
            
            if _user_collection and _kb_collection:
                logger.info("✅ Connected to User & KB Collections.")
                return
        except Exception as e:
            retries -= 1
            logger.warning(f"ChromaDB connection error: {e}. Retrying... ({retries} left)")
            time.sleep(5)
            
    logger.critical("❌ Failed to connect to ChromaDB.")

def get_user_collection() -> Collection:
    if _user_collection is None: connect_chroma_db()
    return _user_collection # type: ignore

def get_kb_collection() -> Collection:
    if _kb_collection is None: connect_chroma_db()
    return _kb_collection # type: ignore

# --- STANDARD OPERATIONS ---

def query_legal_knowledge_base(embedding: List[float], n_results: int = 5, jurisdiction: str = 'ks') -> List[Dict[str, Any]]:
    kb = get_kb_collection()
    try:
        results = kb.query(
            query_embeddings=[embedding], n_results=n_results,
            where={"jurisdiction": {"$eq": 'ks'}}, include=["documents", "metadatas"] # type: ignore
        )
        if not results or not results.get('documents') or not results.get('documents')[0]: return [] # type: ignore
        
        docs = results['documents'][0] # type: ignore
        metas = results['metadatas'][0] if results.get('metadatas') else [{}] * len(docs) # type: ignore
        
        return [{"text": d, "document_name": (m or {}).get("source", "Ligj"), "type": "LAW"} for d, m in zip(docs, metas)]
    except Exception as e:
        logger.error(f"KB Query Error: {e}")
        return []

def create_and_store_embeddings_from_chunks(document_id: str, case_id: str, file_name: str, chunks: List[str], metadatas: Sequence[Dict[str, Any]]) -> bool:
    from . import embedding_service
    collection = get_user_collection()
    
    embeddings = []
    processed_chunks = []
    
    # PHOENIX UPGRADE: Source Injection
    # We prepend the filename to the chunk text so the LLM always knows the source.
    source_tag = f"[[BURIMI: {file_name}]] "
    
    for i, chunk in enumerate(chunks):
        # Add tag to text content
        tagged_chunk = f"{source_tag}{chunk}"
        processed_chunks.append(tagged_chunk)
        
        # Generate embedding on the TAGGED chunk for better context separation
        emb = embedding_service.generate_embedding(tagged_chunk, language=metadatas[i].get('language'))
        if emb: embeddings.append(emb)
    
    if not embeddings: return False
    
    ids = [f"{document_id}_{int(time.time())}_{i}" for i in range(len(processed_chunks))]
    final_metadatas = [{**meta, 'source_document_id': str(document_id), 'case_id': str(case_id), 'file_name': file_name} for meta in metadatas] # type: ignore
    
    try:
        collection.add(embeddings=embeddings, documents=processed_chunks, metadatas=final_metadatas, ids=ids) # type: ignore
        return True
    except Exception as e:
        logger.error(f"Batch Add Failed: {e}")
        return False

def query_by_vector(embedding: List[float], case_id: str, n_results: int = 15, document_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    collection = get_user_collection()
    where_filter = {"case_id": {"$eq": str(case_id)}}
    
    # Support for Specific Document Filtering
    if document_ids:
        if len(document_ids) == 1:
             where_filter = {"$and": [{"case_id": {"$eq": str(case_id)}}, {"source_document_id": {"$eq": str(document_ids[0])}}]} # type: ignore
        else:
             where_filter = {"$and": [{"case_id": {"$eq": str(case_id)}}, {"source_document_id": {"$in": [str(d) for d in document_ids]}}]} # type: ignore

    try:
        results = collection.query(query_embeddings=[embedding], n_results=n_results, where=cast(Where, where_filter), include=["documents", "metadatas"])
        if not results or not results.get('documents') or not results.get('documents')[0]: return [] # type: ignore
        docs = results['documents'][0] # type: ignore
        metas = results['metadatas'][0] if results.get('metadatas') else [{}] * len(docs) # type: ignore
        return [{"text": d, "document_name": (m or {}).get("file_name"), "type": "DOKUMENT"} for d, m in zip(docs, metas)]
    except Exception: return []

# --- CLEANUP OPERATIONS ---

def delete_document_embeddings(document_id: str):
    """
    Deletes vectors for a specific document.
    """
    doc_id_str = str(document_id)
    try: 
        get_user_collection().delete(where={"source_document_id": doc_id_str})
        logger.info(f"🗑️ Deleted Vector Chunks for Doc: {doc_id_str}")
    except Exception as e: 
        logger.warning(f"Failed to delete user chunks for {doc_id_str}: {e}")