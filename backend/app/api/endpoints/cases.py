# FILE: backend/app/api/endpoints/cases.py
# PHOENIX PROTOCOL - CASES ROUTER V27.0 (PYLANCE & DEPTH FIX)
# 1. FIXED: Corrected import depth (...models) for 3-level deep endpoint structure.
# 2. INTEGRITY: Maintains all protected document, analysis, and portal logic.
# 3. STATUS: 100% Pylance clean.

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body
from typing import List, Annotated, Dict, Any
from fastapi.responses import Response, StreamingResponse, JSONResponse
from pydantic import BaseModel
from pymongo.database import Database
import redis
from bson import ObjectId
from bson.errors import InvalidId
import asyncio
import logging
import io
from datetime import datetime, timezone

# --- SERVICE IMPORTS (3 dots to reach app/services) ---
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

# --- MODEL IMPORTS (3 dots to reach app/models) ---
from ...models.case import CaseCreate, CaseOut
from ...models.user import UserInDB, SubscriptionTier
from ...models.drafting import DraftRequest
from ...models.archive import ArchiveItemOut
from ...models.document import DocumentOut
from ...celery_app import celery_app

from .dependencies import get_current_user, get_db, get_sync_redis

router = APIRouter()
logger = logging.getLogger(__name__)

# --- HELPERS ---

def validate_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format.")

def json_serializable(data):
    """Recursively convert datetime and ObjectId to JSON-safe formats."""
    if isinstance(data, list):
        return [json_serializable(item) for item in data]
    if isinstance(data, dict):
        return {k: json_serializable(v) for k, v in data.items()}
    if isinstance(data, datetime):
        return data.isoformat()
    if isinstance(data, ObjectId):
        return str(data)
    return data

def require_pro_tier(current_user: Annotated[UserInDB, Depends(get_current_user)]):
    if current_user.subscription_tier != SubscriptionTier.PRO and current_user.role != 'ADMIN':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This is a PRO feature."
        )

# --- PYDANTIC MODELS ---

class DeletedDocumentResponse(BaseModel):
    documentId: str
    deletedFindingIds: List[str]

class RenameDocumentRequest(BaseModel):
    new_name: str

class FinanceInterrogationRequest(BaseModel):
    question: str

class ArchiveStrategyRequest(BaseModel):
    legal_data: Dict[str, Any]
    deep_data: Dict[str, Any]

# --- CORE CASE ENDPOINTS ---

