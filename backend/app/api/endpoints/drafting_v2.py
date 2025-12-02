# FILE: backend/app/api/endpoints/drafting_v2.py
# PHOENIX PROTOCOL - ROUTING CORRECTION
# 1. FIX: Removed the redundant 'prefix="/drafting"' from the APIRouter definition.
# 2. REASON: The correct prefix is applied once in main.py, fixing the "double prefix" issue that caused the 404 error.
# 3. STATUS: The endpoint routes are now correctly exposed at /api/v2/drafting/*.

from fastapi import APIRouter, Depends, status, HTTPException
from typing import Annotated
from pymongo.database import Database
from celery.result import AsyncResult
import logging

from ...models.user import UserInDB
from ...models.drafting import DraftRequest
from .dependencies import get_current_active_user, get_db
from ...celery_app import celery_app

# PHOENIX FIX: Prefix is removed. It is now handled correctly in main.py.
router = APIRouter(tags=["Drafting V2"])
logger = logging.getLogger(__name__)

@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_drafting_job(
    request_data: DraftRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
):
    try:
        task = celery_app.send_task(
            "process_drafting_job",
            kwargs={
                "case_id": request_data.case_id,
                "user_id": str(current_user.id),
                "draft_type": request_data.document_type,
                "user_prompt": request_data.prompt,
                "use_library": request_data.use_library
            }
        )
        job_id = task.id
        logger.info(f"Dispatched drafting job with Celery Task ID: {job_id} (Library: {request_data.use_library})")
        return {"status": "Job initiated successfully", "job_id": job_id}
    except Exception as e:
        logger.error(f"Failed to dispatch Celery task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate drafting job.")

@router.get("/jobs/{job_id}/status", status_code=status.HTTP_200_OK)
async def get_job_status(
    job_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
):
    task_result = AsyncResult(job_id, app=celery_app)
    task_status = task_result.status
    summary = task_result.result if task_status != "PENDING" else "Task is still pending."
    
    return {"job_id": job_id, "status": task_status, "result_summary": str(summary)}

@router.get("/jobs/{job_id}/result", status_code=status.HTTP_200_OK)
async def get_job_result(
    job_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Database = Depends(get_db)
):
    """
    Fetches the final result from MongoDB.
    """
    logger.info(f"Fetching result for job_id: {job_id}")
    result_doc = db.drafting_results.find_one({"job_id": job_id})

    if not result_doc:
        logger.warning(f"❌ Job {job_id} not found in drafting_results collection.")
        raise HTTPException(status_code=404, detail="No result found for job ID.")

    final_text = result_doc.get("result_text") or result_doc.get("document_text")
    
    if not final_text:
        logger.error(f"❌ Document found but TEXT is missing. Content: {str(result_doc)[:100]}...")
        raise HTTPException(status_code=404, detail="Result text not found in database record.")

    return {
        "job_id": job_id,
        "status": result_doc.get("status"),
        "result_text": final_text,
        "document_text": final_text 
    }