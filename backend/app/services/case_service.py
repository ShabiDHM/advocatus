# FILE: backend/app/services/case_service.py
# PHOENIX PROTOCOL - CASE SERVICE V55.0 (DUAL-TIER LIFECYCLE: 7-DAY CITIZEN & 7-DAY GRACE FOR UNPAID LAWYERS)

import re
import urllib.parse 
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, cast
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from pymongo.database import Database
import logging

from ..models.case import CaseCreate
from ..models.user import UserInDB
from ..celery_app import celery_app
from app.services import storage_service, vector_store_service

logger = logging.getLogger(__name__)


# --- HELPER FUNCTIONS ---

def _safe_str(oid: Any) -> Optional[str]:
    if not oid: return None
    return str(oid)


def _build_case_access_query(user: UserInDB, case_id: Optional[ObjectId] = None) -> Dict[str, Any]:
    access_level = getattr(user, 'org_access_level', 'FULL')
    org_id = getattr(user, 'org_id', None)
    user_id_obj = user.id
    user_id_str = str(user.id)
    
    personal_clauses: List[Dict[str, Any]] = [
        {"owner_id": user_id_obj},
        {"owner_id": user_id_str},
        {"user_id": user_id_obj},
        {"user_id": user_id_str}
    ]

    if access_level == "SELECTIVE":
        assigned_case_ids = getattr(user, 'assigned_case_ids', []) or []
        allowed_case_oids: List[Any] = []
        for cid in assigned_case_ids:
            clean_id = str(cid).strip()
            if clean_id:
                if ObjectId.is_valid(clean_id):
                    allowed_case_oids.append(ObjectId(clean_id))
                allowed_case_oids.append(clean_id)

        selective_clauses: List[Dict[str, Any]] = list(personal_clauses)
        if allowed_case_oids:
            selective_clauses.append({"_id": {"$in": allowed_case_oids}})
        selective_clauses.append({"assigned_user_ids": user_id_str})

        query = {"$or": selective_clauses}

    else:
        if org_id:
            org_clauses = [
                {"org_id": org_id},
                {"org_id": str(org_id)},
                {"organization_id": org_id},
                {"organization_id": str(org_id)}
            ]
            if ObjectId.is_valid(str(org_id)):
                org_clauses.extend([
                    {"org_id": ObjectId(str(org_id))},
                    {"organization_id": ObjectId(str(org_id))}
                ])
            query = {"$or": personal_clauses + org_clauses}
        else:
            query = {"$or": personal_clauses}

    if case_id:
        return {"$and": [{"_id": case_id}, query]}

    return query


def _map_case_document(case_doc: Dict[str, Any], db: Optional[Database] = None) -> Optional[Dict[str, Any]]:
    try:
        case_id_obj = case_doc["_id"]
        case_id_str = str(case_id_obj)
        title = case_doc.get("title") or case_doc.get("case_name") or "Lëndë pa Titull"
        case_number = case_doc.get("case_number") or f"REF-{case_id_str[-6:]}"
        
        created_at = case_doc.get("created_at")
        if not isinstance(created_at, datetime):
            created_at = datetime.now(timezone.utc)
        
        updated_at = case_doc.get("updated_at")
        if not isinstance(updated_at, datetime):
            updated_at = created_at
        
        user_id = case_doc.get("user_id") or case_doc.get("owner_id")
        org_id = case_doc.get("org_id")

        client_obj = case_doc.get("client") if isinstance(case_doc.get("client"), dict) else {}
        client_name = case_doc.get("client_name") or client_obj.get("name") or "Klient"
        
        opposing_obj = case_doc.get("opposing_party")
        opposing_name = (
            opposing_obj.get("name") if isinstance(opposing_obj, dict) else opposing_obj
        ) or case_doc.get("opponent_name") or "Pala Kundërshtare"

        client_position = case_doc.get("client_position") or "DEFENDANT"
        disputed_amount = case_doc.get("disputed_amount") or case_doc.get("amount_eur") or 0.0
        court_name = case_doc.get("court") or case_doc.get("court_name") or "Gjykata Themelore"

        counts = {"document_count": 0, "alert_count": 0, "event_count": 0, "finding_count": 0}
        
        if db is not None:
            event_filter = {"$or": [{"case_id": case_id_str}, {"case_id": case_id_obj}, {"caseId": case_id_str}]}
            counts["event_count"] = db.calendar_events.count_documents(event_filter)
            
            doc_filter = {"$or": [{"case_id": case_id_str}, {"case_id": case_id_obj}], "status": {"$ne": "DELETED"}}
            counts["document_count"] = db.documents.count_documents(doc_filter)
            
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
            "is_unlocked": case_doc.get("is_unlocked", False),
            "unlocked_at": case_doc.get("unlocked_at"),
            "is_purged": case_doc.get("is_purged", False),
            "client_id": _safe_str(case_doc.get("client_id")),
            "client": case_doc.get("client") or {"name": client_name},
            "client_name": client_name,
            "opposing_party": opposing_name,
            "opponent_name": opposing_name,
            "client_position": client_position,
            "disputed_amount": disputed_amount,
            "court": court_name,
            "court_name": court_name,
            "assigned_user_ids": case_doc.get("assigned_user_ids", []),
            "created_at": created_at, 
            "updated_at": updated_at, 
            "chat_history": case_doc.get("chat_history", []), 
            "latest_comprehensive_analysis": case_doc.get("latest_comprehensive_analysis"),
            "latest_analysis": case_doc.get("latest_analysis"), 
            "latest_deep_analysis": case_doc.get("latest_deep_analysis"),
            "analyzed_doc_fingerprints": case_doc.get("analyzed_doc_fingerprints"),
            **counts
        }
    except Exception as e:
        logger.error(f"Error mapping case: {e}")
        return None


