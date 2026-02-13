# FILE: backend/app/services/document_processing_service.py
# PHOENIX PROTOCOL - JURISTI HYDRA ORCHESTRATOR V15.2
# 1. PYLANCE: Removed all references to DocumentStatus.PROCESSED (does not exist). Uses "PROCESSED" string.
# 2. PYLANCE: Added typing.cast to resolve union type errors from asyncio.gather(return_exceptions=True).
# 3. ACCURACY: OCR fallback, deduplication, page‑aware chunking, rich metadata preserved.
# 4. STATUS: 100% Pylance clean – ready for production.

import os
import tempfile
import logging
import shutil
import json
import asyncio
import hashlib
from typing import List, Dict, Any, cast, Optional, Tuple
from datetime import datetime, timezone

from pymongo.database import Database
import redis
from bson import ObjectId

from . import (
    document_service, 
    storage_service, 
    vector_store_service, 
    llm_service, 
    text_extraction_service, 
    conversion_service,
    deadline_service
)
from .graph_service import graph_service 
from .categorization_service import CATEGORIZATION_SERVICE
from .albanian_language_detector import AlbanianLanguageDetector
from .albanian_document_processor import EnhancedDocumentProcessor
from .albanian_metadata_extractor import albanian_metadata_extractor
from ..models.document import DocumentStatus

logger = logging.getLogger(__name__)

# PHOENIX: Threshold for triggering OCR fallback (if extracted text < 100 chars)
OCR_FALLBACK_THRESHOLD = 100

class DocumentNotFoundInDBError(Exception):
    pass

