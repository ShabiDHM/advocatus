# FILE: /app/app/tasks/document_processing.py
# PHOENIX PROTOCOL MODIFICATION V5.1 (STATE MACHINE ALIGNMENT):
# 1. CONTRACT COMPLIANCE: The generic exception handler now imports and uses the
#    `DocumentStatus` Enum from the application's models.
# 2. ROBUSTNESS: The hardcoded status string `"FAILED"` has been replaced with
#    `DocumentStatus.FAILED`. This ensures that even in failure scenarios, the
#    document status adheres strictly to the authoritative data contract.
#
# DEFINITIVE VERSION 20.3 (PHOENIX PROTOCOL FIX: Backend Hard Crash Resolution)
# Fixed the invalid boolean check on the PyMongo database object (db) in the exception handler.

from celery import shared_task
import structlog
import time
from bson import ObjectId

from ..core.db import connect_to_mongo, connect_to_sync_redis, close_mongo_connections
from ..services import document_processing_service
from ..services.document_processing_service import DocumentNotFoundInDBError
# --- PHOENIX PROTOCOL: Import the authoritative Enum ---
from ..models.document import DocumentStatus

logger = structlog.get_logger(__name__)

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

    # Simple backoff to avoid immediate thrashing on transient errors
    if self.request.retries == 0:
        time.sleep(5)

    mongo_client = None
    redis_client = None
    db = None
    try:
        mongo_client, db = connect_to_mongo()
        redis_client = connect_to_sync_redis()

        document_processing_service.orchestrate_document_processing_mongo(
            db=db,
            redis_client=redis_client,
            document_id_str=document_id_str
        )
        log.info("task.completed.success", attempt=self.request.retries)

    except DocumentNotFoundInDBError as e:
        log.warning("task.retrying.doc_not_found", error=str(e), attempt=self.request.retries)
        raise self.retry(exc=e)

    except Exception as e:
        log.error("task.failed.generic", error=str(e), exc_info=True)
        
        if db is not None: 
            try:
                # --- PHOENIX PROTOCOL: Use the Enum for the FAILED state ---
                db.documents.update_one(
                    {"_id": ObjectId(document_id_str)},
                    {"$set": {"status": DocumentStatus.FAILED, "error_message": str(e)}}
                )
                log.critical("task.status_updated_to_failed", final_error=str(e))
            except Exception as db_fail_e:
                 log.critical("task.CRITICAL_DB_FAILURE_ON_FAIL", error=str(db_fail_e))
        raise e

    finally:
        if mongo_client:
            close_mongo_connections(mongo_client, None)
        if redis_client:
            redis_client.close()