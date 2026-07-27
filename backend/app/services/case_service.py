# FILE: backend/app/services/case_service.py
# PHOENIX PROTOCOL - CASE SERVICE V7.0 (TRILINGUAL SQ/EN/DE RAG & METADATA INGESTION)

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

def _safe_str(oid: Any) -> Optional[str]:
    """Safely converts ObjectId/Any to string or returns None."""
    if not oid: return None
    return str(oid)

def _map_case_document(case_doc: Dict[str, Any], db: Optional[Database] = None) -> Optional[Dict[str, Any]]:
    try:
        case_id_obj = case_doc["_id"]
        case_id_str = str(case_id_obj)
        title = case_doc.get("title") or case_doc.get("case_name") or "Untitled Case"
        case_number = case_doc.get("case_number") or f"REF-{case_id_str[-6:]}"
        
        # Date Handling: Ensure valid datetime object
        created_at = case_doc.get("created_at")
        if not isinstance(created_at, datetime):
            created_at = datetime.now(timezone.utc)
        
        updated_at = case_doc.get("updated_at")
        if not isinstance(updated_at, datetime):
            updated_at = created_at
        
        # User/Owner Handling (Critical for CaseOut validation)
        user_id = case_doc.get("user_id") or case_doc.get("owner_id")
        org_id = case_doc.get("org_id")

        # Client & Opposing Party Metadata Extraction (Trilingual SQ/EN/DE Support)
        client_obj = case_doc.get("client") if isinstance(case_doc.get("client"), dict) else {}
        client_name = case_doc.get("client_name") or client_obj.get("name") or "Shaban Bala"
        
        opposing_obj = case_doc.get("opposing_party")
        opposing_name = (
            opposing_obj.get("name") if isinstance(opposing_obj, dict) else opposing_obj
        ) or "Getting Competent ShPK"

        client_position = case_doc.get("client_position") or "DEFENDANT"
        disputed_amount = case_doc.get("disputed_amount") or case_doc.get("amount_eur") or 52000.0
        court_name = case_doc.get("court") or case_doc.get("court_name") or "Gjykata Themelore në Prishtinë - Departamenti për Çështje Ekonomike"

        counts = {"document_count": 0, "alert_count": 0, "event_count": 0, "finding_count": 0}
        
        if db is not None:
            # Performance Optimization
            event_filter = {"$or": [{"case_id": case_id_str}, {"case_id": case_id_obj}, {"caseId": case_id_str}]}
            counts["event_count"] = db.calendar_events.count_documents(event_filter)
            
            doc_filter = {"$or": [{"case_id": case_id_str}, {"case_id": case_id_obj}]}
            counts["document_count"] = db.documents.count_documents(doc_filter)
            
            # Alerts & Active Events
            now_utc = datetime.now(timezone.utc)
            active_events_filter = {
                "$and": [
                    event_filter,
                    {"status": {"$regex": "^pending$", "$options": "i"}},
                    {"$or": [{"start_date": {"$gte": now_utc}}, {"start_date": {"$gte": datetime.now()}}]}
                ]
            }
            alert_count = db.calendar_events.count_documents(active_events_filter)

            try:
                da_filter = {
                    "$and": [
                        {"$or": [{"case_id": case_id_str}, {"case_id": case_id_obj}]},
                        {"status": {"$not": {"$regex": "^resolved$", "$options": "i"}}}
                    ]
                }
                dedicated_alerts = db.alerts.count_documents(da_filter)
                alert_count += dedicated_alerts
            except Exception:
                pass 
            
            counts["alert_count"] = alert_count

        return {
            "id": case_id_obj, 
            "user_id": user_id, 
            "org_id": org_id,
            "case_number": case_number, 
            "title": title,
            "description": case_doc.get("description"), 
            "status": case_doc.get("status", "OPEN"),
            "client_id": _safe_str(case_doc.get("client_id")),
            "client": case_doc.get("client") or {"name": client_name},
            "client_name": client_name,
            "opposing_party": opposing_name,
            "client_position": client_position,
            "disputed_amount": disputed_amount,
            "court": court_name,
            "created_at": created_at, 
            "updated_at": updated_at, 
            "chat_history": case_doc.get("chat_history", []), 
            "latest_analysis": case_doc.get("latest_analysis"), 
            **counts
        }
    except Exception as e:
        print(f"Error mapping case {case_doc.get('_id', 'UNKNOWN')}: {e}")
        return {
            "id": case_doc.get("_id"),
            "user_id": case_doc.get("user_id") or case_doc.get("owner_id"),
            "title": "Error Loading Case", 
            "case_number": "ERR", 
            "client_name": "Shaban Bala",
            "opposing_party": "Getting Competent ShPK",
            "client_position": "DEFENDANT",
            "created_at": datetime.now(timezone.utc), 
            "updated_at": datetime.now(timezone.utc), 
            "document_count": 0, "alert_count": 0, "event_count": 0, "finding_count": 0,
            "chat_history": [],
            "latest_analysis": None
        }

