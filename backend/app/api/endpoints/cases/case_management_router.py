# FILE: backend/app/api/endpoints/cases/case_management_router.py
# PHOENIX PROTOCOL - CASE MANAGEMENT ROUTER V20.0 (CASCADE WIPEOUT)
# V20.0: /clear-audit bën cascade wipeout — fshin edhe case_synthesis,
#        case_extractions, case_cross_references.
# V19.0: DOSSIER-LEVEL AUDIT PERSISTENCE

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Annotated, Dict, Any, Optional
from fastapi.responses import StreamingResponse, JSONResponse, Response
from pymongo.database import Database
from bson import ObjectId
from pydantic import BaseModel, Field
import asyncio
import logging
from datetime import datetime, timezone

from app.services import case_service, storage_service
from app.models.case import CaseCreate, CaseOut
from app.models.user import UserInDB
from app.api.endpoints.dependencies import get_current_user, get_db
from app.api.endpoints.cases.cases_helpers import validate_object_id, ChatHistoryUpdate, UpdateCasePositionRequest

router = APIRouter()
logger = logging.getLogger(__name__)


class CaseDossierAuditPayload(BaseModel):
    content: str = Field(..., description="Përmbajtja e plotë e doktrinës forenzike të fashikullit")


# =========================================================================
# 🌐 1. PUBLIC CLIENT PORTAL ENDPOINTS
# =========================================================================

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


# =========================================================================
# ⚖️ 2. AUTHENTICATED CASE CRUD & MANAGEMENT ENDPOINTS
# =========================================================================

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
# 📜 2.1. DOKTRINA FORENZIKE E FASHIKULLIT — PERSISTENCE (MULTI-DEVICE SYNC)
# =========================================================================

@router.post("/{case_id}/audit", status_code=status.HTTP_200_OK)
async def save_case_dossier_audit(
    case_id: str,
    payload: CaseDossierAuditPayload,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """
    Ruan doktrinën forenzike të fashikullit në MongoDB (koleksioni `cases`).
    """
    case_oid = validate_object_id(case_id)
    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Përmbajtja e doktrinës nuk mund të jetë e zbrazët.")

    case = await asyncio.to_thread(
        case_service.get_case_by_id,
        db=db,
        case_id=case_oid,
        owner=current_user
    )
    if not case:
        raise HTTPException(status_code=404, detail="Lënda nuk u gjet ose nuk keni autorizim.")

    now = datetime.now(timezone.utc)
    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": case_oid},
        {"$set": {
            "latest_dossier_analysis": content,
            "last_dossier_audited_at": now,
            "updated_at": now
        }}
    )

    logger.info(f"🧠 [CASE DOSSIER AUDIT SAVED] Lënda {case_id} — {len(content)} karaktere")

    return {
        "status": "success",
        "case_id": case_id,
        "saved_at": now.isoformat(),
        "length": len(content)
    }


@router.post("/{case_id}/clear-audit", status_code=status.HTTP_200_OK)
@router.delete("/{case_id}/clear-audit", status_code=status.HTTP_200_OK)
async def clear_case_dossier_audit(
    case_id: str,
    document_ids: Optional[List[str]] = Query(
        None,
        description="Nëse jepet, fshin vetëm cache-in për këto dokumente. "
                    "Nëse null, fshin të gjitha cache-t e lëndës."
    ),
    current_user: Annotated[UserInDB, Depends(get_current_user)] = None,
    db: Database = Depends(get_db),
):
    """
    CASCADE WIPEOUT — Fshin të gjitha cache-t e analizës për këtë lëndë:

    - cases.latest_dossier_analysis (fushat e vjetra)
    - case_synthesis (scope=case dhe scope=document)
    - case_extractions (ekstraktimet NER)
    - case_cross_references (lidhjet midis dokumenteve)
    - findings (nëse ka)

    Kjo garanton që "Analizo" pas fshirjes fillon NGA ZERO — zero cache hit.
    """
    case_oid = validate_object_id(case_id)
    case_id_str = str(case_id)

    # Verifiko pronësinë
    case = await asyncio.to_thread(
        case_service.get_case_by_id,
        db=db,
        case_id=case_oid,
        owner=current_user
    )
    if not case:
        raise HTTPException(status_code=404, detail="Lënda nuk u gjet ose nuk keni autorizim.")

    # ═══ Build filter — mbështet String + ObjectId për case_id ═══
    case_id_variants = [case_id_str]
    if ObjectId.is_valid(case_id_str):
        case_id_variants.append(ObjectId(case_id_str))

    base_filter = {"case_id": {"$in": case_id_variants}}

    # Nëse document_ids specifike → scope vetëm ato dokumente
    if document_ids:
        synthesis_filter = {
            "$and": [
                base_filter,
                {"scope": "document"},
                {"document_ids": {"$in": document_ids}},
            ]
        }
        extractions_filter = {
            "$and": [
                base_filter,
                {"document_id": {"$in": document_ids}},
            ]
        }
    else:
        synthesis_filter = base_filter
        extractions_filter = base_filter

    deleted: Dict[str, Any] = {
        "case_synthesis": 0,
        "case_extractions": 0,
        "case_cross_references": 0,
        "findings": 0,
        "latest_dossier_analysis_removed": False,
    }

    # ═══ 1. Fshij case_synthesis (cascade) ═══
    try:
        r = await asyncio.to_thread(db.case_synthesis.delete_many, synthesis_filter)
        deleted["case_synthesis"] = r.deleted_count
    except Exception as e:
        logger.warning(f"⚠️ [CLEAR-AUDIT] case_synthesis delete failed: {e}")

    # ═══ 2. Fshij case_extractions ═══
    try:
        r = await asyncio.to_thread(db.case_extractions.delete_many, extractions_filter)
        deleted["case_extractions"] = r.deleted_count
    except Exception as e:
        logger.warning(f"⚠️ [CLEAR-AUDIT] case_extractions delete failed: {e}")

    # ═══ 3. Fshij case_cross_references (vetëm për case scope) ═══
    if not document_ids:
        try:
            r = await asyncio.to_thread(db.case_cross_references.delete_many, base_filter)
            deleted["case_cross_references"] = r.deleted_count
        except Exception as e:
            logger.warning(f"⚠️ [CLEAR-AUDIT] case_cross_references delete failed: {e}")

    # ═══ 4. Fshij findings (vetëm për case scope) ═══
    if not document_ids:
        try:
            r = await asyncio.to_thread(db.findings.delete_many, base_filter)
            deleted["findings"] = r.deleted_count
        except Exception as e:
            logger.warning(f"⚠️ [CLEAR-AUDIT] findings delete failed: {e}")

    # ═══ 5. Unset fusha në cases ═══
    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": case_oid},
        {"$unset": {
            "latest_dossier_analysis": "",
            "last_dossier_audited_at": ""
        }}
    )
    deleted["latest_dossier_analysis_removed"] = True

    logger.info(
        f"🗑️ [CASCADE WIPEOUT] Lënda {case_id} — "
        f"synthesis={deleted['case_synthesis']}, "
        f"extractions={deleted['case_extractions']}, "
        f"xrefs={deleted['case_cross_references']}, "
        f"findings={deleted['findings']}, "
        f"docs={document_ids or 'ALL'}"
    )

    return {
        "status": "success",
        "message": "Cascade wipeout u ekzekutua me sukses. Cache-i i analizës u fshi plotësisht.",
        "case_id": case_id,
        "document_ids": document_ids,
        "deleted": deleted,
    }


# =========================================================================
# 🗑️ 3. DELETE CASE
# =========================================================================

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