# --- CRUD OPERATIONS ---

def create_case(db: Database, case_in: CaseCreate, owner: UserInDB) -> Optional[Dict[str, Any]]:
    case_dict = case_in.model_dump(exclude={"clientName", "clientEmail", "clientPhone", "opposingParty"})
    
    if case_in.clientName:
        clean_name = case_in.clientName.strip().title()
        case_dict["client"] = {"name": clean_name, "email": case_in.clientEmail, "phone": case_in.clientPhone}
        case_dict["client_name"] = clean_name

    opposing_input = case_in.opposingParty or case_in.opposing_party or case_in.opponent_name
    if opposing_input:
        clean_opposing = str(opposing_input).strip()
        case_dict["opposing_party"] = clean_opposing
        case_dict["opponent_name"] = clean_opposing
    
    org_id = getattr(owner, "org_id", None)
    has_active_sub = getattr(owner, "has_active_subscription", False) or (getattr(owner, "subscription_status", "") == "ACTIVE")
    
    case_dict.update({
        "owner_id": owner.id, 
        "user_id": owner.id,
        "org_id": org_id,
        "assigned_user_ids": [str(owner.id)],
        "is_unlocked": bool(has_active_sub),
        "unlocked_at": datetime.now(timezone.utc) if has_active_sub else None,
        "is_purged": False,
        "created_at": datetime.now(timezone.utc), 
        "updated_at": datetime.now(timezone.utc),
        "case_number": case_dict.get("case_number") or f"R-{int(datetime.now(timezone.utc).timestamp()) % 1000000:06d}"
    })

    result = db.cases.insert_one(case_dict)
    new_case = db.cases.find_one({"_id": result.inserted_id})
    if not new_case: 
        raise HTTPException(status_code=500, detail="Dështoi krijimi i rastit.")
    return _map_case_document(cast(Dict[str, Any], new_case), db)


def get_cases_for_user(db: Database, owner: UserInDB) -> List[Dict[str, Any]]:
    results = []
    query_filter = _build_case_access_query(owner)
    
    cursor = db.cases.find(query_filter).sort("updated_at", -1)
    for case_doc in cursor:
        mapped_case = _map_case_document(case_doc, db)
        if mapped_case:
            results.append(mapped_case)
    return results


def get_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB) -> Optional[Dict[str, Any]]:
    query_filter = _build_case_access_query(owner, case_id=case_id)
    case = db.cases.find_one(query_filter)
    if not case: 
        return None
    return _map_case_document(case, db)


