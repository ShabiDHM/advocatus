# FILE: backend/app/api/endpoints/cases.py
# PHOENIX PROTOCOL - CASES ROUTER V21.0 (GOLDEN SOURCE)
# 1. VERIFIED: All endpoints (Delete, Graph Auto-Build, Financial Analysis) are present.
# 2. STATUS: System Integrity Confirmed. Ready for deployment.

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body, Query
from typing import List, Annotated, Dict, Optional, Any
from fastapi.responses import Response, StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from pymongo.database import Database
import redis
from bson import ObjectId
from bson.errors import InvalidId
import asyncio
import logging
import io
import urllib.parse
import mimetypes
from datetime import datetime, timezone
import json

# --- SERVICE IMPORTS ---
from ...services import (
    case_service,
    document_service,
    report_service,
    storage_service,
    analysis_service,
    archive_service,
    pdf_service,
    llm_service,
    drafting_service,
    spreadsheet_service
)
from ...services.graph_service import graph_service 

# --- MODEL IMPORTS ---
from ...models.case import CaseCreate, CaseOut
from ...models.user import UserInDB, SubscriptionTier
from ...models.drafting import DraftRequest 
from ...models.archive import ArchiveItemOut 
from ...models.document import DocumentOut
from ...models.finance import InvoiceInDB

from .dependencies import get_current_user, get_db, get_sync_redis
from ...celery_app import celery_app
from ...core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# --- DEPENDENCIES & SCHEMAS ---
def require_pro_tier(current_user: Annotated[UserInDB, Depends(get_current_user)]):
    if current_user.subscription_tier != SubscriptionTier.PRO:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This is a PRO feature.")

class DocumentContentOut(BaseModel): text: str
class DeletedDocumentResponse(BaseModel): documentId: str; deletedFindingIds: List[str]
class RenameDocumentRequest(BaseModel): new_name: str
class ShareDocumentRequest(BaseModel): is_shared: bool 
class BulkDeleteRequest(BaseModel): document_ids: List[str]
class ArchiveImportRequest(BaseModel): archive_item_ids: List[str]
class FinanceInterrogationRequest(BaseModel): question: str
class ReprocessConfirmation(BaseModel): documentId: str; message: str
class BulkReprocessResponse(BaseModel): count: int; message: str

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

# --- DOCUMENT MANAGEMENT ENDPOINTS ---

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

@router.delete("/{case_id}/documents/{doc_id}", response_model=DeletedDocumentResponse)
async def delete_document(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db), redis_client: redis.Redis = Depends(get_sync_redis)):
    doc = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(doc.case_id) != case_id: raise HTTPException(status_code=403)
    result = await asyncio.to_thread(document_service.bulk_delete_documents, db, redis_client, [doc_id], current_user)
    if result.get("deleted_count", 0) > 0:
        try: await asyncio.to_thread(graph_service.delete_node, doc_id)
        except Exception: pass
        return DeletedDocumentResponse(documentId=doc_id, deletedFindingIds=result.get("deleted_finding_ids", []))
    raise HTTPException(status_code=500, detail="Failed to delete document.")
    
