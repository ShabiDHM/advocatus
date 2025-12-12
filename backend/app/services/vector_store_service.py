# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - VECTOR STORE V8.0 (TOTAL RECALL DELETE)
# 1. FIX: 'delete_document_embeddings' now wipes data from BOTH User Chunks and Findings Collections.
# 2. LOGIC: Ensures zero residue remains in ChromaDB after document deletion.
# 3. SAFETY: Wrapped in robust try-catch blocks to prevent crashes during cleanup.

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
                logger.info("✅ Connected to all ChromaDB Collections.")
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

def get_findings_collection() -> Collection:
    if _findings_collection is None: connect_chroma_db()
    return _findings_collection # type: ignore

# --- FINDINGS OPERATIONS ---

def store_structured_findings(findings: List[Dict[str, Any]]) -> bool:
    """
    Takes a list of finding objects, generates embeddings, and saves them to ChromaDB.
    """
    from . import embedding_service
    collection = get_findings_collection()
    
    embeddings = []
    documents = []
    metadatas = []
    ids = []

    for f in findings:
        text = f.get("finding_text", "")
        if not text: continue
        
        # Create embedding for the fact
        emb = embedding_service.generate_embedding(text)
        if not emb: continue
        
        embeddings.append(emb)
        documents.append(text)
        
        # Metadata for filtering
        metadatas.append({
            "case_id": str(f.get("case_id")),
            "document_id": str(f.get("document_id")),
            "category": f.get("category", "FAKT"),
            "document_name": f.get("document_name", "N/A")
        })
        
        # Unique ID
        ids.append(f"find_{f.get('document_id')}_{int(time.time())}_{len(ids)}")

    if not ids: return False

    try:
        collection.add(embeddings=embeddings, documents=documents, metadatas=metadatas, ids=ids) # type: ignore
        logger.info(f"✅ Stored {len(ids)} findings in Vector DB.")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to store findings in Vector DB: {e}")
        return False

def query_findings_by_similarity(case_id: str, embedding: List[float], n_results: int = 10) -> List[Dict[str, Any]]:
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
    for i, chunk in enumerate(chunks):
        emb = embedding_service.generate_embedding(chunk, language=metadatas[i].get('language'))
        if emb: embeddings.append(emb)
    
    if not embeddings: return False
    ids = [f"{document_id}_{int(time.time())}_{i}" for i in range(len(chunks))]
    final_metadatas = [{**meta, 'source_document_id': str(document_id), 'case_id': str(case_id), 'file_name': file_name} for meta in metadatas] # type: ignore
    
    try:
        collection.add(embeddings=embeddings, documents=chunks, metadatas=final_metadatas, ids=ids) # type: ignore
        return True
    except Exception as e:
        logger.error(f"Batch Add Failed: {e}")
        return False

def query_by_vector(embedding: List[float], case_id: str, n_results: int = 15, document_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    collection = get_user_collection()
    where_filter = {"case_id": {"$eq": str(case_id)}}
    if document_ids:
        where_filter = {"$and": [{"case_id": {"$eq": str(case_id)}}, {"source_document_id": {"$in": [str(d) for d in document_ids]}}]} # type: ignore

    try:
        results = collection.query(query_embeddings=[embedding], n_results=n_results, where=cast(Where, where_filter), include=["documents", "metadatas"])
        if not results or not results.get('documents') or not results.get('documents')[0]: return [] # type: ignore
        docs = results['documents'][0] # type: ignore
        metas = results['metadatas'][0] if results.get('metadatas') else [{}] * len(docs) # type: ignore
        return [{"text": d, "document_name": (m or {}).get("file_name"), "type": "DOKUMENT"} for d, m in zip(docs, metas)]
    except Exception: return []

# --- CLEANUP OPERATIONS (V8.0 Upgrade) ---

def delete_document_embeddings(document_id: str):
    """
    Deletes ALL traces of a document from the Vector Store:
    1. The raw text chunks (User Collection).
    2. The extracted findings/facts (Findings Collection).
    """
    doc_id_str = str(document_id)
    
    # 1. Delete Raw Text Chunks
    try: 
        get_user_collection().delete(where={"source_document_id": doc_id_str})
        logger.info(f"🗑️ Deleted Vector Chunks for Doc: {doc_id_str}")
    except Exception as e: 
        logger.warning(f"Failed to delete user chunks for {doc_id_str}: {e}")

    # 2. Delete Extracted Findings (PHOENIX UPGRADE)
    try:
        get_findings_collection().delete(where={"document_id": doc_id_str})
        logger.info(f"🗑️ Deleted Vector Findings for Doc: {doc_id_str}")
    except Exception as e:
        logger.warning(f"Failed to delete findings chunks for {doc_id_str}: {e}")