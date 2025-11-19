# FILE: backend/app/services/document_processing_service.py
# PHOENIX PROTOCOL - SYNC EXTRACTION FIX
# 1. Changed findings extraction to run SYNCHRONOUSLY via .apply()
# 2. This ensures Findings exist in DB *before* status becomes READY.

import os
import tempfile
import logging
from pymongo.database import Database
import redis
from bson import ObjectId
from typing import List, Dict, Any
import shutil

from langchain.text_splitter import RecursiveCharacterTextSplitter

# Direct imports
from . import document_service, storage_service, vector_store_service, llm_service, text_extraction_service, conversion_service
from ..models.document import DocumentStatus
from ..tasks.deadline_extraction import extract_deadlines_from_document
from ..tasks.findings_extraction import extract_findings_from_document

logger = logging.getLogger(__name__)

class DocumentNotFoundInDBError(Exception):
    pass

def _process_and_split_text(full_text: str, document_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
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

    temp_original_file_path = ""
    temp_pdf_preview_path = ""
    preview_storage_key = None
    
    try:
        # Step 1: Download
        suffix = os.path.splitext(document.get("file_name", ""))[1]
        temp_file_descriptor, temp_original_file_path = tempfile.mkstemp(suffix=suffix)
        
        file_stream = storage_service.download_original_document_stream(document["storage_key"])
        with os.fdopen(temp_file_descriptor, 'wb') as temp_file:
            shutil.copyfileobj(file_stream, temp_file)
        if hasattr(file_stream, 'close'): file_stream.close()

        # Step 2: PDF Preview (Sync)
        try:
            logger.info(f"Generating PDF preview for {document_id_str}...")
            temp_pdf_preview_path = conversion_service.convert_to_pdf(temp_original_file_path)
            preview_storage_key = storage_service.upload_document_preview(
                file_path=temp_pdf_preview_path,
                user_id=str(document.get("owner_id")),
                case_id=str(document.get("case_id")),
                original_doc_id=document_id_str
            )
        except Exception as e:
            logger.error(f"Preview generation failed: {e}")

        # Step 3: Text Extraction
        extracted_text = text_extraction_service.extract_text(temp_original_file_path, document.get("mime_type", ""))
        if not extracted_text or not extracted_text.strip():
            raise ValueError("Text extraction returned no content.")

        # Step 4: Embeddings (Sync)
        base_doc_metadata = {
            'document_id': document_id_str,
            'case_id': str(document.get("case_id")),
            'user_id': str(document.get("owner_id")),
            'file_name': document.get("file_name", "Unknown"),
        }
        
        enriched_chunks = _process_and_split_text(extracted_text, base_doc_metadata)
        
        processed_text_storage_key = storage_service.upload_processed_text(
            extracted_text, 
            user_id=str(document.get("owner_id")),
            case_id=str(document.get("case_id")), 
            original_doc_id=document_id_str
        )

        BATCH_SIZE = 10
        for i in range(0, len(enriched_chunks), BATCH_SIZE):
            batch = enriched_chunks[i:i + BATCH_SIZE]
            vector_store_service.create_and_store_embeddings_from_chunks(
                document_id=document_id_str,
                case_id=str(document.get("case_id")),
                chunks=[c['content'] for c in batch],
                metadatas=[c['metadata'] for c in batch]
            )

        # Step 5: Summary (Sync)
        summary = llm_service.generate_summary(extracted_text)

        # Step 6: Findings Extraction (PHOENIX FIX: SYNC EXECUTION)
        # We run this *before* finalizing status so findings are ready when UI refreshes.
        logger.info(f"Starting synchronous findings extraction for {document_id_str}")
        # .apply() executes the Celery task locally and synchronously
        extract_findings_from_document.apply(args=[document_id_str, extracted_text])
        logger.info("Findings extraction complete.")
        
        # Also run deadlines sync (fast enough)
        extract_deadlines_from_document.apply(args=[document_id_str, extracted_text])

        # Step 7: Finalize (Sets Status to READY)
        document_service.finalize_document_processing(
            db=db,
            redis_client=redis_client,
            doc_id_str=document_id_str, 
            summary=summary,
            processed_text_storage_key=processed_text_storage_key,
            preview_storage_key=preview_storage_key
        )

    except Exception as e:
        error_message = f"Failed to process document {document_id_str}: {e}"
        logger.error(f"--- [FAILURE] {error_message} ---", exc_info=True)
        db.documents.update_one(
            {"_id": doc_id},
            {"$set": {"status": DocumentStatus.FAILED, "error_message": str(e)}}
        )
        raise e
    finally:
        if temp_original_file_path and os.path.exists(temp_original_file_path): os.remove(temp_original_file_path)
        if temp_pdf_preview_path and os.path.exists(temp_pdf_preview_path): os.remove(temp_pdf_preview_path)