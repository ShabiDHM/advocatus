# FILE: backend/app/tasks/document_processing.py
# PHOENIX PROTOCOL - JURISTI HYDRA WORKER V3.0
# 1. BRIDGE: Integrated asyncio.run to call the refactored Hydra Orchestrator (V14.0).
# 2. DE-DUPLICATION: Removed redundant graph ingestion (now handled in parallel by the service).
# 3. STATUS: Optimized for high-speed parallel document processing.

import asyncio
import structlog
import time
import json
from celery import shared_task
from bson import ObjectId
from typing import Optional, Dict
from redis import Redis 
from pymongo.database import Database

# Import connection functions for Lazy Init
from app.core.db import db_instance as global_db, redis_sync_client as global_redis, connect_to_mongo, connect_to_redis
from app.core.config import settings 
from app.services import document_processing_service
from app.services.document_processing_service import DocumentNotFoundInDBError
from app.models.document import DocumentStatus

logger = structlog.get_logger(__name__)

def get_redis_safe() -> Redis:
    """Ensure we have a valid Redis connection."""
    if global_redis is not None:
        return global_redis
    return connect_to_redis()

def get_db_safe() -> Database:
    """Ensure we have a valid MongoDB connection."""
    if global_db is not None:
        return global_db
    _, db = connect_to_mongo()
    return db

def publish_sse_update(document_id: str, status: str, error: Optional[str] = None):
    """
    Helper to publish status updates to Redis for SSE.
    """
    redis_client = None
    try:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        db = get_db_safe()
        
        doc = db.documents.find_one({"_id": ObjectId(document_id)})
        if not doc:
            logger.warning("sse.doc_not_found", document_id=document_id)
            return
        
        user_id = str(doc.get("owner_id") or doc.get("user_id"))

        payload = {
            "type": "DOCUMENT_STATUS",
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

    # Initial delay for DB consistency on first attempt
    if self.request.retries == 0:
        time.sleep(1) 

    try:
        db = get_db_safe()
        redis_client = get_redis_safe()
    except Exception as e:
        log.critical("task.connection_failure", error=str(e))
        raise e

    try:
        log.info("task.hydra_orchestration_started")
        
        # PHOENIX BRIDGE: Running the Async Hydra Orchestrator inside the Sync Celery Task
        # Note: orchestrate_document_processing_mongo (V14.0) now handles 
        # Embeddings, Summary, Deadlines, Graph, and Storage in parallel.
        asyncio.run(
            document_processing_service.orchestrate_document_processing_mongo(
                db=db,
                redis_client=redis_client, 
                document_id_str=document_id_str
            )
        )

        log.info("task.completed.success")
        # Status update is handled inside finalize_document_processing, 
        # but we send a final SSE trigger here for UI refreshment.
        publish_sse_update(document_id_str, DocumentStatus.READY)

    except DocumentNotFoundInDBError as e:
        log.warning("task.retrying.doc_not_found", error=str(e))
        raise self.retry(exc=e)

    except Exception as e:
        log.error("task.failed.generic", error=str(e), exc_info=True)
        try:
            db_safe = get_db_safe()
            db_safe.documents.update_one(
                {"_id": ObjectId(document_id_str)},
                {"$set": {"status": DocumentStatus.FAILED, "error_message": str(e)}}
            )
            publish_sse_update(document_id_str, DocumentStatus.FAILED, str(e))
        except Exception as db_fail_e:
             log.critical("task.CRITICAL_DB_FAILURE_ON_FAIL", error=str(db_fail_e))
        raise e