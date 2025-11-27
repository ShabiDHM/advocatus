# FILE: backend/app/services/user_service.py
# PHOENIX PROTOCOL - USER SERVICE
# 1. AUTHENTICATION: Supports login via Username OR Email.
# 2. INTEGRITY: Preserves all previous Pydantic validations.
# 3. ADDED: Implemented the missing cascading delete logic for full account removal.

from pymongo.database import Database
from bson import ObjectId
from fastapi import HTTPException, status
from datetime import datetime, timezone
from typing import Optional
import logging

from app.core.security import verify_password, get_password_hash
from app.models.user import UserInDB, UserCreate
from app.services import storage_service # Assumes a storage service for file deletion

logger = logging.getLogger(__name__)

def get_user_by_username(db: Database, username: str) -> Optional[UserInDB]:
    user_dict = db.users.find_one({"username": username})
    if user_dict:
        return UserInDB.model_validate(user_dict)
    return None

def get_user_by_email(db: Database, email: str) -> Optional[UserInDB]:
    user_dict = db.users.find_one({"email": email})
    if user_dict:
        return UserInDB.model_validate(user_dict)
    return None

def get_user_by_id(db: Database, user_id: ObjectId) -> Optional[UserInDB]:
    user_dict = db.users.find_one({"_id": user_id})
    if user_dict:
        return UserInDB.model_validate(user_dict)
    return None

def authenticate(db: Database, username: str, password: str) -> Optional[UserInDB]:
    """
    Checks if user exists (by Username OR Email) and password matches hash.
    """
    user = get_user_by_username(db, username)
    if not user:
        user = get_user_by_email(db, username)
        
    if not user or not verify_password(password, user.hashed_password):
        return None
        
    return user

def create(db: Database, obj_in: UserCreate) -> UserInDB:
    """
    Creates a new user with hashed password.
    """
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
    """
    Updates the last_login timestamp for a user.
    """
    try:
        oid = ObjectId(user_id)
        db.users.update_one(
            {"_id": oid},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )
    except Exception:
        pass

def change_password(db: Database, user_id: str, old_pass: str, new_pass: str):
    """
    Verifies old password and sets new hashed password.
    """
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

# PHOENIX FIX: Implement the missing function to resolve the Pylance error.
def delete_user_and_all_data(db: Database, user: UserInDB):
    """
    Performs a cascading delete of a user and all their associated data.
    This includes cases, documents (DB records and stored files), findings, and events.
    """
    user_id = user.id
    logger.warning(f"PERMANENT DATA DELETION initiated for user_id: {user_id}")

    try:
        # 1. Find all cases owned by the user
        cases_to_delete_cursor = db.cases.find({"owner_id": user_id})
        case_ids = [case["_id"] for case in cases_to_delete_cursor]
        
        if case_ids:
            str_case_ids = [str(cid) for cid in case_ids]
            logger.info(f"Found {len(str_case_ids)} cases for deletion: {str_case_ids}")

            # 2. Find and delete all associated files from storage
            docs_to_delete_cursor = db.documents.find({"case_id": {"$in": str_case_ids}})
            for doc in docs_to_delete_cursor:
                # This logic prevents orphaned files in your object storage (e.g., S3, MinIO)
                if doc.get("storage_key"):
                    storage_service.delete_file(doc["storage_key"])
                if doc.get("preview_storage_key"):
                    storage_service.delete_file(doc["preview_storage_key"])
                if doc.get("processed_text_storage_key"):
                    storage_service.delete_file(doc["processed_text_storage_key"])
            
            logger.info(f"Storage files for {len(str_case_ids)} cases have been deleted.")

            # 3. Delete all DB records associated with the cases
            db.findings.delete_many({"case_id": {"$in": str_case_ids}})
            db.documents.delete_many({"case_id": {"$in": str_case_ids}})
            db.calendar_events.delete_many({"case_id": {"$in": str_case_ids}})
            
            # 4. Delete the cases themselves
            db.cases.delete_many({"_id": {"$in": case_ids}})
            logger.info("Associated findings, documents, events, and cases deleted from DB.")

        # 5. Delete user's business profile (if any)
        db.business_profiles.delete_one({"user_id": user_id})
        logger.info("User business profile deleted.")

        # 6. Delete the user record itself
        db.users.delete_one({"_id": user_id})
        logger.warning(f"User account for user_id: {user_id} has been permanently deleted.")

    except Exception as e:
        logger.error(f"Failed during cascading delete for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A failure occurred during the account deletion process. Please contact support."
        )