# FILE: app/api/endpoints/cases/case_management_router.py
# PHOENIX PROTOCOL - CASE MANAGEMENT ROUTER V16.0 (DEDICATED FORENSIC CHAT PERSISTENCE & $UNSET WIPEOUT)
# 100% COMPLETE CODE • ZERO TS/PY WARNINGS • MULTI-DEVICE FORENSIC CHAT SYNC

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Annotated, Dict, Any, Optional
from pydantic import BaseModel
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

class SavePillarRequest(BaseModel):
    pillar: str
    content: str

class SaveDocPillarRequest(BaseModel):
    pillar: str
    content: str

class ForensicChatUpdate(BaseModel):
    forensic_chat_history: List[Dict[str, Any]]

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
        raise HTTPException(status_code=404, detail="Case not found")
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

# =========================================================================
# 🧠 CHATI FORENZIK I SUPERADMINIT (PERSISTENCË NË MONGODB & MULTI-DEVICE)
# =========================================================================

@router.get("/{case_id}/forensic-chat", status_code=status.HTTP_200_OK)
async def get_forensic_chat_history_endpoint(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """Merr bisedën konfidenciale të Zyrës Forenzike nga MongoDB Atlas."""
    case_oid = validate_object_id(case_id)
    case = db.cases.find_one({"_id": case_oid})
    if not case:
        raise HTTPException(status_code=404, detail="Lënda nuk u gjet.")
    return case.get("forensic_chat_history") or []

@router.put("/{case_id}/forensic-chat", status_code=status.HTTP_200_OK)
async def update_forensic_chat_history_endpoint(
    case_id: str,
    payload: ForensicChatUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """Ruan bisedën konfidenciale të Zyrës Forenzike në MongoDB Atlas."""
    case_oid = validate_object_id(case_id)
    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": case_oid},
        {
            "$set": {
                "forensic_chat_history": payload.forensic_chat_history,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    return {"status": "success", "message": "Biseda forenzike u ruajt në MongoDB."}

@router.delete("/{case_id}/forensic-chat", status_code=status.HTTP_200_OK)
async def delete_forensic_chat_history_endpoint(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """Asgjëson me $unset bisedën konfidenciale forenzike nga MongoDB Atlas (Total Wipeout)."""
    case_oid = validate_object_id(case_id)
    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": case_oid},
        {
            "$unset": {
                "forensic_chat_history": ""
            },
            "$set": {
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    logger.info(f"🧹 [FORENSIC CHAT PURGED] U asgjësua biseda forenzike për lëndën {case_id} nga MongoDB!")
    return {"status": "success", "message": "Biseda forenzike u asgjësua plotësisht nga MongoDB (Total Wipeout)."}

# =========================================================================
# 🧹 PHOENIX TOTAL PURGE: ASGJËSIMI I PLOTË I ANALIZËS SË RASTIT NGA MONGODB
# =========================================================================
@router.post("/{case_id}/analysis/clear", status_code=status.HTTP_200_OK)
@router.delete("/{case_id}/analysis/clear", status_code=status.HTTP_200_OK)
async def clear_full_case_analysis_endpoint(
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
                "latest_deep_analysis": "",
                "latest_comprehensive_analysis": "",
                "latest_analysis": "",
                "standard_summary": "",
                "forensic_pillars": ""
            },
            "$set": {
                "analysis_dirty": True,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    logger.info(f"🧹 [FULL CASE ANALYSIS PURGED] U fshi me $unset çdo gjurmë e analizës për lëndën {case_id} nga MongoDB!")
    return {"status": "success", "message": "Analiza e lëndës u asgjësua plotësisht nga MongoDB."}

# =========================================================================
# 🏛️ SHTJELLAT E LËNDËS NË MONGODB
# =========================================================================

@router.post("/{case_id}/pillars", status_code=status.HTTP_200_OK)
async def save_case_pillar_endpoint(
    case_id: str,
    payload: SavePillarRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    user_oid = ObjectId(current_user.id) if ObjectId.is_valid(current_user.id) else current_user.id
    
    case = db.cases.find_one({"_id": case_oid, "$or": [{"owner_id": user_oid}, {"owner_id": str(user_oid)}]})
    if not case:
        raise HTTPException(status_code=404, detail="Lënda nuk u gjet.")
    
    pillar_key = payload.pillar.strip()
    content_clean = payload.content.strip()

    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": case_oid},
        {
            "$set": {
                f"forensic_pillars.{pillar_key}": content_clean,
                "latest_deep_analysis": content_clean,
                "analysis_dirty": False,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    logger.info(f"💾 [MongoDB Case Pillar Saved] U ruajt {pillar_key} për lëndën {case_id}!")
    return {"status": "success", "pillar": pillar_key}

@router.get("/{case_id}/pillars", status_code=status.HTTP_200_OK)
async def get_case_pillars_endpoint(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    user_oid = ObjectId(current_user.id) if ObjectId.is_valid(current_user.id) else current_user.id
    
    case = db.cases.find_one({"_id": case_oid, "$or": [{"owner_id": user_oid}, {"owner_id": str(user_oid)}]})
    if not case:
        raise HTTPException(status_code=404, detail="Lënda nuk u gjet.")
    
    return case.get("forensic_pillars") or {}

@router.delete("/{case_id}/pillars/{pillar_name}", status_code=status.HTTP_200_OK)
async def delete_single_case_pillar_endpoint(
    case_id: str,
    pillar_name: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    pillar_key = pillar_name.strip()

    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": case_oid},
        {
            "$unset": {
                f"forensic_pillars.{pillar_key}": "",
                "latest_deep_analysis": "",
                "latest_comprehensive_analysis": ""
            },
            "$set": {
                "analysis_dirty": True,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    logger.info(f"🧹 [TOTAL CASCADE WIPEOUT] U fshi plotësisht shtjella {pillar_key} për lëndën {case_id}!")
    return {"status": "success", "message": f"Shtjella {pillar_key} u asgjësua nga MongoDB."}

# =========================================================================
# ⚖️ SHTJELLAT E DOKUMENTIT TË VETËM
# =========================================================================

@router.post("/{case_id}/documents/{document_id}/pillars", status_code=status.HTTP_200_OK)
async def save_document_pillar_endpoint(
    case_id: str,
    document_id: str,
    payload: SaveDocPillarRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    doc_oid = validate_object_id(document_id)
    pillar_key = payload.pillar.strip()
    content_clean = payload.content.strip()

    await asyncio.to_thread(
        db.documents.update_one,
        {"_id": doc_oid, "$or": [{"case_id": case_id}, {"case_id": case_oid}]},
        {
            "$set": {
                f"forensic_pillars.{pillar_key}": content_clean,
                "latest_analysis": content_clean,
                "latest_forensic_audit": content_clean,
                "last_audited_at": datetime.now(timezone.utc)
            }
        }
    )
    logger.info(f"💾 [MongoDB Doc Pillar Saved] U ruajt {pillar_key} për dokumentin {document_id}!")
    return {"status": "success", "document_id": document_id, "pillar": pillar_key}

@router.get("/{case_id}/documents/{document_id}/pillars", status_code=status.HTTP_200_OK)
async def get_document_pillars_endpoint(
    case_id: str,
    document_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    doc_oid = validate_object_id(document_id)
    doc = db.documents.find_one({"_id": doc_oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumenti nuk u gjet.")

    return doc.get("forensic_pillars") or {}

@router.delete("/{case_id}/documents/{document_id}/pillars/{pillar_name}", status_code=status.HTTP_200_OK)
async def delete_single_document_pillar_endpoint(
    case_id: str,
    document_id: str,
    pillar_name: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    doc_oid = validate_object_id(document_id)
    case_oid = validate_object_id(case_id)
    pillar_key = pillar_name.strip()

    await asyncio.to_thread(
        db.documents.update_one,
        {"_id": doc_oid, "$or": [{"case_id": case_id}, {"case_id": case_oid}]},
        {
            "$unset": {
                f"forensic_pillars.{pillar_key}": "",
                "latest_analysis": "",
                "latest_forensic_audit": ""
            }
        }
    )
    logger.info(f"🧹 [TOTAL CASCADE WIPEOUT] U asgjësua {pillar_key} për dokumentin {document_id} nga MongoDB!")
    return {"status": "success", "message": f"Shtjella {pillar_key} u fshi plotësisht nga dokumenti."}

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