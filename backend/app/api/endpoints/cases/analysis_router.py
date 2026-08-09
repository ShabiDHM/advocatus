# FILE: app/api/endpoints/cases/analysis_router.py
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
from app.api.endpoints.cases.cases_helpers import validate_object_id, require_pro_tier, FinanceInterrogationRequest, ArchiveStrategyRequest

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
    case_oid = validate_object_id(case_id)
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
        {"$unset": {"latest_analysis": "", "latest_deep_analysis": "", "analyzed_doc_fingerprints": ""}, "$set": {"updated_at": datetime.now(timezone.utc)}}
    )
    return {"status": "success", "message": "Persistent analysis cleared successfully."}

@router.post("/{case_id}/deep-analysis", dependencies=[Depends(require_pro_tier)])
async def run_deep_case_analysis(
    case_id: str,
    client_position: Optional[str] = Query(None),
    current_user: Annotated[UserInDB, Depends(get_current_user)] = None,
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    result = await analysis_service.run_deep_strategy(db, case_id, str(current_user.id), client_position=client_position)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    
    return JSONResponse(result)

@router.post("/{case_id}/deep-analysis/simulation", dependencies=[Depends(require_pro_tier)])
async def run_deep_simulation_only(
    case_id: str,
    client_position: Optional[str] = Query(None),
    current_user: Annotated[UserInDB, Depends(get_current_user)] = None,
    db: Database = Depends(get_db)
):
    if not await asyncio.to_thread(analysis_service.authorize_case_access, db, case_id, str(current_user.id)):
        raise HTTPException(status_code=403)
    
    c_oid = validate_object_id(case_id)
    case = db.cases.find_one({"_id": c_oid}) or {}
    effective_pos = (client_position or case.get("client_position") or "DEFENDANT").upper()

    context = await analysis_service._fetch_rag_context_async(db, case_id, str(current_user.id), True)
    context_with_role = f"POZICIONI I KLIENTIT TONË: {effective_pos}\n\n{context}"
    res = await llm_service.generate_adversarial_simulation(context_with_role)
    
    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": c_oid},
        {"$set": {"latest_deep_analysis.adversarial_simulation": res, "updated_at": datetime.now(timezone.utc)}}
    )
    return JSONResponse(res)

@router.post("/{case_id}/deep-analysis/chronology", dependencies=[Depends(require_pro_tier)])
async def run_deep_chronology_only(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    if not await asyncio.to_thread(analysis_service.authorize_case_access, db, case_id, str(current_user.id)):
        raise HTTPException(status_code=403)
        
    c_oid = validate_object_id(case_id)
    context = await analysis_service._fetch_rag_context_async(db, case_id, str(current_user.id), False)
    res = await llm_service.build_case_chronology(context)
    timeline = res.get("timeline", [])

    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": c_oid},
        {"$set": {"latest_deep_analysis.chronology": timeline, "updated_at": datetime.now(timezone.utc)}}
    )
    return JSONResponse(timeline)

@router.post("/{case_id}/deep-analysis/contradictions", dependencies=[Depends(require_pro_tier)])
async def run_deep_contradictions_only(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    if not await asyncio.to_thread(analysis_service.authorize_case_access, db, case_id, str(current_user.id)):
        raise HTTPException(status_code=403)
        
    c_oid = validate_object_id(case_id)
    context = await analysis_service._fetch_rag_context_async(db, case_id, str(current_user.id), True)
    res = await llm_service.detect_contradictions(context)
    contradictions = res.get("contradictions", [])

    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": c_oid},
        {"$set": {"latest_deep_analysis.contradictions": contradictions, "updated_at": datetime.now(timezone.utc)}}
    )
    return JSONResponse(contradictions)

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

@router.post("/{case_id}/analyze/spreadsheet/forensic", dependencies=[Depends(require_pro_tier)])
async def analyze_forensic_spreadsheet_endpoint(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    file: UploadFile = File(...),
    db: Database = Depends(get_db)
):
    try:
        content = await file.read()
        result = await spreadsheet_service.forensic_analyze_spreadsheet(
            content, 
            file.filename or "upload", 
            case_id, 
            db, 
            str(current_user.id)
        )
        return JSONResponse(result)
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        logger.error(f"Spreadsheet forensic analysis error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during spreadsheet forensic analysis.")

@router.post("/{case_id}/interrogate-finances/forensic", dependencies=[Depends(require_pro_tier)])
async def interrogate_forensic_finances_endpoint(
    case_id: str,
    body: FinanceInterrogationRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    validate_object_id(case_id)
    result = await spreadsheet_service.forensic_interrogate_evidence(
        case_id, body.question, db
    )
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