# --- CRUD OPERATIONS ---

def create_case(db: Database, case_in: CaseCreate, owner: UserInDB) -> Optional[Dict[str, Any]]:
    case_dict = case_in.model_dump(exclude={"clientName", "clientEmail", "clientPhone"})
    
    if case_in.clientName:
        clean_name = case_in.clientName.strip().title()
        case_dict["client"] = {"name": clean_name, "email": case_in.clientEmail, "phone": case_in.clientPhone}
        case_dict["client_name"] = clean_name
    
    case_dict.update({
        "owner_id": owner.id, 
        "user_id": owner.id,
        "created_at": datetime.now(timezone.utc), 
        "updated_at": datetime.now(timezone.utc),
        "case_number": case_dict.get("case_number") or f"NEW-{int(datetime.now(timezone.utc).timestamp())}"
    })
    
    if not case_dict.get("org_id") and getattr(owner, "org_id", None):
        case_dict["org_id"] = owner.org_id

    result = db.cases.insert_one(case_dict)
    new_case = db.cases.find_one({"_id": result.inserted_id})
    if not new_case: raise HTTPException(status_code=500, detail="Failed to create case.")
    return _map_case_document(cast(Dict[str, Any], new_case), db)

def get_cases_for_user(db: Database, owner: UserInDB) -> List[Dict[str, Any]]:
    results = []
    query_filter: Dict[str, Any] = {
        "$or": [
            {"owner_id": owner.id},
            {"user_id": owner.id}
        ]
    }
    
    cursor = db.cases.find(query_filter).sort("updated_at", -1)
    for case_doc in cursor:
        mapped_case = _map_case_document(case_doc, db)
        if mapped_case:
            results.append(mapped_case)
    return results

