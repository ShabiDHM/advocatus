# FILE: backend/app/tasks/findings_extraction.py

import structlog
from typing import Optional # <-- PHOENIX PROTOCOL CURE: Import Optional for correct type hinting.
from ..celery_app import celery_app
from ..services import findings_service
from ..core.db import get_db
from pymongo.database import Database

logger = structlog.get_logger(__name__)

@celery_app.task(name="extract_findings_from_document", bind=True)
def extract_findings_from_document(self, document_id: str, full_text: str) -> str:
    """
    Acquires its own DB connection, delegates to the findings service, and returns a status message.
    This stateless approach is robust and eliminates the ImportError that crashed the worker.
    """
    log = logger.bind(document_id=document_id, task_id=self.request.id)
    log.info("findings_extraction.task.received")

    # PHOENIX PROTOCOL CURE: Use Optional[Database] to correctly type the variable.
    db: Optional[Database] = None
    try:
        db_generator = get_db()
        db = next(db_generator)

        if db is None:
            log.error("findings_extraction.db_connection_failed")
            raise RuntimeError("Failed to acquire MongoDB connection from the provider.")

        findings_saved_count = findings_service.extract_and_save_findings(db, document_id, full_text)
        result_message = f"Successfully saved {findings_saved_count} findings."
        log.info("findings_extraction.task.success", count=findings_saved_count)
        return result_message

    except Exception as e:
        log.error("findings_extraction.task.failure", error=str(e), exc_info=True)
        self.retry(exc=e, countdown=60, max_retries=3)
        # PHOENIX PROTOCOL CURE: Add a raise to make the exceptional exit explicit to the linter,
        # satisfying the return type requirement. This does not change runtime behavior as self.retry also raises.
        raise

    finally:
        if db is not None and 'db_generator' in locals():
            try:
                next(db_generator, None)
            except StopIteration:
                pass
            log.info("findings_extraction.task.db_connection_closed")