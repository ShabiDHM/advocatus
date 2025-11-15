# FILE: backend/app/tasks/drafting_tasks.py - CORRECTED VERSION
# PHOENIX PROTOCOL MODIFICATION: Validation Error Resilience

import asyncio
from bson import ObjectId
import logging
from datetime import datetime
from pydantic import ValidationError

from ..celery_app import celery_app
from ..services import drafting_service
from ..core.db import db_instance
from ..models.user import UserInDB

logger = logging.getLogger(__name__)

@celery_app.task(name="process_drafting_job", bind=True)
def process_drafting_job(self, user_id: str, request_data_dict: dict):
    """
    This task calls the drafting service to generate intelligent documents
    using the globally available database instance.
    """
    job_id = self.request.id
    logger.info(f"[JOB:{job_id}] Received drafting job for user {user_id}.")
    
    try:
        # PHOENIX PROTOCOL CURE: Enhanced user validation with error handling
        user_doc = db_instance.users.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            error_msg = f"User with ID {user_id} not found in the database."
            logger.error(f"[JOB:{job_id}] {error_msg}")
            raise Exception(error_msg)
        
        # Convert MongoDB document to UserInDB with validation
        try:
            user = UserInDB(**user_doc)
        except ValidationError as e:
            logger.error(f"[JOB:{job_id}] User data validation failed: {e}")
            logger.error(f"[JOB:{job_id}] Problematic user document: {user_doc}")
            raise Exception(f"User data validation failed: {str(e)}")
        
        async def run_draft_generation():
            stream_generator = drafting_service.generate_draft_stream(
                context=request_data_dict.get("context", ""),
                prompt_text=request_data_dict.get("prompt", ""),
                user=user,
                draft_type=request_data_dict.get("document_type"),
                case_id=request_data_dict.get("case_id"),
                jurisdiction=request_data_dict.get("jurisdiction"),
                favorability=request_data_dict.get("favorability"),
                db=db_instance
            )
            return "".join([chunk async for chunk in stream_generator])

        logger.info(f"[JOB:{job_id}] Starting intelligent draft generation...")
        final_document_text = asyncio.run(run_draft_generation())
        
        result_document = {
            "job_id": job_id, 
            "user_id": user_id, 
            "created_at": datetime.utcnow(),
            "status": "SUCCESS", 
            "request_data": request_data_dict,
            "result_text": final_document_text
        }
        db_instance.drafting_results.insert_one(result_document)
        
        logger.info(f"[JOB:{job_id}] Drafting job finished and result stored successfully.")
        return {"status": "complete", "message": "Result stored in MongoDB."}

    except Exception as e:
        logger.error(f"[JOB:{job_id}] A critical error occurred during drafting: {e}", exc_info=True)
        # Update the job status to FAILURE using the global db_instance.
        db_instance.drafting_results.update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "FAILURE", 
                "error_message": str(e), 
                "finished_at": datetime.utcnow()
            }},
            upsert=True
        )
        # Re-raise the original exception so Celery marks the task as failed
        raise