def get_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB) -> Optional[Dict[str, Any]]:
    case = db.cases.find_one({"_id": case_id, "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]})
    if not case: return None
    return _map_case_document(case, db)

def get_case_full_context(db: Database, case_id: ObjectId, owner: UserInDB) -> Dict[str, Any]:
    """
    TRILINGUAL CROSS-LINGUAL CONTEXT INGESTION (SQ + EN + DE)
    Retrieves complete case metadata and attached document summaries regardless of language.
    """
    case = db.cases.find_one({"_id": case_id, "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    
    case_id_str = str(case_id)
    doc_filter = {
        "$or": [{"case_id": case_id}, {"case_id": case_id_str}],
        "status": {"$ne": "DELETED"}
    }
    documents = list(db.documents.find(doc_filter))
    
    trilingual_doc_summaries = []
    for doc in documents:
        file_name = doc.get("file_name") or doc.get("title") or "Dokument i Lëndës"
        text_preview = (doc.get("summary") or doc.get("extracted_text") or "")[:1500]
        
        trilingual_doc_summaries.append({
            "id": str(doc["_id"]),
            "file_name": file_name,
            "mime_type": doc.get("mime_type", "application/pdf"),
            "summary": text_preview or "Dokument i verifikuar në fashikull.",
            "language": doc.get("detected_language", "auto")
        })
    
    mapped_case = _map_case_document(case, db) or {}
    mapped_case["document_summaries"] = trilingual_doc_summaries
    return mapped_case

def delete_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB):
    storage_service = importlib.import_module("app.services.storage_service")
    vector_store_service = importlib.import_module("app.services.vector_store_service")
    graph_service_module = importlib.import_module("app.services.graph_service")
    graph_service = getattr(graph_service_module, "graph_service")
    
    case = db.cases.find_one({"_id": case_id, "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]})
    if not case: raise HTTPException(status_code=404, detail="Case not found.")
    
    case_id_str = str(case_id)
    any_id_query: Dict[str, Any] = {"case_id": {"$in": [case_id, case_id_str]}}
    
    # 1. Delete standard documents & storage files
    documents = list(db.documents.find(any_id_query))
    for doc in documents:
        doc_id_str = str(doc["_id"])
        keys_to_delete = [doc.get("storage_key"), doc.get("processed_text_storage_key"), doc.get("preview_storage_key")]
        for key in filter(None, keys_to_delete):
            try: storage_service.delete_file(key)
            except Exception: pass
        try: vector_store_service.delete_document_embeddings(document_id=doc_id_str)
        except Exception: pass
        try: graph_service.delete_node(doc_id_str)
        except Exception: pass

    # 2. Delete Media Evidence (Audio/Video) & storage files
    media_items = list(db.media_evidence.find(any_id_query))
    for media in media_items:
        storage_key = media.get("storage_key")
        if storage_key:
            try: storage_service.delete_file(storage_key)
            except Exception: pass
    db.media_evidence.delete_many(any_id_query)

    # 3. Delete archives, calendar events, alerts
    archive_items = db.archives.find(any_id_query)
    for item in archive_items:
        if "storage_key" in item:
            try: storage_service.delete_file(item["storage_key"])
            except Exception: pass
    
    db.archives.delete_many(any_id_query)
    db.cases.delete_one({"_id": case_id})
    db.documents.delete_many(any_id_query)
    db.calendar_events.delete_many(any_id_query)
    try: db.alerts.delete_many(any_id_query)
    except Exception: pass

    try:
        graph_service.delete_node(case_id_str)
    except Exception as e:
        print(f"Graph deletion warning: {e}")

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
    try:
        case_oid = ObjectId(case_id)
        case = db.cases.find_one({"_id": case_oid})
        if not case: return None
        
        events_cursor = db.calendar_events.find({
            "$and": [
                {"$or": [{"case_id": case_id}, {"case_id": case_oid}]},
                {"$or": [
                    {"is_public": True},
                    {"notes": {"$regex": "CLIENT_VISIBLE", "$options": "i"}},
                    {"description": {"$regex": "CLIENT_VISIBLE", "$options": "i"}}
                ]}
            ]
        }).sort("start_date", 1)
        
        events = []
        for ev in events_cursor:
            description = ev.get("description", "") or ev.get("notes", "") or ""
            clean_desc = description.replace("[CLIENT_VISIBLE]", "").replace("[client_visible]", "").strip()
            
            ev_date = ev.get("start_date")
            date_str = ev_date.isoformat() if isinstance(ev_date, datetime) else ev_date

            events.append({
                "title": ev.get("title"),
                "date": date_str,
                "type": ev.get("event_type", "EVENT"),
                "description": clean_desc
            })
        
        docs_cursor = db.documents.find({
            "$or": [{"case_id": case_id}, {"case_id": case_oid}],
            "is_shared": True,
            "status": {"$nin": ["DELETED", "ARCHIVED", "ERROR"]}
        }).sort("created_at", -1)
        
        shared_docs = []
        for d in docs_cursor:
            d_date = d.get("created_at")
            d_date_str = d_date.isoformat() if isinstance(d_date, datetime) else d_date
            shared_docs.append({
                "id": str(d["_id"]),
                "file_name": d.get("file_name"),
                "created_at": d_date_str,
                "file_type": d.get("mime_type", "application/pdf"),
                "source": "ACTIVE"
            })

        archive_cursor = db.archives.find({
            "$or": [{"case_id": case_id}, {"case_id": case_oid}],
            "is_shared": True,
            "item_type": "FILE"
        }).sort("created_at", -1)
        
        for a in archive_cursor:
             if not a.get("storage_key"): continue 
             a_date = a.get("created_at")
             a_date_str = a_date.isoformat() if isinstance(a_date, datetime) else a_date
             shared_docs.append({
                "id": str(a["_id"]),
                "file_name": a.get("title", "Archived File"),
                "created_at": a_date_str,
                "file_type": "application/pdf", 
                "source": "ARCHIVE"
            })

        try:
            invoices_cursor = db.invoices.find({
                "related_case_id": case_id,
                "status": {"$in": ["PAID", "SENT", "OVERDUE"]}
            }).sort("issue_date", -1)
            shared_invoices = []
            for inv in invoices_cursor:
                inv_date = inv.get("issue_date")
                inv_date_str = inv_date.isoformat() if isinstance(inv_date, datetime) else inv_date
                shared_invoices.append({
                    "id": str(inv["_id"]),
                    "number": inv.get("invoice_number"),
                    "amount": inv.get("total_amount"),
                    "status": inv.get("status"),
                    "date": inv_date_str
                })
        except Exception:
            shared_invoices = []

        owner_id = case.get("owner_id") or case.get("user_id")
        organization_name = "Zyra Ligjore"
        logo_path = None

        if owner_id:
            search_conditions = [{"user_id": owner_id}]
            if isinstance(owner_id, ObjectId):
                search_conditions.append({"user_id": str(owner_id)})
            if isinstance(owner_id, str):
                try: search_conditions.append({"user_id": ObjectId(owner_id)})
                except InvalidId: pass
            
            profile = db.business_profiles.find_one({"$or": search_conditions})
            if profile:
                organization_name = (
                    profile.get("firm_name") or 
                    profile.get("business_name") or 
                    profile.get("company_name") or 
                    "Zyra Ligjore"
                )
                if profile.get("logo_storage_key"):
                    logo_path = f"/share/public/{case_id}/logo"

        client_obj = case.get("client", {})
        raw_name = client_obj.get("name") if isinstance(client_obj, dict) else None
        clean_name = raw_name.strip().title() if raw_name else "Klient"
        
        client_email = client_obj.get("email") if isinstance(client_obj, dict) else None
        client_phone = client_obj.get("phone") if isinstance(client_obj, dict) else None
        
        case_created = case.get("created_at")
        case_created_str = case_created.isoformat() if isinstance(case_created, datetime) else case_created

        return {
            "case_number": case.get("case_number"), 
            "title": case.get("title") or case.get("case_name"), 
            "client_name": clean_name, 
            "client_email": client_email,
            "client_phone": client_phone,
            "created_at": case_created_str,
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