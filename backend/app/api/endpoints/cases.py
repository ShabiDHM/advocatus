# FILE: backend/app/api/endpoints/cases.py
# PHOENIX PROTOCOL - CASES ROUTER V17.0 (TOTAL AUTOMATION)
# 1. PURGED: All manual import/creation logic for evidence maps.
# 2. FIX: Standardized graph extraction to ensure Neo4j data flows instantly to the canvas.
# 3. FIX: Added a "force_refresh" parameter to the evidence-map endpoint to bypass stale MongoDB layouts.
# 4. STATUS: 100% Automated, Professional, and Clean.

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

router = APIRouter(tags=["Cases"])
logger = logging.getLogger(__name__)

# --- DEPENDENCIES ---
def require_pro_tier(current_user: Annotated[UserInDB, Depends(get_current_user)]):
    if current_user.subscription_tier != SubscriptionTier.PRO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This is a PRO feature. Please upgrade your subscription."
        )

# --- LOCAL SCHEMAS ---
class DocumentContentOut(BaseModel):
    text: str

class DeletedDocumentResponse(BaseModel):
    documentId: str
    deletedFindingIds: List[str]

class RenameDocumentRequest(BaseModel):
    new_name: str

class ShareDocumentRequest(BaseModel):
    is_shared: bool 

class BulkDeleteRequest(BaseModel):
    document_ids: List[str]

class ArchiveImportRequest(BaseModel):
    archive_item_ids: List[str]

class FinanceInterrogationRequest(BaseModel):
    question: str
    
class ReprocessConfirmation(BaseModel):
    documentId: str
    message: str

class BulkReprocessResponse(BaseModel):
    count: int
    message: str

def validate_object_id(id_str: str) -> ObjectId:
    try: return ObjectId(id_str)
    except InvalidId: raise HTTPException(status_code=400, detail="Invalid ID format.")

# --- CASE CRUD ---

