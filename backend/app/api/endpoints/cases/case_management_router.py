# FILE: backend/app/api/endpoints/cases/case_management_router.py
# PHOENIX PROTOCOL - CASE MANAGEMENT ROUTER V22.1
# V22.1: SECURITY HARDENING —
#        - DOC_ID VALIDATION: _parse_doc_ids_param + save_audit validon
#          ObjectId format për çdo doc_id. Parandalon MongoDB field injection
#          përmes `document_reviews.{doc_id}` ($ dhe . prefikse).
#        - DOC_IDS LIMIT: MAX_DOC_IDS_PER_REQUEST = 100 (parandalon 16MB
#          BSON doc limit kur ka mijëra doc_ids në $unset).
#        - CHAT_HISTORY LIMIT: MAX_HISTORY_MESSAGES = 500 (parandalon
#          DocumentTooLarge në Mongo me 16MB limit nga history i pakufizuar).
#        - DEAD CODE: hequr `unset_fields["updated_at"]` + .pop() në
#          DOCUMENT SCOPE (ishte shtuar dhe hequr menjëherë, pa kuptim).
# V22.0: PER-DOCUMENT AUDIT STORAGE — raporte të veçanta për çdo dokument
#        në `cases.document_reviews.{doc_id}`. Case synthesis mbetet në
#        `latest_dossier_analysis` (backward compat + 1 raport për case).
# V21.2: Log emërtimi CASE/DOCUMENT AUDIT.
# V21.1: SECURITY FIX update_case_client_position.
# V21.0: DOSSIER READ-ENDPOINT + SCOPE PERSISTENCE.

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


# ═══════════════════════════════════════════════════════════════════════════
# V22.1: SECURITY LIMITS
# ═══════════════════════════════════════════════════════════════════════════

MAX_HISTORY_MESSAGES = 500
MAX_DOC_IDS_PER_REQUEST = 100


class CaseDossierAuditPayload(BaseModel):
    content: str = Field(..., description="Përmbajtja e plotë e doktrinës forenzike")
    document_ids: Optional[List[str]] = Field(
        None,
        description="Nëse jepet → scope='document', ruhet në document_reviews. "
                    "Nëse null → scope='case', ruhet në latest_dossier_analysis."
    )


def _validate_doc_id_format(doc_id: str) -> str:
    """
    V22.1: Validon që doc_id është ObjectId hex 24-karakteresh.

    Parandalon MongoDB field injection përmes `document_reviews.{doc_id}`:
      - Prefiks `$` → refuzohet nga Mongo me OperationFailure (500 error)
      - Pika `.` → interpretohet si nested field (korrupsion i dhënave)
    """
    clean = str(doc_id).strip()
    if not clean:
        raise HTTPException(status_code=400, detail="doc_id i zbrazët.")
    if not ObjectId.is_valid(clean):
        # Nuk logo çelësin e plotë — mund të përmbajë input malicious
        safe_preview = clean[:30].replace('\n', ' ').replace('\r', ' ')
        raise HTTPException(
            status_code=400,
            detail=f"doc_id i pavlefshëm: '{safe_preview}' — duhet ObjectId (24 hex)."
        )
    return clean


def _parse_doc_ids_param(document_ids: Optional[str]) -> List[str]:
    """
    V22.1: Parse query string 'doc1,doc2' → ['doc1', 'doc2'].
    Validon format ObjectId + limit.
    """
    if not document_ids:
        return []
    parts = [d.strip() for d in document_ids.split(',') if d.strip()]
    if len(parts) > MAX_DOC_IDS_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"Shumë doc_ids: max {MAX_DOC_IDS_PER_REQUEST} "
                   f"(u dërguan {len(parts)})."
        )
    return [_validate_doc_id_format(d) for d in parts]