def get_case_full_context(db: Database, case_id: ObjectId, owner: UserInDB) -> Dict[str, Any]:
    query_filter = _build_case_access_query(owner, case_id=case_id)
    case = db.cases.find_one(query_filter)
    if not case:
        raise HTTPException(status_code=404, detail="Rasti nuk u gjet ose nuk keni qasje.")
    
    case_id_str = str(case_id)
    doc_filter = {
        "$or": [{"case_id": case_id}, {"case_id": case_id_str}],
        "status": {"$ne": "DELETED"}
    }
    documents = list(db.documents.find(doc_filter))
    
    trilingual_doc_summaries = []
    for doc in documents:
        file_name = doc.get("file_name") or doc.get("title") or "Dokument i Lëndës"
        raw_t = doc.get("extracted_text") or ""
        summ = doc.get("summary") or ""
        if summ == "Sinteza...":
            summ = ""

        if summ and raw_t:
            text_preview = f"{summ}\n{raw_t[:1000]}".strip()
        else:
            text_preview = (raw_t[:2000] or summ or "Dokument i verifikuar në fashikull.").strip()

        trilingual_doc_summaries.append({
            "id": str(doc["_id"]),
            "file_name": file_name,
            "mime_type": doc.get("mime_type", "application/pdf"),
            "summary": text_preview,
            "language": doc.get("detected_language", "auto")
        })
    
    mapped_case = _map_case_document(case, db) or {}
    mapped_case["document_summaries"] = trilingual_doc_summaries
    return mapped_case


def delete_case_by_id(db: Database, case_id: ObjectId, owner: UserInDB):
    query_filter = _build_case_access_query(owner, case_id=case_id)
    case = db.cases.find_one(query_filter)
    if not case: 
        raise HTTPException(status_code=404, detail="Rasti nuk u gjet.")
    
    case_id_str = str(case_id)
    any_id_query: Dict[str, Any] = {"case_id": {"$in": [case_id, case_id_str]}}
    
    documents = list(db.documents.find(any_id_query))
    for doc in documents:
        doc_id_str = str(doc["_id"])
        keys_to_delete = [doc.get("storage_key"), doc.get("processed_text_storage_key"), doc.get("preview_storage_key")]
        for key in filter(None, keys_to_delete):
            try: 
                storage_service.delete_file(key)
            except Exception: 
                pass
        try: 
            vector_store_service.delete_document_embeddings(user_id=str(owner.id), document_id=doc_id_str)
        except Exception: 
            pass

    media_items = list(db.media_evidence.find(any_id_query))
    for media in media_items:
        storage_key = media.get("storage_key")
        if storage_key:
            try: 
                storage_service.delete_file(storage_key)
            except Exception: 
                pass
    db.media_evidence.delete_many(any_id_query)

    archive_items = db.archives.find(any_id_query)
    for item in archive_items:
        if "storage_key" in item:
            try: 
                storage_service.delete_file(item["storage_key"])
            except Exception: 
                pass
    
    db.archives.delete_many(any_id_query)
    db.cases.delete_one({"_id": case_id})
    db.documents.delete_many(any_id_query)
    db.calendar_events.delete_many(any_id_query)
    try: 
        db.alerts.delete_many(any_id_query)
    except Exception: 
        pass


# =========================================================================
# 🧹 PASTRIMI AUTOMATIK ME DY STANDARDE (ONE-TIME CITIZEN & GRACE PERIOD)
# =========================================================================

