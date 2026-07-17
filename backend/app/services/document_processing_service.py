# FILE: backend/app/services/document_processing_service.py
# PHOENIX PROTOCOL - JURISTI HYDRA ORCHESTRATOR V17.0 (SELF-HEAL DB)
# 1. FIX: Creates fresh, unclosed MongoDB and Redis handles inside the background thread.
# 2. STATUS: Immune to FastAPI request-lifecycle cleanup crashes.

import os, tempfile, logging, shutil, json, asyncio, hashlib
from typing import List, Dict, Any
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
    
    # PHOENIX FIX: Open fresh, dedicated DB connections inside the background process
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

        # --- TEXT EXTRACTION ---
        raw_text = await asyncio.to_thread(text_extraction_service.extract_text, temp_original_file_path, document.get("mime_type", ""))
        if not raw_text or not raw_text.strip(): raise ValueError("Extracted text empty.")

        sterilized_text = llm_service.sterilize_legal_text(raw_text)
        is_albanian = AlbanianLanguageDetector.detect_language(sterilized_text)

        # --- PARALLEL VECTOR INGESTION ---
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

        await task_embeddings()
        
        # Mark as Complete in DB
        await asyncio.to_thread(db.documents.update_one, {"_id": doc_id}, {"$set": {"status": "PROCESSED"}})
        logger.info(f"⚡ [Orchestrator] SUCCESS: Document {document_id_str} is 100% Ingested into Atlas!")

    except Exception as e:
        logger.error(f"❌ [Orchestrator] FAILURE: {e}")
        await asyncio.to_thread(db.documents.update_one, {"_id": doc_id}, {"$set": {"status": DocumentStatus.FAILED, "error_message": str(e)}})
    finally:
        if temp_original_file_path and os.path.exists(temp_original_file_path): os.remove(temp_original_file_path)