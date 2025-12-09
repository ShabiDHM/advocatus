# FILE: backend/app/services/case_service.py
# PHOENIX PROTOCOL - CASE SERVICE V2.2 (POLYMORPHIC DATE FIX)
# 1. FIX: 'alert_count' query now checks for BOTH BSON Date objects and ISO Strings.
# 2. LOGIC: Ensures 'event_count' accurately reflects all items linked to the case ID.
# 3. ROBUSTNESS: Explicitly handles ObjectId/String mismatches in DB queries.

import re
import importlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, cast
from bson import ObjectId
from fastapi import HTTPException
from pymongo.database import Database

from ..models.case import CaseCreate
from ..models.user import UserInDB
from ..models.drafting import DraftRequest
from ..celery_app import celery_app

# --- HELPER FUNCTIONS ---

def _map_case_document(case_doc: Dict[str, Any], db: Optional[Database] = None) -> Optional[Dict[str, Any]]:
    try:
        case_id_obj = case_doc["_id"]
        case_id_str = str(case_id_obj)
        title = case_doc.get("title") or case_doc.get("case_name") or "Untitled Case"
        case_number = case_doc.get("case_number") or f"REF-{case_id_str[-6:]}"
        created_at = case_doc.get("created_at") or datetime.now(timezone.utc)
        updated_at = case_doc.get("updated_at") or created_at
        
        counts = {"document_count": 0, "alert_count": 0, "event_count": 0, "finding_count": 0}
        
        if db is not None:
            # PHOENIX CORE: Dual-Mode ID Query (Matches stored ObjectIds OR Strings)
            any_id_query: Dict[str, Any] = {"case_id": {"$in": [case_id_obj, case_id_str]}}
            
            # 1. Standard Counts (Broadest possible match)
            counts["document_count"] = db.documents.count_documents(any_id_query)
            counts["finding_count"] = db.findings.count_documents(any_id_query)
            counts["event_count"] = db.calendar_events.count_documents(any_id_query)
            
            # 2. Advanced Alert Counting (Polymorphic Date Handling)
            # We must detect events that are 'PENDING' and in the 'FUTURE'.
            # MongoDB stores dates as BSON Dates (if datetime used) or Strings (if ISO used).
            # We query for BOTH to be safe.
            
            now_utc = datetime.now(timezone.utc)
            now_iso = now_utc.isoformat()
            
            calendar_alert_query = {
                **any_id_query, 
                "status": "PENDING", 
                "$or": [
                    {"start_date": {"$gte": now_utc}},              # Match BSON Date
                    {"start_date": {"$gte": now_iso}},              # Match ISO String
                    {"start_date": {"$gte": now_utc.replace(tzinfo=None)}} # Match Naive Date (Fallback)
                ]
            }
            calendar_alerts = db.calendar_events.count_documents(calendar_alert_query)
            
            # 3. Dedicated Alerts Collection (If exists)
            dedicated_alerts = 0
            if "alerts" in db.list_collection_names():
                alert_collection_query = {**any_id_query, "status": {"$ne": "RESOLVED"}}
                dedicated_alerts = db.alerts.count_documents(alert_collection_query)
            
            # Sum the sources
            counts["alert_count"] = calendar_alerts + dedicated_alerts

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
        # Return basic map on error to prevent UI crash
        return {
             "id": case_doc["_id"], "title": "Error Loading Case", "case_number": "ERR", 
             "created_at": datetime.now(), "updated_at": datetime.now(), **counts
        }

def _parse_finding_date(text: str) -> datetime | None:
    return None

def sync_case_calendar_from_findings(db: Database, case_id: str, user_id: ObjectId):
    pass

# --- CRUD OPERATIONS ---

def create_case(db: Database, case_in: CaseCreate, owner: UserInDB) -> Optional[Dict[str, Any]]:
    case_dict = case_in.model_dump(exclude={"clientName", "clientEmail", "clientPhone"})
    if case_in.clientName:
        case_dict["client"] = {"name": case_in.clientName, "email": case_in.clientEmail, "phone": case_in.clientPhone}
    case_dict.update({
        "owner_id": owner.id, "user_id": owner.id,
        "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
        "case_number": case_dict.get("case_number") or f"NEW-{int(datetime.now(timezone.utc).timestamp())}"
    })
    result = db.cases.insert_one(case_dict)
    new_case = db.cases.find_one({"_id": result.inserted_id})
    if not new_case: raise HTTPException(status_code=500, detail="Failed to create case.")
    return _map_case_document(cast(Dict[str, Any], new_case), db)

