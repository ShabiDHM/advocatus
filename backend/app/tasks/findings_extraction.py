# FILE: backend/app/tasks/findings_extraction.py
# DEFINITIVE VERSION 4.0 (PHOENIX PROTOCOL: CRASH FIX)
# 1. CRITICAL FIX: Changed the invalid database check from 'if not db:' to 'if db is None:'.
#    This resolves the 'NotImplementedError' crash caused by PyMongo's library constraints.

import structlog
from ..celery_app import celery_app, worker_state 
from ..services import findings_service
from pymongo.database import Database
from typing import Optional

logger = structlog.get_logger(__name__)

@celery_app.task(name="extract_findings_from_document")
def extract_findings_from_document(document_id: str, full_text: str) -> str:
    """
    Accepts document text, delegates to the service, and returns a status message.
    """
    log = logger.bind(document_id=document_id)
    log.info("findings_extraction.task.received")
    
    db: Optional[Database] = worker_state.get('db')
    
    # --- PHOENIX PROTOCOL FIX: Use 'is None' for PyMongo Database object validation ---
    if db is None:
        log.error("findings_extraction.db_connection_missing")
        raise RuntimeError("MongoDB connection not available in worker state.")
    # --------------------------------------------------------------------------------------
    
    try:
        findings_saved_count = findings_service.extract_and_save_findings(db, document_id, full_text)
        result_message = f"Successfully saved {findings_saved_count} findings."
        log.info("findings_extraction.task.success", message=result_message)
        return result_message
    except Exception as e:
        log.error("findings_extraction.task.failure", error=str(e), exc_info=True)
        raise