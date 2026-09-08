# FILE: backend/app/services/user_service.py
# PHOENIX PROTOCOL - USER SERVICE V2.0 (GDPR COMPLIANT)
# 1. ADDED: is_deleted check in authenticate().
# 2. ADDED: consent_date default in create().
# 3. ENHANCED: delete_user_and_all_data() now also deletes user's archive items and logs audit.
# 4. PRESERVED: All existing functionality and import style.

from pymongo.database import Database
from bson import ObjectId
from fastapi import HTTPException
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging
import re

from app.core.security import verify_password, get_password_hash
from app.models.user import UserInDB, UserCreate
from app.services import storage_service

logger = logging.getLogger(__name__)


def _log_user_audit(db: Database, action: str, user_id: ObjectId, details: Optional[Dict[str, Any]] = None):
    """Regjistron një ngjarje auditimi për veprime të ndjeshme të përdoruesit."""
    try:
        audit_entry = {
            "action": action,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc),
            "details": details or {}
        }
        db.user_audit.insert_one(audit_entry)
    except Exception as e:
        logger.error(f"Failed to write user audit log: {e}")


def get_user_by_username(db: Database, username: str) -> Optional[UserInDB]:
    query = {"username": {"$regex": f"^{re.escape(username)}$", "$options": "i"}}
    user_dict = db.users.find_one(query)
    if user_dict:
        return UserInDB.model_validate(user_dict)
    return None


def get_user_by_email(db: Database, email: str) -> Optional[UserInDB]:
    query = {"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}}
    user_dict = db.users.find_one(query)
    if user_dict:
        return UserInDB.model_validate(user_dict)
    return None


def get_user_by_id(db: Database, user_id: ObjectId) -> Optional[UserInDB]:
    user_dict = db.users.find_one({"_id": user_id})
    if user_dict:
        return UserInDB.model_validate(user_dict)
    return None


def authenticate(db: Database, username: str, password: str) -> Optional[UserInDB]:
    user = get_user_by_username(db, username)
    if not user:
        user = get_user_by_email(db, username)
        
    if not user:
        return None

    # GDPR: nuk lejohet hyrja për përdorues të fshirë
    if user.is_deleted:
        return None
        
    # PHOENIX FIX V1.5: Check if hashed_password is None before attempting verification.
    if user.hashed_password is None:
        return None
        
    if not verify_password(password, user.hashed_password):
        return None
        
    return user


def create(db: Database, obj_in: UserCreate) -> UserInDB:
    user_data = obj_in.model_dump()
    password = user_data.pop("password")
    hashed_password = get_password_hash(password)
    
    user_data["hashed_password"] = hashed_password
    user_data["created_at"] = datetime.now(timezone.utc)
    user_data["updated_at"] = datetime.now(timezone.utc)
    
    # GDPR: nëse consent_date nuk është dhënë, vendose tani
    if not user_data.get("consent_date"):
        user_data["consent_date"] = datetime.now(timezone.utc)
    
    # Explicitly set status for Gatekeeper
    user_data["subscription_status"] = "INACTIVE"
    
    result = db.users.insert_one(user_data)
    new_user = db.users.find_one({"_id": result.inserted_id})
    
    if not new_user:
        raise HTTPException(status_code=500, detail="User creation failed")
        
    return UserInDB.model_validate(new_user)


def update_last_login(db: Database, user_id: str):
    try:
        oid = ObjectId(user_id)
        db.users.update_one({"_id": oid}, {"$set": {"last_login": datetime.now(timezone.utc)}})
    except Exception:
        pass


def change_password(db: Database, user_id: str, old_pass: str, new_pass: str):
    try:
        oid = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user_dict = db.users.find_one({"_id": oid})
    if not user_dict:
        raise HTTPException(status_code=404, detail="User not found")
    
    # GDPR: mos lejo ndryshim fjalëkalimi për përdorues të fshirë
    if user_dict.get("is_deleted"):
        raise HTTPException(status_code=403, detail="Account is deleted")
    
    if not verify_password(old_pass, user_dict["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid old password")

    # Opsionale: verifiko fuqinë e fjalëkalimit të ri
    # (nëse dëshironi të shtoni, importo check_password_strength nga core.security)
    
    new_hash = get_password_hash(new_pass)
    db.users.update_one({"_id": oid}, {"$set": {"hashed_password": new_hash}})


def delete_user_and_all_data(db: Database, user: UserInDB):
    """
    Fshin plotësisht përdoruesin dhe të gjitha të dhënat e lidhura me të.
    Përfshin: cases, documents, findings, calendar events, business profile,
    archive items, dhe regjistron auditimin.
    """
    user_id = user.id
    try:
        # 1. Fshi rastet dhe dokumentet e lidhura
        cases_to_delete = list(db.cases.find({"owner_id": user_id}))
        if cases_to_delete:
            case_ids = [c["_id"] for c in cases_to_delete]
            docs_to_delete = list(db.documents.find({"case_id": {"$in": case_ids}}))
            for doc in docs_to_delete:
                if doc.get("storage_key"): storage_service.delete_file(doc["storage_key"])
                if doc.get("preview_storage_key"): storage_service.delete_file(doc["preview_storage_key"])
                if doc.get("processed_text_storage_key"): storage_service.delete_file(doc["processed_text_storage_key"])
            
            db.findings.delete_many({"case_id": {"$in": case_ids}})
            db.documents.delete_many({"case_id": {"$in": case_ids}})
            db.calendar_events.delete_many({"case_id": {"$in": case_ids}})
            db.cases.delete_many({"_id": {"$in": case_ids}})

        # 2. Fshi të dhënat e biznesit
        db.business_profiles.delete_one({"user_id": str(user_id)})

        # 3. Fshi elementet e arkivës së përdoruesit dhe skedarët në S3
        archive_items = list(db.archives.find({"$or": [{"user_id": user_id}, {"owner_id": user_id}]}))
        for item in archive_items:
            # Fshi skedarin nga S3 nëse ka
            if item.get("storage_key"):
                try:
                    storage_service.delete_file(item["storage_key"])
                except Exception as e:
                    logger.error(f"Failed to delete archive S3 object {item['storage_key']}: {e}")
            # Fshi rekordin nga MongoDB
            db.archives.delete_one({"_id": item["_id"]})

        # 4. Fshi përdoruesin nga koleksioni users
        db.users.delete_one({"_id": user_id})
        
        # 5. Regjistro auditimin
        _log_user_audit(db, "USER_DELETED", user_id, {"email": user.email, "username": user.username})
        
    except Exception as e:
        logger.error(f"Failed during cascading delete for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="A failure occurred during the account deletion process.")