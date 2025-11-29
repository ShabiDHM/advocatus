# FILE: backend/app/services/case_service.py
# PHOENIX PROTOCOL - CASE SERVICE (DEEP CLEAN ENABLED)
# 1. UPDATE: 'delete_case_by_id' now wipes associated Archive files from S3/MinIO and DB.
# 2. LOGIC: Uses 'storage_service' to ensure no orphaned files remain in cloud storage.
# 3. STATUS: Fully implements the "Digital Shredder" for cases.

from fastapi import HTTPException, status
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, cast

from ..models.case import CaseCreate
from ..models.user import UserInDB
from ..models.drafting import DraftRequest
from ..celery_app import celery_app
from .graph_service import graph_service
# PHOENIX NEW: Import Storage Service for file cleanup
from . import storage_service

# --- HELPER: DATA ADAPTER ---
def _map_case_document(case_doc: Dict[str, Any], db: Optional[Database] = None) -> Optional[Dict[str, Any]]:
    """
    Normalizes a MongoDB case document to match the CaseOut schema.
    """
    try:
        case_id_obj = case_doc["_id"]
        case_id_str = str(case_id_obj)
        
        title = case_doc.get("title") or case_doc.get("case_name") or "Untitled Case"
        case_number = case_doc.get("case_number") or f"REF-{case_id_str[-6:]}"
        created_at = case_doc.get("created_at") or datetime.now(timezone.utc)
        updated_at = case_doc.get("updated_at") or created_at

        # Counts
        counts = {
            "document_count": 0,
            "alert_count": 0,
            "event_count": 0,
            "finding_count": 0
        }
        
        if db is not None:
            # Handle potential inconsistency between ObjectId and String storage
            any_id_query: Dict[str, Any] = {"case_id": {"$in": [case_id_obj, case_id_str]}}
            
            counts["document_count"] = db.documents.count_documents(any_id_query)
            counts["event_count"] = db.calendar_events.count_documents(any_id_query)
            counts["finding_count"] = db.findings.count_documents(any_id_query)
            
            alert_query = any_id_query.copy()
            alert_query.update({
                "status": "PENDING", 
                "start_date": {"$gte": datetime.now().isoformat()}
            })
            counts["alert_count"] = db.calendar_events.count_documents(alert_query)

        return {
            "id": case_id_obj,
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

    return _map_case_document(cast(Dict[str, Any], new_case), db)

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
    case = db.cases.find_one({
        "_id": case_id, 
        "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]
    })
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    case_id_str = str(case_id)
    any_id_query: Dict[str, Any] = {"case_id": {"$in": [case_id, case_id_str]}}

    # --- 1. ARCHIVE CLEANUP (Deep Clean) ---
    # Find all archive items linked to this case
    archive_items = db.archives.find(any_id_query)
    for item in archive_items:
        if "storage_key" in item:
            try:
                # Delete physical file from Cloud Storage
                storage_service.delete_file(item["storage_key"])
            except Exception as e:
                print(f"Warning: Failed to delete archive file {item.get('title')}: {e}")
    
    # Delete Archive records
    db.archives.delete_many(any_id_query)

    # --- 2. GRAPH CLEANUP ---
    docs = db.documents.find({"case_id": case_id})
    for doc in docs:
        try:
            graph_service.delete_document_nodes(str(doc["_id"]))
        except Exception:
            pass

    # --- 3. DELETE CASE ENTITY ---
    db.cases.delete_one({"_id": case_id})
    
    # --- 4. CLEANUP ASSOCIATED DATA ---
    db.documents.delete_many(any_id_query)
    db.calendar_events.delete_many(any_id_query)
    db.findings.delete_many(any_id_query)
    db.alerts.delete_many(any_id_query)

def create_draft_job_for_case(db: Database, case_id: ObjectId, job_in: DraftRequest, owner: UserInDB) -> Dict[str, Any]:
    """
    Validates case ownership and dispatches a drafting job linked to the case.
    """
    case = db.cases.find_one({
        "_id": case_id, 
        "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]
    })
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    task = celery_app.send_task(
        "process_drafting_job",
        kwargs={
            "case_id": str(case_id),
            "user_id": str(owner.id),
            "draft_type": job_in.document_type,
            "user_prompt": job_in.prompt,
            "use_library": job_in.use_library
        }
    )
    
    return {"job_id": task.id, "status": "queued", "message": "Drafting job initiated for case."}