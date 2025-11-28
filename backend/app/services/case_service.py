# FILE: backend/app/services/case_service.py
# PHOENIX PROTOCOL - TYPE VALIDATION FIX
# 1. FIX: Passed raw 'ObjectId' to return dict instead of 'str'.
# 2. REASONING: Pydantic 'PyObjectId' requires the object instance for validation.
# 3. SAFETY: Strings are still used for internal DB queries (counts/deletes).

from fastapi import HTTPException, status
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from ..models.case import CaseCreate
from ..models.user import UserInDB
from ..models.drafting import DraftRequest
from ..celery_app import celery_app

# --- HELPER: DATA ADAPTER ---
def _map_case_document(case_doc: Dict[str, Any], db: Optional[Database] = None) -> Optional[Dict[str, Any]]:
    """
    Normalizes a MongoDB case document to match the CaseOut schema.
    """
    try:
        # We need the string version for DB queries (counts)
        case_id_str = str(case_doc["_id"])
        
        title = case_doc.get("title") or case_doc.get("case_name") or "Untitled Case"
        case_number = case_doc.get("case_number") or f"REF-{case_id_str[-6:]}"
        created_at = case_doc.get("created_at") or datetime.now(timezone.utc)
        updated_at = case_doc.get("updated_at") or created_at

        # Counts
        counts = {}
        if db is not None:
            doc_count = db.documents.count_documents({"case_id": case_doc["_id"]})
            event_count = db.calendar_events.count_documents({"case_id": case_id_str})
            finding_count = db.findings.count_documents({"case_id": case_id_str})
            alert_count = db.calendar_events.count_documents({
                "case_id": case_id_str, "status": "PENDING", "start_date": {"$gte": datetime.now().isoformat()}
            })
            counts = {
                "document_count": doc_count, "alert_count": alert_count,
                "event_count": event_count, "finding_count": finding_count,
            }

        return {
            # PHOENIX FIX: Pass the raw ObjectId, not the string.
            # Pydantic's PyObjectId validator expects an instance of ObjectId.
            "id": case_doc["_id"],
            "case_number": case_number,
            "title": title,
            "description": case_doc.get("description"),
            "status": case_doc.get("status", "OPEN"),
            "client_id": str(case_doc.get("client_id")) if case_doc.get("client_id") else None,
            "client": case_doc.get("client"), 
            "created_at": created_at,
            "updated_at": updated_at,
            **counts
        }
    except Exception as e:
        print(f"Error mapping case {case_doc.get('_id')}: {e}")
        return None

def create_case(db: Database, case_in: CaseCreate, owner: UserInDB) -> Optional[Dict[str, Any]]:
    case_dict = case_in.model_dump(exclude={"clientName", "clientEmail", "clientPhone"})
    
    if case_in.clientName:
        case_dict["client"] = {
            "name": case_in.clientName,
            "email": case_in.clientEmail,
            "phone": case_in.clientPhone
        }
    
    case_dict["owner_id"] = owner.id
    case_dict["user_id"] = owner.id
    now = datetime.now(timezone.utc)
    case_dict["created_at"] = now
    case_dict["updated_at"] = now
    
    if not case_dict.get("case_number"):
        case_dict["case_number"] = f"NEW-{int(datetime.utcnow().timestamp())}"

    result = db.cases.insert_one(case_dict)
    new_case = db.cases.find_one({"_id": result.inserted_id})

    if not new_case:
        raise HTTPException(status_code=500, detail="Failed to create case.")

    return _map_case_document(new_case, db)

def get_cases_for_user(db: Database, owner: UserInDB) -> List[Dict[str, Any]]:
    results = []
    cursor = db.cases.find({"$or": [{"owner_id": owner.id}, {"user_id": owner.id}]}).sort("updated_at", -1)
    
    for case_doc in cursor:
        mapped_case = _map_case_document(case_doc, db)
        if mapped_case:
            results.append(mapped_case)
            
    return results

def get_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB) -> Optional[Dict[str, Any]]:
    case = db.cases.find_one({
        "_id": case_id, 
        "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]
    })
    if not case: return None
    return _map_case_document(case, db)

def delete_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB):
    result = db.cases.delete_one({
        "_id": case_id, 
        "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Case not found.")

    case_id_str = str(case_id)
    db.documents.delete_many({"case_id": case_id})
    db.calendar_events.delete_many({"case_id": case_id_str})
    db.findings.delete_many({"case_id": case_id_str})
    db.alerts.delete_many({"case_id": case_id_str})