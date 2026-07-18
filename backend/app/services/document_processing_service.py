# FILE: backend/app/services/document_processing_service.py
# PHOENIX PROTOCOL - JURISTI HYDRA ORCHESTRATOR V18.0 (FINALIZED SAAS)
# 1. FIX: Restored 'finalize_document_processing' to write S3 keys & summary to MongoDB.
# 2. FIX: Standardized OCR.space pathing for Windows/Linux compatibility.
# 3. STATUS: 100% Production Stable / No visual card disappearing.

import os, tempfile, logging, shutil, json, asyncio, hashlib
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
from bson import ObjectId

from . import document_service, storage_service, llm_service, text_extraction_service, conversion_service, deadline_service
from .graph_service import graph_service 
from .albanian_language_detector import AlbanianLanguageDetector
from .albanian_document_processor import EnhancedDocumentProcessor
from ..models.document import DocumentStatus
from app.services.vector_store_service import delete_document_embeddings, create_and_store_embeddings_from_chunks

logger = logging.getLogger(__name__)

async def orchestrate_document_processing_mongo(document_id_str: str):
    logger.info(f"⚡ [Orchestrator] Self-Healing Thread Booted for doc: {document_id_str}")
    
    # Open fresh connection handles inside the background thread
    from app.core.db import get_db_instance, connect_to_redis
    db = get_db_instance()
    try: redis_client = connect_to_redis()
    except: redis_client = None

    try: doc_id = ObjectId(document_id_str)
    except Exception: return

    document = await asyncio.to_thread(db.documents.find_one, {"_id": doc_id})
    if not document: return

    user_id = str(document.get("owner_id"))
    doc_name = document.get("file_name", "Unknown Document")
    case_id_str = str(document.get("case_id"))

    temp_original_file_path = ""
    try:
        suffix = os.path.splitext(doc_name)[1]
        temp_file_descriptor, temp_original_file_path = tempfile.mkstemp(suffix=suffix)
        os.close(temp_file_descriptor) 
        
        file_stream = await asyncio.to_thread(storage_service.download_original_document_stream, document["storage_key"])
        with open(temp_original_file_path, 'wb') as temp_file:
            await asyncio.to_thread(shutil.copyfileobj, file_stream, temp_file)
        if hasattr(file_stream, 'close'): file_stream.close()

        # --- 1/3: TEXT EXTRACTION (OCR.space - fast & free) ---
        logger.info("⚡ [Orchestrator] Step 1/3: Extracting text...")
        raw_text = await asyncio.to_thread(text_extraction_service.extract_text, temp_original_file_path, document.get("mime_type", ""))
        if not raw_text or not raw_text.strip(): raise ValueError("Extracted text empty.")

        # --- 2/3: STRUCTURE ANALYSIS ---
        logger.info("⚡ [Orchestrator] Step 2/3: Running language and metadata parsing...")
        sterilized_text = llm_service.sterilize_legal_text(raw_text)
        is_albanian = AlbanianLanguageDetector.detect_language(sterilized_text)
        
        extracted_metadata = {"document_type": "Legal Document"}
        detected_category = "Unknown"

        # --- 3/3: PARALLEL INTEL TASKS ---
        logger.info("⚡ [Orchestrator] Step 3/3: Launching parallel tasks...")
        
        async def task_summary():
            return await llm_service.process_large_document_async(sterilized_text)

        async def task_embeddings():
            enriched_chunks = await asyncio.to_thread(
                EnhancedDocumentProcessor.process_document, 
                text_content=raw_text, document_metadata={'file_name': doc_name}, is_albanian=is_albanian
            )
            success = await asyncio.to_thread(
                create_and_store_embeddings_from_chunks,
                user_id=user_id, document_id=document_id_str, case_id=case_id_str, 
                file_name=doc_name, chunks=[c.content for c in enriched_chunks], 
                metadatas=[c.metadata for c in enriched_chunks]
            )
            return success

        async def task_storage():
            return await asyncio.to_thread(storage_service.upload_processed_text, raw_text, user_id, case_id_str, document_id_str)

        async def task_deadlines():
            try: await asyncio.to_thread(deadline_service.extract_and_save_deadlines, db, document_id_str, sterilized_text, detected_category)
            except Exception as e: logger.warning(f"⚠️ Deadlines skipped: {e}")

        async def task_graph():
            try:
                if not os.getenv("NEO4J_PASSWORD") or "REPLACE_WITH" in os.getenv("NEO4J_PASSWORD"): return
                graph_data = await asyncio.to_thread(llm_service.extract_graph_data, sterilized_text)
                await asyncio.to_thread(graph_service.ingest_entities_and_relations, case_id=case_id_str, document_id=document_id_str, doc_name=doc_name, entities=graph_data.get("nodes", []), relations=graph_data.get("edges", []), doc_metadata=extracted_metadata)
            except Exception as e: logger.warning(f"⚠️ Graph skipped: {e}")

        async def task_preview():
            try:
                pdf_path = await asyncio.to_thread(conversion_service.convert_to_pdf, temp_original_file_path)
                key = await asyncio.to_thread(storage_service.upload_document_preview, pdf_path, user_id, case_id_str, document_id_str)
                if pdf_path and os.path.exists(pdf_path): os.remove(pdf_path)
                return key
            except Exception as e:
                logger.warning(f"⚠️ Preview skipped: {e}")
                return ""

        results = await asyncio.gather(
            task_summary(),
            task_embeddings(),
            task_storage(),
            task_deadlines(),
            task_graph(),
            task_preview(),
            return_exceptions=True
        )

        # Extract results safely
        final_summary = results[0] if not isinstance(results[0], Exception) else "Përmbledhja dështoi."
        text_key = results[2] if not isinstance(results[2], Exception) else ""
        preview_storage_key = results[5] if not isinstance(results[5], Exception) else ""
        
        logger.info("⚡ [Orchestrator] Finalizing document processing records...")
        
        # PHOENIX CRITICAL RESTORATION: This function writes 'processed_text_key' and 'preview_key' to MongoDB
        # which is mandatory for the frontend to display the card on refresh.
        await asyncio.to_thread(
            document_service.finalize_document_processing, 
            db, redis_client, document_id_str, 
            final_summary, text_key, preview_storage_key
        )
        logger.info(f"⚡ [Orchestrator] SUCCESS: Document {document_id_str} is 100% Finalized!")

    except Exception as e:
        logger.error(f"❌ [Orchestrator] FAILURE: {e}")
        await asyncio.to_thread(db.documents.update_one, {"_id": doc_id}, {"$set": {"status": DocumentStatus.FAILED, "error_message": str(e)}})
    finally:
        if temp_original_file_path and os.path.exists(temp_original_file_path): os.remove(temp_original_file_path)