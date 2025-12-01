# FILE: backend/app/services/case_service.py
# PHOENIX PROTOCOL - CASE SERVICE (FULL SHREDDER V2)
# 1. UPDATE: delete_case_by_id now iterates documents to delete PHYSICAL files and VECTORS.
# 2. STATUS: Zero-waste deletion. No orphaned files or embeddings.

from fastapi import HTTPException, status
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, cast
import re

from ..models.case import CaseCreate
from ..models.user import UserInDB
from ..models.drafting import DraftRequest
from ..celery_app import celery_app
from .graph_service import graph_service
# PHOENIX FIX: Added vector_store_service import
from . import storage_service, vector_store_service

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

# --- AUTO-SYNC LOGIC ---
def _parse_finding_date(text: str) -> datetime | None:
    if not text: return None
    text = text.lower().strip()
    
    # 1. Numeric (DD/MM/YYYY)
    match = re.search(r'(\d{1,2})[./-](\d{1,2})[./-](\d{4})', text)
    if match:
        return datetime(int(match.group(3)), int(match.group(2)), int(match.group(1)), tzinfo=timezone.utc)
        
    # 2. Albanian Months
    months = {
        'janar': 1, 'shkurt': 2, 'mars': 3, 'prill': 4, 'maj': 5, 'qershor': 6,
        'korrik': 7, 'gusht': 8, 'shtator': 9, 'tetor': 10, 'nëntor': 11, 'nentor': 11, 'dhjetor': 12
    }
    
    for m_name, m_num in months.items():
        # With Year: "15 Dhjetor 2025"
        if match := re.search(r'(\d{1,2})[\s.-]+' + m_name + r'[\s.-]+(\d{4})', text):
            return datetime(int(match.group(2)), m_num, int(match.group(1)), tzinfo=timezone.utc)
        # Without Year: "25 Dhjetor" -> Smart Year
        if match := re.search(r'(\d{1,2})[\s.-]+' + m_name + r'(?!\w)', text):
            day = int(match.group(1))
            now = datetime.now(timezone.utc)
            year = now.year
            # If month passed, assume next year
            if m_num < now.month: year += 1
            return datetime(year, m_num, day, tzinfo=timezone.utc)
            
    return None

def sync_case_calendar_from_findings(db: Database, case_id: str, user_id: ObjectId):
    """
    Scans all findings for a case, detects dates, and populates the calendar_events table.
    Smart Deduplication: If ANY event exists on the target day for this case, skip auto-creation.
    """
    try:
        findings = list(db.findings.find({"case_id": {"$in": [case_id, ObjectId(case_id)]}}))
        
        events_to_create = []
        for f in findings:
            f_text = f.get('finding_text', '')
            dt = _parse_finding_date(f_text)
            
            if dt:
                # PHOENIX FIX: Strict Day-Level Deduplication
                start_of_day = datetime(dt.year, dt.month, dt.day, 0, 0, 0)
                end_of_day = datetime(dt.year, dt.month, dt.day, 23, 59, 59)
                
                # Check for ANY existing event on this day for this case
                exists = db.calendar_events.find_one({
                    "case_id": {"$in": [case_id, ObjectId(case_id)]},
                    "$or": [
                        {"start_date": {"$gte": start_of_day, "$lte": end_of_day}},
                        {"start_date": {"$gte": start_of_day.isoformat(), "$lte": end_of_day.isoformat()}} 
                    ]
                })
                
                if not exists:
                    title_fragment = f_text[:60] + "..." if len(f_text) > 60 else f_text
                    events_to_create.append({
                        "title": title_fragment,
                        "description": f"Burimi (Auto-Detected): {f_text}",
                        "start_date": dt,
                        "end_date": dt,
                        "is_all_day": True,
                        "event_type": "DEADLINE",
                        "priority": "HIGH",
                        "status": "PENDING",
                        "case_id": case_id, 
                        "owner_id": user_id,
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    })
        
        if events_to_create:
            db.calendar_events.insert_many(events_to_create)
            
    except Exception as e:
        print(f"Error syncing calendar for case {case_id}: {e}")

# --- CRUD OPERATIONS ---

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
    
    sync_case_calendar_from_findings(db, str(case_id), owner.id)
    
    return _map_case_document(case, db)

def delete_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB):
    """
    Deletes a case and ALL associated data (Documents, Files, Embeddings, Events, etc.)
    """
    case = db.cases.find_one({
        "_id": case_id, 
        "$or": [{"owner_id": owner.id}, {"user_id": owner.id}]
    })
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    case_id_str = str(case_id)
    # Flexible query to catch inconsistencies
    any_id_query: Dict[str, Any] = {"case_id": {"$in": [case_id, case_id_str]}}

    # --- 1. DOCUMENTS DEEP CLEAN (Files + Vectors) ---
    # Fetch all docs first so we have their storage keys
    documents = list(db.documents.find(any_id_query))
    for doc in documents:
        doc_id_str = str(doc["_id"])
        
        # A. Delete Physical Files
        keys_to_delete = [
            doc.get("storage_key"),
            doc.get("processed_text_storage_key"),
            doc.get("preview_storage_key")
        ]
        for key in keys_to_delete:
            if key:
                try:
                    storage_service.delete_file(key)
                except Exception as e:
                    print(f"Warning: Failed to delete file key {key}: {e}")

        # B. Delete Vector Embeddings
        try:
            vector_store_service.delete_document_embeddings(document_id=doc_id_str)
        except Exception as e:
            print(f"Warning: Failed to delete embeddings for doc {doc_id_str}: {e}")

        # C. Delete Graph Nodes
        try:
            graph_service.delete_document_nodes(doc_id_str)
        except Exception:
            pass

    # --- 2. ARCHIVE CLEANUP ---
    archive_items = db.archives.find(any_id_query)
    for item in archive_items:
        if "storage_key" in item:
            try:
                storage_service.delete_file(item["storage_key"])
            except Exception as e:
                print(f"Warning: Failed to delete archive file {item.get('title')}: {e}")
    db.archives.delete_many(any_id_query)

    # --- 3. DELETE CASE ENTITY ---
    db.cases.delete_one({"_id": case_id})
    
    # --- 4. CLEANUP ASSOCIATED DB RECORDS ---
    db.documents.delete_many(any_id_query)
    db.calendar_events.delete_many(any_id_query)
    db.findings.delete_many(any_id_query)
    db.alerts.delete_many(any_id_query)

def create_draft_job_for_case(db: Database, case_id: ObjectId, job_in: DraftRequest, owner: UserInDB) -> Dict[str, Any]:
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