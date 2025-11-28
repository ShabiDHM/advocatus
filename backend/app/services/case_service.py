# FILE: backend/app/services/case_service.py
# PHOENIX PROTOCOL - DATA ADAPTER & ROBUSTNESS (TYPE SAFE)
# 1. FIX: Updated type hints to allow Optional returns.
# 2. FIX: Explicit 'is not None' check for Database object.

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
    Normalizes a MongoDB case document to match the CaseOut Pydantic schema.
    """
    try:
        case_id_str = str(case_doc["_id"])
        
        # 1. Handle Title/Name discrepancy
        title = case_doc.get("title") or case_doc.get("case_name") or "Untitled Case"
        
        # 2. Handle Case Number
        case_number = case_doc.get("case_number") or f"LEGACY-{str(case_doc['_id'])[-6:]}"
        
        # 3. Handle Timestamps
        created_at = case_doc.get("created_at") or datetime.now(timezone.utc)
        updated_at = case_doc.get("updated_at") or created_at

        # 4. Optional Counts
        counts = {}
        # PHOENIX FIX: Explicit check for None
        if db is not None:
            doc_count = db.documents.count_documents({"case_id": case_doc["_id"]})
            event_count = db.calendar_events.count_documents({"case_id": case_id_str})
            finding_count = db.findings.count_documents({"case_id": case_id_str})
            
            alert_query = {
                "case_id": case_id_str,
                "status": "PENDING",
                "start_date": {"$gte": datetime.now().isoformat()}
            }
            alert_count = db.calendar_events.count_documents(alert_query)
            
            counts = {
                "document_count": doc_count,
                "alert_count": alert_count,
                "event_count": event_count,
                "finding_count": finding_count,
            }

        return {
            "id": case_id_str,
            "case_number": case_number,
            "title": title,
            "description": case_doc.get("description"),
            "status": case_doc.get("status", "OPEN"),
            "client_id": str(case_doc.get("client_id")) if case_doc.get("client_id") else None,
            "created_at": created_at,
            "updated_at": updated_at,
            **counts
        }
    except Exception as e:
        print(f"Error mapping case {case_doc.get('_id')}: {e}")
        return None

def create_case(db: Database, case_in: CaseCreate, owner: UserInDB) -> Optional[Dict[str, Any]]:
    case_dict = case_in.model_dump(by_alias=True)
    case_dict["owner_id"] = owner.id
    now = datetime.now(timezone.utc)
    case_dict["created_at"] = now
    case_dict["updated_at"] = now
    
    if "status" not in case_dict:
        case_dict["status"] = "OPEN"

    result = db.cases.insert_one(case_dict)
    new_case = db.cases.find_one({"_id": result.inserted_id})

    if not new_case:
        raise HTTPException(status_code=500, detail="Failed to create case.")

    return _map_case_document(new_case)

def get_cases_for_user(db: Database, owner: UserInDB) -> List[Dict[str, Any]]:
    results = []
    cursor = db.cases.find({"owner_id": owner.id}).sort("updated_at", -1)
    
    for case_doc in cursor:
        mapped_case = _map_case_document(case_doc, db) # Pass db to get counts
        if mapped_case:
            results.append(mapped_case)
            
    return results

def get_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB) -> Optional[Dict[str, Any]]:
    case = db.cases.find_one({"_id": case_id, "owner_id": owner.id})
    if not case:
        return None
        
    return _map_case_document(case, db)

def delete_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB):
    result = db.cases.delete_one({"_id": case_id, "owner_id": owner.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Case not found.")

    case_id_str = str(case_id)
    db.documents.delete_many({"case_id": case_id})
    db.calendar_events.delete_many({"case_id": case_id_str})
    db.findings.delete_many({"case_id": case_id_str})
    db.alerts.delete_many({"case_id": case_id_str})

def create_draft_job_for_case(
    db: Database,
    case_id: ObjectId,
    job_in: DraftRequest,
    owner: UserInDB
) -> Dict[str, str]:
    case = db.cases.find_one({"_id": case_id, "owner_id": owner.id})
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or access denied."
        )

    task = celery_app.send_task(
        "process_drafting_job",
        kwargs={
            "case_id": str(case_id),
            "user_id": str(owner.id),
            "draft_type": job_in.document_type,
            "user_prompt": job_in.prompt
        }
    )

    return {"job_id": task.id}