# FILE: backend/app/services/document_processing_service.py
# DEFINITIVE VERSION 4.4 (PHOENIX PROTOCOL: CRITICAL RAG INDEXING METADATA FIX)
# 1. CRITICAL FIX: Added 'file_name' from the MongoDB document to the base_doc_metadata.
#    This ensures the document name is indexed in the vector store, allowing the RAG service to 
#    cite the source and preventing the LLM from defaulting to the "no information" response.
# 2. Corrected a minor potential issue where 'user_id' was not present in the document metadata for the storage service call.

import os
import tempfile
import logging
from pymongo.database import Database
import redis
from bson import ObjectId
from typing import List, Tuple, Dict, Any

from langchain.text_splitter import RecursiveCharacterTextSplitter

from . import document_service, storage_service, vector_store_service, llm_service, text_extraction_service
from ..tasks.deadline_extraction import extract_deadlines_from_document
from ..tasks.findings_extraction import extract_findings_from_document

ALBANIAN_PROCESSOR_AVAILABLE = False
language_detector = None
document_processor = None

logger = logging.getLogger(__name__)

class DocumentNotFoundInDBError(Exception):
    pass

def _process_and_split_text(full_text: str, document_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Simplified chunking logic for clarity and robustness
    base_metadata = document_metadata.copy()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, length_function=len)
    text_chunks = text_splitter.split_text(full_text)
    
    return [
        {'content': chunk, 'metadata': {**base_metadata, 'chunk_index': i}}
        for i, chunk in enumerate(text_chunks)
    ]

def orchestrate_document_processing_mongo(
    db: Database,
    redis_client: redis.Redis,
    document_id_str: str
):
    try:
        doc_id = ObjectId(document_id_str)
    except Exception:
        logger.error(f"Invalid Document ID format: {document_id_str}.")
        return

    document = db.documents.find_one({"_id": doc_id})
    if not document:
        raise DocumentNotFoundInDBError(f"Document with ID {document_id_str} not found.")

    temp_file_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(document.get("file_name", ""))[1]) as temp_file:
            temp_file_path = temp_file.name
        
        storage_service.download_original_document(document["storage_key"], temp_file_path)
        extracted_text = text_extraction_service.extract_text(temp_file_path, document.get("mime_type", ""))
        if not extracted_text or not extracted_text.strip():
            raise ValueError("Text extraction returned no content.")

        # CRITICAL FIX: Add 'file_name' to base_doc_metadata for RAG retrieval and citation
        base_doc_metadata = {
            'document_id': document_id_str,
            'case_id': str(document.get("case_id")),
            'user_id': str(document.get("owner_id")), # owner_id is the user_id in documents collection
            'file_name': document.get("file_name", "Dokument i Paidentifikuar"),
        }
        
        enriched_chunks = _process_and_split_text(extracted_text, base_doc_metadata)
        
        # Save extracted text to storage
        processed_text_storage_key = storage_service.upload_processed_text(
            extracted_text, 
            user_id=str(document.get("owner_id")), # Use owner_id as user_id for storage
            case_id=str(document.get("case_id")), 
            original_doc_id=document_id_str
        )

        BATCH_SIZE = 10 # Safe batch size
        for i in range(0, len(enriched_chunks), BATCH_SIZE):
            batch = enriched_chunks[i:i + BATCH_SIZE]
            # vector_store_service.create_and_store_embeddings_from_chunks is called with correct arguments
            vector_store_service.create_and_store_embeddings_from_chunks(
                document_id=document_id_str,
                case_id=str(document.get("case_id")),
                chunks=[c['content'] for c in batch],
                metadatas=[c['metadata'] for c in batch]
            )
            logger.info(f"Processed embedding batch {i//BATCH_SIZE + 1} for document {document_id_str}")

        summary = llm_service.generate_summary(extracted_text)

        document_service.finalize_document_processing(
            db=db,
            redis_client=redis_client,
            doc_id_str=document_id_str, 
            summary=summary,
            processed_text_storage_key=processed_text_storage_key
        )

        extract_deadlines_from_document.delay(document_id_str, extracted_text)
        extract_findings_from_document.delay(document_id_str, extracted_text)

    except Exception as e:
        error_message = f"Failed to process document: {e}"
        logger.error(f"--- [FAILURE] {error_message} (ID: {document_id_str}) ---", exc_info=True)
        raise e
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)