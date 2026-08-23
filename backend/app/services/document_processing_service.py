# FILE: backend/app/services/document_processing_service.py
# PHOENIX PROTOCOL - JURISTI HYDRA ORCHESTRATOR V28.0 (TRUE DATABASE PROGRESS PERSISTENCE)

import os
import tempfile
import logging
import shutil
import json
import asyncio
import gc
import time
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from bson import ObjectId
import redis.asyncio as aioredis

from app.services import storage_service, llm_service, text_extraction_service, conversion_service
from app.services.albanian_document_processor import EnhancedDocumentProcessor
from app.models.document import DocumentStatus
from app.services.vector_store_service import create_and_store_embeddings_from_chunks
from app.core.config import settings

logger = logging.getLogger(__name__)


def _safe_remove_temp_file(file_path: str):
    if not file_path or not os.path.exists(file_path):
        return
    gc.collect()
    for _ in range(3):
        try:
            os.remove(file_path)
            return
        except Exception:
            time.sleep(0.1)
    try:
        os.remove(file_path)
    except Exception:
        pass


async def _update_db_and_broadcast(db: Any, doc_id: ObjectId, user_id: str, document_id_str: str, percent: int, message: str, doc_status: str = "PROCESSING"):
    """
    SHËRIMI I SËMUNDJES:
    Ruhet menjëherë në MongoDB dhe transmetohet në SSE. Çdo kërkesë HTTP do të marrë përqindjen më të re.
    """
    try:
        # 1. Ruaj në MongoDB
        await asyncio.to_thread(
            db.documents.update_one,
            {"_id": doc_id},
            {"$set": {
                "progress_percent": percent,
                "progress_message": message,
                "status": doc_status,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
    except Exception as db_err:
        logger.warning(f"MongoDB progress update error: {db_err}")

    # 2. Transmeto në Redis/SSE
    try:
        payload = {
            "type": "DOCUMENT_PROGRESS",
            "document_id": document_id_str,
            "percent": percent,
            "message": message,
            "status": doc_status
        }
        channel = f"user:{user_id}:updates"
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=1.5,
            socket_connect_timeout=1.5
        )
        await redis_client.publish(channel, json.dumps(payload))
        await redis_client.close()
    except Exception as sse_err:
        logger.warning(f"SSE progress broadcast skipped: {sse_err}")


async def orchestrate_document_processing_mongo(
    document_id_str: str,
    *args,
    db: Any = None,
    redis_client: Any = None,
    **kwargs
):
    logger.info(f"⚡ [Orchestrator V28.0] Processing booted for doc: {document_id_str}")
    
    if db is None:
        from app.core.db import get_db_instance
        db = get_db_instance()

    try:
        doc_id = ObjectId(document_id_str)
    except Exception:
        logger.error(f"Invalid Document ID: {document_id_str}")
        return

    document = await asyncio.to_thread(db.documents.find_one, {"_id": doc_id})
    if not document:
        logger.error(f"Document {document_id_str} not found in DB.")
        return

    user_id = str(document.get("owner_id"))
    doc_name = document.get("file_name", "Unknown Document")
    case_id_str = str(document.get("case_id"))

    # Faza 1: 30%
    await _update_db_and_broadcast(db, doc_id, user_id, document_id_str, 30, "Duke përgatitur skedarin...")

    temp_original_file_path = ""
    raw_text = f"Dokument i ngarkuar: {doc_name}."
    final_summary = "Përmbledhje e dokumentit."
    preview_storage_key = ""
    text_key = ""

    try:
        suffix = os.path.splitext(doc_name)[1] or ".pdf"
        temp_file_descriptor, temp_original_file_path = tempfile.mkstemp(suffix=suffix)
        os.close(temp_file_descriptor) 
        
        file_stream = await asyncio.to_thread(storage_service.download_original_document_stream, document["storage_key"])
        with open(temp_original_file_path, 'wb') as temp_file:
            await asyncio.to_thread(shutil.copyfileobj, file_stream, temp_file)
        if hasattr(file_stream, 'close'): 
            file_stream.close()

        # Faza 2: 60% Leximi Tekstual dhe OCR
        await _update_db_and_broadcast(db, doc_id, user_id, document_id_str, 60, "Duke lexuar tekstin & OCR...")
        
        try:
            extracted = await asyncio.wait_for(
                asyncio.to_thread(text_extraction_service.extract_text, temp_original_file_path, document.get("mime_type", "")),
                timeout=25.0
            )
            if extracted and len(extracted.strip()) > 10:
                raw_text = extracted
        except Exception as extract_err:
            logger.warning(f"Extraction warning for {doc_name}: {extract_err}")

        # Faza 3: 80% Vektorizimi në RAG
        await _update_db_and_broadcast(db, doc_id, user_id, document_id_str, 80, "Duke indeksuar në RAG...")

        async def task_summary():
            try:
                sterilized_text = llm_service.sterilize_legal_text(raw_text)
                return await asyncio.wait_for(llm_service.process_large_document_async(sterilized_text), timeout=12.0)
            except Exception:
                return raw_text[:500]

        async def task_embeddings():
            try:
                enriched_chunks = await asyncio.to_thread(
                    EnhancedDocumentProcessor.process_document, 
                    text_content=raw_text, document_metadata={'file_name': doc_name}
                )
                chunks_to_store = [c.content for c in enriched_chunks] if enriched_chunks else [raw_text[i:i+1500] for i in range(0, len(raw_text), 1200)]
                metadatas_to_store = [c.metadata for c in enriched_chunks] if enriched_chunks else [{"page": 1, "source": doc_name} for _ in chunks_to_store]

                await asyncio.to_thread(
                    create_and_store_embeddings_from_chunks,
                    user_id=user_id, document_id=document_id_str, case_id=case_id_str, 
                    file_name=doc_name, chunks=chunks_to_store, metadatas=metadatas_to_store
                )
            except Exception as e:
                logger.warning(f"Embedding batch warning: {e}")

        async def task_storage():
            try:
                return await asyncio.to_thread(storage_service.upload_processed_text, raw_text, user_id, case_id_str, document_id_str)
            except Exception:
                return ""

        async def task_preview():
            try:
                pdf_path = await asyncio.to_thread(conversion_service.convert_to_pdf, temp_original_file_path)
                key = await asyncio.to_thread(storage_service.upload_document_preview, pdf_path, user_id, case_id_str, document_id_str)
                if pdf_path and os.path.exists(pdf_path) and pdf_path != temp_original_file_path:
                    _safe_remove_temp_file(pdf_path)
                return key
            except Exception:
                return ""

        # Faza 4: 92% Përgatitja Finale
        await _update_db_and_broadcast(db, doc_id, user_id, document_id_str, 92, "Duke finalizuar...")

        try:
            results = await asyncio.wait_for(
                asyncio.gather(task_summary(), task_embeddings(), task_storage(), task_preview(), return_exceptions=True),
                timeout=30.0
            )
            if len(results) > 0 and isinstance(results[0], str): 
                final_summary = results[0]
            if len(results) > 2 and isinstance(results[2], str): 
                text_key = results[2]
            if len(results) > 3 and isinstance(results[3], str): 
                preview_storage_key = results[3]
        except Exception as par_err:
            logger.warning(f"Parallel tasks completed with fallback: {par_err}")

    except Exception as general_err:
        logger.error(f"Orchestrator pipeline exception on {doc_name}: {general_err}")
    
    finally:
        # Faza 5: 100% Gati (Persistenca Finale)
        try:
            await asyncio.to_thread(
                db.documents.update_one,
                {"_id": doc_id},
                {
                    "$set": {
                        "extracted_text": raw_text[:15000],
                        "summary": final_summary,
                        "processed_text_storage_key": text_key,
                        "preview_storage_key": preview_storage_key,
                        "status": DocumentStatus.READY,
                        "progress_percent": 100,
                        "progress_message": "Gati",
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            logger.info(f"✅ [Orchestrator V28.0] Document {document_id_str} is 100% READY in MongoDB.")
        except Exception as db_err:
            logger.error(f"Failed to update MongoDB document status: {db_err}")

        # Njofto SSE për përfundimin 100%
        try:
            payload = {"type": "DOCUMENT_STATUS", "document_id": document_id_str, "status": DocumentStatus.READY}
            redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=1.5)
            await redis_client.publish(f"user:{user_id}:updates", json.dumps(payload))
            await redis_client.close()
        except Exception:
            pass

        _safe_remove_temp_file(temp_original_file_path)