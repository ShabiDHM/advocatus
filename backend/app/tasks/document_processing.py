# FILE: backend/app/tasks/document_processing.py
# PHOENIX PROTOCOL - INGESTION TASK V2.2 (BOOLEAN SAFETY)
# 1. FIX: Changed 'if global_db:' to 'if global_db is not None:' to satisfy PyMongo strict boolean rules.
# 2. STATUS: Resolves Pylance error regarding __bool__.

from celery import shared_task
import structlog
import time
import json
from bson import ObjectId
from typing import Optional, Dict
from redis import Redis 
from pymongo.database import Database

# Import connection functions for Lazy Init
from app.core.db import db_instance as global_db, redis_sync_client as global_redis, connect_to_mongo, connect_to_redis
from app.core.config import settings 
from app.services import document_processing_service
from app.services.graph_service import graph_service
from app.services.document_processing_service import DocumentNotFoundInDBError
from app.models.document import DocumentStatus

logger = structlog.get_logger(__name__)

def get_redis_safe() -> Redis:
    """Ensure we have a valid Redis connection."""
    # PHOENIX FIX: Explicit check against None
    if global_redis is not None:
        return global_redis
    return connect_to_redis()

def get_db_safe() -> Database:
    """Ensure we have a valid MongoDB connection."""
    # PHOENIX FIX: Explicit check against None (PyMongo requires this)
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
        
        user_id = str(doc.get("owner_id"))
        if not user_id or user_id == "None":
             user_id = str(doc.get("user_id"))

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

    if self.request.retries == 0:
        time.sleep(2) 

    try:
        db = get_db_safe()
        redis_client = get_redis_safe()
    except Exception as e:
        log.critical("task.connection_failure", error=str(e))
        raise e

    try:
        # Step 1: Perform core document processing
        processed_data = document_processing_service.orchestrate_document_processing_mongo(
            db=db,
            redis_client=redis_client, 
            document_id_str=document_id_str
        )
        log.info("task.mongo_processing_complete")

        # Step 2: Ingest into Graph
        if processed_data:
            log.info("task.graph_ingestion_started")
            # Explicit cast or check can be added if needed, but Optional[Dict] handles None
            meta: Optional[Dict] = processed_data.get("metadata")
            
            graph_service.ingest_entities_and_relations(
                case_id=processed_data.get("case_id"),
                document_id=document_id_str,
                doc_name=processed_data.get("doc_name"),
                entities=processed_data.get("entities", []),
                relations=processed_data.get("relations", []),
                doc_metadata=meta
            )
            log.info("task.graph_ingestion_complete")

        log.info("task.completed.success")
        publish_sse_update(document_id_str, DocumentStatus.READY)

    except DocumentNotFoundInDBError as e:
        log.warning("task.retrying.doc_not_found", error=str(e))
        raise self.retry(exc=e)

    except Exception as e:
        log.error("task.failed.generic", error=str(e), exc_info=True)
        try:
            # We re-fetch DB here just in case the error was connection related, 
            # though get_db_safe should have handled it.
            db_safe = get_db_safe()
            db_safe.documents.update_one(
                {"_id": ObjectId(document_id_str)},
                {"$set": {"status": DocumentStatus.FAILED, "error_message": str(e)}}
            )
            publish_sse_update(document_id_str, DocumentStatus.FAILED, str(e))
        except Exception as db_fail_e:
             log.critical("task.CRITICAL_DB_FAILURE_ON_FAIL", error=str(db_fail_e))
        raise e