def purge_expired_cases_data(db: Database, expiry_days: int = 7) -> Dict[str, Any]:
    """
    RREGULLI I DYFISHTË I PASTRIMIT:
    1. QYTETARËT (One-Time Pass): Fshihen pas 7 ditëve nga zhbllokimi i lëndës.
    2. AVOKATËT (Abonim Mujor): Dokumentet RUHEN PËRGJITHMONË për sa kohë që abonimi është aktiv.
       Nëse abonimi skadon dhe NUK rinovohet brenda 7 ditëve (Grace Period), atëherë fshihen skedarët e rëndë.
    """
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=expiry_days)
    
    all_unpurged_cases = list(db.cases.find({
        "is_purged": {"$ne": True}
    }))

    purged_cases_count = 0
    deleted_docs_count = 0

    for case in all_unpurged_cases:
        case_id = case["_id"]
        case_id_str = str(case_id)
        owner_id = str(case.get("owner_id", ""))
        
        # Lexo pronarin e lëndës nga databaza
        owner_doc = db.users.find_one({"_id": ObjectId(owner_id) if ObjectId.is_valid(owner_id) else owner_id})
        if not owner_doc:
            continue

        is_lawyer = owner_doc.get("product_plan") in ["SOLO_PLAN", "TEAM_PLAN", "PRO", "GROWTH"] or owner_doc.get("account_type") == "ORGANIZATION"
        has_active_sub = bool(owner_doc.get("has_active_subscription") or owner_doc.get("subscription_status") == "ACTIVE")
        sub_expiry = owner_doc.get("subscription_expiry")

        should_purge = False

        # RASTI 1: QYTETAR (One-Time Pass) ➔ Skadon pas 7 ditëve nga zhbllokimi
        if not is_lawyer:
            unlocked_time = case.get("unlocked_at") or case.get("created_at")
            if unlocked_time:
                if not isinstance(unlocked_time, datetime):
                    try: unlocked_time = datetime.fromisoformat(str(unlocked_time).replace('Z', '+00:00'))
                    except: unlocked_time = now
                if unlocked_time <= cutoff_date:
                    should_purge = True

        # RASTI 2: AVOKAT (Abonim Mujor) ➔ Pastrohet VETËM nëse kanë kaluar 7 ditë nga skadimi i abonimit pa u paguar
        else:
            if has_active_sub:
                # Abonim aktiv ➔ NUK FSHIHET KURRË!
                should_purge = False
            else:
                # Abonimi ka skaduar ➔ Kontrollo periudhën e tolerimit (7-Day Grace Period)
                if sub_expiry:
                    if not isinstance(sub_expiry, datetime):
                        try: sub_expiry = datetime.fromisoformat(str(sub_expiry).replace('Z', '+00:00'))
                        except: sub_expiry = now
                    if sub_expiry <= cutoff_date:
                        should_purge = True
                else:
                    # Pa datë skadimi por jo aktiv
                    should_purge = True

        # NËSE ËSHTË PËR T'U PASTRUAR:
        if should_purge:
            any_id_query = {"case_id": {"$in": [case_id, case_id_str]}}

            # 1. Fshi skedarët origjinalë nga Backblaze B2
            documents = list(db.documents.find(any_id_query))
            for doc in documents:
                doc_id_str = str(doc["_id"])
                keys_to_delete = [doc.get("storage_key"), doc.get("processed_text_storage_key"), doc.get("preview_storage_key")]
                for key in filter(None, keys_to_delete):
                    try:
                        storage_service.delete_file(key)
                    except Exception:
                        pass
                
                # 2. Fshi vektorët nga MongoDB
                try:
                    vector_store_service.delete_document_embeddings(user_id=owner_id, document_id=doc_id_str)
                except Exception:
                    pass
                
                deleted_docs_count += 1

            # 3. Fshi audiot/videot nga Backblaze
            media_items = list(db.media_evidence.find(any_id_query))
            for media in media_items:
                s_key = media.get("storage_key")
                if s_key:
                    try:
                        storage_service.delete_file(s_key)
                    except Exception:
                        pass
            db.media_evidence.delete_many(any_id_query)

            # 4. Përditëso dokumentet në status "PURGED"
            db.documents.update_many(
                any_id_query,
                {"$set": {
                    "status": "PURGED",
                    "extracted_text": "[Dokumenti është fshirë automatikisht për mbrojtjen e privatësisë.]",
                    "storage_key": None,
                    "preview_storage_key": None
                }}
            )

            # 5. Shëno lëndën si të pastruar (Raporti i Analizës mbetet i ruajtur!)
            db.cases.update_one(
                {"_id": case_id},
                {"$set": {
                    "is_purged": True,
                    "purged_at": now,
                    "status": "ARCHIVED_COMPLETED",
                    "updated_at": now
                }}
            )
            purged_cases_count += 1
            logger.info(f"🧹 [Auto-Purge] Lënda {case_id_str} u pastrua (Pronari: {'Avokat i Skaduar' if is_lawyer else 'Qytetar'}).")

    return {
        "status": "success",
        "purged_cases_count": purged_cases_count,
        "deleted_documents_count": deleted_docs_count,
        "timestamp": now.isoformat()
    }


def get_public_case_events(db: Database, case_id: str) -> Optional[Dict[str, Any]]:
    try:
        case_oid = ObjectId(case_id)
        case = db.cases.find_one({"_id": case_oid})
        if not case: 
            return None
        
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
            "status": {"$nin": ["DELETED", "ARCHIVED", "ERROR", "PURGED"]}
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

        return {
            "case_number": case.get("case_number"), 
            "title": case.get("title") or case.get("case_name"), 
            "status": case.get("status", "OPEN"), 
            "timeline": events,
            "documents": shared_docs
        }
    except Exception as e:
        logger.error(f"Public Portal Error: {e}")
        return None