def _validate_doc_ids_list(doc_ids: Optional[List[str]]) -> List[str]:
    """
    V22.1: Validon listë doc_ids nga body (jo query string).
    """
    if not doc_ids:
        return []
    if len(doc_ids) > MAX_DOC_IDS_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"Shumë doc_ids: max {MAX_DOC_IDS_PER_REQUEST} "
                   f"(u dërguan {len(doc_ids)})."
        )
    return [_validate_doc_id_format(d) for d in doc_ids]


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
    """V21.1: SECURITY — verifiko aksesin para se të ndryshosh pozicionin."""
    case_oid = validate_object_id(case_id)
    pos = body.client_position.upper()
    if pos not in ["DEFENDANT", "PLAINTIFF", "NEUTRAL"]:
        raise HTTPException(status_code=400, detail="Position must be DEFENDANT, PLAINTIFF, or NEUTRAL")

    case = await asyncio.to_thread(
        case_service.get_case_by_id,
        db=db,
        case_id=case_oid,
        owner=current_user
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found or access denied.")

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

    # V22.1: LIMIT — parandalon DocumentTooLarge në Mongo (16MB) nga
    # history i pakufizuar (100k mesazhe × 10KB = 1GB).
    history_count = len(update.chat_history or [])
    if history_count > MAX_HISTORY_MESSAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Historiku i bisedës është shumë i gjatë. "
                   f"Max {MAX_HISTORY_MESSAGES} mesazhe (u dërguan {history_count})."
        )

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
# 📜 2.1. DOKTRINA FORENZIKE — PERSISTENCE + READ + CLEAR (V22.1)
# =========================================================================

@router.get("/{case_id}/audit", status_code=status.HTTP_200_OK)
async def get_case_dossier_audit(
    case_id: str,
    document_ids: Optional[str] = Query(
        None,
        description="Comma-separated doc IDs. Nëse jepet → lexon raportin "
                    "e atij dokumenti. Nëse jo → lexon case synthesis."
    ),
    current_user: Annotated[UserInDB, Depends(get_current_user)] = None,
    db: Database = Depends(get_db)
):
    """
    V22.0: Lexon raportin:
    - document_ids jepet → document_reviews[doc_id]
    - document_ids None → latest_dossier_analysis (case synthesis)
    """
    case_oid = validate_object_id(case_id)

    case = await asyncio.to_thread(
        case_service.get_case_by_id,
        db=db,
        case_id=case_oid,
        owner=current_user
    )
    if not case:
        raise HTTPException(status_code=404, detail="Lënda nuk u gjet ose nuk keni autorizim.")

    # V22.1: _parse_doc_ids_param tani validon format + limit
    doc_id_list = _parse_doc_ids_param(document_ids)

    # ═════════════════════════════════════════════════════════════════════
    # V22.0: DOCUMENT SCOPE — lexo document_reviews[doc_id]
    # ═════════════════════════════════════════════════════════════════════
    if doc_id_list:
        primary_doc_id = doc_id_list[0]

        doc = await asyncio.to_thread(
            db.cases.find_one,
            {"_id": case_oid},
            {
                "document_reviews": 1,
                # Backward compat fusha
                "latest_dossier_analysis": 1,
                "last_dossier_audited_at": 1,
                "latest_dossier_scope": 1,
                "latest_dossier_document_ids": 1,
            }
        )

        if not doc:
            return {"has_audit": False, "content": None, "audited_at": None, "scope": "document", "document_ids": doc_id_list}

        # 1) Provo fushën e re
        reviews = doc.get("document_reviews") or {}
        review = reviews.get(primary_doc_id)

        if review and review.get("content"):
            audited_at = review.get("audited_at")
            audited_at_str = audited_at.isoformat() if isinstance(audited_at, datetime) else (str(audited_at) if audited_at else None)
            logger.info(f"📖 [DOC AUDIT READ] case={case_id} doc={primary_doc_id} ({len(review['content'])} chars)")
            return {
                "has_audit": True,
                "content": review["content"],
                "audited_at": audited_at_str,
                "scope": "document",
                "document_ids": doc_id_list,
                "length": len(review["content"]),
            }

        # 2) Backward compat: lexo latest_dossier_analysis nëse scope=document + match
        old_scope = doc.get("latest_dossier_scope")
        old_doc_ids = doc.get("latest_dossier_document_ids") or []
        old_content = doc.get("latest_dossier_analysis")

        if old_scope == "document" and primary_doc_id in old_doc_ids and old_content:
            audited_at = doc.get("last_dossier_audited_at")
            audited_at_str = audited_at.isoformat() if isinstance(audited_at, datetime) else (str(audited_at) if audited_at else None)
            logger.info(f"📖 [DOC AUDIT READ — LEGACY] case={case_id} doc={primary_doc_id} ({len(old_content)} chars)")
            return {
                "has_audit": True,
                "content": old_content,
                "audited_at": audited_at_str,
                "scope": "document",
                "document_ids": doc_id_list,
                "length": len(old_content),
            }

        logger.info(f"📖 [DOC AUDIT READ] case={case_id} doc={primary_doc_id}: nuk ka audit")
        return {
            "has_audit": False,
            "content": None,
            "audited_at": None,
            "scope": "document",
            "document_ids": doc_id_list,
        }

    # ═════════════════════════════════════════════════════════════════════
    # CASE SCOPE — lexo latest_dossier_analysis
    # ═════════════════════════════════════════════════════════════════════
    doc = await asyncio.to_thread(
        db.cases.find_one,
        {"_id": case_oid},
        {
            "latest_dossier_analysis": 1,
            "last_dossier_audited_at": 1,
            "latest_dossier_scope": 1,
        }
    )

    if not doc:
        return {"has_audit": False, "content": None, "audited_at": None, "scope": "case", "document_ids": None}

    content = doc.get("latest_dossier_analysis")
    if not content or not str(content).strip():
        return {"has_audit": False, "content": None, "audited_at": None, "scope": "case", "document_ids": None}

    audited_at = doc.get("last_dossier_audited_at")
    audited_at_str = audited_at.isoformat() if isinstance(audited_at, datetime) else (str(audited_at) if audited_at else None)

    return {
        "has_audit": True,
        "content": content,
        "audited_at": audited_at_str,
        "scope": doc.get("latest_dossier_scope") or "case",
        "document_ids": None,
        "length": len(str(content)),
    }


