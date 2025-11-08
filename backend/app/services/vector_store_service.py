# FILE: /app/app/services/vector_store_service.py
# DEFINITIVE VERSION 6.4 (LINTED & FINAL): Corrected all "None is not subscriptable" errors.

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
COLLECTION_NAME = "advocatus_phoenix_documents"
_client: Optional[ClientAPI] = None
_collection: Optional[Collection] = None

VECTOR_WRITE_BATCH_SIZE = 64

def connect_chroma_db():
    global _client, _collection
    if _collection and _client: return
    if not CHROMA_HOST or not CHROMA_PORT:
        logger.critical(f"CHROMA_HOST or CHROMA_PORT is missing.")
        return 
    retries = 5
    while retries > 0:
        try:
            _client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
            _client.heartbeat()
            _collection = _client.get_or_create_collection(name=COLLECTION_NAME)
            logger.info("Successfully connected to ChromaDB.")
            return
        except Exception as e:
            retries -= 1
            logger.warning(f"ChromaDB connection error: {e}. Retrying... ({retries} left)")
            time.sleep(5)
    logger.critical("Could not connect to ChromaDB after all retries.")
    _client = None
    _collection = None

def get_collection() -> Collection:
    if _collection is None:
        connect_chroma_db()
        if _collection is None:
            raise ConnectionError("Failed to establish a ChromaDB collection connection.")
    return _collection

def create_and_store_embeddings_from_chunks(
    document_id: str, case_id: str, chunks: List[str], metadatas: Sequence[Dict[str, Any]]
) -> bool:
    from . import embedding_service
    collection = get_collection()
    document_id_str, case_id_str = str(document_id), str(case_id)
    if len(metadatas) != len(chunks): raise ValueError("Mismatch between chunks and metadatas count.")
    embeddings = []
    for i, chunk in enumerate(chunks):
        try:
            if 'file_name' not in metadatas[i]: metadatas[i]['file_name'] = "Unknown Document"
            embedding = embedding_service.generate_embedding(chunk, language=metadatas[i].get('language'))
            embeddings.append(embedding)
        except Exception as e:
            logger.error(f"Failed to generate embedding for chunk in document {document_id_str}: {e}")
            return False 
    if len(embeddings) != len(chunks): raise ValueError("Mismatch between embeddings and chunks count.")
    ids = [f"{document_id_str}_{i}" for i in range(len(chunks))]
    final_metadatas_list: List[Metadata] = [
        cast(Metadata, {**meta, 'source_document_id': document_id_str, 'case_id': case_id_str})
        for meta in metadatas
    ]
    total_chunks = len(chunks)
    for i in range(0, total_chunks, VECTOR_WRITE_BATCH_SIZE):
        end = min(i + VECTOR_WRITE_BATCH_SIZE, total_chunks)
        for attempt in range(3):
            try:
                collection.add(
                    embeddings=embeddings[i:end], documents=chunks[i:end], 
                    metadatas=final_metadatas_list[i:end], ids=ids[i:end]
                )
                break
            except Exception as e:
                logger.warning(f"Failed to store batch (Attempt {attempt+1}/3): {e}")
                if attempt == 2:
                    logger.error(f"CRITICAL: Failed to store batch for document {document_id_str}.")
                    return False
                time.sleep(2)
    logger.info(f"All {total_chunks} embeddings stored for document {document_id_str}.")
    return True 

def ensure_string_id(value: Any) -> str: return str(value)

def query_by_vector(
    embedding: List[float], case_id: str, n_results: int = 15, document_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    collection = get_collection()
    where_filter: Dict[str, Any] = {"case_id": {"$eq": ensure_string_id(case_id)}}
    if document_ids:
        where_filter = { "$and": [ where_filter, {"source_document_id": {"$in": document_ids}} ] }
    try:
        results = collection.query(
            query_embeddings=[embedding], n_results=n_results, where=where_filter, include=["documents", "metadatas"]
        )
        # --- DEFINITIVE FIX for "None is not subscriptable" on lines 145, 146 ---
        if not results: return []
        docs = results.get('documents')
        metas = results.get('metadatas')
        if not docs or not metas or not docs[0] or not metas[0]: return []
        # --- END FIX ---
        return [
            { "text": doc, "document_id": meta.get("source_document_id"), "document_name": meta.get("file_name") }
            for doc, meta in zip(docs[0], metas[0]) if meta
        ]
    except Exception as e:
        logger.error(f"Error querying ChromaDB with filter {where_filter}: {e}")
        return []

def delete_document_embeddings(document_id: str):
    collection = get_collection()
    try:
        collection.delete(where={"source_document_id": ensure_string_id(document_id)})
        logger.info(f"Successfully deleted embeddings for document: {ensure_string_id(document_id)}")
    except Exception as e:
        logger.error(f"Error deleting embeddings for document {ensure_string_id(document_id)}: {e}")
        raise

def store_document_embedding(document_id: Any, case_id: Any, embedding: List[float], text_chunk: str):
    collection = get_collection()
    doc_id_str, case_id_str = ensure_string_id(document_id), ensure_string_id(case_id)
    metadata: Metadata = {"source_document_id": doc_id_str, "case_id": case_id_str}
    chunk_id = f"{doc_id_str}_{hash(text_chunk)}"
    for attempt in range(3):
        try:
            collection.add(embeddings=[embedding], documents=[text_chunk], metadatas=[metadata], ids=[chunk_id])
            break
        except Exception as e:
            logger.warning(f"Failed to store single embedding (Attempt {attempt+1}/3): {e}")
            if attempt == 2: raise
            time.sleep(1)

def query_across_cases(
    embedding: List[float], case_ids: List[str], n_results: int = 10
) -> List[Dict[str, Any]]:
    collection = get_collection()
    if not case_ids: return []
    where_filter: Dict[str, Any] = {"case_id": {"$in": case_ids}}
    try:
        results = collection.query(
            query_embeddings=[embedding], n_results=n_results, where=where_filter, 
            include=["documents", "metadatas", "distances"]
        )
        if not results: return []
        docs = results.get('documents')
        metas = results.get('metadatas')
        distances = results.get('distances')
        if not docs or not metas or not distances or not docs[0] or not metas[0] or not distances[0]: return []
        formatted_results = []
        for doc_text, meta, dist in zip(docs[0], metas[0], distances[0]):
            if not meta: continue
            doc_id = str(meta.get("source_document_id", ""))
            if not doc_id: continue
            formatted_results.append({
                "document_id": doc_id, "case_id": meta.get("case_id"), "file_name": meta.get('file_name', 'Unknown'),
                "score": 1 - (dist or 0.0), "text_chunk": doc_text
            })
        return formatted_results
    except Exception as e:
        logger.error(f"Error querying ChromaDB across cases with filter {where_filter}: {e}")
        return []