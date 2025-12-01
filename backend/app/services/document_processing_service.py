# FILE: backend/app/services/document_processing_service.py
# PHOENIX PROTOCOL - IMPORT FIX
# 1. FIX: Added 'Optional' to typing imports.
# 2. STATUS: Error free.

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
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Core Services
from . import (
    document_service, 
    storage_service, 
    vector_store_service, 
    llm_service, 
    text_extraction_service, 
    conversion_service,
    deadline_service,
    findings_service
)
from .graph_service import graph_service 
from .categorization_service import CATEGORIZATION_SERVICE
from .albanian_language_detector import AlbanianLanguageDetector
from ..models.document import DocumentStatus

logger = logging.getLogger(__name__)

class DocumentNotFoundInDBError(Exception):
    pass

def _process_and_split_text(full_text: str, document_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    base_metadata = document_metadata.copy()
    # Optimized for Legal Texts
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200, 
        chunk_overlap=250, 
        length_function=len
    )
    text_chunks = text_splitter.split_text(full_text)
    return [{'content': chunk, 'metadata': {**base_metadata, 'chunk_index': i}} for i, chunk in enumerate(text_chunks)]

def _emit_progress(redis_client: redis.Redis, user_id: str, doc_id: str, message: str, percent: int):
    """Sends real-time updates to the UI via Redis Pub/Sub."""
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
        # --- PHASE 1: PREPARATION ---
        _emit_progress(redis_client, user_id, document_id_str, "Shkarkimi i dokumentit...", 10)
        
        suffix = os.path.splitext(doc_name)[1]
        temp_file_descriptor, temp_original_file_path = tempfile.mkstemp(suffix=suffix)
        
        file_stream = storage_service.download_original_document_stream(document["storage_key"])
        with os.fdopen(temp_file_descriptor, 'wb') as temp_file:
            shutil.copyfileobj(file_stream, temp_file)
        if hasattr(file_stream, 'close'): file_stream.close()

        # PDF Preview (Critical for UI)
        try:
            _emit_progress(redis_client, user_id, document_id_str, "Gjenerimi i pamjes (Preview)...", 15)
            temp_pdf_preview_path = conversion_service.convert_to_pdf(temp_original_file_path)
            preview_storage_key = storage_service.upload_document_preview(
                file_path=temp_pdf_preview_path,
                user_id=user_id,
                case_id=case_id_str,
                original_doc_id=document_id_str
            )
        except Exception as e: 
            logger.warning(f"Preview generation failed: {e}")

        # Text Extraction (OCR)
        _emit_progress(redis_client, user_id, document_id_str, "Ekstraktimi i tekstit (OCR)...", 25)
        extracted_text = text_extraction_service.extract_text(temp_original_file_path, document.get("mime_type", ""))
        
        if not extracted_text or not extracted_text.strip():
            raise ValueError("OCR dështoi: Dokumenti duket bosh.")

        # --- PHASE 2: METADATA & CLASSIFICATION ---
        
        # 1. Categorization (DeepSeek)
        _emit_progress(redis_client, user_id, document_id_str, "Klasifikimi Inteligjent...", 30)
        try:
            detected_category = CATEGORIZATION_SERVICE.categorize_document(extracted_text)
            db.documents.update_one({"_id": doc_id}, {"$set": {"category": detected_category}})
        except Exception:
            detected_category = "Unknown"

        # 2. Language Detection
        is_albanian = AlbanianLanguageDetector.detect_language(extracted_text)
        detected_lang = 'albanian' if is_albanian else 'standard'

        # --- PHASE 3: PARALLEL INTELLIGENCE ---
        # We run heavy tasks in parallel threads to speed up processing
        
        _emit_progress(redis_client, user_id, document_id_str, "Analizë e Thellë AI...", 40)
        logger.info(f"🚀 Starting Parallel AI Tasks for {document_id_str}...")
        
        def task_embeddings() -> bool:
            try:
                _emit_progress(redis_client, user_id, document_id_str, "Indeksimi Vektorial...", 50)
                base_doc_metadata = {
                    'document_id': document_id_str,
                    'case_id': case_id_str,
                    'user_id': user_id,
                    'file_name': doc_name,
                    'language': detected_lang,
                    'category': detected_category 
                }
                enriched_chunks = _process_and_split_text(extracted_text, base_doc_metadata)
                
                # Batch write to ChromaDB
                BATCH_SIZE = 10
                for i in range(0, len(enriched_chunks), BATCH_SIZE):
                    batch = enriched_chunks[i:i + BATCH_SIZE]
                    vector_store_service.create_and_store_embeddings_from_chunks(
                        document_id=document_id_str,
                        case_id=case_id_str,
                        chunks=[c['content'] for c in batch],
                        metadatas=[c['metadata'] for c in batch]
                    )
                return True
            except Exception as e:
                logger.error(f"Embedding Task Failed: {e}")
                return False

        def task_storage() -> Optional[str]:
            # Backup clean text to S3/MinIO
            try:
                return storage_service.upload_processed_text(
                    extracted_text, user_id=user_id, case_id=case_id_str, original_doc_id=document_id_str
                )
            except Exception: return None

        def task_summary() -> str:
            # DeepSeek Summary
            try:
                _emit_progress(redis_client, user_id, document_id_str, "Gjenerimi i Përmbledhjes...", 60)
                limit_start, limit_end = 25000, 10000
                if len(extracted_text) > (limit_start + limit_end):
                    optimized = extracted_text[:limit_start] + "\n\n...\n\n" + extracted_text[-limit_end:]
                else:
                    optimized = extracted_text
                return llm_service.generate_summary(optimized)
            except Exception: return "Përmbledhja nuk është e disponueshme."

        def task_findings() -> None:
            # DeepSeek Findings
            try:
                _emit_progress(redis_client, user_id, document_id_str, "Analiza e Gjetjeve...", 70)
                findings_service.extract_and_save_findings(db, document_id_str, extracted_text)
            except Exception as e: 
                logger.error(f"Findings Extraction Error: {e}")

        def task_deadlines() -> None:
            # DeepSeek Deadlines
            try:
                _emit_progress(redis_client, user_id, document_id_str, "Ekstraktimi i Afateve...", 80)
                deadline_service.extract_and_save_deadlines(db, document_id_str, extracted_text)
            except Exception as e:
                logger.error(f"Deadline Extraction Error: {e}")

        def task_graph() -> None:
            # DeepSeek Graph Extraction
            try:
                _emit_progress(redis_client, user_id, document_id_str, "Ndërtimi i Grafit...", 90)
                graph_data = llm_service.extract_graph_data(extracted_text)
                
                entities = graph_data.get("entities", [])
                relations = graph_data.get("relations", [])
                
                if entities or relations:
                    graph_service.ingest_entities_and_relations(
                        case_id=case_id_str,
                        document_id=document_id_str,
                        doc_name=doc_name,
                        entities=entities,
                        relations=relations
                    )
            except Exception as e:
                logger.error(f"Graph Ingestion Error: {e}")

        # Execute Parallel Tasks
        summary_result = None
        text_storage_key = None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            future_embed = executor.submit(task_embeddings)
            future_storage = executor.submit(task_storage)
            future_summary = executor.submit(task_summary)
            future_findings = executor.submit(task_findings)
            future_deadlines = executor.submit(task_deadlines)
            future_graph = executor.submit(task_graph)
            
            # PHOENIX FIX: Explicit typing for Pylance strict mode
            futures_list: List[concurrent.futures.Future[Any]] = [
                future_embed, future_storage, future_summary, 
                future_findings, future_deadlines, future_graph
            ]
            concurrent.futures.wait(futures_list)
            
            # Retrieve critical results
            try:
                summary_result = future_summary.result()
                text_storage_key = future_storage.result()
            except Exception: pass

        # --- PHASE 4: FINALIZATION ---
        _emit_progress(redis_client, user_id, document_id_str, "Përfunduar", 100)
        
        document_service.finalize_document_processing(
            db=db,
            redis_client=redis_client,
            doc_id_str=document_id_str, 
            summary=summary_result,
            processed_text_storage_key=text_storage_key,
            preview_storage_key=preview_storage_key
        )
        logger.info(f"✅ Document {document_id_str} processing completed successfully.")

    except Exception as e:
        _emit_progress(redis_client, user_id, document_id_str, "Dështoi: " + str(e), 0)
        logger.error(f"--- [CRITICAL FAILURE] Doc Processing: {e} ---", exc_info=True)
        db.documents.update_one(
            {"_id": doc_id},
            {"$set": {"status": DocumentStatus.FAILED, "error_message": str(e)}}
        )
        # Re-raise to ensure celery knows it failed
        raise e
        
    finally:
        # Cleanup
        if temp_original_file_path and os.path.exists(temp_original_file_path): os.remove(temp_original_file_path)
        if temp_pdf_preview_path and os.path.exists(temp_pdf_preview_path): os.remove(temp_pdf_preview_path)