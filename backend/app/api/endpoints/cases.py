# FILE: backend/app/api/endpoints/cases.py
# PHOENIX PROTOCOL - CASES ROUTER V21.6 (STABILITY FIRST)
# 1. CLEANUP: Removed all imports and references to the deleted manual evidence_map logic.
# 2. FIX: Resolved Pylance 'deletedFindingIds' argument issue.
# 3. STATUS: 100% Pylance Clear. Safe for deployment.

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

from .dependencies import get_current_user, get_db, get_sync_redis

router = APIRouter()
logger = logging.getLogger(__name__)

# --- DEPENDENCIES & SCHEMAS ---
def require_pro_tier(current_user: Annotated[UserInDB, Depends(get_current_user)]):
    if current_user.subscription_tier != SubscriptionTier.PRO and current_user.role != 'ADMIN':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This is a PRO feature.")

class DocumentContentOut(BaseModel): text: str
class DeletedDocumentResponse(BaseModel): 
    documentId: str
    deletedFindingIds: List[str]

class FinanceInterrogationRequest(BaseModel): question: str

def validate_object_id(id_str: str) -> ObjectId:
    try: return ObjectId(id_str)
    except InvalidId: raise HTTPException(status_code=400, detail="Invalid ID format.")

# --- CORE CASE ENDPOINTS ---

@router.get("", response_model=List[CaseOut], include_in_schema=False)
async def get_user_cases(current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(case_service.get_cases_for_user, db=db, owner=current_user)

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

@router.post("/{case_id}/documents/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document_for_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], file: UploadFile = File(...), db: Database = Depends(get_db)):
    pdf_bytes, filename = await pdf_service.pdf_service.process_and_brand_pdf(file, case_id)
    key = await asyncio.to_thread(storage_service.upload_bytes_as_file, io.BytesIO(pdf_bytes), filename, str(current_user.id), case_id, "application/pdf")
    doc = document_service.create_document_record(db, current_user, case_id, filename, key, "application/pdf")
    from ...celery_app import celery_app
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
        return DeletedDocumentResponse(
            documentId=doc_id, 
            deletedFindingIds=result.get("deleted_finding_ids", [])
        )
    raise HTTPException(status_code=500, detail="Failed to delete document.")

# --- EVIDENCE MAP (AI-AUTOMATED PATH) ---

@router.get("/{case_id}/evidence-map")
async def get_evidence_map(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    """Returns the AI-generated graph from Neo4j."""
    validate_object_id(case_id)
    raw_graph = await asyncio.to_thread(graph_service.get_case_graph, case_id)
    
    nodes = [{"id": n["id"], "type": "claimNode" if "CLAIM" in n.get("group","") else "factNode" if "FACT" in n.get("group","") else "lawNode" if "LAW" in n.get("group","") else "evidenceNode", "position": {"x":0,"y":0}, "data": {"label": n.get("name",""), "content": n.get("description","")}} for n in raw_graph.get("nodes", [])]
    links = [{"id": f"e-{l['source']}-{l['target']}", "source": l["source"], "target": l["target"], "label": l.get("label", "LIDHET"), "animated": True} for l in raw_graph.get("links", [])]
    
    return {"nodes": nodes, "links": links, "is_empty": len(nodes) == 0}

@router.post("/{case_id}/analyze")
async def run_textual_case_analysis(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validate_object_id(case_id)
    return JSONResponse(await asyncio.to_thread(analysis_service.cross_examine_case, db, case_id, str(current_user.id)))

@router.post("/{case_id}/interrogate-finances/forensic", dependencies=[Depends(require_pro_tier)])
async def interrogate_forensic_finances_endpoint(case_id: str, body: FinanceInterrogationRequest, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validate_object_id(case_id)
    result = await spreadsheet_service.forensic_interrogate_evidence(case_id, body.question, db)
    return JSONResponse(result)