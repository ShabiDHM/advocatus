# FILE: backend/app/services/document_processing_service.py
# PHOENIX PROTOCOL - JURISTI HYDRA ORCHESTRATOR V14.0
# 1. HYDRA: Replaced truncated summary logic with Async Map-Reduce (V68.0).
# 2. PERFORMANCE: Now utilizes asyncio for non-blocking API calls.
# 3. INTEGRITY: Preserved context-aware categorization and strict calendar gating.

import os
import tempfile
import logging
import shutil
import json
import asyncio
from typing import List, Dict, Any, cast, Optional
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

class DocumentNotFoundInDBError(Exception):
    pass

async def _emit_progress_async(redis_client: redis.Redis, user_id: str, doc_id: str, message: str, percent: int):
    """Async wrapper for SSE progress notifications."""
    try:
        if not user_id or not redis_client: return
        channel = f"user:{user_id}:updates"
        payload = {"type": "DOCUMENT_PROGRESS", "document_id": doc_id, "message": message, "percent": percent}
        # Redis publish is sync in this driver, wrap in thread
        await asyncio.to_thread(redis_client.publish, channel, json.dumps(payload))
    except Exception: pass

async def orchestrate_document_processing_mongo(db: Database, redis_client: redis.Redis, document_id_str: str):
    """
    Main Ingestion Orchestrator refactored for the Hydra Tactic.
    Uses Async/Await for LLM calls and Threads for local I/O.
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
    
    try:
        # 1. Download (Sync I/O -> Thread)
        suffix = os.path.splitext(doc_name)[1]
        temp_file_descriptor, temp_original_file_path = tempfile.mkstemp(suffix=suffix)
        os.close(temp_file_descriptor) 
        
        file_stream = await asyncio.to_thread(storage_service.download_original_document_stream, document["storage_key"])
        with open(temp_original_file_path, 'wb') as temp_file:
            await asyncio.to_thread(shutil.copyfileobj, file_stream, temp_file)
        if hasattr(file_stream, 'close'): file_stream.close()

        # 2. OCR (CPU Heavy -> Thread)
        await _emit_progress_async(redis_client, user_id, document_id_str, "Ekstraktimi i tekstit...", 20)
        raw_text = await asyncio.to_thread(text_extraction_service.extract_text, temp_original_file_path, document.get("mime_type", ""))
        if not raw_text or not raw_text.strip(): raise ValueError("Teksti i ekstraktuar është bosh.")

        # 3. Metadata & Categorization
        await _emit_progress_async(redis_client, user_id, document_id_str, "Analiza e strukturës...", 35)
        extracted_text = llm_service.sterilize_legal_text(raw_text)
        is_albanian = AlbanianLanguageDetector.detect_language(extracted_text)
        
        # Meta extraction (Sync LLM call inside, but we'll run it in thread for now)
        extracted_metadata = await asyncio.to_thread(albanian_metadata_extractor.extract, extracted_text, document_id_str)
        
        try:
            detected_category = await asyncio.to_thread(CATEGORIZATION_SERVICE.categorize_document, extracted_text)
        except Exception:
            detected_category = "Unknown"
        
        await asyncio.to_thread(
            db.documents.update_one, 
            {"_id": doc_id}, 
            {"$set": {
                "detected_language": "sq" if is_albanian else "en", 
                "category": detected_category, 
                "metadata": extracted_metadata
            }}
        )

        # 4. HYDRA TACTIC: Async Parallel Map-Reduce for Summary
        # This replaces the old truncated 35k char logic. Now analyzes the FULL text.
        await _emit_progress_async(redis_client, user_id, document_id_str, "Gjenerimi i analizës Hydra...", 50)
        summary_task = llm_service.process_large_document_async(extracted_text)

        # 5. Parallel Background Sub-tasks (I/O & CPU)
        async def task_embeddings():
            enriched_chunks = await asyncio.to_thread(
                EnhancedDocumentProcessor.process_document, 
                text_content=extracted_text, 
                document_metadata={'category': detected_category, 'file_name': doc_name}, 
                is_albanian=is_albanian
            )
            await asyncio.to_thread(
                vector_store_service.create_and_store_embeddings_from_chunks,
                user_id=user_id, document_id=document_id_str, case_id=case_id_str, 
                file_name=doc_name, chunks=[c.content for c in enriched_chunks], 
                metadatas=[c.metadata for c in enriched_chunks]
            )

        async def task_storage():
            return await asyncio.to_thread(storage_service.upload_processed_text, extracted_text, user_id, case_id_str, document_id_str)

        async def task_deadlines():
            await asyncio.to_thread(deadline_service.extract_and_save_deadlines, db, document_id_str, extracted_text, detected_category)

        async def task_graph():
            graph_data = await asyncio.to_thread(llm_service.extract_graph_data, extracted_text)
            entities = graph_data.get("nodes") or graph_data.get("entities") or []
            relations = graph_data.get("edges") or graph_data.get("relations") or []
            await asyncio.to_thread(
                graph_service.ingest_entities_and_relations, 
                case_id=case_id_str, document_id=document_id_str, doc_name=doc_name, 
                entities=entities, relations=relations, doc_metadata=extracted_metadata
            )

        async def task_preview():
            pdf_path = await asyncio.to_thread(conversion_service.convert_to_pdf, temp_original_file_path)
            key = await asyncio.to_thread(storage_service.upload_document_preview, pdf_path, user_id, case_id_str, document_id_str)
            return pdf_path, key

        # Launch all remaining tasks in parallel
        await _emit_progress_async(redis_client, user_id, document_id_str, "Përpunimi i inteligjencës...", 75)
        
        # Gathering the results
        results = await asyncio.gather(
            summary_task, 
            task_embeddings(), 
            task_storage(), 
            task_deadlines(), 
            task_graph(),
            task_preview()
        )
        
        final_summary = results[0]
        text_key = results[2]
        pdf_temp_path, preview_storage_key = results[5]
        
        # 6. Finalize
        await _emit_progress_async(redis_client, user_id, document_id_str, "Përfunduar", 100)
        await asyncio.to_thread(
            document_service.finalize_document_processing, 
            db, redis_client, document_id_str, final_summary, text_key, preview_storage_key
        )

        if pdf_temp_path and os.path.exists(pdf_temp_path):
            os.remove(pdf_temp_path)

    except Exception as e:
        logger.error(f"Dështim gjatë procesimit të dokumentit {document_id_str}: {e}")
        await asyncio.to_thread(
            db.documents.update_one, 
            {"_id": doc_id}, 
            {"$set": {"status": DocumentStatus.FAILED, "error_message": str(e)}}
        )
        raise e
    finally:
        if temp_original_file_path and os.path.exists(temp_original_file_path): 
            os.remove(temp_original_file_path)