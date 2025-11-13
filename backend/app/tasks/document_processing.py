# FILE: /app/app/tasks/document_processing.py

from celery import shared_task
import structlog
import time
from bson import ObjectId

# PHOENIX PROTOCOL CURE: Use absolute imports to permanently resolve linter path issues.
from app.core.db import db_instance, redis_sync_client
from app.services import document_processing_service
from app.services.document_processing_service import DocumentNotFoundInDBError
from app.models.document import DocumentStatus

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

    if self.request.retries == 0:
        time.sleep(5)

    try:
        document_processing_service.orchestrate_document_processing_mongo(
            db=db_instance,
            redis_client=redis_sync_client,
            document_id_str=document_id_str
        )
        log.info("task.completed.success", attempt=self.request.retries)

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
        except Exception as db_fail_e:
             log.critical("task.CRITICAL_DB_FAILURE_ON_FAIL", error=str(db_fail_e))
        raise e