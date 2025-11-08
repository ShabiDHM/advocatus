# backend/app/tasks/deadline_extraction.py
# DEFINITIVE VERSION 3.0 (ARCHITECTURAL CORRECTION):
# Task now creates its own DB connection and passes it to the refactored service.

from ..celery_app import celery_app
from ..services import deadline_service
# PHOENIX PROTOCOL FIX: Import connection logic, not dependency providers
from ..core.db import connect_to_mongo, close_mongo_connections

@celery_app.task(name="extract_deadlines_from_document")
def extract_deadlines_from_document(document_id: str, full_text: str):
    """
    Celery task to extract deadlines. Manages its own database connection.
    """
    mongo_client = None
    try:
        mongo_client, db = connect_to_mongo()
        deadline_service.extract_and_save_deadlines(db=db, document_id=document_id, full_text=full_text)
    finally:
        if mongo_client:
            close_mongo_connections(sync_client=mongo_client, async_client=None)