# FILE: backend/app/api/endpoints/forensic/dossier_router.py
# PHOENIX PROTOCOL - FORENSIC DOSSIER & CUSTODY ROUTER V1.0

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.db import get_db
from app.api.endpoints.dependencies import get_current_forensic_user
from app.models.user import UserInDB
from app.services.forensic.forensic_chain_of_custody import create_custody_stamp
from app.services.forensic.forensic_audit_service import log_forensic_action, get_case_audit_trail

router = APIRouter()

FORENSIC_DOSSIERS_COLLECTION = "forensic_dossiers"

class ForensicDossierCreate(BaseModel):
    title: str = Field(..., min_length=3)
    case_number: Optional[str] = None
    court_jurisdiction: Optional[str] = "Gjykata Themelore"
    practice_area: Optional[str] = "Penale"
    case_summary: Optional[str] = None
    target_actors: List[str] = Field(default_factory=list)

class SealCustodyRequest(BaseModel):
    action_note: str = "Vulosje e Provave Materiale"
    evidence_ids: List[str] = Field(default_factory=list)

@router.post("/dossiers", status_code=status.HTTP_201_CREATED)
def create_forensic_dossier(
    payload: ForensicDossierCreate,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """Krijon një dosje të re hetimore me Chain of Custody fillestare."""
    user_id = str(current_user.id)
    now_utc = datetime.now(timezone.utc)

    # Gjenero vulën e parë të serverit
    custody_stamp = create_custody_stamp(
        user_id=user_id,
        case_id="NEW_DOSSIER",
        action="DOSSIER_INITIALIZED",
        metadata={"title": payload.title}
    )

    doc = {
        "title": payload.title,
        "case_number": payload.case_number or f"FOR-{now_utc.strftime('%Y%m%d')}-{int(now_utc.timestamp())%10000}",
        "court_jurisdiction": payload.court_jurisdiction,
        "practice_area": payload.practice_area,
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

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=doc_id,
        action="DOSSIER_CREATED",
        details={"case_number": doc["case_number"], "title": doc["title"]}
    )

    doc["_id"] = doc_id
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    return doc

@router.get("/dossiers")
def list_forensic_dossiers(
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Liston të gjitha dosjet hetimore forenzike."""
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

@router.get("/dossiers/{case_id}")
def get_forensic_dossier(
    case_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """Merr detajet e plota të dosjes forenzike."""
    try:
        query = {"_id": ObjectId(case_id)}
    except Exception:
        query = {"_id": case_id}

    dossier = db[FORENSIC_DOSSIERS_COLLECTION].find_one(query)
    if not dossier:
        # Provo të kërkosh edhe në koleksionin e rregullt të cases nëse po konvertohet
        regular_case = db["cases"].find_one(query)
        if not regular_case:
            raise HTTPException(status_code=404, detail="Dosja forenzike nuk u gjet.")
        dossier = {
            "_id": str(regular_case["_id"]),
            "title": regular_case.get("title", "Lëndë Juridike"),
            "case_number": regular_case.get("case_number", "PA-NUMËR"),
            "practice_area": regular_case.get("practice_area", "E Përgjithshme"),
            "case_summary": regular_case.get("description", ""),
            "created_at": regular_case.get("created_at", datetime.now(timezone.utc)),
            "chain_of_custody": [],
            "is_sealed": False
        }

    dossier["_id"] = str(dossier["_id"])
    return dossier

@router.post("/dossiers/{case_id}/seal-custody")
def seal_case_chain_of_custody(
    case_id: str,
    payload: SealCustodyRequest,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """
    Vulos me hash kriptografik server-side gjendjen aktuale të dosjes dhe provave.
    """
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

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=case_id,
        action="CHAIN_OF_CUSTODY_SEALED",
        details={"note": payload.action_note, "hash": stamp["custody_hash"]},
        evidence_ids=payload.evidence_ids
    )

    return {
        "success": True,
        "message": "Dosja dhe provat u vulosën me sukses nga serveri.",
        "custody_stamp": stamp
    }

@router.get("/dossiers/{case_id}/audit-trail")
def get_case_audit(
    case_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """Kthen regjistrin e pandryshueshëm të veprimeve të kryera mbi dosjen."""
    trail = get_case_audit_trail(db, case_id)
    return {"case_id": case_id, "total_records": len(trail), "trail": trail}