# FILE: backend/app/api/endpoints/drafting_v2.py
# DEFINITIVE VERSION 18.4 (ARCHITECTURAL CORRECTION):
# Corrected the import path for 'get_db' to align with the centralized
# dependency architecture, resolving the 'ImportError' startup crash.

from fastapi import APIRouter, Depends, status, HTTPException
from typing import Annotated
from pymongo.database import Database
from celery.result import AsyncResult
import logging

from ...models.user import UserInDB
from ...models.drafting import DraftRequest
# --- PHOENIX PROTOCOL FIX: Import all dependencies from the correct, centralized location ---
from .dependencies import get_current_active_user, get_db
from ...tasks.drafting_tasks import process_drafting_job
from ...celery_app import celery_app

router = APIRouter(prefix="/api/v2/drafting", tags=["Drafting V2"])
logger = logging.getLogger(__name__)


@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_drafting_job(
    request_data: DraftRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
):
    """
    Initiates a new drafting job.
    """
    try:
        task = process_drafting_job.delay(
            user_id=str(current_user.id),
            request_data_dict=request_data.model_dump()
        )
        job_id = task.id
        logger.info(f"Dispatched drafting job with Celery Task ID: {job_id}")
        return {"status": "Job initiated successfully", "job_id": job_id}
    except Exception as e:
        logger.error(f"Failed to dispatch Celery task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate drafting job.")


@router.get("/jobs/{job_id}/status", status_code=status.HTTP_200_OK)
async def get_job_status(
    job_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
):
    """
    Polls for the status of an existing drafting job.
    """
    logger.debug(f"Checking status for job_id: {job_id}")
    task_result = AsyncResult(job_id, app=celery_app)
    task_status = task_result.status
    
    summary = task_result.result if task_status != "PENDING" else "Task is still pending."
    
    response = {"job_id": job_id, "status": task_status, "result_summary": summary}
    if task_status == "FAILURE":
        response["result_summary"] = str(summary)
    
    return response


@router.get("/jobs/{job_id}/result", status_code=status.HTTP_200_OK)
async def get_job_result(
    job_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Database = Depends(get_db)
):
    """
    Fetches the final result of a completed drafting job from MongoDB.
    """
    logger.info(f"Fetching result for job_id: {job_id}")
    result_doc = db.drafting_results.find_one({"job_id": job_id})

    if not result_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No result found for job ID: {job_id}."
        )

    final_text = result_doc.get("result_text")
    if not final_text:
        raise HTTPException(
            status_code=404,
            detail=f"Result text not found for job ID: {job_id}."
        )

    return {
        "job_id": job_id,
        "status": result_doc.get("status"),
        "result_text": final_text
    }