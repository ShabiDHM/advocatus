# FILE: backend/app/services/user_service.py
# PHOENIX PROTOCOL MODIFICATION 30.1 (SYNTAX CORRECTION):
# 1. CRITICAL FIX: Corrected a syntax error in the 'create_user' function definition.
#    Replaced an erroneous closing bracket ']' with the required colon ':'.
# 2. This resolves the Pylance "Expected ':'" error and ensures the file is valid Python code.

from typing import Optional, Dict, Any, List
from datetime import datetime
from bson import ObjectId
from pymongo.database import Database
from passlib.context import CryptContext
import logging

from ..models.user import UserCreate, UserInDB, UserLoginResponse, UserOut
from ..models.api_key import ApiKeyInDB
from ..core.security import get_password_hash, verify_password, create_access_token, create_refresh_token, decode_token
from ..core.db import get_collection

USER_COLLECTION = "users"
CASE_COLLECTION = "cases"
DOCUMENT_COLLECTION = "documents"
API_KEY_COLLECTION = "api_keys"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)

# --- CORE USER GETTERS ---
def get_user_by_username(db: Database, username: str) -> Optional[UserInDB]:
    user_data = get_collection(db, USER_COLLECTION).find_one({"username": username})
    if user_data:
        return UserInDB(**user_data)
    return None

def get_user_by_email(db: Database, email: str) -> Optional[UserInDB]:
    user_data = get_collection(db, USER_COLLECTION).find_one({"email": email})
    if user_data:
        return UserInDB(**user_data)
    return None

def get_user_by_id(db: Database, user_id: ObjectId) -> Optional[UserInDB]:
    user_data = get_collection(db, USER_COLLECTION).find_one({"_id": user_id})
    if user_data:
        return UserInDB(**user_data)
    return None

def get_all_users(db: Database) -> List[UserInDB]:
    users_data = list(get_collection(db, USER_COLLECTION).find())
    return [UserInDB(**data) for data in users_data]

def get_user_from_token(db: Database, token: str, expected_token_type: str) -> Optional[UserInDB]:
    """
    Decodes the token and fetches the user. Returns the UserInDB object on success,
    or None on any failure (e.g., invalid token, user not found, type mismatch).
    This function is safe to call from both HTTP and WebSocket contexts.
    """
    if token.startswith("Bearer "):
        clean_token = token[7:]
    else:
        clean_token = token

    try:
        payload = decode_token(clean_token)
        
        if payload.get("type") != expected_token_type:
            logger.warning(f"Token type mismatch. Expected '{expected_token_type}', got '{payload.get('type')}'.")
            return None
            
        user_id_str = payload.get("id")
        if not user_id_str:
            logger.warning("Token is missing user ID ('id' claim).")
            return None
        
        user = get_user_by_id(db, ObjectId(user_id_str))
        if not user:
            logger.warning(f"User not found for token ID: {user_id_str}")
            return None
            
        return user
            
    except Exception as e:
        logger.error(f"Failed to validate token: {e}", exc_info=False)
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
    return user

# --- SYNTAX FIX: Replaced ']' with ':' ---
def create_user(db: Database, user: UserCreate, role: str = 'user') -> UserInDB:
    hashed_password = get_password_hash(user.password)
    user_data = user.model_dump(exclude={"password"}, exclude_none=True)
    user_data["hashed_password"] = hashed_password
    user_data["role"] = role.lower()
    user_data["subscription_status"] = "none"
    
    result = get_collection(db, USER_COLLECTION).insert_one(user_data)
    user_data["_id"] = result.inserted_id
    return UserInDB(**user_data)

# --- USER MANAGEMENT ACTIONS ---
def delete_user_and_all_data(user: UserInDB, db: Database):
    user_id = user.id
    get_collection(db, API_KEY_COLLECTION).delete_many({"user_id": user_id})
    get_collection(db, CASE_COLLECTION).delete_many({"owner_id": user_id})
    user_result = get_collection(db, USER_COLLECTION).delete_one({"_id": user_id})

    if user_result.deleted_count == 0:
        raise Exception("User was not found for deletion.")

def update_user_profile(db: Database, user_id: ObjectId, data: Dict[str, Any]) -> Optional[UserInDB]:
    if 'role' in data:
        data['role'] = data['role'].lower()
    
    update_result = get_collection(db, USER_COLLECTION).update_one(
        {"_id": user_id},
        {"$set": data}
    )
    if update_result.modified_count > 0:
        return get_user_by_id(db, user_id)
    return None

def change_user_password(db: Database, user: UserInDB, new_password: str) -> bool:
    new_hashed_password = get_password_hash(new_password)
    result = get_collection(db, USER_COLLECTION).update_one(
        {"_id": user.id},
        {"$set": {"hashed_password": new_hashed_password}}
    )
    return result.modified_count > 0