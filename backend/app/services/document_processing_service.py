# FILE: backend/app/services/document_processing_service.py
# PHOENIX PROTOCOL - JURISTI HYDRA ORCHESTRATOR V16.1 (HIGH VISIBILITY DIAGNOSTIC)
# 1. ADDED: High-visibility logger.info before and after every single sub-task.
# 2. STATUS: Designed to locate the exact "freeze" point at 75%.

import os, tempfile, logging, shutil, json, asyncio, hashlib
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
from pymongo.database import Database
import redis
from bson import ObjectId

from . import (
    document_service, 
    storage_service, 
    llm_service, 
    text_extraction_service, 
    conversion_service,
    deadline_service
)
from .graph_service import graph_service 
from .albanian_language_detector import AlbanianLanguageDetector
from .albanian_document_processor import EnhancedDocumentProcessor
from ..models.document import DocumentStatus

# Absolute imports for vector store functions
from app.services.vector_store_service import (
    delete_document_embeddings,
    create_and_store_embeddings_from_chunks,
    copy_document_embeddings
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Force Info level for diagnostics
OCR_FALLBACK_THRESHOLD = 100

class DocumentNotFoundInDBError(Exception): pass

def _compute_file_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''): sha256.update(chunk)
    return sha256.hexdigest()

def _stringify_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    result = {}
    for k, v in metadata.items():
        if isinstance(v, (str, int, float, bool)): result[k] = v
        else: result[k] = json.dumps(v, ensure_ascii=False)
    return result

async def _emit_progress_async(redis_client: redis.Redis, user_id: str, doc_id: str, message: str, percent: int):
    try:
        if not user_id or not redis_client: return
        channel = f"user:{user_id}:updates"
        payload = {"type": "DOCUMENT_PROGRESS", "document_id": doc_id, "message": message, "percent": percent}
        await asyncio.to_thread(redis_client.publish, channel, json.dumps(payload))
    except Exception: pass

