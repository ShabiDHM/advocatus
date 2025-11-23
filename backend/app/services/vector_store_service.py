# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - COMPLETED PIPELINE
# 1. ADDED: 'create_and_store_embeddings_from_chunks' to handle batch indexing.
# 2. FIXED: 'chroma' host configuration to work in Docker.

import os
import time
import logging
from typing import List, Dict, Optional, Any, Sequence, cast
import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.types import Metadata

logger = logging.getLogger(__name__)

# --- SMART CONFIGURATION ---
CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")

# If internal docker 'chroma', use 8000. If external/local, usually 8000 or 8002.
if CHROMA_HOST == "chroma":
    CHROMA_PORT = 8000
else:
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
    
    if _user_collection and _kb_collection and _client: 
        return

    if not CHROMA_HOST:
        logger.critical("CHROMA_HOST is missing.")
        return 

    retries = 5
    while retries > 0:
        try:
            if not _client:
                logger.info(f"🔌 Connecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}...")
                _client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
                _client.heartbeat()
            
            # 1. Connect User Collection
            if not _user_collection:
                _user_collection = _client.get_or_create_collection(name=USER_COLLECTION_NAME)
                logger.info("✅ Connected to User Documents Collection.")
            
            # 2. Connect Knowledge Base
            if not _kb_collection:
                try:
                    _kb_collection = _client.get_or_create_collection(name=KB_COLLECTION_NAME)
                    logger.info("✅ Connected to Legal Knowledge Base.")
                except Exception as e:
                    logger.warning(f"⚠️ KB Connection Warning: {e}")

            if _user_collection and _kb_collection:
                return

        except Exception as e:
            retries -= 1
            logger.warning(f"ChromaDB connection error: {e}. Retrying... ({retries} left)")
            time.sleep(5)
            
    if not _user_collection:
        logger.critical("❌ Failed to connect to User Collection.")

def get_user_collection() -> Collection:
    if _user_collection is None:
        connect_chroma_db()
        if _user_collection is None:
            raise ConnectionError("Failed to establish ChromaDB User connection.")
    return _user_collection

def get_kb_collection() -> Optional[Collection]:
    if _kb_collection is None:
        connect_chroma_db()
    return _kb_collection

# --- KNOWLEDGE BASE QUERY ---
def query_legal_knowledge_base(embedding: List[float], n_results: int = 5) -> List[Dict[str, Any]]:
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
        
        if not docs_list or not docs_list[0]: return []
        
        found_docs = docs_list[0]
        found_metas = metas_list[0] if (metas_list and metas_list[0]) else [None] * len(found_docs)
        
        return [
            { 
                "text": doc, 
                "document_name": (meta or {}).get("source", "Ligj i Panjohur"), 
                "type": "LAW" 
            }
            for doc, meta in zip(found_docs, found_metas) if doc
        ]
    except Exception as e:
        logger.error(f"❌ Error querying Knowledge Base: {e}")
        return []

# --- USER DOCUMENT OPERATIONS (THE FIX) ---

def create_and_store_embeddings_from_chunks(
    document_id: str, case_id: str, chunks: List[str], metadatas: Sequence[Dict[str, Any]]
) -> bool:
    """
    Generates embeddings for a batch of text chunks and stores them in ChromaDB.
    """
    # Import inside function to avoid circular dependency
    from . import embedding_service
    
    collection = get_user_collection()
    document_id_str, case_id_str = str(document_id), str(case_id)
    
    embeddings = []
    # 1. Generate Embeddings (Calls AI Core or Local Model)
    for i, chunk in enumerate(chunks):
        try:
            # Ensure metadata has file_name
            if 'file_name' not in metadatas[i]: 
                metadatas[i]['file_name'] = "Unknown Document"
                
            embedding = embedding_service.generate_embedding(chunk, language=metadatas[i].get('language'))
            if embedding:
                embeddings.append(embedding)
            else:
                logger.error(f"Embedding generation returned None for chunk {i}")
                return False
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return False 
            
    if not embeddings:
        return False

    # 2. Store in ChromaDB
    ids = [f"{document_id_str}_{int(time.time())}_{i}" for i in range(len(chunks))]
    
    # Cast metadata to match ChromaDB requirements
    final_metadatas_list: List[Metadata] = [
        cast(Metadata, {
            **meta, 
            'source_document_id': document_id_str, 
            'case_id': case_id_str
        })
        for meta in metadatas
    ]
    
    total_chunks = len(chunks)
    # Batch write to DB
    for i in range(0, total_chunks, VECTOR_WRITE_BATCH_SIZE):
        end = min(i + VECTOR_WRITE_BATCH_SIZE, total_chunks)
        try:
            collection.add(
                embeddings=embeddings[i:end], 
                documents=chunks[i:end], 
                metadatas=final_metadatas_list[i:end], 
                ids=ids[i:end]
            )
        except Exception as e:
            logger.error(f"Failed to store batch in ChromaDB: {e}")
            return False
            
    logger.info(f"✅ Successfully indexed {len(chunks)} chunks for document {document_id_str}")
    return True 

def ensure_string_id(value: Any) -> str: return str(value)

def query_by_vector(
    embedding: List[float], case_id: str, n_results: int = 15, document_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    collection = get_user_collection()
    where_filter: Dict[str, Any] = {"case_id": {"$eq": ensure_string_id(case_id)}}
    
    if document_ids:
        # If specific documents are selected, filter by their IDs
        where_filter = { 
            "$and": [ 
                {"case_id": {"$eq": ensure_string_id(case_id)}}, 
                {"source_document_id": {"$in": document_ids}} 
            ] 
        }

    try:
        results = collection.query(
            query_embeddings=[embedding], 
            n_results=n_results, 
            where=where_filter, 
            include=["documents", "metadatas"]
        )
        
        if not results: return []
        docs = results.get('documents')
        metas = results.get('metadatas')
        
        if not docs or not metas or not docs[0] or not metas[0]: return []
        
        return [
            { 
                "text": doc, 
                "document_id": meta.get("source_document_id"), 
                "document_name": meta.get("file_name"),
                "type": "DOKUMENT"
            }
            for doc, meta in zip(docs[0], metas[0]) if meta
        ]
    except Exception as e:
        logger.error(f"Error querying User Docs: {e}")
        return []

def delete_document_embeddings(document_id: str):
    collection = get_user_collection()
    try:
        collection.delete(where={"source_document_id": ensure_string_id(document_id)})
        logger.info(f"Deleted embeddings for document {document_id}")
    except Exception as e:
        logger.error(f"Error deleting embeddings: {e}")
        raise