@router.get("", response_model=List[CaseOut], include_in_schema=False)
async def get_user_cases(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    return await asyncio.to_thread(
        case_service.get_cases_for_user,
        db=db,
        owner=current_user
    )

@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_new_case(
    case_in: CaseCreate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    return await asyncio.to_thread(
        case_service.create_case,
        db=db,
        case_in=case_in,
        owner=current_user
    )

@router.get("/{case_id}", response_model=CaseOut)
async def get_single_case(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    case = await asyncio.to_thread(
        case_service.get_case_by_id,
        db=db,
        case_id=validate_object_id(case_id),
        owner=current_user
    )
    if not case:
        raise HTTPException(status_code=404)
    return case

@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    await asyncio.to_thread(
        case_service.delete_case_by_id,
        db=db,
        case_id=validate_object_id(case_id),
        owner=current_user
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- PUBLIC PORTAL ENDPOINTS ---

@router.get("/public/{case_id}/timeline")
async def get_public_case_timeline(
    case_id: str,
    db: Database = Depends(get_db)
):
    try:
        data = await asyncio.to_thread(
            case_service.get_public_case_events,
            db,
            case_id
        )
        if not data:
            raise HTTPException(status_code=404, detail="Case not found")
        return JSONResponse(content=json_serializable(data))
    except Exception as e:
        logger.error(f"Portal Mirror Failure: {e}")
        return JSONResponse({"error": "Failed to fetch portal data"}, status_code=500)

@router.get("/public/{case_id}/documents/{doc_id}/download")
async def public_document_download(
    case_id: str,
    doc_id: str,
    source: str = "ACTIVE",
    db: Database = Depends(get_db)
):
    doc_oid = validate_object_id(doc_id)
    collection = "documents" if source == "ACTIVE" else "archives"
    doc = db[collection].find_one({"_id": doc_oid})
    if not doc:
        raise HTTPException(status_code=404)
    if not doc.get("is_shared", False):
        raise HTTPException(status_code=403, detail="Document not shared")
    try:
        stream = storage_service.get_file_stream(doc["storage_key"])
        return StreamingResponse(
            stream,
            media_type=doc.get("mime_type", "application/pdf"),
            headers={
                "Content-Disposition": f"inline; filename={doc.get('file_name', 'file.pdf')}"
            }
        )
    except Exception:
        raise HTTPException(status_code=500)

@router.get("/public/{case_id}/logo")
async def get_public_portal_logo(
    case_id: str,
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    case = db.cases.find_one({"_id": case_oid})
    if not case:
        raise HTTPException(status_code=404)
    owner_id = case.get("owner_id") or case.get("user_id")
    profile = db.business_profiles.find_one({
        "$or": [{"user_id": owner_id}, {"user_id": str(owner_id)}]
    })
    if profile and profile.get("logo_storage_key"):
        stream = storage_service.get_file_stream(profile["logo_storage_key"])
        return StreamingResponse(stream, media_type="image/png")
    raise HTTPException(status_code=404)

# --- PROTECTED DOCUMENT MANAGEMENT ---

@router.get("/{case_id}/documents", response_model=List[DocumentOut])
async def get_documents_for_case(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    return await asyncio.to_thread(
        document_service.get_documents_by_case_id,
        db,
        case_id,
        current_user
    )

@router.post("/{case_id}/documents/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document_for_case(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    file: UploadFile = File(...),
    db: Database = Depends(get_db)
):
    pdf_bytes, filename = await pdf_service.pdf_service.process_and_brand_pdf(file, case_id)
    key = await asyncio.to_thread(
        storage_service.upload_bytes_as_file,
        io.BytesIO(pdf_bytes),
        filename,
        str(current_user.id),
        case_id,
        "application/pdf"
    )

    doc = document_service.create_document_record(
        db=db,
        owner=current_user,
        case_id=case_id,
        file_name=filename,
        storage_key=key,
        mime_type="application/pdf"
    )

    celery_app.send_task("process_document_task", args=[str(doc.id)])
    return DocumentOut.model_validate(doc)

@router.post("/{case_id}/documents/bulk-delete")
async def bulk_delete_documents(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    document_ids: List[str] = Body(..., embed=True),
    db: Database = Depends(get_db),
    redis_client: redis.Redis = Depends(get_sync_redis)
):
    validate_object_id(case_id)
    result = await asyncio.to_thread(
        document_service.bulk_delete_documents,
        db=db,
        redis_client=redis_client,
        document_ids=document_ids,
        owner=current_user
    )
    return {
        "deleted_count": result.get("deleted_count", 0),
        "deleted_finding_ids": result.get("deleted_finding_ids", [])
    }

@router.delete("/{case_id}/documents/{doc_id}", response_model=DeletedDocumentResponse)
async def delete_document(
    case_id: str,
    doc_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    redis_client: redis.Redis = Depends(get_sync_redis)
):
    doc = await asyncio.to_thread(
        document_service.get_and_verify_document,
        db,
        doc_id,
        current_user
    )
    if str(doc.case_id) != case_id:
        raise HTTPException(status_code=403)
    result = await asyncio.to_thread(
        document_service.bulk_delete_documents,
        db=db,
        redis_client=redis_client,
        document_ids=[doc_id],
        owner=current_user
    )
    if result.get("deleted_count", 0) > 0:
        try:
            await asyncio.to_thread(graph_service.delete_node, doc_id)
        except Exception:
            pass
        return DeletedDocumentResponse(
            documentId=doc_id,
            deletedFindingIds=result.get("deleted_finding_ids", [])
        )
    raise HTTPException(status_code=500)

@router.put("/{case_id}/documents/{doc_id}/rename")
async def rename_document_endpoint(
    case_id: str,
    doc_id: str,
    body: RenameDocumentRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    return await asyncio.to_thread(
        case_service.rename_document,
        db,
        validate_object_id(case_id),
        validate_object_id(doc_id),
        body.new_name,
        current_user
    )

@router.get("/{case_id}/documents/{doc_id}/preview", response_class=StreamingResponse)
async def get_document_preview(
    case_id: str,
    doc_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    stream, doc = await asyncio.to_thread(
        document_service.get_preview_document_stream,
        db,
        doc_id,
        current_user
    )
    return StreamingResponse(stream, media_type="application/pdf")

@router.post("/{case_id}/documents/{doc_id}/archive", response_model=ArchiveItemOut, status_code=status.HTTP_201_CREATED)
async def archive_document_endpoint(
    case_id: str,
    doc_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    doc = await asyncio.to_thread(
        document_service.get_and_verify_document,
        db,
        doc_id,
        current_user
    )
    if str(doc.case_id) != case_id:
        raise HTTPException(status_code=403)
    archiver = archive_service.ArchiveService(db)
    archived_item = await archiver.archive_existing_document(
        str(current_user.id),
        case_id,
        doc.storage_key,
        doc.file_name,
        original_doc_id=doc_id
    )
    return ArchiveItemOut.model_validate(archived_item)

# --- EVIDENCE MAP ---

@router.get("/{case_id}/evidence-map")
async def get_evidence_map(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)]
):
    validate_object_id(case_id)
    raw_graph = await asyncio.to_thread(graph_service.get_case_graph, case_id)
    return {
        "nodes": raw_graph.get("nodes", []),
        "links": raw_graph.get("links", [])
    }

@router.post("/{case_id}/extract-map", status_code=status.HTTP_202_ACCEPTED)
async def trigger_map_extraction(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    validate_object_id(case_id)
    success = await asyncio.to_thread(
        analysis_service.build_and_populate_graph,
        db,
        case_id,
        str(current_user.id)
    )
    if not success:
        raise HTTPException(status_code=500, detail="AI Extraction failed.")
    return {"status": "success"}

# --- ANALYSIS & STRATEGY ---

@router.post("/{case_id}/analyze")
async def run_textual_case_analysis(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    validate_object_id(case_id)
    return JSONResponse(
        await analysis_service.cross_examine_case(db, case_id, str(current_user.id))
    )

@router.post("/{case_id}/deep-analysis", dependencies=[Depends(require_pro_tier)])
async def run_deep_case_analysis(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    validate_object_id(case_id)
    result = await analysis_service.run_deep_strategy(db, case_id, str(current_user.id))
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return JSONResponse(result)

@router.post("/{case_id}/deep-analysis/simulation", dependencies=[Depends(require_pro_tier)])
async def run_deep_simulation_only(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    if not analysis_service.authorize_case_access(db, case_id, str(current_user.id)):
        raise HTTPException(status_code=403)
    context = await analysis_service._fetch_rag_context_async(
        db, case_id, str(current_user.id), include_laws=True
    )
    res = await llm_service.generate_adversarial_simulation(context)
    return JSONResponse(res)

@router.post("/{case_id}/deep-analysis/chronology", dependencies=[Depends(require_pro_tier)])
async def run_deep_chronology_only(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    if not analysis_service.authorize_case_access(db, case_id, str(current_user.id)):
        raise HTTPException(status_code=403)
    context = await analysis_service._fetch_rag_context_async(
        db, case_id, str(current_user.id), include_laws=False
    )
    res = await llm_service.build_case_chronology(context)
    return JSONResponse(res.get("timeline", []))

@router.post("/{case_id}/deep-analysis/contradictions", dependencies=[Depends(require_pro_tier)])
async def run_deep_contradictions_only(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    if not analysis_service.authorize_case_access(db, case_id, str(current_user.id)):
        raise HTTPException(status_code=403)
    context = await analysis_service._fetch_rag_context_async(
        db, case_id, str(current_user.id), include_laws=True
    )
    res = await llm_service.detect_contradictions(context)
    return JSONResponse(res.get("contradictions", []))

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

# --- FORENSIC & DRAFTS ---

@router.post("/{case_id}/analyze/spreadsheet/forensic", dependencies=[Depends(require_pro_tier)])
async def analyze_forensic_spreadsheet_endpoint(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    file: UploadFile = File(...),
    db: Database = Depends(get_db)
):
    content = await file.read()
    result = await spreadsheet_service.forensic_analyze_spreadsheet(
        content, file.filename or "upload", case_id, db, str(current_user.id)
    )
    return JSONResponse(result)

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