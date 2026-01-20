# FILE: backend/app/tasks/deadline_extraction.py
# PHOENIX PROTOCOL - DEADLINE TASK V2.0 (TYPE SAFETY)
# 1. FIX: Implemented 'get_db_safe' to resolve Pylance 'None' type error.
# 2. LOGIC: Ensures valid DB connection for Celery worker.

from celery import shared_task
import structlog
from pymongo.database import Database

# PHOENIX FIX: Safe DB connection logic imports
from app.core.db import db_instance as global_db, connect_to_mongo
from app.services import deadline_service

logger = structlog.get_logger(__name__)

def get_db_safe() -> Database:
    """Ensure we have a valid MongoDB connection."""
    if global_db is not None:
        return global_db
    _, db = connect_to_mongo()
    return db

@shared_task(name="extract_deadlines_from_document")
def extract_deadlines_from_document(document_id: str, text_content: str):
    """
    Celery task wrapper for deadline extraction.
    """
    logger.info("task.deadline_extraction.started", document_id=document_id)
    
    try:
        # PHOENIX FIX: Use safe getter to ensure non-None Database
        db = get_db_safe()
        
        deadline_service.extract_and_save_deadlines(
            db=db,
            document_id=document_id,
            full_text=text_content
        )
        logger.info("task.deadline_extraction.success", document_id=document_id)
    except Exception as e:
        logger.error("task.deadline_extraction.failed", error=str(e), document_id=document_id)
        # We catch exceptions so the main process continues even if deadlines fail