# FILE: backend/app/tasks/deadline_extraction.py

import logging
# PHOENIX PROTOCOL CURE: Use an absolute import to permanently resolve linter path issues.
from app.celery_app import celery_app
from ..services import deadline_service
from ..core.db import db_instance

logger = logging.getLogger(__name__)

@celery_app.task(name="extract_deadlines_from_document")
def extract_deadlines_from_document(document_id: str, full_text: str):
    """
    Celery task to extract deadlines using the globally available database instance.
    """
    logger.info(f"--- [Task] Starting deadline extraction for document_id: {document_id} ---")
    try:
        deadline_service.extract_and_save_deadlines(
            db=db_instance, 
            document_id=document_id, 
            full_text=full_text
        )
        logger.info(f"--- [Task] Successfully completed deadline extraction for document_id: {document_id} ---")
    except Exception as e:
        logger.error(f"--- [Task FAILURE] Error during deadline extraction for document_id: {document_id}. Reason: {e}", exc_info=True)
        # Re-raising the exception allows Celery to register the task as 'FAILED'.
        raise