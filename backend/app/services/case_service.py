# FILE: backend/app/services/case_service.py
# PHOENIX PROTOCOL - CASE SERVICE V4.4 (BRANDING INJECTION)
# 1. FEATURE: Injects 'organization_name' and 'logo' into public portal data.
# 2. LOGIC: Fetches owner profile to display Law Firm Identity instead of App Identity.

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
        
        counts = {"document_count": 0, "alert_count": 0, "event_count": 0}
        
        if db is not None:
            c1 = db.calendar_events.count_documents({"case_id": case_id_str})
            c2 = db.calendar_events.count_documents({"case_id": case_id_obj})
            c3 = db.calendar_events.count_documents({"caseId": case_id_str})
            counts["event_count"] = c1 + c2 + c3
            
            d1 = db.documents.count_documents({"case_id": case_id_str})
            d2 = db.documents.count_documents({"case_id": case_id_obj})
            counts["document_count"] = d1 + d2
            
            now_utc = datetime.now(timezone.utc)
            now_iso = now_utc.isoformat()
            status_regex = {"$regex": "^pending$", "$options": "i"}
            future_filter = {"$or": [{"start_date": {"$gte": now_utc}}, {"start_date": {"$gte": now_iso}}, {"start_date": {"$gte": datetime.now()}}]}

            a1 = db.calendar_events.count_documents({"case_id": case_id_str, "status": status_regex, **future_filter})
            a2 = db.calendar_events.count_documents({"case_id": case_id_obj, "status": status_regex, **future_filter})

            dedicated_alerts = 0
            if "alerts" in db.list_collection_names():
                da1 = db.alerts.count_documents({"case_id": case_id_str, "status": {"$not": {"$regex": "^resolved$", "$options": "i"}}})
                da2 = db.alerts.count_documents({"case_id": case_id_obj, "status": {"$not": {"$regex": "^resolved$", "$options": "i"}}})
                dedicated_alerts = da1 + da2
            
            counts["alert_count"] = a1 + a2 + dedicated_alerts

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
        return {
            "id": case_doc.get("_id", "UNKNOWN"), "title": "Error Loading Case", "case_number": "ERR", 
            "created_at": datetime.now(), "updated_at": datetime.now(), **counts
        }

# --- CRUD OPERATIONS ---
def create_case(db: Database, case_in: CaseCreate, owner: UserInDB) -> Optional[Dict[str, Any]]:
    case_dict = case_in.model_dump(exclude={"clientName", "clientEmail", "clientPhone"})
    
    if case_in.clientName:
        clean_name = case_in.clientName.strip().title()
        case_dict["client"] = {"name": clean_name, "email": case_in.clientEmail, "phone": case_in.clientPhone}
    
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
    cursor = db.cases.find({"$or": [{"owner_id": owner.id}, {"user_id": owner.id}]}).sort("updated_at", -1)
    for case_doc in cursor:
        if mapped_case := _map_case_document(case_doc, db): results.append(mapped_case)
    return results

