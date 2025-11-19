# FILE: backend/app/tasks/document_processing.py
# PHOENIX PROTOCOL - TYPE SAFE & ROBUST
# 1. Passes 'redis_sync_client' to service to satisfy type requirements.
# 2. Uses 'Fresh Redis Connection' for the critical status update to ensure delivery.

from celery import shared_task
import structlog
import time
import json
from bson import ObjectId
from typing import Optional
from redis import Redis 

from app.core.db import db_instance, redis_sync_client # <--- We use this one for the service call
from app.core.config import settings 
from app.services import document_processing_service
from app.services.document_processing_service import DocumentNotFoundInDBError
from app.models.document import DocumentStatus

logger = structlog.get_logger(__name__)

def publish_sse_update(document_id: str, status: str, error: Optional[str] = None):
    """
    Helper to publish status updates to Redis for SSE.
    Uses a fresh connection to ensure reliability in Celery workers.
    """
    redis_client = None
    try:
        # 1. Establish a FRESH connection (Critical for Celery reliability)
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

        # 2. Get User ID
        doc = db_instance.documents.find_one({"_id": ObjectId(document_id)})
        if not doc:
            logger.warning("sse.doc_not_found", document_id=document_id)
            return
        
        user_id = str(doc.get("owner_id"))
        if not user_id or user_id == "None":
             user_id = str(doc.get("user_id"))

        # 3. Construct Payload
        payload = {
            "type": "DOCUMENT_STATUS",
            "document_id": document_id,
            "status": status,
            "error": error
        }
        
        # 4. Publish
        channel = f"user:{user_id}:updates"
        redis_client.publish(channel, json.dumps(payload))
        
        logger.info(f"🚀 SSE PUBLISHED: {channel} -> {status}")
        
    except Exception as e:
        logger.error("sse.publish_failed", error=str(e))
    finally:
        if redis_client:
            redis_client.close()

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
        time.sleep(2) 

    try:
        # FIXED: Passing redis_sync_client instead of None to satisfy Pylance
        document_processing_service.orchestrate_document_processing_mongo(
            db=db_instance,
            redis_client=redis_sync_client, 
            document_id_str=document_id_str
        )
        log.info("task.completed.success")
        
        # NOTIFY FRONTEND: SUCCESS (Uses the Robust Publisher)
        publish_sse_update(document_id_str, DocumentStatus.READY)

    except DocumentNotFoundInDBError as e:
        log.warning("task.retrying.doc_not_found", error=str(e))
        raise self.retry(exc=e)

    except Exception as e:
        log.error("task.failed.generic", error=str(e), exc_info=True)
        
        try:
            db_instance.documents.update_one(
                {"_id": ObjectId(document_id_str)},
                {"$set": {"status": DocumentStatus.FAILED, "error_message": str(e)}}
            )
            
            # NOTIFY FRONTEND: FAILURE
            publish_sse_update(document_id_str, DocumentStatus.FAILED, str(e))
            
        except Exception as db_fail_e:
             log.critical("task.CRITICAL_DB_FAILURE_ON_FAIL", error=str(db_fail_e))
        raise e