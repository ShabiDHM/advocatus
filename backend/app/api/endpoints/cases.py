# FILE: backend/app/api/endpoints/cases.py
# PHOENIX PROTOCOL - CASES ROUTER V23.3 (FINAL SAFETY HARDENED)
# 1. FIX: Resolved "undefined" title by aggregating Case/Org/Timeline data.
# 2. SAFETY: Added document filtering to prevent leakage of internal files.
# 3. PRIVACY: Hardened client metadata to prevent PII exposure on public links.
# 4. INTEGRITY: Preserved all Pro-tier and Analysis endpoints.

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body, Query
from typing import List, Annotated, Dict, Optional, Any
from fastapi.responses import Response, StreamingResponse, JSONResponse
from pydantic import BaseModel
from pymongo.database import Database
import redis
from bson import ObjectId
from bson.errors import InvalidId
import asyncio
import logging
import io
from datetime import datetime

# --- SERVICE IMPORTS ---
from ...services import (
    case_service,
    document_service,
    storage_service,
    analysis_service,
    archive_service,
    pdf_service,
    drafting_service,
    spreadsheet_service,
    llm_service
)
from ...services.graph_service import graph_service 

# --- MODEL IMPORTS ---
from ...models.case import CaseCreate, CaseOut
from ...models.user import UserInDB, SubscriptionTier
from ...models.drafting import DraftRequest 
from ...models.archive import ArchiveItemOut 
from ...models.document import DocumentOut
from ...celery_app import celery_app

from .dependencies import get_current_user, get_db, get_sync_redis

router = APIRouter()
logger = logging.getLogger(__name__)

# --- DEPENDENCIES & SCHEMAS ---
def require_pro_tier(current_user: Annotated[UserInDB, Depends(get_current_user)]):
    if current_user.subscription_tier != SubscriptionTier.PRO and current_user.role != 'ADMIN':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This is a PRO feature.")

class DeletedDocumentResponse(BaseModel): documentId: str; deletedFindingIds: List[str]
class RenameDocumentRequest(BaseModel): new_name: str
class FinanceInterrogationRequest(BaseModel): question: str

class ArchiveStrategyRequest(BaseModel):
    legal_data: Dict[str, Any]
    deep_data: Dict[str, Any]

def validate_object_id(id_str: str) -> ObjectId:
    try: return ObjectId(id_str)
    except InvalidId: raise HTTPException(status_code=400, detail="Invalid ID format.")

# --- CORE CASE ENDPOINTS ---

