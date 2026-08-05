# FILE: app/api/endpoints/cases/case_management_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Annotated
from fastapi.responses import StreamingResponse, JSONResponse, Response
from pymongo.database import Database
import asyncio
import logging
from datetime import datetime, timezone
from bson import ObjectId

from app.services import case_service, storage_service
from app.models.case import CaseCreate, CaseOut
from app.models.user import UserInDB
from app.api.endpoints.dependencies import get_current_user, get_db
from app.api.endpoints.cases.cases_helpers import validate_object_id, ChatHistoryUpdate, UpdateCasePositionRequest

router = APIRouter()
logger = logging.getLogger(__name__)

# --- PUBLIC CLIENT PORTAL ENDPOINTS ---

@router.get("/public/{case_id}/timeline")
async def get_public_case_timeline(
    case_id: str,
    db: Database = Depends(get_db)
):
    try:
        case_data = case_service.get_public_case_events(db, case_id)
        if not case_data:
            raise HTTPException(status_code=404, detail="Case not found or not public.")
        return JSONResponse(case_data)
    except Exception as e:
        logger.error(f"Public timeline error for case {case_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/public/{case_id}/logo")
async def get_public_firm_logo(
    case_id: str,
    db: Database = Depends(get_db)
):
    try:
        case_oid = validate_object_id(case_id)
        case = db.cases.find_one({"_id": case_oid})
        if not case:
            raise HTTPException(status_code=404)
        
        owner_id = case.get("owner_id") or case.get("user_id")
        if not owner_id:
            raise HTTPException(status_code=404)
            
        profile = db.business_profiles.find_one({"$or": [{"user_id": owner_id}, {"user_id": str(owner_id)}]})
        if not profile or not profile.get("logo_storage_key"):
            raise HTTPException(status_code=404)
            
        logo_key = profile["logo_storage_key"]
        stream = storage_service.get_file_stream(logo_key)
        if not stream:
            raise HTTPException(status_code=404)
            
        return StreamingResponse(stream, media_type="image/png")
    except Exception:
        raise HTTPException(status_code=404, detail="Logo not found.")

@router.get("/public/{case_id}/documents/{doc_id}/download")
async def download_public_shared_document(
    case_id: str,
    doc_id: str,
    source: str = "ACTIVE",
    db: Database = Depends(get_db)
):
    try:
        if source == "ARCHIVE":
            archive_item = db.archives.find_one({"_id": ObjectId(doc_id)})
            if not archive_item or not archive_item.get("is_shared"):
                raise HTTPException(status_code=403, detail="Access denied.")
            storage_key = archive_item.get("storage_key")
            filename = archive_item.get("title", "document.pdf")
        else:
            doc = db.documents.find_one({"_id": ObjectId(doc_id)})
            if not doc or not doc.get("is_shared"):
                raise HTTPException(status_code=403, detail="Access denied.")
            storage_key = doc.get("storage_key") or doc.get("preview_storage_key")
            filename = doc.get("file_name", "document.pdf")

        if not storage_key:
            raise HTTPException(status_code=404, detail="File not found in storage.")

        stream = storage_service.get_file_stream(storage_key)
        if not stream:
            raise HTTPException(status_code=404, detail="File stream error.")

        return StreamingResponse(
            stream,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

# --- AUTHENTICATED CASE ENDPOINTS ---

@router.get("/", response_model=List[CaseOut], include_in_schema=False)
async def get_user_cases(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    return await asyncio.to_thread(
        case_service.get_cases_for_user,
        db=db,
        owner=current_user
    )

@router.post("/", response_model=CaseOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
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
    case_oid = validate_object_id(case_id)
    pos = body.client_position.upper()
    if pos not in ["DEFENDANT", "PLAINTIFF", "NEUTRAL"]:
        raise HTTPException(status_code=400, detail="Position must be DEFENDANT, PLAINTIFF, or NEUTRAL")

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