async def orchestrate_document_processing_mongo(db: Database, redis_client: redis.Redis, document_id_str: str):
    logger.info(f"⚡ [Orchestrator] Starting processing pipeline for document: {document_id_str}")
    try: doc_id = ObjectId(document_id_str)
    except Exception: return

    document = await asyncio.to_thread(db.documents.find_one, {"_id": doc_id})
    if not document: raise DocumentNotFoundInDBError(document_id_str)

    user_id = str(document.get("owner_id"))
    doc_name = document.get("file_name", "Unknown Document")
    case_id_str = str(document.get("case_id"))
    
    await _emit_progress_async(redis_client, user_id, document_id_str, "Inicializimi...", 5)

    temp_original_file_path = ""
    file_hash = None
    
    try:
        suffix = os.path.splitext(doc_name)[1]
        temp_file_descriptor, temp_original_file_path = tempfile.mkstemp(suffix=suffix)
        os.close(temp_file_descriptor) 
        
        logger.info("⚡ [Orchestrator] Downloading file from Backblaze B2...")
        file_stream = await asyncio.to_thread(storage_service.download_original_document_stream, document["storage_key"])
        with open(temp_original_file_path, 'wb') as temp_file:
            await asyncio.to_thread(shutil.copyfileobj, file_stream, temp_file)
        if hasattr(file_stream, 'close'): file_stream.close()

        file_hash = _compute_file_hash(temp_original_file_path)

        # --- TEXT EXTRACTION ---
        logger.info("⚡ [Orchestrator] Step 1/3: Extracting text from document...")
        await _emit_progress_async(redis_client, user_id, document_id_str, "Ekstraktimi i tekstit...", 20)
        raw_text = await asyncio.to_thread(text_extraction_service.extract_text, temp_original_file_path, document.get("mime_type", ""))
        
        if not raw_text or not raw_text.strip():
            raise ValueError("Teksti i ekstraktuar është bosh.")

        # --- METADATA & CATEGORIZATION ---
        logger.info("⚡ [Orchestrator] Step 2/3: Running language detection and metadata parsing...")
        await _emit_progress_async(redis_client, user_id, document_id_str, "Analiza e strukturës...", 35)
        sterilized_text = llm_service.sterilize_legal_text(raw_text)
        is_albanian = AlbanianLanguageDetector.detect_language(sterilized_text)
        
        extracted_metadata = _stringify_metadata({"document_type": "Legal Document"})
        detected_category = "Unknown"
        
        await asyncio.to_thread(
            db.documents.update_one, 
            {"_id": doc_id}, 
            {"$set": {"detected_language": "sq" if is_albanian else "en", "category": detected_category, "metadata": extracted_metadata, "file_hash": file_hash}}
        )

        # --- ASYNC SUMMARY ---
        logger.info("⚡ [Orchestrator] Step 3/3: Initiating parallel processing tasks...")
        await _emit_progress_async(redis_client, user_id, document_id_str, "Gjenerimi i analizës...", 50)
        
        # Parallel tasks definitions with individual logs
        async def task_summary():
            logger.info("   [TASK START] -> Summary Generation")
            res = await llm_service.process_large_document_async(sterilized_text)
            logger.info("   [TASK COMPLETE] -> Summary Generation")
            return res

        async def task_embeddings():
            logger.info("   [TASK START] -> Vector Embeddings Generation")
            try:
                enriched_chunks = await asyncio.to_thread(
                    EnhancedDocumentProcessor.process_document, 
                    text_content=raw_text,
                    document_metadata={'category': detected_category, 'file_name': doc_name, **extracted_metadata}, 
                    is_albanian=is_albanian
                )
                success = await asyncio.to_thread(
                    create_and_store_embeddings_from_chunks,
                    user_id=user_id, document_id=document_id_str, case_id=case_id_str, 
                    file_name=doc_name, chunks=[c.content for c in enriched_chunks], 
                    metadatas=[c.metadata for c in enriched_chunks]
                )
                logger.info(f"   [TASK COMPLETE] -> Vector Embeddings (Success: {success})")
                return success
            except Exception as e:
                logger.error(f"   [TASK FAILED] -> Vector Embeddings: {e}")
                return False

        async def task_storage():
            logger.info("   [TASK START] -> Storage Upload (Processed Text)")
            res = await asyncio.to_thread(storage_service.upload_processed_text, raw_text, user_id, case_id_str, document_id_str)
            logger.info("   [TASK COMPLETE] -> Storage Upload")
            return res

        async def task_deadlines():
            logger.info("   [TASK START] -> Deadline Extraction")
            try:
                await asyncio.to_thread(deadline_service.extract_and_save_deadlines, db, document_id_str, sterilized_text, detected_category)
                logger.info("   [TASK COMPLETE] -> Deadline Extraction")
            except Exception as e:
                logger.warning(f"   [TASK SKIPPED] -> Deadline Extraction: {e}")

        async def task_graph():
            logger.info("   [TASK START] -> Neo4j Graph Ingestion")
            try:
                if not os.getenv("NEO4J_PASSWORD") or "REPLACE_WITH" in os.getenv("NEO4J_PASSWORD"):
                    logger.info("   [TASK SKIPPED] -> Neo4j (Credentials missing)")
                    return
                graph_data = await asyncio.to_thread(llm_service.extract_graph_data, sterilized_text)
                entities = graph_data.get("nodes") or []
                relations = graph_data.get("edges") or []
                await asyncio.to_thread(graph_service.ingest_entities_and_relations, case_id=case_id_str, document_id=document_id_str, doc_name=doc_name, entities=entities, relations=relations, doc_metadata=extracted_metadata)
                logger.info("   [TASK COMPLETE] -> Neo4j Graph Ingestion")
            except Exception as e:
                logger.warning(f"   [TASK FAILED] -> Neo4j: {e}")

        async def task_preview():
            logger.info("   [TASK START] -> PDF Preview Generation")
            try:
                pdf_path = await asyncio.to_thread(conversion_service.convert_to_pdf, temp_original_file_path)
                key = await asyncio.to_thread(storage_service.upload_document_preview, pdf_path, user_id, case_id_str, document_id_str)
                if pdf_path and os.path.exists(pdf_path): os.remove(pdf_path)
                logger.info("   [TASK COMPLETE] -> PDF Preview Generation")
                return key
            except Exception as e:
                logger.warning(f"   [TASK FAILED] -> PDF Preview: {e}")
                return ""

        await _emit_progress_async(redis_client, user_id, document_id_str, "Përpunimi i inteligjencës...", 75)
        
        # Execute all tasks in parallel
        logger.info("⚡ [Orchestrator] Launching asyncio.gather for parallel tasks...")
        results = await asyncio.gather(
            task_summary(),
            task_embeddings(),
            task_storage(),
            task_deadlines(),
            task_graph(),
            task_preview(),
            return_exceptions=True
        )
        
        final_summary = results[0] if not isinstance(results[0], Exception) else "Analiza e përmbledhjes dështoi."
        text_key = results[2] if not isinstance(results[2], Exception) else ""
        preview_storage_key = results[5] if not isinstance(results[5], Exception) else ""
        
        logger.info("⚡ [Orchestrator] Finalizing document processing records...")
        await _emit_progress_async(redis_client, user_id, document_id_str, "Përfunduar", 100)
        
        await asyncio.to_thread(
            document_service.finalize_document_processing, 
            db, redis_client, document_id_str, 
            final_summary, text_key, preview_storage_key
        )
        logger.info("⚡ [Orchestrator] SUCCESS: Pipeline finished.")

    except Exception as e:
        logger.error(f"❌ [Orchestrator] CRITICAL PIPELINE FAILURE: {e}")
        await asyncio.to_thread(db.documents.update_one, {"_id": doc_id}, {"$set": {"status": DocumentStatus.FAILED, "error_message": str(e), "file_hash": file_hash}})
        raise e
    finally:
        if temp_original_file_path and os.path.exists(temp_original_file_path): 
            os.remove(temp_original_file_path)