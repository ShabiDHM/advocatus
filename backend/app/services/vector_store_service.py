# FILE: /app/app/services/vector_store_service.py
# PHOENIX PROTOCOL - DUAL RAG ENABLED
# 1. ADDED: Robust Metadata Handling for KB.
# 2. ADDED: Collection Count Logging for diagnostics.

import os
import time
import logging
from typing import List, Dict, Optional, Any, Sequence, cast
import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.types import Metadata

logger = logging.getLogger(__name__)

CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))

# Collections
USER_COLLECTION_NAME = "advocatus_phoenix_documents"
KB_COLLECTION_NAME = "legal_knowledge_base"

_client: Optional[ClientAPI] = None
_user_collection: Optional[Collection] = None
_kb_collection: Optional[Collection] = None

VECTOR_WRITE_BATCH_SIZE = 64

def connect_chroma_db():
    global _client, _user_collection, _kb_collection
    if _user_collection and _client: return

    if not CHROMA_HOST or not CHROMA_PORT:
        logger.critical("CHROMA_HOST or CHROMA_PORT is missing.")
        return 

    retries = 5
    while retries > 0:
        try:
            _client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
            _client.heartbeat()
            
            # 1. User Documents Collection
            _user_collection = _client.get_or_create_collection(name=USER_COLLECTION_NAME)
            
            # 2. Legal Knowledge Base Collection
            try:
                _kb_collection = _client.get_or_create_collection(name=KB_COLLECTION_NAME)
                # Diagnostic: Check if KB is empty
                kb_count = _kb_collection.count()
                logger.info(f"✅ Connected to Legal Knowledge Base. Documents available: {kb_count}")
                if kb_count == 0:
                    logger.warning("⚠️ Legal Knowledge Base is empty! RAG will not find laws.")
            except Exception as e:
                logger.warning(f"⚠️ Could not connect to KB Collection: {e}")

            logger.info("✅ Successfully connected to ChromaDB User Collection.")
            return
        except Exception as e:
            retries -= 1
            logger.warning(f"ChromaDB connection error: {e}. Retrying... ({retries} left)")
            time.sleep(5)
            
    logger.critical("❌ Could not connect to ChromaDB after all retries.")
    _client = None
    _user_collection = None

def get_user_collection() -> Collection:
    if _user_collection is None:
        connect_chroma_db()
        if _user_collection is None:
            raise ConnectionError("Failed to establish ChromaDB User connection.")
    return _user_collection

def get_kb_collection() -> Optional[Collection]:
    """Returns the Knowledge Base collection if available."""
    if _kb_collection is None:
        connect_chroma_db()
    return _kb_collection

# --- KNOWLEDGE BASE QUERY ---
def query_legal_knowledge_base(embedding: List[float], n_results: int = 5) -> List[Dict[str, Any]]:
    """
    Searches the Global Legal Knowledge Base (Laws, Codes).
    Robustly handles missing metadata.
    """
    kb = get_kb_collection()
    if not kb:
        return []
        
    try:
        results = kb.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas"]
        )
        
        if not results: return []
        
        docs_list = results.get('documents')
        metas_list = results.get('metadatas')
        
        # Check if we got any documents back
        if not docs_list or not docs_list[0]: 
            return []
            
        found_docs = docs_list[0]
        
        # Handle case where metadatas might be None or the list inside might be None
        # If metas_list is None or metas_list[0] is None, create a list of empty dicts or None
        found_metas = []
        if metas_list and metas_list[0]:
            found_metas = metas_list[0]
        else:
            # Fill with None so zip still works
            found_metas = [None] * len(found_docs)
        
        response = []
        for doc, meta in zip(found_docs, found_metas):
            if doc: # Ensure doc text exists
                safe_meta = meta or {}
                response.append({
                    "text": doc,
                    "document_name": safe_meta.get("source", "Ligj i Panjohur"),
                    "type": "LAW"
                })
        
        return response

    except Exception as e:
        logger.error(f"❌ Error querying Knowledge Base: {e}")
        return []

# --- USER DOCUMENT OPERATIONS (Existing Logic) ---

def create_and_store_embeddings_from_chunks(
    document_id: str, case_id: str, chunks: List[str], metadatas: Sequence[Dict[str, Any]]
) -> bool:
    from . import embedding_service
    collection = get_user_collection()
    document_id_str, case_id_str = str(document_id), str(case_id)
    
    embeddings = []
    for i, chunk in enumerate(chunks):
        try:
            if 'file_name' not in metadatas[i]: metadatas[i]['file_name'] = "Unknown Document"
            embedding = embedding_service.generate_embedding(chunk, language=metadatas[i].get('language'))
            embeddings.append(embedding)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return False 
            
    ids = [f"{document_id_str}_{i}" for i in range(len(chunks))]
    final_metadatas_list: List[Metadata] = [
        cast(Metadata, {**meta, 'source_document_id': document_id_str, 'case_id': case_id_str})
        for meta in metadatas
    ]
    
    total_chunks = len(chunks)
    for i in range(0, total_chunks, VECTOR_WRITE_BATCH_SIZE):
        end = min(i + VECTOR_WRITE_BATCH_SIZE, total_chunks)
        try:
            collection.add(
                embeddings=embeddings[i:end], documents=chunks[i:end], 
                metadatas=final_metadatas_list[i:end], ids=ids[i:end]
            )
        except Exception as e:
            logger.error(f"Failed to store batch: {e}")
            return False
            
    return True 

def ensure_string_id(value: Any) -> str: return str(value)

def query_by_vector(
    embedding: List[float], case_id: str, n_results: int = 15, document_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    collection = get_user_collection()
    where_filter: Dict[str, Any] = {"case_id": {"$eq": ensure_string_id(case_id)}}
    if document_ids:
        where_filter = { "$and": [ where_filter, {"source_document_id": {"$in": document_ids}} ] }
    try:
        results = collection.query(
            query_embeddings=[embedding], n_results=n_results, where=where_filter, include=["documents", "metadatas"]
        )
        if not results: return []
        docs = results.get('documents')
        metas = results.get('metadatas')
        if not docs or not metas or not docs[0] or not metas[0]: return []
        
        return [
            { "text": doc, "document_id": meta.get("source_document_id"), "document_name": meta.get("file_name") }
            for doc, meta in zip(docs[0], metas[0]) if meta
        ]
    except Exception as e:
        logger.error(f"Error querying User Docs: {e}")
        return []

def delete_document_embeddings(document_id: str):
    collection = get_user_collection()
    try:
        collection.delete(where={"source_document_id": ensure_string_id(document_id)})
    except Exception as e:
        logger.error(f"Error deleting embeddings: {e}")
        raise