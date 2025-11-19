# FILE: backend/app/tasks/document_processing.py
# PHOENIX PROTOCOL - SSE PUBLISHER RESTORATION
# 1. Restores the logic to publish "DOCUMENT_STATUS" to Redis.
# 2. This fixes the "Pending Forever" issue on the frontend.

from celery import shared_task
import structlog
import time
import json
from bson import ObjectId
from typing import Optional

# Absolute imports for reliability
from app.core.db import db_instance, redis_sync_client
from app.services import document_processing_service
from app.services.document_processing_service import DocumentNotFoundInDBError
from app.models.document import DocumentStatus

logger = structlog.get_logger(__name__)

def publish_sse_update(document_id: str, status: str, error: Optional[str] = None):
    """
    Helper to publish status updates to Redis for SSE.
    This matches the channel the Frontend is listening to.
    """
    try:
        # 1. We need the User ID to know which channel to publish to.
        doc = db_instance.documents.find_one({"_id": ObjectId(document_id)})
        if not doc:
            return
        
        user_id = str(doc.get("owner_id"))
        if not user_id or user_id == "None":
             user_id = str(doc.get("user_id"))

        # 2. Construct the payload
        payload = {
            "type": "DOCUMENT_STATUS",
            "document_id": document_id,
            "status": status,
            "error": error
        }
        
        # 3. Publish to "user:{id}:updates"
        channel = f"user:{user_id}:updates"
        
        # Use the sync client for Celery tasks
        redis_sync_client.publish(channel, json.dumps(payload))
        
        structlog.get_logger(__name__).info("sse.published", channel=channel, status=status)
        
    except Exception as e:
        # Never let SSE failure break the actual task
        structlog.get_logger(__name__).error("sse.publish_failed", error=str(e))

@shared_task(
    bind=True,
    name='process_document_task',
    autoretry_for=(DocumentNotFoundInDBError,),
    retry_kwargs={'max_retries': 5, 'countdown': 10},
    default_retry_delay=10
)
def process_document_task(self, document_id_str: str):
    log = logger.bind(document_id=document_id_str, task_id=self.request.id)
    log.info("task.received", attempt=self.request.retries)

    if self.request.retries == 0:
        time.sleep(2) # Short pause to ensure DB commit

    try:
        # Run the heavy processing (Extraction, AI, Preview Generation)
        document_processing_service.orchestrate_document_processing_mongo(
            db=db_instance,
            redis_client=redis_sync_client,
            document_id_str=document_id_str
        )
        log.info("task.completed.success", attempt=self.request.retries)
        
        # --- PHOENIX FIX: NOTIFY FRONTEND ---
        # This is the line that makes the status flip to GREEN
        publish_sse_update(document_id_str, DocumentStatus.READY)

    except DocumentNotFoundInDBError as e:
        log.warning("task.retrying.doc_not_found", error=str(e), attempt=self.request.retries)
        raise self.retry(exc=e)

    except Exception as e:
        log.error("task.failed.generic", error=str(e), exc_info=True)
        
        try:
            db_instance.documents.update_one(
                {"_id": ObjectId(document_id_str)},
                {"$set": {"status": DocumentStatus.FAILED, "error_message": str(e)}}
            )
            log.critical("task.status_updated_to_failed", final_error=str(e))
            
            # Notify Frontend of Failure
            publish_sse_update(document_id_str, DocumentStatus.FAILED, str(e))
            
        except Exception as db_fail_e:
             log.critical("task.CRITICAL_DB_FAILURE_ON_FAIL", error=str(db_fail_e))
        raise e