def get_cases_for_user(db: Database, owner: UserInDB) -> List[Dict[str, Any]]:
    results = []
    # Sort by updated_at desc to show most recent activity first
    cursor = db.cases.find({"$or": [{"owner_id": owner.id}, {"user_id": owner.id}]}).sort("updated_at", -1)
    for case_doc in cursor:
        if mapped_case := _map_case_document(case_doc, db):
            results.append(mapped_case)
    return results

def get_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB) -> Optional[Dict[str, Any]]:
    case = db.cases.find_one({"_id": case_id, "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]})
    if not case: return None
    sync_case_calendar_from_findings(db, str(case_id), owner.id)
    return _map_case_document(case, db)

def delete_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB):
    storage_service = importlib.import_module("app.services.storage_service")
    vector_store_service = importlib.import_module("app.services.vector_store_service")
    graph_service_module = importlib.import_module("app.services.graph_service")
    graph_service = getattr(graph_service_module, "graph_service")

    case = db.cases.find_one({"_id": case_id, "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    case_id_str = str(case_id)
    any_id_query: Dict[str, Any] = {"case_id": {"$in": [case_id, case_id_str]}}

    documents = list(db.documents.find(any_id_query))
    for doc in documents:
        doc_id_str = str(doc["_id"])
        keys_to_delete = [
            doc.get("storage_key"), doc.get("processed_text_storage_key"), doc.get("preview_storage_key")
        ]
        for key in filter(None, keys_to_delete):
            try: storage_service.delete_file(key)
            except Exception: pass
        try: vector_store_service.delete_document_embeddings(document_id=doc_id_str)
        except Exception: pass
        try: graph_service.delete_document_nodes(doc_id_str)
        except Exception: pass

    archive_items = db.archives.find(any_id_query)
    for item in archive_items:
        if "storage_key" in item:
            try: storage_service.delete_file(item["storage_key"])
            except Exception: pass
    db.archives.delete_many(any_id_query)

    db.cases.delete_one({"_id": case_id})
    db.documents.delete_many(any_id_query)
    db.calendar_events.delete_many(any_id_query)
    db.findings.delete_many(any_id_query)
    
    # Clean up alerts if the collection exists
    if "alerts" in db.list_collection_names():
        db.alerts.delete_many(any_id_query)

def create_draft_job_for_case(db: Database, case_id: ObjectId, job_in: DraftRequest, owner: UserInDB) -> Dict[str, Any]:
    case = db.cases.find_one({"_id": case_id, "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    task = celery_app.send_task(
        "process_drafting_job",
        kwargs={
            "case_id": str(case_id), "user_id": str(owner.id),
            "draft_type": job_in.document_type, "user_prompt": job_in.prompt,
            "use_library": job_in.use_library
        }
    )
    return {"job_id": task.id, "status": "queued", "message": "Drafting job created."}

# PHOENIX NEW: Document Renaming Logic
def rename_document(db: Database, case_id: ObjectId, doc_id: ObjectId, new_name: str, owner: UserInDB) -> Dict[str, Any]:
    """
    Updates the 'file_name' (and optionally 'title') of a document.
    Ensures the document belongs to the user's case.
    """
    # 1. Verify Case Ownership
    case = db.cases.find_one({"_id": case_id, "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    # 2. Verify Document Existence
    doc = db.documents.find_one({"_id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    # Check if doc belongs to this case (using string or ObjectId comparison)
    doc_case_id = doc.get("case_id")
    if str(doc_case_id) != str(case_id):
         raise HTTPException(status_code=403, detail="Document does not belong to this case.")

    # 3. Update Name
    # Ensure extension is preserved if user didn't type it
    original_name = doc.get("file_name", "untitled")
    extension = ""
    if "." in original_name:
        extension = original_name.split(".")[-1]
    
    final_name = new_name
    if extension and not final_name.endswith(f".{extension}"):
        final_name = f"{final_name}.{extension}"

    db.documents.update_one(
        {"_id": doc_id},
        {"$set": {"file_name": final_name, "title": final_name, "updated_at": datetime.now(timezone.utc)}}
    )

    return {"id": str(doc_id), "file_name": final_name, "message": "Document renamed successfully."}