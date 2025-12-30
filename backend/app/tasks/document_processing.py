# FILE: backend/app/tasks/document_processing.py
# PHOENIX PROTOCOL - ARCHIVE PROCESSING V1.1 (FIX)
# 1. FIX: Added 'from datetime import datetime' to resolve NameError.
# 2. STATUS: Clean build.

from celery import shared_task
import structlog
import time
import json
import io
from datetime import datetime # <--- FIXED MISSING IMPORT
from bson import ObjectId
from typing import Optional
from redis import Redis 

from app.core.db import db_instance, redis_sync_client
from app.core.config import settings 
from app.services import document_processing_service, storage_service, text_extraction_service, vector_store_service
from app.services.document_processing_service import DocumentNotFoundInDBError
from app.models.document import DocumentStatus

logger = structlog.get_logger(__name__)

def publish_sse_update(document_id: str, status: str, error: Optional[str] = None, is_archive: bool = False):
    redis_client = None
    try:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        collection = db_instance.archives if is_archive else db_instance.documents
        doc = collection.find_one({"_id": ObjectId(document_id)})
        
        if not doc:
            logger.warning("sse.doc_not_found", document_id=document_id)
            return
        
        user_id = str(doc.get("owner_id") or doc.get("user_id"))
        payload = {
            "type": "ARCHIVE_STATUS" if is_archive else "DOCUMENT_STATUS",
            "document_id": document_id,
            "status": status,
            "error": error
        }
        channel = f"user:{user_id}:updates"
        redis_client.publish(channel, json.dumps(payload))
        logger.info(f"🚀 SSE PUBLISHED: {channel} -> {status}")
    except Exception as e:
        logger.error("sse.publish_failed", error=str(e))
    finally:
        if redis_client: redis_client.close()

@shared_task(bind=True, name='process_document_task', autoretry_for=(DocumentNotFoundInDBError,), retry_kwargs={'max_retries': 5, 'countdown': 10}, default_retry_delay=10)
def process_document_task(self, document_id_str: str):
    log = logger.bind(document_id=document_id_str, task_id=self.request.id)
    log.info("task.received", attempt=self.request.retries)
    if self.request.retries == 0: time.sleep(2) 
    try:
        document_processing_service.orchestrate_document_processing_mongo(db=db_instance, redis_client=redis_sync_client, document_id_str=document_id_str)
        log.info("task.completed.success")
        publish_sse_update(document_id_str, DocumentStatus.READY)
    except DocumentNotFoundInDBError as e:
        log.warning("task.retrying.doc_not_found", error=str(e)); raise self.retry(exc=e)
    except Exception as e:
        log.error("task.failed.generic", error=str(e), exc_info=True)
        try:
            db_instance.documents.update_one({"_id": ObjectId(document_id_str)}, {"$set": {"status": DocumentStatus.FAILED, "error_message": str(e)}})
            publish_sse_update(document_id_str, DocumentStatus.FAILED, str(e))
        except Exception: pass
        raise e

@shared_task(bind=True, name='app.tasks.document_processing.process_archive_document')
def process_archive_document(self, archive_id_str: str):
    log = logger.bind(archive_id=archive_id_str, task="archive_ingestion")
    log.info("archive_task.started")
    try:
        item = db_instance.archives.find_one({"_id": ObjectId(archive_id_str)})
        if not item: log.error("archive_task.item_not_found"); return
        user_id = str(item["user_id"])
        
        db_instance.archives.update_one({"_id": ObjectId(archive_id_str)}, {"$set": {"indexing_status": "PROCESSING"}})
        publish_sse_update(archive_id_str, "PROCESSING", is_archive=True)

        storage_key = item.get("storage_key")
        if not storage_key: raise ValueError("No storage key found")
        file_bytes = storage_service.download_processed_text(storage_key)
        if not file_bytes: raise ValueError("Empty file content")

        from io import BytesIO
        file_obj = BytesIO(file_bytes)
        text_content = text_extraction_service.extract_text_from_file(file_obj, item.get("file_type", "PDF"))
        
        if not text_content or len(text_content) < 50: raise ValueError("No extractable text found.")

        from langchain.text_splitter import RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_text(text_content)
        metadatas = [{"source": "archive", "archive_id": archive_id_str, "language": "sq"} for _ in chunks]

        success = vector_store_service.create_and_store_embeddings_from_chunks(user_id=user_id, document_id=archive_id_str, case_id="archive", file_name=item["title"], chunks=chunks, metadatas=metadatas)
        if not success: raise RuntimeError("Vector embedding failed")

        db_instance.archives.update_one({"_id": ObjectId(archive_id_str)}, {"$set": {"indexing_status": "COMPLETED", "last_indexed": datetime.utcnow()}})
        log.info("archive_task.success")
        publish_sse_update(archive_id_str, "COMPLETED", is_archive=True)
    except Exception as e:
        log.error("archive_task.failed", error=str(e))
        db_instance.archives.update_one({"_id": ObjectId(archive_id_str)}, {"$set": {"indexing_status": "FAILED", "indexing_error": str(e)}})
        publish_sse_update(archive_id_str, "FAILED", str(e), is_archive=True)