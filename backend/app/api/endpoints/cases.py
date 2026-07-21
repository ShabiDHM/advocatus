# FILE: backend/app/api/endpoints/cases.py
# PHOENIX PROTOCOL - CASES ROUTER V31.0 (CLIENT POSITION STANCE ENDPOINT INTEGRATED)

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body, BackgroundTasks, Query
from typing import List, Annotated, Dict, Any, Optional
from fastapi.responses import Response, StreamingResponse, JSONResponse
from pydantic import BaseModel
from pymongo.database import Database
import redis
from bson import ObjectId
from bson.errors import InvalidId
import asyncio
import logging
import io
import json
from datetime import datetime, timezone

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

from ...models.case import CaseCreate, CaseOut
from ...models.user import UserInDB
from ...models.drafting import DraftRequest
from ...models.archive import ArchiveItemOut
from ...models.document import DocumentOut
from ...models.chat import ChatMessage

from .dependencies import get_current_user, get_db, get_sync_redis

router = APIRouter()
logger = logging.getLogger(__name__)

def validate_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format.")

def json_serializable(data):
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
    return

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

class ChatHistoryUpdate(BaseModel):
    chat_history: List[ChatMessage]

class UpdateCasePositionRequest(BaseModel):
    client_position: str  # 'DEFENDANT' or 'PLAINTIFF'

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

@router.put("/{case_id}/position", status_code=status.HTTP_200_OK)
async def update_case_client_position(
    case_id: str,
    body: UpdateCasePositionRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """Updates the party position mandate (DEFENDANT vs PLAINTIFF) for a case."""
    case_oid = validate_object_id(case_id)
    pos = body.client_position.upper()
    if pos not in ["DEFENDANT", "PLAINTIFF"]:
        raise HTTPException(status_code=400, detail="Position must be DEFENDANT or PLAINTIFF")

    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": case_oid},
        {"$set": {"client_position": pos, "updated_at": datetime.now(timezone.utc)}}
    )
    return {"status": "success", "client_position": pos}

@router.put("/{case_id}/chat", status_code=status.HTTP_200_OK)
async def update_case_chat_history(
    case_id: str,
    update: ChatHistoryUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    case = await asyncio.to_thread(
        case_service.get_case_by_id,
        db=db,
        case_id=case_oid,
        owner=current_user
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    chat_history_dicts = []
    for msg in update.chat_history:
        msg_dict = msg.model_dump() if hasattr(msg, "model_dump") else msg.dict()
        if isinstance(msg_dict.get("timestamp"), datetime):
            msg_dict["timestamp"] = msg_dict["timestamp"].isoformat()
        chat_history_dicts.append(msg_dict)
    
    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": case_oid},
        {"$set": {"chat_history": chat_history_dicts}}
    )
    return {"status": "success", "message": "Chat history saved"}

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

# --- PROTECTED DOCUMENT MANAGEMENT ---

@router.get("/{case_id}/documents", response_model=List[DocumentOut])
async def get_documents_for_case(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    user_oid = ObjectId(current_user.id)
    cursor = db.documents.find({"case_id": case_oid, "owner_id": user_oid})
    docs = list(cursor)
    return [DocumentOut.model_validate(d) for d in docs]

@router.post("/{case_id}/documents/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document_for_case(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Database = Depends(get_db),
    redis_client: redis.Redis = Depends(get_sync_redis)
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

    from ...services.document_processing_service import orchestrate_document_processing_mongo
    background_tasks.add_task(
        orchestrate_document_processing_mongo,
        str(doc.id)
    )

    return DocumentOut.model_validate(doc)

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
        raise HTTPException(status_code=403, detail="Document does not belong to this case.")
        
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
        except Exception as e:
            logger.warning(f"Failed to remove graph node: {e}")
            
        return DeletedDocumentResponse(
            documentId=doc_id,
            deletedFindingIds=result.get("deleted_finding_ids", [])
        )
    raise HTTPException(status_code=500, detail="Failed to delete document.")

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
    filename = doc.file_name if hasattr(doc, 'file_name') else "document.pdf"
    return StreamingResponse(
        stream, 
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=\"{filename}\"",
            "Cache-Control": "no-cache"
        }
    )

# --- CASE ANALYSIS & WAR ROOM ---

@router.post("/{case_id}/analyze")
async def run_textual_case_analysis(
    case_id: str,
    client_position: Optional[str] = Query(None),
    current_user: Annotated[UserInDB, Depends(get_current_user)] = None,
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    analysis_result = await analysis_service.cross_examine_case(
        db, 
        case_id, 
        str(current_user.id),
        client_position=client_position
    )
    if analysis_result and "error" not in analysis_result:
        await asyncio.to_thread(
            db.cases.update_one,
            {"_id": case_oid},
            {"$set": {"latest_analysis": analysis_result, "updated_at": datetime.now(timezone.utc)}}
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
        {"$unset": {"latest_analysis": ""}, "$set": {"updated_at": datetime.now(timezone.utc)}}
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
    return JSONResponse(res)

@router.post("/{case_id}/deep-analysis/chronology", dependencies=[Depends(require_pro_tier)])
async def run_deep_chronology_only(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    if not await asyncio.to_thread(analysis_service.authorize_case_access, db, case_id, str(current_user.id)):
        raise HTTPException(status_code=403)
        
    context = await analysis_service._fetch_rag_context_async(db, case_id, str(current_user.id), False)
    res = await llm_service.build_case_chronology(context)
    return JSONResponse(res.get("timeline", []))

@router.post("/{case_id}/deep-analysis/contradictions", dependencies=[Depends(require_pro_tier)])
async def run_deep_contradictions_only(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    if not await asyncio.to_thread(analysis_service.authorize_case_access, db, case_id, str(current_user.id)):
        raise HTTPException(status_code=403)
        
    context = await analysis_service._fetch_rag_context_async(db, case_id, str(current_user.id), True)
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