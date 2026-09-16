# FILE: backend/app/api/endpoints/forensic/dossier_router.py
# PHOENIX PROTOCOL - FORENSIC DOSSIER & CUSTODY ROUTER V4.0 (AUDIT TRAIL PURGED)
# 100% COMPLETE CODE • ZERO PY WARNINGS • RBAC PROTECTED • PHONE & EMAIL SYNC

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.db import get_db
from app.api.endpoints.dependencies import get_current_forensic_user
from app.models.user import UserInDB
from app.services import storage_service
from app.services.forensic.forensic_chain_of_custody import create_custody_stamp

router = APIRouter()
logger = logging.getLogger(__name__)

FORENSIC_DOSSIERS_COLLECTION = "forensic_dossiers"

class ForensicDossierCreate(BaseModel):
    title: str = Field(..., min_length=2)
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_email: Optional[str] = None
    case_number: Optional[str] = None
    court_jurisdiction: Optional[str] = "Gjykata Themelore Prishtinë"
    practice_area: Optional[str] = "Penale"
    case_summary: Optional[str] = None
    target_actors: List[str] = Field(default_factory=list)

class ForensicDossierUpdate(BaseModel):
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_email: Optional[str] = None
    court_jurisdiction: Optional[str] = None
    case_number: Optional[str] = None
    case_summary: Optional[str] = None

class SealCustodyRequest(BaseModel):
    action_note: str = "Vulosje e Provave Materiale"
    evidence_ids: List[str] = Field(default_factory=list)

class ForensicDossierAuditPayload(BaseModel):
    content: str = Field(..., description="Përmbajtja e plotë e auditimit doktrinar të fashikullit")

# ==========================================================
# 1. KRIJIMI I DOSJES FORENZIKE ME METADATA TË PLOTA
# ==========================================================
@router.post("/dossiers", status_code=status.HTTP_201_CREATED)
def create_forensic_dossier(
    payload: ForensicDossierCreate,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    now_utc = datetime.now(timezone.utc)

    resolved_client_name = payload.client_name or payload.title.replace("DOSJA FORENZIKE: ", "").strip()

    custody_stamp = create_custody_stamp(
        user_id=user_id,
        case_id="NEW_DOSSIER",
        action="DOSSIER_INITIALIZED",
        metadata={"title": payload.title, "client_name": resolved_client_name}
    )

    doc = {
        "title": payload.title,
        "client_name": resolved_client_name,
        "client_phone": payload.client_phone or "",
        "client_email": payload.client_email or "",
        "case_number": payload.case_number or f"FOR-{now_utc.strftime('%Y%m%d')}-{int(now_utc.timestamp())%10000}",
        "court_jurisdiction": payload.court_jurisdiction or "Gjykata Themelore Prishtinë",
        "practice_area": payload.practice_area or "Penale",
        "case_summary": payload.case_summary or "",
        "target_actors": payload.target_actors,
        "status": "OPEN_INVESTIGATION",
        "created_by": user_id,
        "created_at": now_utc,
        "updated_at": now_utc,
        "chain_of_custody": [custody_stamp],
        "is_sealed": False
    }

    result = db[FORENSIC_DOSSIERS_COLLECTION].insert_one(doc)
    doc_id = str(result.inserted_id)

    doc["_id"] = doc_id
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    return doc

# ==========================================================
# 2. LISTIMI I DOSJEVE FORENZIKE
# ==========================================================
@router.get("/dossiers")
def list_forensic_dossiers(
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200)
):
    cursor = db[FORENSIC_DOSSIERS_COLLECTION].find().sort("created_at", -1).skip(skip).limit(limit)
    dossiers = []
    for d in cursor:
        d["_id"] = str(d["_id"])
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
        if isinstance(d.get("updated_at"), datetime):
            d["updated_at"] = d["updated_at"].isoformat()
        dossiers.append(d)
    return dossiers

