# FILE: backend/app/tasks/deadline_extraction.py
# PHOENIX PROTOCOL - TASK WRAPPER
# 1. BRIDGES the Celery Task to the Deadline Service logic.
# 2. Resolves the "cannot import name" error crashing the backend.

from celery import shared_task
import structlog
from app.core.db import db_instance
from app.services import deadline_service

logger = structlog.get_logger(__name__)

@shared_task(name="extract_deadlines_from_document")
def extract_deadlines_from_document(document_id: str, text_content: str):
    """
    Celery task wrapper for deadline extraction.
    Can be called asynchronously via .delay() or synchronously via .apply().
    """
    logger.info("task.deadline_extraction.started", document_id=document_id)
    
    try:
        deadline_service.extract_and_save_deadlines(
            db=db_instance,
            document_id=document_id,
            full_text=text_content
        )
        logger.info("task.deadline_extraction.success", document_id=document_id)
    except Exception as e:
        logger.error("task.deadline_extraction.failed", error=str(e), document_id=document_id)
        # We generally catch exceptions here so the main document processing flow doesn't crash completely
        # if just the deadline extraction fails.