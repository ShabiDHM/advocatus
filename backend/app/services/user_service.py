# FILE: backend/app/services/user_service.py
# PHOENIX PROTOCOL - THE FINAL AND DEFINITIVE CORRECTION (ROLE SYSTEM SYNCHRONIZATION)
# CORRECTION: The create_user function's default role has been updated from 'STANDARD'
# to 'USER' to align with the new, simplified data model.

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from pymongo.database import Database
from passlib.context import CryptContext
from pydantic import ValidationError
import logging

from ..models.user import UserCreate, UserInDB
from ..core.security import get_password_hash, verify_password, create_access_token, create_refresh_token

USER_COLLECTION = "users"
CASE_COLLECTION = "cases"
DOCUMENT_COLLECTION = "documents"
API_KEY_COLLECTION = "api_keys"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)

# --- CORE USER GETTERS (HARDENED) ---
def get_user_by_username(db: Database, username: str) -> Optional[UserInDB]:
    user_data = db[USER_COLLECTION].find_one({"username": username})
    if not user_data:
        return None
    try:
        return UserInDB(**user_data)
    except ValidationError as e:
        logger.error(f"Data validation error for user '{username}': {e}")
        return None

def get_user_by_email(db: Database, email: str) -> Optional[UserInDB]:
    user_data = db[USER_COLLECTION].find_one({"email": email})
    if not user_data:
        return None
    try:
        return UserInDB(**user_data)
    except ValidationError as e:
        logger.error(f"Data validation error for user with email '{email}': {e}")
        return None

def get_user_by_id(db: Database, user_id: ObjectId) -> Optional[UserInDB]:
    user_data = db[USER_COLLECTION].find_one({"_id": user_id})
    if not user_data:
        return None
    try:
        return UserInDB(**user_data)
    except ValidationError as e:
        logger.error(f"Data validation error for user ID '{user_id}': {e}")
        return None

# --- AUTHENTICATION & TOKEN CREATION ---
def create_both_tokens(data: Dict[str, Any]) -> Dict[str, str]:
    access_token = create_access_token(data=data)
    refresh_token = create_refresh_token(data=data)
    return {"access_token": access_token, "refresh_token": refresh_token}

def authenticate_user(username: str, password: str, db: Database) -> Optional[UserInDB]:
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None

    db[USER_COLLECTION].update_one(
        {"_id": user.id},
        {"$set": {"last_login": datetime.now(timezone.utc)}}
    )
    return user

# --- USER CREATION (SYNCHRONIZED DEFAULTS) ---
def create_user(db: Database, user: UserCreate, role: str = 'USER') -> UserInDB:
    hashed_password = get_password_hash(user.password)
    user_data = user.model_dump(exclude={"password"}, exclude_none=True)
    
    full_user_data = {
        **user_data,
        "hashed_password": hashed_password,
        "role": role.upper(),
        "subscription_status": "INACTIVE",
        "last_login": None,
    }
    
    result = db[USER_COLLECTION].insert_one(full_user_data)
    
    created_user_doc = db[USER_COLLECTION].find_one({"_id": result.inserted_id})
    if not created_user_doc:
        raise Exception("Failed to retrieve user immediately after creation.")
        
    return UserInDB(**created_user_doc)

# --- USER MANAGEMENT ACTIONS ---
def delete_user_and_all_data(user: UserInDB, db: Database):
    user_id = user.id
    db[API_KEY_COLLECTION].delete_many({"user_id": user_id})
    db[CASE_COLLECTION].delete_many({"owner_id": user_id})
    user_result = db[USER_COLLECTION].delete_one({"_id": user_id})

    if user_result.deleted_count == 0:
        raise Exception("User was not found for deletion.")

def update_user_profile(db: Database, user_id: ObjectId, data: Dict[str, Any]) -> Optional[UserInDB]:
    if 'role' in data:
        data['role'] = data['role'].upper()
    
    update_result = db[USER_COLLECTION].update_one(
        {"_id": user_id},
        {"$set": data}
    )
    if update_result.modified_count > 0:
        return get_user_by_id(db, user_id)
    return None

def change_user_password(db: Database, user: UserInDB, new_password: str) -> bool:
    new_hashed_password = get_password_hash(new_password)
    result = db[USER_COLLECTION].update_one(
        {"_id": user.id},
        {"$set": {"hashed_password": new_hashed_password}}
    )
    return result.modified_count > 0