def get_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB) -> Optional[Dict[str, Any]]:
    case = db.cases.find_one({"_id": case_id, "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]})
    if not case: return None
    return _map_case_document(case, db)

def delete_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB):
    storage_service = importlib.import_module("app.services.storage_service")
    vector_store_service = importlib.import_module("app.services.vector_store_service")
    graph_service_module = importlib.import_module("app.services.graph_service")
    graph_service = getattr(graph_service_module, "graph_service")
    case = db.cases.find_one({"_id": case_id, "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]})
    if not case: raise HTTPException(status_code=404, detail="Case not found.")
    case_id_str = str(case_id)
    any_id_query: Dict[str, Any] = {"case_id": {"$in": [case_id, case_id_str]}}
    documents = list(db.documents.find(any_id_query))
    for doc in documents:
        doc_id_str = str(doc["_id"])
        keys_to_delete = [doc.get("storage_key"), doc.get("processed_text_storage_key"), doc.get("preview_storage_key")]
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
    if "alerts" in db.list_collection_names(): db.alerts.delete_many(any_id_query)

def create_draft_job_for_case(db: Database, case_id: ObjectId, job_in: DraftRequest, owner: UserInDB) -> Dict[str, Any]:
    case = db.cases.find_one({"_id": case_id, "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]})
    if not case: raise HTTPException(status_code=404, detail="Case not found.")
    task = celery_app.send_task("process_drafting_job", kwargs={"case_id": str(case_id), "user_id": str(owner.id), "draft_type": job_in.document_type, "user_prompt": job_in.prompt, "use_library": job_in.use_library})
    return {"job_id": task.id, "status": "queued", "message": "Drafting job created."}

def rename_document(db: Database, case_id: ObjectId, doc_id: ObjectId, new_name: str, owner: UserInDB) -> Dict[str, Any]:
    case = db.cases.find_one({"_id": case_id, "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]})
    if not case: raise HTTPException(status_code=404, detail="Case not found.")
    doc = db.documents.find_one({"_id": doc_id})
    if not doc: raise HTTPException(status_code=404, detail="Document not found.")
    if str(doc.get("case_id")) != str(case_id): raise HTTPException(status_code=403, detail="Document does not belong to this case.")
    original_name = doc.get("file_name", "untitled")
    extension = original_name.split(".")[-1] if "." in original_name else ""
    final_name = new_name if not extension or new_name.endswith(f".{extension}") else f"{new_name}.{extension}"
    db.documents.update_one({"_id": doc_id}, {"$set": {"file_name": final_name, "title": final_name, "updated_at": datetime.now(timezone.utc)}})
    return {"id": str(doc_id), "file_name": final_name, "message": "Document renamed successfully."}

# --- PUBLIC PORTAL FUNCTIONS ---
def get_public_case_events(db: Database, case_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches public-safe data for the Client Portal.
    Includes:
    1. Timeline (Public Events)
    2. Shared Documents (Only is_shared=True)
    3. Invoices (Excluding Drafts)
    4. PHOENIX NEW: Law Firm Branding (organization_name, logo)
    """
    try:
        case_oid = ObjectId(case_id)
        case = db.cases.find_one({"_id": case_oid})
        if not case: return None
        
        # 1. Fetch Timeline
        events_cursor = db.calendar_events.find({
            "$or": [{"case_id": case_id}, {"case_id": case_oid}],
            "$or": [
                {"is_public": True},
                {"notes": {"$regex": "CLIENT_VISIBLE", "$options": "i"}},
                {"description": {"$regex": "CLIENT_VISIBLE", "$options": "i"}}
            ]
        }).sort("start_date", 1)
        
        events = []
        for ev in events_cursor:
            description = ev.get("description", "") or ev.get("notes", "") or ""
            clean_desc = description.replace("[CLIENT_VISIBLE]", "").replace("[client_visible]", "").strip()
            
            events.append({
                "title": ev.get("title"),
                "date": ev.get("start_date"),
                "type": ev.get("event_type", "EVENT"),
                "description": clean_desc
            })
        
        # 2. Fetch Shared Documents
        docs_cursor = db.documents.find({
            "$or": [{"case_id": case_id}, {"case_id": case_oid}],
            "is_shared": True 
        }).sort("created_at", -1)
        
        shared_docs = []
        for d in docs_cursor:
            shared_docs.append({
                "id": str(d["_id"]),
                "file_name": d.get("file_name"),
                "created_at": d.get("created_at"),
                "file_type": d.get("mime_type", "application/pdf"),
                "source": "ACTIVE"
            })

        # 3. Fetch Archive Items
        archive_cursor = db.archives.find({
            "$or": [{"case_id": case_id}, {"case_id": case_oid}],
            "is_shared": True,
            "item_type": "FILE"
        }).sort("created_at", -1)
        
        for a in archive_cursor:
             shared_docs.append({
                "id": str(a["_id"]),
                "file_name": a.get("title", "Archived File"),
                "created_at": a.get("created_at"),
                "file_type": "application/pdf", 
                "source": "ARCHIVE"
            })

        # 4. Fetch Invoices
        invoices_cursor = db.invoices.find({
            "related_case_id": case_id,
            "status": {"$ne": "DRAFT"}
        }).sort("issue_date", -1)

        shared_invoices = []
        for inv in invoices_cursor:
            shared_invoices.append({
                "id": str(inv["_id"]),
                "number": inv.get("invoice_number"),
                "amount": inv.get("total_amount"),
                "status": inv.get("status"),
                "date": inv.get("issue_date")
            })

        # PHOENIX NEW: Fetch User Branding
        owner_id = case.get("owner_id") or case.get("user_id")
        organization_name = None
        logo = None
        
        if owner_id:
            owner = db.users.find_one({"_id": owner_id})
            if owner:
                organization_name = owner.get("organization_name")
                logo = owner.get("logo")

        raw_name = case.get("client", {}).get("name", "Klient")
        clean_name = raw_name.strip().title() if raw_name else "Klient"
        
        return {
            "case_number": case.get("case_number"), 
            "title": case.get("title") or case.get("case_name"), 
            "client_name": clean_name, 
            "status": case.get("status", "OPEN"), 
            "organization_name": organization_name, # Injected
            "logo": logo, # Injected
            "timeline": events,
            "documents": shared_docs,
            "invoices": shared_invoices
        }
    except Exception as e:
        print(f"Public Portal Error: {e}")
        return None