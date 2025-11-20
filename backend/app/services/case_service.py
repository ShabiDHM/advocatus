# FILE: backend/app/services/case_service.py
# PHOENIX PROTOCOL - DATA INTEGRITY FIX
# 1. QUERY FIX: Converted 'case_id' to string before querying counts.
# 2. This resolves the "0 Alerts / 0 Events" bug.

from fastapi import HTTPException, status
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timezone

from ..models.case import CaseCreate, ClientDetailsOut
from ..models.user import UserInDB

def create_case(db: Database, case_in: CaseCreate, owner: UserInDB) -> dict:
    case_dict = case_in.model_dump(by_alias=True)
    
    client_obj = ClientDetailsOut(
        name=case_in.clientName, 
        email=case_in.clientEmail, 
        phone=case_in.clientPhone
    )
    case_dict["client"] = client_obj.model_dump(exclude_none=True)
    
    case_dict.pop("clientName", None)
    case_dict.pop("clientEmail", None)
    case_dict.pop("clientPhone", None)

    case_dict["owner_id"] = owner.id
    case_dict["created_at"] = datetime.now(timezone.utc)
    
    result = db.cases.insert_one(case_dict)
    new_case = db.cases.find_one({"_id": result.inserted_id})
    
    if not new_case:
        raise HTTPException(status_code=500, detail="Failed to create case.")

    return {
        "id": str(new_case["_id"]),
        "case_name": new_case["case_name"],
        "client": new_case.get("client"),
        "status": new_case.get("status", "active"),
        "owner_id": str(new_case["owner_id"]),
        "created_at": new_case.get("created_at"),
        "document_count": 0, "alert_count": 0, "event_count": 0, "finding_count": 0
    }

def get_cases_for_user(db: Database, owner: UserInDB) -> list[dict]:
    results = []
    for case in db.cases.find({"owner_id": owner.id}):
        results.append(get_case_by_id(db=db, case_id=case["_id"], owner=owner) or {})
    return [r for r in results if r]


def get_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB) -> dict | None:
    case = db.cases.find_one({"_id": case_id, "owner_id": owner.id})
    if case:
        # PHOENIX FIX: Convert ObjectId to string for relational queries
        # Foreign keys in documents/events are stored as Strings, not ObjectIds.
        case_id_str = str(case_id)
        
        counts = {
            "document_count": db.documents.count_documents({"case_id": case_id_str}),
            "alert_count": db.alerts.count_documents({"case_id": case_id_str}),
            "event_count": db.calendar_events.count_documents({"case_id": case_id_str}),
            "finding_count": db.findings.count_documents({"case_id": case_id_str}),
        }
        return {**case, **counts, "id": str(case["_id"])}
    return None

def delete_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB):
    if db.cases.delete_one({"_id": case_id, "owner_id": owner.id}).deleted_count == 0:
        raise HTTPException(status_code=404, detail="Case not found.")