@router.post("/{case_id}/audit", status_code=status.HTTP_200_OK)
async def save_case_dossier_audit(
    case_id: str,
    payload: CaseDossierAuditPayload,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """
    V22.1: Ruan raportin:
    - document_ids jepet → document_reviews[doc_id] (ruan veçmas për çdo dokument)
    - document_ids None → latest_dossier_analysis (case synthesis)

    Validon format + limit i doc_ids për të shmangur field injection.
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

    # V22.1: Validim format + limit (field injection protection)
    doc_ids = _validate_doc_ids_list(payload.document_ids)
    now = datetime.now(timezone.utc)

    if doc_ids:
        # ═══════════ DOCUMENT SCOPE ═══════════
        primary_doc_id = doc_ids[0]

        review_data = {
            "content": content,
            "audited_at": now,
            "scope": "document",
            "document_ids": doc_ids,
            "created_by": str(current_user.id),
        }

        await asyncio.to_thread(
            db.cases.update_one,
            {"_id": case_oid},
            {
                "$set": {
                    f"document_reviews.{primary_doc_id}": review_data,
                    "updated_at": now,
                }
            }
        )

        logger.info(
            f"🧠 [DOCUMENT AUDIT SAVED] Lënda {case_id} — "
            f"doc={primary_doc_id}, {len(content)} karaktere"
        )

        return {
            "status": "success",
            "case_id": case_id,
            "scope": "document",
            "document_ids": doc_ids,
            "saved_at": now.isoformat(),
            "length": len(content),
        }

    # ═══════════ CASE SCOPE ═══════════
    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": case_oid},
        {"$set": {
            "latest_dossier_analysis": content,
            "last_dossier_audited_at": now,
            "latest_dossier_scope": "case",
            "latest_dossier_document_ids": None,
            "updated_at": now,
        }}
    )

    logger.info(
        f"🧠 [CASE AUDIT SAVED] Lënda {case_id} — {len(content)} karaktere"
    )

    return {
        "status": "success",
        "case_id": case_id,
        "scope": "case",
        "document_ids": None,
        "saved_at": now.isoformat(),
        "length": len(content),
    }


@router.post("/{case_id}/clear-audit", status_code=status.HTTP_200_OK)
@router.delete("/{case_id}/clear-audit", status_code=status.HTTP_200_OK)
async def clear_case_dossier_audit(
    case_id: str,
    document_ids: Optional[str] = Query(
        None,
        description="Comma-separated doc IDs. Nëse jepet → fshin VETËM "
                    "document_reviews[doc_id]. Nëse jo → CASCADE total."
    ),
    current_user: Annotated[UserInDB, Depends(get_current_user)] = None,
    db: Database = Depends(get_db),
):
    """
    V22.1: Fshin raportin:
    - document_ids jepet → fshin VETËM document_reviews[doc_id]. Case synthesis NUK preket.
    - document_ids None → CASCADE WIPEOUT total.
    """
    case_oid = validate_object_id(case_id)
    case_id_str = str(case_id)

    case = await asyncio.to_thread(
        case_service.get_case_by_id,
        db=db,
        case_id=case_oid,
        owner=current_user
    )
    if not case:
        raise HTTPException(status_code=404, detail="Lënda nuk u gjet ose nuk keni autorizim.")

    # V22.1: _parse_doc_ids_param tani validon format + limit
    doc_id_list = _parse_doc_ids_param(document_ids)

    # ═════════════════════════════════════════════════════════════════════
    # V22.0: DOCUMENT SCOPE — fshin VETËM document_reviews[doc_id]
    # V22.1: Hequr dead code për `updated_at` (ishte shtuar + hequr menjëherë)
    # ═════════════════════════════════════════════════════════════════════
    if doc_id_list:
        unset_fields: Dict[str, str] = {
            f"document_reviews.{did}": "" for did in doc_id_list
        }

        result = await asyncio.to_thread(
            db.cases.update_one,
            {"_id": case_oid},
            {
                "$unset": unset_fields,
                "$set": {"updated_at": datetime.now(timezone.utc)},
            }
        )

        logger.info(
            f"🗑️ [DOC AUDIT CLEAR] Lënda {case_id} — fshin {len(doc_id_list)} "
            f"dokument(e): {doc_id_list} (case synthesis NUK preket)"
        )

        return {
            "status": "success",
            "message": f"Raporti i {len(doc_id_list)} dokument(eve) u fshi. "
                      f"Case synthesis mbetet i paprekur.",
            "case_id": case_id,
            "document_ids": doc_id_list,
            "deleted": {
                "document_reviews": len(doc_id_list),
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
            },
        }

    # ═════════════════════════════════════════════════════════════════════
    # CASE SCOPE — CASCADE WIPEOUT total
    # ═════════════════════════════════════════════════════════════════════
    case_id_variants = [case_id_str]
    if ObjectId.is_valid(case_id_str):
        case_id_variants.append(ObjectId(case_id_str))

    base_filter = {"case_id": {"$in": case_id_variants}}

    deleted: Dict[str, Any] = {
        "case_synthesis": 0,
        "case_extractions": 0,
        "case_cross_references": 0,
        "findings": 0,
        "document_reviews_cleared": 0,
        "latest_dossier_analysis_removed": False,
    }

    try:
        r = await asyncio.to_thread(db.case_synthesis.delete_many, base_filter)
        deleted["case_synthesis"] = r.deleted_count
    except Exception as e:
        logger.warning(f"⚠️ [CLEAR-AUDIT] case_synthesis delete failed: {e}")

    try:
        r = await asyncio.to_thread(db.case_extractions.delete_many, base_filter)
        deleted["case_extractions"] = r.deleted_count
    except Exception as e:
        logger.warning(f"⚠️ [CLEAR-AUDIT] case_extractions delete failed: {e}")

    try:
        r = await asyncio.to_thread(db.case_cross_references.delete_many, base_filter)
        deleted["case_cross_references"] = r.deleted_count
    except Exception as e:
        logger.warning(f"⚠️ [CLEAR-AUDIT] case_cross_references delete failed: {e}")

    try:
        r = await asyncio.to_thread(db.findings.delete_many, base_filter)
        deleted["findings"] = r.deleted_count
    except Exception as e:
        logger.warning(f"⚠️ [CLEAR-AUDIT] findings delete failed: {e}")

    # V22.0: Numëro document_reviews para se t'i fshijmë (për log)
    try:
        doc_with_reviews = await asyncio.to_thread(
            db.cases.find_one,
            {"_id": case_oid},
            {"document_reviews": 1}
        )
        reviews = (doc_with_reviews or {}).get("document_reviews") or {}
        deleted["document_reviews_cleared"] = len(reviews)
    except Exception:
        pass

    await asyncio.to_thread(
        db.cases.update_one,
        {"_id": case_oid},
        {
            "$unset": {
                "latest_dossier_analysis": "",
                "last_dossier_audited_at": "",
                "latest_dossier_scope": "",
                "latest_dossier_document_ids": "",
            },
            "$set": {
                "document_reviews": {},
                "updated_at": datetime.now(timezone.utc),
            },
        }
    )
    deleted["latest_dossier_analysis_removed"] = True

    logger.info(
        f"🗑️ [CASCADE WIPEOUT] Lënda {case_id} — "
        f"synthesis={deleted['case_synthesis']}, "
        f"extractions={deleted['case_extractions']}, "
        f"xrefs={deleted['case_cross_references']}, "
        f"findings={deleted['findings']}, "
        f"doc_reviews={deleted['document_reviews_cleared']}"
    )

    return {
        "status": "success",
        "message": "Cascade wipeout u ekzekutua me sukses (përfshirë të gjitha document reviews).",
        "case_id": case_id,
        "document_ids": None,
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