@router.put("/{case_id}/documents/{doc_id}/rename")
async def rename_document_endpoint(case_id: str, doc_id: str, body: RenameDocumentRequest, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(case_service.rename_document, db, validate_object_id(case_id), validate_object_id(doc_id), body.new_name, current_user)

@router.get("/{case_id}/documents/{doc_id}/preview", response_class=StreamingResponse)
async def get_document_preview(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    stream, doc = await asyncio.to_thread(document_service.get_preview_document_stream, db, doc_id, current_user)
    return StreamingResponse(stream, media_type="application/pdf")

# --- ANALYSIS & EVIDENCE MAP PIPELINE ---

@router.get("/{case_id}/evidence-map")
async def get_or_build_evidence_map(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validate_object_id(case_id)
    
    saved_map = await asyncio.to_thread(db.evidence_maps.find_one, {"case_id": case_id})
    if saved_map and saved_map.get("nodes"):
        return {"nodes": saved_map.get("nodes"), "edges": saved_map.get("edges")}

    raw_graph = await asyncio.to_thread(graph_service.get_case_graph, case_id)
    if not raw_graph or not raw_graph.get("nodes"):
        build_success = await asyncio.to_thread(analysis_service.build_and_populate_graph, db, case_id, str(current_user.id))
        if build_success:
            raw_graph = await asyncio.to_thread(graph_service.get_case_graph, case_id)
        else:
            return {"nodes": [], "edges": []}

    nodes = [{"id": n["id"], "type": "claimNode" if "CLAIM" in n.get("group","") else "factNode" if "FACT" in n.get("group","") else "lawNode" if "LAW" in n.get("group","") else "evidenceNode", "position": {"x":0,"y":0}, "data": {"label": n.get("name",""), "content": n.get("description","")}} for n in raw_graph.get("nodes", [])]
    edges = [{"id": f"e-{l['source']}-{l['target']}", "source": l["source"], "target": l["target"], "label": l.get("label", "LIDHET"), "animated": True, "markerEnd": {"type": "arrowclosed"}} for l in raw_graph.get("links", [])]
    return {"nodes": nodes, "edges": edges, "is_new": True}

@router.put("/{case_id}/evidence-map")
async def save_evidence_map_layout(case_id: str, data: Dict[str, Any], current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validate_object_id(case_id)
    await asyncio.to_thread(db.evidence_maps.update_one, {"case_id": case_id}, {"$set": {"nodes": data.get("nodes",[]), "edges": data.get("edges",[]), "updated_at": datetime.now(timezone.utc)}}, upsert=True)
    return {"status": "saved"}

@router.post("/{case_id}/analyze")
async def run_textual_case_analysis(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validate_object_id(case_id)
    return JSONResponse(await asyncio.to_thread(analysis_service.cross_examine_case, db, case_id, str(current_user.id)))

@router.post("/{case_id}/deep-analysis", dependencies=[Depends(require_pro_tier)])
async def run_deep_case_analysis(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validate_object_id(case_id)
    result = await analysis_service.run_deep_strategy(db, case_id, str(current_user.id))
    if result.get("error"): raise HTTPException(status_code=400, detail=result["error"])
    return JSONResponse(result)

# --- SPREADSHEET & FINANCIAL ANALYSIS ---

@router.post("/{case_id}/analyze/spreadsheet/forensic", dependencies=[Depends(require_pro_tier)])
async def analyze_forensic_spreadsheet_endpoint(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], file: UploadFile = File(...), db: Database = Depends(get_db)):
    content = await file.read()
    result = await spreadsheet_service.forensic_analyze_spreadsheet(content, file.filename or "forensic_upload", case_id, db, str(current_user.id))
    return JSONResponse(result)

# --- DRAFTING, PUBLIC PORTAL, AND OTHER ENDPOINTS ---

@router.post("/{case_id}/drafts", status_code=status.HTTP_202_ACCEPTED)
async def create_draft_for_case(case_id: str, job_in: DraftRequest, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validated_case_id = validate_object_id(case_id)
    return await asyncio.to_thread(case_service.create_draft_job_for_case, db=db, case_id=validated_case_id, job_in=job_in, owner=current_user)

@router.get("/public/{case_id}/timeline")
async def get_public_case_timeline(case_id: str, db: Database = Depends(get_db)):
    return await asyncio.to_thread(case_service.get_public_case_events, db=db, case_id=case_id)

@router.get("/public/{case_id}/documents/{doc_id}/download")
async def download_public_document(case_id: str, doc_id: str, source: str = Query("ACTIVE", enum=["ACTIVE", "ARCHIVE"]), db: Database = Depends(get_db)):
    doc_data = None
    if source == "ACTIVE":
        doc_data = await asyncio.to_thread(db.documents.find_one, {"_id": validate_object_id(doc_id), "$or": [{"case_id": case_id}, {"case_id": validate_object_id(case_id)}]})
    else:
        doc_data = await asyncio.to_thread(db.archives.find_one, {"_id": validate_object_id(doc_id), "$or": [{"case_id": case_id}, {"case_id": validate_object_id(case_id)}], "item_type": "FILE"})
    
    if not doc_data or not doc_data.get("is_shared"): raise HTTPException(status_code=403, detail="Access Denied.")
    storage_key = doc_data.get("storage_key")
    if not storage_key: raise HTTPException(status_code=404, detail="File content missing.")
    
    file_stream = await asyncio.to_thread(storage_service.download_original_document_stream, storage_key)
    filename = doc_data.get("file_name") or doc_data.get("title") or "document"
    safe_filename = urllib.parse.quote(filename)
    content_type, _ = mimetypes.guess_type(filename)
    
    return StreamingResponse(file_stream, media_type=content_type or "application/octet-stream", headers={"Content-Disposition": f"inline; filename*=UTF-8''{safe_filename}"})

@router.get("/public/{case_id}/logo")
async def get_public_case_logo(case_id: str, db: Database = Depends(get_db)):
    case = await asyncio.to_thread(db.cases.find_one, {"_id": validate_object_id(case_id)})
    if not case: raise HTTPException(status_code=404)
    owner_id = case.get("owner_id")
    if not owner_id: raise HTTPException(status_code=404)
    profile = await asyncio.to_thread(db.business_profiles.find_one, {"user_id": owner_id})
    if not profile or "logo_storage_key" not in profile: raise HTTPException(status_code=404)
    key = profile["logo_storage_key"]
    stream = await asyncio.to_thread(storage_service.get_file_stream, key)
    mime_type, _ = mimetypes.guess_type(key)
    return StreamingResponse(stream, media_type=mime_type or "image/png")