@router.get("", response_model=List[CaseOut])
@router.get("/", response_model=List[CaseOut])
async def get_user_cases(current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(case_service.get_cases_for_user, db=db, owner=current_user)

@router.post("/", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
async def create_new_case(case_in: CaseCreate, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(case_service.create_case, db=db, case_in=case_in, owner=current_user)

@router.get("/{case_id}", response_model=CaseOut)
async def get_single_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validated_case_id = validate_object_id(case_id)
    case = await asyncio.to_thread(case_service.get_case_by_id, db=db, case_id=validated_case_id, owner=current_user)
    if not case: raise HTTPException(status_code=404, detail="Case not found.")
    return case

@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validated_case_id = validate_object_id(case_id)
    await asyncio.to_thread(case_service.delete_case_by_id, db=db, case_id=validated_case_id, owner=current_user)
    try: await asyncio.to_thread(graph_service.delete_node, node_id=case_id)
    except Exception: pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- DOCUMENT MANAGEMENT ---

@router.get("/{case_id}/documents", response_model=List[DocumentOut], tags=["Documents"])
async def get_documents_for_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(document_service.get_documents_by_case_id, db, case_id, current_user)

@router.post("/{case_id}/documents/upload", status_code=status.HTTP_202_ACCEPTED, tags=["Documents"])
async def upload_document_for_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], file: UploadFile = File(...), db: Database = Depends(get_db)):
    try:
        pdf_bytes, final_filename = await pdf_service.pdf_service.process_and_brand_pdf(file, case_id)
        storage_key = await asyncio.to_thread(storage_service.upload_bytes_as_file, file_obj=io.BytesIO(pdf_bytes), filename=final_filename, user_id=str(current_user.id), case_id=case_id, content_type="application/pdf")
        new_document = document_service.create_document_record(db=db, owner=current_user, case_id=case_id, file_name=final_filename, storage_key=storage_key, mime_type="application/pdf")
        celery_app.send_task("process_document_task", args=[str(new_document.id)])
        return DocumentOut.model_validate(new_document)
    except Exception: raise HTTPException(status_code=500, detail="Upload failed.")

@router.post("/{case_id}/documents/reprocess-all", response_model=BulkReprocessResponse, tags=["Documents"])
async def reprocess_all_documents(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    docs = await asyncio.to_thread(document_service.get_documents_by_case_id, db, case_id, current_user)
    for doc in docs: celery_app.send_task("process_document_task", args=[str(doc.id)])
    return BulkReprocessResponse(count=len(docs), message="AI analysis restarted.")

# --- EVIDENCE MAP (AUTOMATED VISUALIZATION) ---

@router.get("/{case_id}/evidence-map", tags=["Analysis"])
async def get_case_evidence_map(
    case_id: str, 
    current_user: Annotated[UserInDB, Depends(get_current_user)], 
    db: Database = Depends(get_db),
    refresh: bool = Query(False)
):
    """
    STRICT AUTOMATION: Synchronizes Neo4j AI extraction with the React Flow canvas.
    """
    validate_object_id(case_id)
    
    # 1. Try to fetch existing layout from MongoDB (unless refresh is requested)
    if not refresh:
        saved_map = await asyncio.to_thread(db.evidence_maps.find_one, {"case_id": case_id})
        if saved_map and saved_map.get("nodes"):
            return {"nodes": saved_map.get("nodes"), "edges": saved_map.get("edges")}

    # 2. Pull Intelligence from Neo4j
    try:
        raw_graph = await asyncio.to_thread(graph_service.get_case_graph, case_id)
        
        flow_nodes = []
        for node in raw_graph.get("nodes", []):
            group = node.get("group", "EVIDENCE").upper()
            flow_nodes.append({
                "id": node["id"],
                "type": "claimNode" if "CLAIM" in group else "factNode" if "FACT" in group else "lawNode" if "LAW" in group else "evidenceNode",
                "position": {"x": 0, "y": 0},
                "data": {"label": node.get("name", "N/A"), "content": node.get("description", "")}
            })
            
        flow_edges = []
        for link in raw_graph.get("links", []):
            flow_edges.append({
                "id": f"e-{link['source']}-{link['target']}",
                "source": link["source"], "target": link["target"],
                "label": link.get("label", "MBËSHTET"), "animated": True,
                "markerEnd": {"type": "arrowclosed", "color": "#4ade80"}
            })

        return {"nodes": flow_nodes, "edges": flow_edges, "is_new": True}
    except Exception as e:
        logger.error(f"Auto-init map failed: {e}")
        return {"nodes": [], "edges": []}

@router.put("/{case_id}/evidence-map", tags=["Analysis"])
async def save_case_evidence_map(case_id: str, data: Dict[str, Any], current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validate_object_id(case_id)
    await asyncio.to_thread(db.evidence_maps.update_one, {"case_id": case_id}, {"$set": {"nodes": data.get("nodes", []), "edges": data.get("edges", []), "updated_at": datetime.now(timezone.utc)}}, upsert=True)
    return {"status": "saved"}

# --- OTHER ENDPOINTS (CLEANED) ---

@router.post("/{case_id}/analyze", tags=["Analysis"])
async def analyze_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return JSONResponse(content=await asyncio.to_thread(analysis_service.cross_examine_case, db=db, case_id=case_id, user_id=str(current_user.id)))

@router.get("/{case_id}/documents/{doc_id}/preview", tags=["Documents"])
async def get_doc_preview(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    file_stream, doc = await asyncio.to_thread(document_service.get_preview_document_stream, db, doc_id, current_user)
    return StreamingResponse(file_stream, media_type="application/pdf")

@router.delete("/{case_id}/documents/{doc_id}", tags=["Documents"])
async def delete_doc(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db), redis_client: redis.Redis = Depends(get_sync_redis)):
    result = await asyncio.to_thread(document_service.bulk_delete_documents, db=db, redis_client=redis_client, document_ids=[doc_id], owner=current_user)
    return JSONResponse(status_code=200, content=result)