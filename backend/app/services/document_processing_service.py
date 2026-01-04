# FILE: backend/app/services/document_processing_service.py
# PHOENIX PROTOCOL - INGESTION PIPELINE V10.0 (SYNCED)
# 1. CRITICAL FIX: Passes 'user_id' correctly to the V13.0 Vector Store.
# 2. STATUS: Fixes "Context Detachment" by ensuring embeddings land in the Private Case KB.

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
        payload = {
            "type": "DOCUMENT_PROGRESS",
            "document_id": doc_id,
            "message": message,
            "percent": percent
        }
        redis_client.publish(channel, json.dumps(payload))
    except Exception as e:
        logger.warning(f"Failed to emit progress: {e}")

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

    user_id = str(document.get("owner_id"))
    doc_name = document.get("file_name", "Unknown Document")
    case_id_str = str(document.get("case_id"))
    
    _emit_progress(redis_client, user_id, document_id_str, "Inicializimi...", 5)

    temp_original_file_path = ""
    temp_pdf_preview_path = ""
    preview_storage_key = None
    
    try:
        _emit_progress(redis_client, user_id, document_id_str, "Shkarkimi...", 10)
        
        # Safe temp file creation
        suffix = os.path.splitext(doc_name)[1]
        temp_file_descriptor, temp_original_file_path = tempfile.mkstemp(suffix=suffix)
        os.close(temp_file_descriptor) # Close immediately, we just needed the path
        
        file_stream = storage_service.download_original_document_stream(document["storage_key"])
        with open(temp_original_file_path, 'wb') as temp_file:
            shutil.copyfileobj(file_stream, temp_file)
        if hasattr(file_stream, 'close'): file_stream.close()

        try:
            _emit_progress(redis_client, user_id, document_id_str, "Gjenerimi i pamjes...", 15)
            temp_pdf_preview_path = conversion_service.convert_to_pdf(temp_original_file_path)
            preview_storage_key = storage_service.upload_document_preview(file_path=temp_pdf_preview_path, user_id=user_id, case_id=case_id_str, original_doc_id=document_id_str)
        except Exception as e: 
            logger.warning(f"Preview generation failed: {e}")

        _emit_progress(redis_client, user_id, document_id_str, "Ekstraktimi i tekstit (OCR)...", 25)
        raw_text = text_extraction_service.extract_text(temp_original_file_path, document.get("mime_type", ""))
        
        if not raw_text or not raw_text.strip():
            raise ValueError("OCR dështoi: Dokumenti duket bosh (Empty Text).")

        _emit_progress(redis_client, user_id, document_id_str, "Sterilizimi Ligjor...", 28)
        extracted_text = llm_service.sterilize_legal_text(raw_text)
        
        _emit_progress(redis_client, user_id, document_id_str, "Klasifikimi...", 30)
        is_albanian = AlbanianLanguageDetector.detect_language(extracted_text)
        extracted_metadata = albanian_metadata_extractor.extract(extracted_text, document_id_str)
        
        update_payload = {"detected_language": "sq" if is_albanian else "en", "metadata": extracted_metadata}
        try:
            detected_category = CATEGORIZATION_SERVICE.categorize_document(extracted_text)
            update_payload["category"] = detected_category
        except Exception:
            detected_category = "Unknown"
        db.documents.update_one({"_id": doc_id}, {"$set": update_payload})

        _emit_progress(redis_client, user_id, document_id_str, "Analizë e Thellë...", 40)
        
        # --- SUB-TASKS ---
        def task_embeddings() -> bool:
            try:
                _emit_progress(redis_client, user_id, document_id_str, "Indeksimi Vektorial...", 50)
                base_doc_metadata = {'language': 'sq' if is_albanian else 'en', 'category': detected_category, 'file_name': doc_name}
                if extracted_metadata:
                    base_doc_metadata.update({k: v for k, v in extracted_metadata.items() if v})
                
                enriched_chunks = EnhancedDocumentProcessor.process_document(text_content=extracted_text, document_metadata=base_doc_metadata, is_albanian=is_albanian)
                
                # PHOENIX FIX: Passing 'user_id' explicitly to V13.0 Store
                success = vector_store_service.create_and_store_embeddings_from_chunks(
                    user_id=user_id, 
                    document_id=document_id_str, 
                    case_id=case_id_str, 
                    file_name=doc_name,
                    chunks=[c.content for c in enriched_chunks],
                    metadatas=[c.metadata for c in enriched_chunks]
                )
                if not success: logger.error("Vector Store returned False")
                return success
            except Exception as e:
                logger.error(f"Embedding Task Failed: {e}", exc_info=True)
                return False

        def task_storage() -> Optional[str]:
            try: return storage_service.upload_processed_text(extracted_text, user_id=user_id, case_id=case_id_str, original_doc_id=document_id_str)
            except Exception: return None

        def task_summary() -> str:
            try:
                _emit_progress(redis_client, user_id, document_id_str, "Gjenerimi i Përmbledhjes...", 60)
                limit = 35000
                optimized = extracted_text[:limit] if len(extracted_text) > limit else extracted_text
                return llm_service.generate_summary(optimized)
            except Exception: return "Përmbledhja nuk është e disponueshme."

        def task_deadlines() -> None:
            try:
                _emit_progress(redis_client, user_id, document_id_str, "Ekstraktimi i Afateve...", 80)
                deadline_service.extract_and_save_deadlines(db, document_id_str, extracted_text)
            except Exception as e: logger.error(f"Deadline Extraction Error: {e}")

        def task_graph() -> None:
            try:
                _emit_progress(redis_client, user_id, document_id_str, "Ndërtimi i Grafit...", 90)
                graph_data = llm_service.extract_graph_data(extracted_text)
                entities = graph_data.get("entities", [])
                relations = graph_data.get("relations", [])
                if entities or relations or extracted_metadata:
                    graph_service.ingest_entities_and_relations(
                        case_id=case_id_str, document_id=document_id_str, doc_name=doc_name,
                        entities=entities, relations=relations,
                        doc_metadata=extracted_metadata 
                    )
            except Exception as e: logger.error(f"Graph Ingestion Error: {e}")

        summary_result, text_storage_key = None, None
        
        # Parallel Execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures_list = [executor.submit(task) for task in [task_embeddings, task_storage, task_summary, task_deadlines, task_graph]]
            # Wait for critical results
            summary_result = futures_list[2].result()
            text_storage_key = futures_list[1].result()
            
            # Check embedding status
            emb_status = futures_list[0].result()
            if not emb_status:
                logger.warning(f"⚠️ Document {doc_name} was processed but Embeddings failed.")

        _emit_progress(redis_client, user_id, document_id_str, "Përfunduar", 100)
        
        document_service.finalize_document_processing(db=db, redis_client=redis_client, doc_id_str=document_id_str, summary=summary_result, processed_text_storage_key=text_storage_key, preview_storage_key=preview_storage_key)
        logger.info(f"✅ Document {document_id_str} processing completed successfully.")

    except Exception as e:
        _emit_progress(redis_client, user_id, document_id_str, "Dështoi: " + str(e), 0)
        logger.error(f"--- [CRITICAL FAILURE] Doc Processing: {e} ---", exc_info=True)
        db.documents.update_one({"_id": doc_id},{"$set": {"status": DocumentStatus.FAILED, "error_message": str(e)}})
        raise e
        
    finally:
        if temp_original_file_path and os.path.exists(temp_original_file_path): os.remove(temp_original_file_path)
        if temp_pdf_preview_path and os.path.exists(temp_pdf_preview_path): os.remove(temp_pdf_preview_path)