# FILE: backend/app/services/document_processing_service.py
# PHOENIX PROTOCOL - INGESTION PIPELINE V13.0 (CONTEXT-AWARE)
# 1. FIX: Passed 'detected_category' to the deadline service to enable strict calendar gating.
# 2. LOGIC: Ensures Chat Logs are handled as historical data, not active agenda items.

import os
import tempfile
import logging
import shutil
import json
import concurrent.futures
from typing import List, Dict, Any, cast, Optional

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

def _emit_progress(redis_client: redis.Redis, user_id: str, doc_id: str, message: str, percent: int):
    try:
        if not user_id or not redis_client: return
        channel = f"user:{user_id}:updates"
        payload = {"type": "DOCUMENT_PROGRESS", "document_id": doc_id, "message": message, "percent": percent}
        redis_client.publish(channel, json.dumps(payload))
    except Exception: pass

def orchestrate_document_processing_mongo(db: Database, redis_client: redis.Redis, document_id_str: str):
    try:
        doc_id = ObjectId(document_id_str)
    except Exception: return

    document = db.documents.find_one({"_id": doc_id})
    if not document: raise DocumentNotFoundInDBError(document_id_str)

    user_id = str(document.get("owner_id"))
    doc_name = document.get("file_name", "Unknown Document")
    case_id_str = str(document.get("case_id"))
    
    _emit_progress(redis_client, user_id, document_id_str, "Inicializimi...", 5)

    temp_original_file_path = ""
    temp_pdf_preview_path = ""
    preview_storage_key = None
    
    try:
        # 1. Download
        suffix = os.path.splitext(doc_name)[1]
        temp_file_descriptor, temp_original_file_path = tempfile.mkstemp(suffix=suffix)
        os.close(temp_file_descriptor) 
        file_stream = storage_service.download_original_document_stream(document["storage_key"])
        with open(temp_original_file_path, 'wb') as temp_file:
            shutil.copyfileobj(file_stream, temp_file)
        if hasattr(file_stream, 'close'): file_stream.close()

        # 2. OCR
        _emit_progress(redis_client, user_id, document_id_str, "Ekstraktimi i tekstit...", 25)
        raw_text = text_extraction_service.extract_text(temp_original_file_path, document.get("mime_type", ""))
        if not raw_text or not raw_text.strip(): raise ValueError("Empty Text")

        # 3. Categorization (CRITICAL FOR GATING)
        _emit_progress(redis_client, user_id, document_id_str, "Klasifikimi...", 35)
        extracted_text = llm_service.sterilize_legal_text(raw_text)
        is_albanian = AlbanianLanguageDetector.detect_language(extracted_text)
        extracted_metadata = albanian_metadata_extractor.extract(extracted_text, document_id_str)
        
        try:
            detected_category = CATEGORIZATION_SERVICE.categorize_document(extracted_text)
        except Exception:
            detected_category = "Unknown"
        
        db.documents.update_one({"_id": doc_id}, {"$set": {"detected_language": "sq" if is_albanian else "en", "category": detected_category, "metadata": extracted_metadata}})

        # 4. Parallel Sub-tasks
        def task_embeddings():
            enriched_chunks = EnhancedDocumentProcessor.process_document(text_content=extracted_text, document_metadata={'category': detected_category, 'file_name': doc_name}, is_albanian=is_albanian)
            vector_store_service.create_and_store_embeddings_from_chunks(user_id=user_id, document_id=document_id_str, case_id=case_id_str, file_name=doc_name, chunks=[c.content for c in enriched_chunks], metadatas=[c.metadata for c in enriched_chunks])

        def task_storage():
            return storage_service.upload_processed_text(extracted_text, user_id, case_id_str, document_id_str)

        def task_summary():
            return llm_service.generate_summary(extracted_text[:35000])

        def task_deadlines():
            # PHOENIX: Passed detected_category to service
            deadline_service.extract_and_save_deadlines(db, document_id_str, extracted_text, detected_category)

        def task_graph():
            graph_data = llm_service.extract_graph_data(extracted_text)
            entities = graph_data.get("nodes") or graph_data.get("entities") or []
            relations = graph_data.get("edges") or graph_data.get("relations") or []
            graph_service.ingest_entities_and_relations(case_id=case_id_str, document_id=document_id_str, doc_name=doc_name, entities=entities, relations=relations, doc_metadata=extracted_metadata)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(task) for task in [task_embeddings, task_storage, task_summary, task_deadlines, task_graph]]
            text_key = futures[1].result()
            summary = futures[2].result()

        # 5. Preview & Finalize
        temp_pdf_preview_path = conversion_service.convert_to_pdf(temp_original_file_path)
        preview_storage_key = storage_service.upload_document_preview(temp_pdf_preview_path, user_id, case_id_str, document_id_str)
        
        _emit_progress(redis_client, user_id, document_id_str, "Përfunduar", 100)
        document_service.finalize_document_processing(db, redis_client, document_id_str, summary, text_key, preview_storage_key)

    except Exception as e:
        db.documents.update_one({"_id": doc_id}, {"$set": {"status": DocumentStatus.FAILED, "error_message": str(e)}})
        raise e
    finally:
        if temp_original_file_path and os.path.exists(temp_original_file_path): os.remove(temp_original_file_path)
        if temp_pdf_preview_path and os.path.exists(temp_pdf_preview_path): os.remove(temp_pdf_preview_path)