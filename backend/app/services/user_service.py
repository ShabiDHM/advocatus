# FILE: backend/app/services/user_service.py
# DEFINITIVE VERSION 31.1 (AGGREGATION LOGIC):
# 1. REPLACED: The 'get_all_users' function is replaced with the new
#    'get_all_users_with_details' function.
# 2. This new function implements a MongoDB aggregation pipeline to compute the
#    'case_count' and 'document_count' for each user and derives 'created_at'
#    from the user's '_id', providing all data required by the frontend.

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

def get_all_users_with_details(db: Database) -> List[Dict[str, Any]]:
    """
    Retrieves all users with aggregated details like case and document counts
    using a MongoDB aggregation pipeline.
    """
    pipeline = [
        {
            "$lookup": {
                "from": CASE_COLLECTION,
                "let": { "user_id": "$_id" },
                "pipeline": [
                    { "$match": { "$expr": { "$eq": ["$owner_id", "$$user_id"] } } },
                    { "$project": { "_id": 1 } }
                ],
                "as": "owned_cases"
            }
        },
        {
            "$lookup": {
                "from": DOCUMENT_COLLECTION,
                "let": { "case_ids": "$owned_cases._id" },
                "pipeline": [
                    { "$match": { "$expr": { "$in": ["$case_id", "$$case_ids"] } } },
                    { "$count": "total_docs" }
                ],
                "as": "doc_count_result"
            }
        },
        {
            "$addFields": {
                "id": "$_id",
                "created_at": { "$toDate": "$_id" },
                "case_count": { "$size": "$owned_cases" },
                "document_count": { "$ifNull": [ { "$first": "$doc_count_result.total_docs" }, 0 ] }
            }
        },
        {
            "$project": {
                "owned_cases": 0,
                "doc_count_result": 0,
                "hashed_password": 0 
            }
        }
    ]
    users_data = list(get_collection(db, USER_COLLECTION).aggregate(pipeline))
    return users_data

def get_user_from_token(db: Database, token: str, expected_token_type: str) -> Optional[UserInDB]:
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
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None

    # Update last_login on successful authentication
    get_collection(db, USER_COLLECTION).update_one(
        {"_id": user.id},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    return user

def create_user(db: Database, user: UserCreate, role: str = 'user') -> UserInDB:
    hashed_password = get_password_hash(user.password)
    user_data = user.model_dump(exclude={"password"}, exclude_none=True)
    user_data["hashed_password"] = hashed_password
    user_data["role"] = role.lower()
    user_data["subscription_status"] = "none"
    user_data["last_login"] = None # Initialize last_login field
    
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