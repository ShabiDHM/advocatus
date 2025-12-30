# FILE: backend/app/tasks/drafting_tasks.py
# PHOENIX PROTOCOL - DRAFTING TASK (AGENTIC) V2.1 (TYPE FIX)
# 1. FIX: Resolved 'self.request.id' attribute access error for Pylance.
# 2. STATUS: Type-safe and production-ready.

import logging
import asyncio
from datetime import datetime, timezone
from celery import shared_task, Task

# Use a generic way to get the DB instance inside a Celery task
from app.core.db import get_db
from app.services import drafting_service

logger = logging.getLogger(__name__)

@shared_task(name="process_drafting_job", bind=True)
def process_drafting_job(
    self: Task, # Explicitly type 'self' as a Celery Task
    case_id: str,
    user_id: str,
    draft_type: str,
    user_prompt: str,
    use_library: bool 
):
    """
    Celery task to run the agentic drafting service in the background.
    """
    # PHOENIX FIX: Assign request.id to a variable to help Pylance resolve the type
    job_id = self.request.id
    if not job_id:
        logger.error("Celery task started without a request ID. Aborting.")
        return "Task failed: No ID."

    logger.info(f"[JOB:{job_id}] Starting AGENTIC drafting job for user {user_id}.")
    
    # Get a DB instance from the generator
    db_gen = get_db()
    db = next(db_gen)

    try:
        # Run the async service function using asyncio.run
        final_draft = asyncio.run(drafting_service.generate_draft(
            db=db,
            user_id=user_id,
            case_id=case_id,
            draft_type=draft_type,
            user_prompt=user_prompt
        ))

        # Save the result to the database
        db.drafting_results.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "job_id": job_id,
                    "status": "COMPLETED",
                    "result_text": final_draft,
                    "document_text": final_draft, # For compatibility
                    "completed_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        logger.info(f"✅ AGENTIC drafting job {job_id} completed successfully.")
        return "Drafting completed successfully."

    except Exception as e:
        logger.error(f"❌ AGENTIC drafting job {job_id} failed: {e}", exc_info=True)
        # Save error state to the database
        db.drafting_results.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "job_id": job_id,
                    "status": "FAILED",
                    "error": str(e),
                    "completed_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        # Re-raise the exception so Celery marks the task as FAILED
        raise