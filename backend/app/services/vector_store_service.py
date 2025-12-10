# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - VECTOR STORE V7.1 (NULL SAFETY)
# 1. FIX: Added robust 'None' and 'empty list' checks to all query functions.
# 2. STATUS: Resolves the "Object of type None is not subscriptable" Pylance error.
# 3. ROBUSTNESS: Service is now resilient to empty or malformed ChromaDB query results.

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
FINDINGS_COLLECTION_NAME = "advocatus_findings"

_client: Optional[ClientAPI] = None
_user_collection: Optional[Collection] = None
_kb_collection: Optional[Collection] = None
_findings_collection: Optional[Collection] = None

VECTOR_WRITE_BATCH_SIZE = 64

def connect_chroma_db():
    global _client, _user_collection, _kb_collection, _findings_collection
    if _user_collection and _kb_collection and _findings_collection: return

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
            if not _findings_collection:
                _findings_collection = _client.get_or_create_collection(name=FINDINGS_COLLECTION_NAME)
            
            if _user_collection and _kb_collection and _findings_collection:
                logger.info("✅ Connected to all ChromaDB Collections (Users, KB, Findings).")
                return
        except Exception as e:
            retries -= 1
            logger.warning(f"ChromaDB connection error: {e}. Retrying... ({retries} left)")
            time.sleep(5)
            
    logger.critical("❌ Failed to connect to one or more ChromaDB collections.")

def get_user_collection() -> Collection:
    if _user_collection is None:
        connect_chroma_db()
        if _user_collection is None: raise ConnectionError("ChromaDB User connection failed.")
    return _user_collection

def get_kb_collection() -> Optional[Collection]:
    if _kb_collection is None:
        connect_chroma_db()
    return _kb_collection

def get_findings_collection() -> Collection:
    if _findings_collection is None:
        connect_chroma_db()
        if _findings_collection is None: raise ConnectionError("ChromaDB Findings connection failed.")
    return _findings_collection

# --- KNOWLEDGE BASE QUERY (STRICT KOSOVO) ---
def query_legal_knowledge_base(embedding: List[float], n_results: int = 5, jurisdiction: str = 'ks') -> List[Dict[str, Any]]:
    kb = get_kb_collection()
    if not kb: return []
    
    forced_jurisdiction = 'ks'
    where_filter: Dict[str, Any] = {"jurisdiction": {"$eq": forced_jurisdiction}}
    
    try:
        results = kb.query(
            query_embeddings=[embedding], n_results=n_results,
            where=cast(Where, where_filter), include=["documents", "metadatas"]
        )
        if not results: return []
        
        docs_list_outer = results.get('documents')
        metas_list_outer = results.get('metadatas')

        if not docs_list_outer or not docs_list_outer[0]: return []
        docs_list = docs_list_outer[0]

        # PHOENIX FIX: Robustly handle None or empty metas
        metas_list = metas_list_outer[0] if metas_list_outer and metas_list_outer[0] else [{}] * len(docs_list)
        
        return [
            {"text": doc, "document_name": (meta or {}).get("source", "Ligj i Kosovës"), "type": "LAW"}
            for doc, meta in zip(docs_list, metas_list) if doc
        ]
    except Exception as e:
        logger.error(f"❌ KB Query Error: {e}")
        return []

# --- FINDINGS QUERY (FOR PRECISION DRAFTING) ---
def query_findings_by_similarity(
    case_id: str, embedding: List[float], n_results: int = 10
) -> List[Dict[str, Any]]:
    collection = get_findings_collection()
    where_filter = {"case_id": {"$eq": str(case_id)}}
    
    try:
        results = collection.query(
            query_embeddings=[embedding], n_results=n_results,
            where=cast(Where, where_filter), include=["documents", "metadatas"]
        )
        if not results: return []
            
        docs_outer = results.get('documents')
        metas_outer = results.get('metadatas')

        if not docs_outer or not docs_outer[0]: return []
        docs = docs_outer[0]
        
        # PHOENIX FIX: This is the critical null-safety check for the Pylance error.
        metas = metas_outer[0] if metas_outer and metas_outer[0] else [{}] * len(docs)

        return [
            {
                "finding_text": doc,
                "category": (meta or {}).get("category", "FAKT"),
                "source_document_name": (meta or {}).get("document_name", "N/A"),
            }
            for doc, meta in zip(docs, metas) if doc
        ]
    except Exception as e:
        logger.error(f"❌ Findings Similarity Query Error: {e}")
        return []

# --- USER DOCUMENT OPERATIONS ---
def create_and_store_embeddings_from_chunks(
    document_id: str, case_id: str, file_name: str, 
    chunks: List[str], metadatas: Sequence[Dict[str, Any]]
) -> bool:
    from . import embedding_service
    
    collection = get_user_collection()
    embeddings = []
    
    for i, chunk in enumerate(chunks):
        try:
            embedding = embedding_service.generate_embedding(chunk, language=metadatas[i].get('language'))
            if embedding: embeddings.append(embedding)
        except Exception:
            return False
            
    if not embeddings: return False

    ids = [f"{document_id}_{int(time.time())}_{i}" for i in range(len(chunks))]
    
    final_metadatas: List[Metadata] = [
        cast(Metadata, {
            **meta, 'source_document_id': str(document_id), 
            'case_id': str(case_id), 'file_name': file_name 
        }) for meta in metadatas
    ]
    
    for i in range(0, len(chunks), VECTOR_WRITE_BATCH_SIZE):
        end = min(i + VECTOR_WRITE_BATCH_SIZE, len(chunks))
        try:
            collection.add(
                embeddings=embeddings[i:end], documents=chunks[i:end], 
                metadatas=final_metadatas[i:end], ids=ids[i:end]
            )
        except Exception as e:
            logger.error(f"ChromaDB Batch Add Failed: {e}")
            return False
    return True 

def ensure_string_id(value: Any) -> str: return str(value)

def query_by_vector(
    embedding: List[float], case_id: str, n_results: int = 15, document_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    collection = get_user_collection()
    
    if document_ids:
        str_doc_ids = [ensure_string_id(doc_id) for doc_id in document_ids]
        where_filter: Dict[str, Any] = {
            "$and": [{"case_id": {"$eq": ensure_string_id(case_id)}}, {"source_document_id": {"$in": str_doc_ids}}]
        }
    else:
        where_filter = {"case_id": {"$eq": ensure_string_id(case_id)}}

    logger.info(f"🔎 ChromaDB Query Filter: {where_filter}")
    
    try:
        results = collection.query(
            query_embeddings=[embedding], n_results=n_results, 
            where=cast(Where, where_filter), include=["documents", "metadatas"]
        )
        if not results: return []

        docs_outer = results.get('documents')
        metas_outer = results.get('metadatas')
        
        if not docs_outer or not docs_outer[0]: return []
        docs = docs_outer[0]
        
        # PHOENIX FIX: Robustly handle None or empty metas
        metas = metas_outer[0] if metas_outer and metas_outer[0] else [{}] * len(docs)
        
        return [
            { 
                "text": doc, "document_id": (meta or {}).get("source_document_id"), 
                "document_name": (meta or {}).get("file_name"), "type": "DOKUMENT"
            } for doc, meta in zip(docs, metas) if meta
        ]
    except Exception as e:
        logger.error(f"User Docs Query Error: {e}")
        return []

def delete_document_embeddings(document_id: str):
    collection = get_user_collection()
    try:
        collection.delete(where={"source_document_id": ensure_string_id(document_id)})
    except Exception as e:
        logger.error(f"Embedding Deletion Error: {e}")
        raise