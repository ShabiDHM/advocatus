# FILE: app/api/endpoints/cases/analysis_router.py
# PHOENIX PROTOCOL - ANALYSIS ROUTER V12.0 (REACTIVE INSTANT WAR ROOM ROUTER)

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from typing import Annotated, Optional
from fastapi.responses import JSONResponse
from pymongo.database import Database
import asyncio
import logging
from datetime import datetime, timezone

from app.services import analysis_service, llm_service, spreadsheet_service, case_service
from app.models.user import UserInDB
from app.models.drafting import DraftRequest
from app.api.endpoints.dependencies import get_current_user, get_db
from app.api.endpoints.cases.cases_helpers import (
    validate_object_id,
    require_pro_tier,
    FinanceInterrogationRequest,
    ArchiveStrategyRequest
)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/{case_id}/analyze")
async def run_textual_case_analysis(
    case_id: str,
    client_position: Optional[str] = Query(None),
    force: Optional[bool] = Query(False),
    current_user: Annotated[UserInDB, Depends(get_current_user)] = None,
    db: Database = Depends(get_db)
):
    validate_object_id(case_id)
    analysis_result = await analysis_service.cross_examine_case(
        db, 
        case_id, 
        str(current_user.id),
        client_position=client_position,
        force=force or False
    )
    return JSONResponse(content=analysis_result)

@router.post("/{case_id}/analyze/clear", status_code=status.HTTP_200_OK)
async def clear_case_analysis_endpoint(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": case_oid},
        {
            "$unset": {
                "latest_analysis": "",
                "latest_deep_analysis": "",
                "analyzed_doc_ids": ""
            },
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    return {"status": "success", "message": "Persistent analysis cleared successfully."}

@router.post("/{case_id}/deep-analysis", dependencies=[Depends(require_pro_tier)])
async def run_deep_case_analysis(
    case_id: str,
    client_position: Optional[str] = Query(None),
    current_user: Annotated[UserInDB, Depends(get_current_user)] = None,
    db: Database = Depends(get_db)
):
    validate_object_id(case_id)
    result = await analysis_service.run_deep_strategy(
        db, case_id, str(current_user.id), client_position=client_position
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    
    return JSONResponse(result)

@router.post("/{case_id}/archive-strategy", dependencies=[Depends(require_pro_tier)])
async def archive_case_strategy_endpoint(
    case_id: str,
    body: ArchiveStrategyRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    validate_object_id(case_id)
    result = await analysis_service.archive_full_strategy_report(
        db, case_id, str(current_user.id), body.legal_data, body.deep_data
    )
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return JSONResponse(result)

@router.post("/{case_id}/drafts", status_code=status.HTTP_202_ACCEPTED)
async def create_draft_for_case(
    case_id: str,
    job_in: DraftRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    validated_case_id = validate_object_id(case_id)
    return await asyncio.to_thread(
        case_service.create_draft_job_for_case,
        db=db,
        case_id=validated_case_id,
        job_in=job_in,
        owner=current_user
    )