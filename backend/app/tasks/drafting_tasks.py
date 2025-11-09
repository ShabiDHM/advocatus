# FILE: backend/app/tasks/drafting_tasks.py
# PHOENIX PROTOCOL DEFINITIVE CURE (EXPLICIT CONDITIONAL):
# 1. DISEASE IDENTIFIED: The `except` block contained an ambiguous conditional check ('if db:')
#    which is forbidden by the PyMongo driver and was causing a secondary crash, overriding
#    the original, user-friendly error message.
# 2. THE CURE: The conditional has been changed to the explicit, type-safe check:
#    'if db is not None:'.
# 3. This is the definitive fix. It allows the error handling logic to execute correctly,
#    ensuring that when a drafting job fails, the true cause is properly logged and the
#    job is marked as a "FAILURE" in the database, curing the final bug.

import asyncio
from bson import ObjectId
import logging
from datetime import datetime

from ..celery_app import celery_app
from ..services import drafting_service
from ..core.db import connect_to_mongo, close_mongo_connections
from ..models.user import UserInDB

logger = logging.getLogger(__name__)

@celery_app.task(name="process_drafting_job", bind=True)
def process_drafting_job(self, user_id: str, request_data_dict: dict):
    """
    This task calls the drafting service to generate intelligent documents.
    It manages its own database connection.
    """
    job_id = self.request.id
    logger.info(f"[JOB:{job_id}] Received drafting job for user {user_id}.")
    
    mongo_client = None
    db = None
    try:
        mongo_client, db = connect_to_mongo()
        
        user_doc = db.users.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            raise Exception(f"User with ID {user_id} not found in the database.")
        user = UserInDB(**user_doc)

        async def run_draft_generation():
            stream_generator = drafting_service.generate_draft_stream(
                context=request_data_dict.get("context", ""),
                prompt_text=request_data_dict.get("prompt", ""),
                user=user,
                draft_type=request_data_dict.get("document_type"),
                case_id=request_data_dict.get("case_id"),
                jurisdiction=request_data_dict.get("jurisdiction"),
                favorability=request_data_dict.get("favorability"),
                db=db
            )
            return "".join([chunk async for chunk in stream_generator])

        logger.info(f"[JOB:{job_id}] Starting intelligent draft generation...")
        final_document_text = asyncio.run(run_draft_generation())
        
        result_document = {
            "job_id": job_id, "user_id": user_id, "created_at": datetime.utcnow(),
            "status": "SUCCESS", 
            "request_data": request_data_dict,
            "result_text": final_document_text
        }
        db.drafting_results.insert_one(result_document)
        
        logger.info(f"[JOB:{job_id}] Drafting job finished and result stored successfully.")
        return {"status": "complete", "message": "Result stored in MongoDB."}

    except Exception as e:
        logger.error(f"[JOB:{job_id}] A critical error occurred during drafting: {e}", exc_info=True)
        # --- THE CURE: Use explicit 'is not None' check ---
        if db is not None:
            db.drafting_results.update_one(
                {"job_id": job_id},
                {"$set": {"status": "FAILURE", "error_message": str(e), "finished_at": datetime.utcnow()}},
                upsert=True
            )
        # Re-raise the original exception so Celery marks the task as failed
        raise
    finally:
        if mongo_client:
            close_mongo_connections(sync_client=mongo_client, async_client=None)