# FILE: backend/app/services/user_service.py
# PHOENIX PROTOCOL - USER SERVICE V1.1 (CASE INSENSITIVE QUERIES)
# 1. FIX: All username/email lookups are now case-insensitive using Regex.
# 2. LOGIC: Allows login with 'shaban' even if registered as 'Shaban'.

from pymongo.database import Database
from bson import ObjectId
from fastapi import HTTPException
from datetime import datetime, timezone
from typing import Optional
import logging
import re

from app.core.security import verify_password, get_password_hash
from app.models.user import UserInDB, UserCreate
from app.services import storage_service

logger = logging.getLogger(__name__)

def get_user_by_username(db: Database, username: str) -> Optional[UserInDB]:
    # PHOENIX FIX: Case-insensitive regex query
    query = {"username": {"$regex": f"^{re.escape(username)}$", "$options": "i"}}
    user_dict = db.users.find_one(query)
    if user_dict:
        return UserInDB.model_validate(user_dict)
    return None

def get_user_by_email(db: Database, email: str) -> Optional[UserInDB]:
    # PHOENIX FIX: Case-insensitive regex query
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
        
    if not user or not verify_password(password, user.hashed_password):
        return None
        
    return user

def create(db: Database, obj_in: UserCreate) -> UserInDB:
    user_data = obj_in.model_dump()
    password = user_data.pop("password")
    hashed_password = get_password_hash(password)
    
    user_data["hashed_password"] = hashed_password
    user_data["created_at"] = datetime.now(timezone.utc)
    
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
    
    if not verify_password(old_pass, user_dict["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid old password")

    new_hash = get_password_hash(new_pass)
    db.users.update_one({"_id": oid}, {"$set": {"hashed_password": new_hash}})

def delete_user_and_all_data(db: Database, user: UserInDB):
    user_id = user.id
    try:
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

        db.business_profiles.delete_one({"user_id": user_id})
        db.users.delete_one({"_id": user_id})
        
    except Exception as e:
        logger.error(f"Failed during cascading delete for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="A failure occurred during the account deletion process.")