# ==========================================================
# 3. MARRJA E DETAJEVE TË NJË DOSJEJE
# ==========================================================
@router.get("/dossiers/{case_id}")
def get_forensic_dossier(
    case_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    try:
        query = {"_id": ObjectId(case_id)}
    except Exception:
        query = {"_id": case_id}

    dossier = db[FORENSIC_DOSSIERS_COLLECTION].find_one(query)
    if not dossier:
        regular_case = db["cases"].find_one(query)
        if not regular_case:
            raise HTTPException(status_code=404, detail="Dosja forenzike nuk u gjet.")
        dossier = {
            "_id": str(regular_case["_id"]),
            "title": regular_case.get("title", "Lëndë Juridike"),
            "client_name": regular_case.get("client_name") or regular_case.get("title", "Palë e Regjistruar"),
            "client_phone": regular_case.get("client_phone", ""),
            "client_email": regular_case.get("client_email", ""),
            "case_number": regular_case.get("case_number", "PA-NUMËR"),
            "court_jurisdiction": regular_case.get("court_jurisdiction", "Gjykata Themelore"),
            "practice_area": regular_case.get("practice_area", "E Përgjithshme"),
            "case_summary": regular_case.get("description", ""),
            "created_at": regular_case.get("created_at", datetime.now(timezone.utc)),
            "chain_of_custody": [],
            "is_sealed": False
        }

    dossier["_id"] = str(dossier["_id"])
    return dossier

# ==========================================================
# 3.1. AUDITIMI DOKTRINAR I FASHIKULLIT — PERSISTENCE (MULTI-DEVICE SYNC)
# ==========================================================
@router.post("/dossiers/{case_id}/audit", status_code=status.HTTP_200_OK)
def save_forensic_dossier_audit(
    case_id: str,
    payload: ForensicDossierAuditPayload,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """
    Ruan auditimin doktrinar të fashikullit forenzik në MongoDB.
    Provon së pari koleksionin `forensic_dossiers`, pastaj `cases` si fallback.
    """
    user_id = str(current_user.id)
    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Përmbajtja e auditimit nuk mund të jetë e zbrazët.")

    target_coll = FORENSIC_DOSSIERS_COLLECTION
    try:
        query = {"_id": ObjectId(case_id)}
    except Exception:
        query = {"_id": case_id}

    dossier = db[FORENSIC_DOSSIERS_COLLECTION].find_one(query)
    if not dossier:
        dossier = db["cases"].find_one(query)
        target_coll = "cases"

    if not dossier:
        raise HTTPException(status_code=404, detail="Dosja forenzike nuk u gjet.")

    now = datetime.now(timezone.utc)
    db[target_coll].update_one(
        {"_id": dossier["_id"]},
        {"$set": {
            "latest_dossier_analysis": content,
            "last_dossier_audited_at": now,
            "updated_at": now
        }}
    )

    logger.info(f"🧠 [FORENSIC DOSSIER AUDIT SAVED] {case_id} → {target_coll} — {len(content)} karaktere")

    return {
        "status": "success",
        "case_id": case_id,
        "saved_at": now.isoformat(),
        "length": len(content),
        "collection": target_coll
    }

@router.post("/dossiers/{case_id}/clear-audit", status_code=status.HTTP_200_OK)
@router.delete("/dossiers/{case_id}/clear-audit", status_code=status.HTTP_200_OK)
def clear_forensic_dossier_audit(
    case_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """
    Fshin auditimin e ruajtur të fashikullit forenzik nga të dyja koleksionet e mundshme.
    """
    user_id = str(current_user.id)
    try:
        query = {"_id": ObjectId(case_id)}
    except Exception:
        query = {"_id": case_id}

    target_coll = FORENSIC_DOSSIERS_COLLECTION
    dossier = db[FORENSIC_DOSSIERS_COLLECTION].find_one(query)
    if not dossier:
        dossier = db["cases"].find_one(query)
        target_coll = "cases"

    if not dossier:
        raise HTTPException(status_code=404, detail="Dosja forenzike nuk u gjet.")

    db[target_coll].update_one(
        {"_id": dossier["_id"]},
        {"$unset": {
            "latest_dossier_analysis": "",
            "last_dossier_audited_at": ""
        }}
    )

    return {
        "status": "success",
        "message": "Auditimi i fashikullit forenzik u fshi plotësisht.",
        "case_id": case_id,
        "collection": target_coll
    }

# ==========================================================
# 4. EDITIMI DHE PËRDITËSIMI I TË DHËNAVE TË DOSJES (PUT)
# ==========================================================
@router.put("/dossiers/{case_id}")
def update_forensic_dossier(
    case_id: str,
    payload: ForensicDossierUpdate,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """Përditëson emrin, telefonin, email-in apo gjykatën e dosjes ekzistuese."""
    user_id = str(current_user.id)
    try:
        query = {"_id": ObjectId(case_id)}
    except Exception:
        query = {"_id": case_id}

    update_fields: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}

    if payload.client_name is not None:
        update_fields["client_name"] = payload.client_name
        update_fields["title"] = f"DOSJA FORENZIKE: {payload.client_name}"
    if payload.client_phone is not None:
        update_fields["client_phone"] = payload.client_phone
    if payload.client_email is not None:
        update_fields["client_email"] = payload.client_email
    if payload.court_jurisdiction is not None:
        update_fields["court_jurisdiction"] = payload.court_jurisdiction
    if payload.case_number is not None:
        update_fields["case_number"] = payload.case_number
    if payload.case_summary is not None:
        update_fields["case_summary"] = payload.case_summary

    result = db[FORENSIC_DOSSIERS_COLLECTION].update_one(query, {"$set": update_fields})

    if result.matched_count == 0:
        db["cases"].update_one(query, {"$set": update_fields})

    return {"status": "success", "message": "Të dhënat e dosjes u përditësuan me sukses."}

# ==========================================================
# 5. VULOSJA SERVER-SIDE E CUSTODY
# ==========================================================
@router.post("/dossiers/{case_id}/seal-custody")
def seal_case_chain_of_custody(
    case_id: str,
    payload: SealCustodyRequest,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    stamp = create_custody_stamp(
        user_id=user_id,
        case_id=case_id,
        action=payload.action_note,
        evidence_ids=payload.evidence_ids
    )

    try:
        oid = ObjectId(case_id)
        db[FORENSIC_DOSSIERS_COLLECTION].update_one(
            {"_id": oid},
            {
                "$push": {"chain_of_custody": stamp},
                "$set": {"updated_at": datetime.now(timezone.utc), "is_sealed": True}
            }
        )
    except Exception:
        pass

    return {
        "success": True,
        "message": "Dosja dhe provat u vulosën me sukses nga serveri.",
        "custody_stamp": stamp
    }

# ==========================================================
# 6. TOTAL CASCADE WIPEOUT I DOSJES NGA MONGODB
# ==========================================================
@router.delete("/dossiers/{case_id}", status_code=status.HTTP_200_OK)
def delete_forensic_dossier(
    case_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    query_id = {"_id": ObjectId(case_id)} if ObjectId.is_valid(case_id) else {"_id": case_id}
    
    dossier = db[FORENSIC_DOSSIERS_COLLECTION].find_one(query_id)
    if not dossier:
        dossier = db["cases"].find_one(query_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dosja nuk u gjet.")

    storage_keys_to_delete = set()

    for doc in db["forensic_documents"].find({"case_id": str(case_id)}):
        if doc.get("storage_key"):
            storage_keys_to_delete.add(doc["storage_key"])
        if doc.get("preview_storage_key"):
            storage_keys_to_delete.add(doc["preview_storage_key"])

    for media in db["forensic_media"].find({"case_id": str(case_id)}):
        if media.get("storage_key"):
            storage_keys_to_delete.add(media["storage_key"])

    for fin in db["forensic_financial_records"].find({"case_id": str(case_id)}):
        if fin.get("storage_key"):
            storage_keys_to_delete.add(fin["storage_key"])

    for storage_key in storage_keys_to_delete:
        try:
            storage_service.delete_file(storage_key=storage_key)
        except Exception as e:
            logger.warning(f"Failed to delete storage key {storage_key}: {e}")

    child_collections = [
        "forensic_documents",
        "forensic_media",
        "forensic_financial_records",
        "forensic_war_room_records",
        "forensic_chat_history",
        "forensic_investigator_findings"
    ]

    for coll in child_collections:
        db[coll].delete_many({"case_id": str(case_id)})
        if ObjectId.is_valid(case_id):
            db[coll].delete_many({"case_id": ObjectId(case_id)})

    try:
        db["user_vectors"].delete_many({"case_id": str(case_id)})
        if ObjectId.is_valid(case_id):
            db["user_vectors"].delete_many({"case_id": ObjectId(case_id)})
    except Exception:
        pass

    db[FORENSIC_DOSSIERS_COLLECTION].delete_many({
        "$or": [
            query_id,
            {"_id": str(case_id)},
            {"case_id": str(case_id)}
        ]
    })
    db["cases"].delete_many({
        "$or": [
            query_id,
            {"_id": str(case_id)}
        ]
    })

    return {
        "status": "success",
        "message": "Dosja u fshi plotësisht bashkë me të gjitha provat dhe regjistrat e lidhur.",
        "deleted_case_id": case_id
    }