def _compute_file_hash(file_path: str) -> str:
    """SHA256 hash of file content for deduplication."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

async def _emit_progress_async(redis_client: redis.Redis, user_id: str, doc_id: str, message: str, percent: int):
    """Async wrapper for SSE progress notifications."""
    try:
        if not user_id or not redis_client: return
        channel = f"user:{user_id}:updates"
        payload = {"type": "DOCUMENT_PROGRESS", "document_id": doc_id, "message": message, "percent": percent}
        await asyncio.to_thread(redis_client.publish, channel, json.dumps(payload))
    except Exception: pass

async def orchestrate_document_processing_mongo(db: Database, redis_client: redis.Redis, document_id_str: str):
    """
    Main Ingestion Orchestrator – refactored for accuracy, deduplication, and Pylance safety.
    """
    try:
        doc_id = ObjectId(document_id_str)
    except Exception: return

    document = await asyncio.to_thread(db.documents.find_one, {"_id": doc_id})
    if not document: raise DocumentNotFoundInDBError(document_id_str)

    user_id = str(document.get("owner_id"))
    doc_name = document.get("file_name", "Unknown Document")
    case_id_str = str(document.get("case_id"))
    
    await _emit_progress_async(redis_client, user_id, document_id_str, "Inicializimi...", 5)

    temp_original_file_path = ""
    temp_pdf_preview_path = ""
    file_hash = None
    
    try:
        # 1. Download (Sync I/O -> Thread)
        suffix = os.path.splitext(doc_name)[1]
        temp_file_descriptor, temp_original_file_path = tempfile.mkstemp(suffix=suffix)
        os.close(temp_file_descriptor) 
        
        file_stream = await asyncio.to_thread(storage_service.download_original_document_stream, document["storage_key"])
        with open(temp_original_file_path, 'wb') as temp_file:
            await asyncio.to_thread(shutil.copyfileobj, file_stream, temp_file)
        if hasattr(file_stream, 'close'): file_stream.close()

        # Compute file hash for deduplication
        file_hash = _compute_file_hash(temp_original_file_path)

        # PHOENIX: Check for existing, successfully processed document with same hash, case, owner
        # We consider a document "successfully processed" if it has processed_text_key and status is not FAILED
        existing_doc = await asyncio.to_thread(
            db.documents.find_one,
            {
                "file_hash": file_hash,
                "case_id": document["case_id"],
                "owner_id": document["owner_id"],
                "processed_text_key": {"$exists": True, "$ne": None},
                "status": {"$ne": DocumentStatus.FAILED}
            }
        )
        
        if existing_doc:
            logger.info(f"Duplicate document detected (hash: {file_hash}). Copying metadata from {existing_doc['_id']}")
            await _emit_progress_async(redis_client, user_id, document_id_str, "Dokument i dyfishuar – kopjohet...", 50)
            
            # Copy processed text and preview keys
            text_key = existing_doc.get("processed_text_key")
            preview_key = existing_doc.get("preview_key")
            
            # PHOENIX: Conditionally copy embeddings if the function exists
            copy_embeddings_fn = getattr(vector_store_service, "copy_document_embeddings", None)
            if copy_embeddings_fn:
                await asyncio.to_thread(
                    copy_embeddings_fn,
                    source_document_id=str(existing_doc["_id"]),
                    target_document_id=document_id_str,
                    target_user_id=user_id,
                    target_case_id=case_id_str
                )
            else:
                logger.warning("vector_store_service.copy_document_embeddings not available – will reprocess embeddings.")
                # Mark that we need to reprocess embeddings; fall through to normal ingestion
            
            # PHOENIX: DocumentStatus.PROCESSED does NOT exist – use string literal "PROCESSED"
            update_data = {
                "status": "PROCESSED",
                "processed_text_key": text_key,
                "preview_key": preview_key,
                "file_hash": file_hash,
                "detected_language": existing_doc.get("detected_language"),
                "category": existing_doc.get("category"),
                "metadata": existing_doc.get("metadata", {}),
                "summary": existing_doc.get("summary"),
                "processing_time": datetime.now(timezone.utc)
            }
            
            await asyncio.to_thread(
                db.documents.update_one,
                {"_id": doc_id},
                {"$set": update_data}
            )
            
            # If we successfully copied embeddings, we are done
            if copy_embeddings_fn:
                await _emit_progress_async(redis_client, user_id, document_id_str, "Përfunduar (kopjuar)", 100)
                return
            # else: continue to full ingestion

        # 2. Text Extraction with OCR Fallback (if available)
        await _emit_progress_async(redis_client, user_id, document_id_str, "Ekstraktimi i tekstit...", 20)
        
        # First attempt: standard extraction
        raw_text = await asyncio.to_thread(
            text_extraction_service.extract_text, 
            temp_original_file_path, 
            document.get("mime_type", "")
        )
        
        # OCR fallback if available and text is too short
        if (not raw_text or len(raw_text.strip()) < OCR_FALLBACK_THRESHOLD):
            ocr_fn = getattr(text_extraction_service, "extract_text_with_ocr", None)
            if ocr_fn:
                logger.warning(f"Low text content ({len(raw_text or '')} chars). Attempting OCR...")
                await _emit_progress_async(redis_client, user_id, document_id_str, "OCR në progres...", 25)
                raw_text = await asyncio.to_thread(
                    ocr_fn,
                    temp_original_file_path,
                    document.get("mime_type", "")
                )
            else:
                logger.warning("OCR function not available – continuing with extracted text.")
            
        if not raw_text or not raw_text.strip():
            raise ValueError("Teksti i ekstraktuar është bosh edhe pas OCR (nëse ishte i disponueshëm).")

        # 3. Metadata & Categorization
        await _emit_progress_async(redis_client, user_id, document_id_str, "Analiza e strukturës...", 35)
        
        sterilized_text = llm_service.sterilize_legal_text(raw_text)
        is_albanian = AlbanianLanguageDetector.detect_language(sterilized_text)
        
        extracted_metadata = await asyncio.to_thread(
            albanian_metadata_extractor.extract, 
            sterilized_text, 
            document_id_str
        )
        
        try:
            detected_category = await asyncio.to_thread(
                CATEGORIZATION_SERVICE.categorize_document, 
                sterilized_text
            )
        except Exception:
            detected_category = "Unknown"
        
        await asyncio.to_thread(
            db.documents.update_one, 
            {"_id": doc_id}, 
            {"$set": {
                "detected_language": "sq" if is_albanian else "en", 
                "category": detected_category, 
                "metadata": extracted_metadata,
                "file_hash": file_hash
            }}
        )

        # 4. HYDRA TACTIC: Async Parallel Map-Reduce for Summary
        await _emit_progress_async(redis_client, user_id, document_id_str, "Gjenerimi i analizës Hydra...", 50)
        summary_task = llm_service.process_large_document_async(sterilized_text)

        # 5. Parallel Background Sub-tasks (I/O & CPU)
        async def task_embeddings():
            # Delete any existing vectors for this document (clean slate)
            await asyncio.to_thread(
                vector_store_service.delete_document_embeddings,
                user_id=user_id,
                document_id=document_id_str
            )
            
            enriched_chunks = await asyncio.to_thread(
                EnhancedDocumentProcessor.process_document, 
                text_content=raw_text,
                document_metadata={
                    'category': detected_category, 
                    'file_name': doc_name,
                    **extracted_metadata
                }, 
                is_albanian=is_albanian
            )
            
            for chunk in enriched_chunks:
                if 'page' not in chunk.metadata or not chunk.metadata['page']:
                    chunk.metadata['page'] = 1
                chunk.metadata['document_type'] = extracted_metadata.get('document_type', detected_category)
                chunk.metadata['case_id'] = case_id_str
                chunk.metadata['owner_id'] = user_id
                chunk.metadata['language'] = 'sq' if is_albanian else 'en'
                chunk.metadata['file_hash'] = file_hash
            
            success = await asyncio.to_thread(
                vector_store_service.create_and_store_embeddings_from_chunks,
                user_id=user_id, 
                document_id=document_id_str, 
                case_id=case_id_str, 
                file_name=doc_name, 
                chunks=[c.content for c in enriched_chunks], 
                metadatas=[c.metadata for c in enriched_chunks]
            )
            if not success:
                raise RuntimeError("Embedding creation failed – vector store rejected chunks.")
            return enriched_chunks

        async def task_storage():
            return await asyncio.to_thread(
                storage_service.upload_processed_text, 
                raw_text,
                user_id, 
                case_id_str, 
                document_id_str
            )

        async def task_deadlines():
            await asyncio.to_thread(
                deadline_service.extract_and_save_deadlines, 
                db, 
                document_id_str, 
                sterilized_text, 
                detected_category
            )

        async def task_graph():
            graph_data = await asyncio.to_thread(
                llm_service.extract_graph_data, 
                sterilized_text
            )
            entities = graph_data.get("nodes") or graph_data.get("entities") or []
            relations = graph_data.get("edges") or graph_data.get("relations") or []
            await asyncio.to_thread(
                graph_service.ingest_entities_and_relations, 
                case_id=case_id_str, 
                document_id=document_id_str, 
                doc_name=doc_name, 
                entities=entities, 
                relations=relations, 
                doc_metadata=extracted_metadata
            )

        async def task_preview():
            pdf_path = await asyncio.to_thread(
                conversion_service.convert_to_pdf, 
                temp_original_file_path
            )
            key = await asyncio.to_thread(
                storage_service.upload_document_preview, 
                pdf_path, 
                user_id, 
                case_id_str, 
                document_id_str
            )
            return pdf_path, key

        await _emit_progress_async(redis_client, user_id, document_id_str, "Përpunimi i inteligjencës...", 75)
        
        # Launch all tasks in parallel, capturing exceptions
        results = await asyncio.gather(
            summary_task,
            task_embeddings(),
            task_storage(),
            task_deadlines(),
            task_graph(),
            task_preview(),
            return_exceptions=True
        )
        
        # PHOENIX: Explicitly check each result; if any is an exception, raise it.
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                raise RuntimeError(f"Task {i} failed: {res}")
        
        # PHOENIX: After ensuring no exceptions, we cast to expected types.
        # This eliminates Pylance union type errors.
        from typing import cast
        final_summary = cast(str, results[0])
        _embeddings_result = cast(Any, results[1])   # not used
        text_key = cast(str, results[2])
        _deadlines_result = cast(Any, results[3])    # not used
        _graph_result = cast(Any, results[4])        # not used
        preview_result = cast(Tuple[str, str], results[5])
        pdf_temp_path, preview_storage_key = preview_result
        
        # 6. Finalize
        await _emit_progress_async(redis_client, user_id, document_id_str, "Përfunduar", 100)
        await asyncio.to_thread(
            document_service.finalize_document_processing, 
            db, 
            redis_client, 
            document_id_str, 
            final_summary, 
            text_key, 
            preview_storage_key
        )

        if pdf_temp_path and os.path.exists(pdf_temp_path):
            os.remove(pdf_temp_path)

    except Exception as e:
        logger.error(f"Dështim gjatë procesimit të dokumentit {document_id_str}: {e}")
        
        # Clean up any embeddings that might have been partially stored
        try:
            await asyncio.to_thread(
                vector_store_service.delete_document_embeddings,
                user_id=user_id,
                document_id=document_id_str
            )
        except Exception as cleanup_error:
            logger.error(f"Cleanup failed: {cleanup_error}")
        
        await asyncio.to_thread(
            db.documents.update_one, 
            {"_id": doc_id}, 
            {"$set": {
                "status": DocumentStatus.FAILED, 
                "error_message": str(e),
                "file_hash": file_hash
            }}
        )
        raise e
    finally:
        if temp_original_file_path and os.path.exists(temp_original_file_path): 
            os.remove(temp_original_file_path)