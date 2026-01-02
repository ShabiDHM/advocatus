# FILE: backend/app/services/case_service.py
# PHOENIX PROTOCOL - CASE SERVICE V5.7 (PUBLIC DATA EXPANSION)
# 1. UPDATE: Exposed 'client_email', 'client_phone', and 'created_at' to Public Portal.
# 2. LOGIC: Allows frontend to render full case card details.

import re
import importlib
import urllib.parse 
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, cast
from bson import ObjectId
from bson.errors import InvalidId
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
    cursor = db.cases.find({
        "$or": [
            {"owner_id": owner.id},
            {"user_id": owner.id}
        ]
    }).sort("updated_at", -1)
    
    for case_doc in cursor:
        if mapped_case := _map_case_document(case_doc, db):
            results.append(mapped_case)
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
        
        # 2. Fetch Shared Documents (Strictly Active)
        docs_cursor = db.documents.find({
            "$or": [{"case_id": case_id}, {"case_id": case_oid}],
            "is_shared": True,
            "status": {"$nin": ["DELETED", "ARCHIVED", "ERROR"]}
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

        # 3. Fetch Archive Items (Only if file exists)
        archive_cursor = db.archives.find({
            "$or": [{"case_id": case_id}, {"case_id": case_oid}],
            "is_shared": True,
            "item_type": "FILE"
        }).sort("created_at", -1)
        
        for a in archive_cursor:
             if not a.get("storage_key"): continue 
             
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
            "status": {"$in": ["PAID", "SENT", "OVERDUE"]}
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

        # --- BRANDING & CLIENT INFO ---
        owner_id = case.get("owner_id") or case.get("user_id")
        organization_name = "Zyra Ligjore"
        logo_path = None

        if owner_id:
            query_id = owner_id
            if isinstance(query_id, str):
                try: query_id = ObjectId(query_id)
                except: pass
            
            profile = db.business_profiles.find_one({"user_id": query_id})
            
            if not profile and isinstance(owner_id, ObjectId):
                profile = db.business_profiles.find_one({"user_id": str(owner_id)})

            if profile:
                organization_name = profile.get("firm_name") or "Zyra Ligjore"
                if profile.get("logo_storage_key"):
                    logo_path = f"/cases/public/{case_id}/logo"

        # Client Details Extraction
        client_obj = case.get("client", {})
        raw_name = client_obj.get("name") if isinstance(client_obj, dict) else None
        clean_name = raw_name.strip().title() if raw_name else "Klient"
        
        # PHOENIX UPDATE: Extracting Email, Phone, and Creation Date
        client_email = client_obj.get("email") if isinstance(client_obj, dict) else None
        client_phone = client_obj.get("phone") if isinstance(client_obj, dict) else None
        created_at = case.get("created_at")

        return {
            "case_number": case.get("case_number"), 
            "title": case.get("title") or case.get("case_name"), 
            "client_name": clean_name, 
            "client_email": client_email, # New Field
            "client_phone": client_phone, # New Field
            "created_at": created_at,     # New Field
            "status": case.get("status", "OPEN"), 
            "organization_name": organization_name,
            "logo": logo_path,
            "timeline": events,
            "documents": shared_docs,
            "invoices": shared_invoices
        }
    except Exception as e:
        print(f"Public Portal Error: {e}")
        return None