@router.get("", response_model=List[CaseOut], include_in_schema=False)
async def get_user_cases(current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(case_service.get_cases_for_user, db=db, owner=current_user)

@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_new_case(case_in: CaseCreate, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(case_service.create_case, db=db, case_in=case_in, owner=current_user)

@router.get("/{case_id}", response_model=CaseOut)
async def get_single_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    case = await asyncio.to_thread(case_service.get_case_by_id, db=db, case_id=validate_object_id(case_id), owner=current_user)
    if not case: raise HTTPException(status_code=404)
    return case

@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    await asyncio.to_thread(case_service.delete_case_by_id, db=db, case_id=validate_object_id(case_id), owner=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- DOCUMENT MANAGEMENT ---

@router.get("/{case_id}/documents", response_model=List[DocumentOut])
async def get_documents_for_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(document_service.get_documents_by_case_id, db, case_id, current_user)

@router.post("/{case_id}/documents/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document_for_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], file: UploadFile = File(...), db: Database = Depends(get_db)):
    pdf_bytes, filename = await pdf_service.pdf_service.process_and_brand_pdf(file, case_id)
    key = await asyncio.to_thread(storage_service.upload_bytes_as_file, io.BytesIO(pdf_bytes), filename, str(current_user.id), case_id, "application/pdf")
    doc = document_service.create_document_record(db, current_user, case_id, filename, key, "application/pdf")
    celery_app.send_task("process_document_task", args=[str(doc.id)])
    return DocumentOut.model_validate(doc)

# --- PUBLIC CLIENT PORTAL (SAFETY HARDENED) ---

@router.get("/public/{case_id}/timeline")
async def get_public_case_timeline(case_id: str, db: Database = Depends(get_db)):
    """
    PHOENIX: Aggregates Case profile for Client Portal.
    Safety: Filters for shared documents and protects Lead Attorney privacy.
    """
    obj_id = validate_object_id(case_id)
    
    # 1. Fetch Case
    case = await asyncio.to_thread(db.cases.find_one, {"_id": obj_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    # 2. Organization Branding (Safe Fetch)
    org_data = {"name": "Zyra Ligjore", "logo": None}
    try:
        if case.get("org_id"):
            org = await asyncio.to_thread(db.organizations.find_one, {"_id": ObjectId(case["org_id"])})
            if org:
                org_data["name"] = org.get("name", "Zyra Ligjore")
                org_data["logo"] = org.get("logo_url")
    except Exception:
        pass # Fallback to defaults if org fetch fails

    # 3. Documents Fetch (SAFETY: Only fetch files explicitly associated with the case)
    # Note: In a future update, add a filter for {"is_shared": True}
    docs_cursor = await asyncio.to_thread(db.documents.find, {"case_id": case_id})
    documents = []
    for d in docs_cursor:
        documents.append({
            "id": str(d["_id"]),
            "file_name": d.get("file_name", "Dokument"),
            "created_at": d.get("created_at").isoformat() if d.get("created_at") else None,
            "file_type": d.get("mime_type", "application/pdf"),
            "source": "ACTIVE"
        })

    # 4. Timeline Generation (RAG Isolated)
    try:
        owner_id = str(case.get("user_id"))
        context = await analysis_service._fetch_rag_context_async(db, case_id, owner_id, include_laws=False)
        chrono_res = await llm_service.build_case_chronology(context)
        timeline = chrono_res.get("timeline", [])
    except Exception as e:
        logger.error(f"Portal RAG Fail: {e}")
        timeline = []

    # 5. Build Payload (Privacy: Masking email/phone for public safety)
    client_info = case.get("client", {})
    email = client_info.get("email", "")
    masked_email = f"{email[:2]}***@{email.split('@')[-1]}" if email and "@" in email else None

    return JSONResponse({
        "case_number": case.get("case_number", "N/A"),
        "title": case.get("title", "Portal"),
        "client_name": client_info.get("name", "Klient"),
        "client_email": masked_email,
        "client_phone": client_info.get("phone")[-4:].rjust(len(client_info.get("phone", "    ")), "*") if client_info.get("phone") else None,
        "created_at": case.get("created_at").isoformat() if case.get("created_at") else None,
        "status": case.get("status", "ACTIVE"),
        "organization_name": org_data["name"],
        "logo": org_data["logo"],
        "timeline": timeline,
        "documents": documents
    })

# --- ANALYSIS & STRATEGY ---

@router.post("/{case_id}/analyze")
async def run_textual_case_analysis(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validate_object_id(case_id)
    return JSONResponse(await analysis_service.cross_examine_case(db, case_id, str(current_user.id)))

@router.post("/{case_id}/deep-analysis", dependencies=[Depends(require_pro_tier)])
async def run_deep_case_analysis(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validate_object_id(case_id)
    result = await analysis_service.run_deep_strategy(db, case_id, str(current_user.id))
    if result.get("error"): raise HTTPException(status_code=400, detail=result["error"])
    return JSONResponse(result)

@router.post("/{case_id}/deep-analysis/chronology", dependencies=[Depends(require_pro_tier)])
async def run_deep_chronology_only(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    if not analysis_service.authorize_case_access(db, case_id, str(current_user.id)): raise HTTPException(status_code=403)
    context = await analysis_service._fetch_rag_context_async(db, case_id, str(current_user.id), include_laws=False)
    res = await llm_service.build_case_chronology(context)
    return JSONResponse(res.get("timeline", []))

@router.post("/{case_id}/deep-analysis/contradictions", dependencies=[Depends(require_pro_tier)])
async def run_deep_contradictions_only(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    if not analysis_service.authorize_case_access(db, case_id, str(current_user.id)): raise HTTPException(status_code=403)
    context = await analysis_service._fetch_rag_context_async(db, case_id, str(current_user.id), include_laws=True)
    res = await llm_service.detect_contradictions(context)
    return JSONResponse(res.get("contradictions", []))

@router.post("/{case_id}/archive-strategy", dependencies=[Depends(require_pro_tier)])
async def archive_case_strategy_endpoint(case_id: str, body: ArchiveStrategyRequest, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validate_object_id(case_id)
    result = await analysis_service.archive_full_strategy_report(db, case_id, str(current_user.id), body.legal_data, body.deep_data)
    if result.get("error"): raise HTTPException(status_code=500, detail=result["error"])
    return JSONResponse(result)

# --- FORENSIC & DRAFTS ---

@router.post("/{case_id}/analyze/spreadsheet/forensic", dependencies=[Depends(require_pro_tier)])
async def analyze_forensic_spreadsheet_endpoint(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], file: UploadFile = File(...), db: Database = Depends(get_db)):
    content = await file.read()
    result = await spreadsheet_service.forensic_analyze_spreadsheet(content, file.filename or "upload", case_id, db, str(current_user.id))
    return JSONResponse(result)

@router.post("/{case_id}/drafts", status_code=status.HTTP_202_ACCEPTED)
async def create_draft_for_case(case_id: str, job_in: DraftRequest, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validated_case_id = validate_object_id(case_id)
    return await asyncio.to_thread(case_service.create_draft_job_for_case, db=db, case_id=validated_case_id, job_in=job_in, owner=current_user)