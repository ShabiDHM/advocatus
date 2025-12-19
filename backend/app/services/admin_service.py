# FILE: backend/app/services/admin_service.py
# PHOENIX PROTOCOL - ADMIN SERVICE V2.1 (FORCED UPDATE)
# 1. LOGIC: Explicitly extracts 'status' to ensure it's never dropped.
# 2. VERIFICATION: Reads the document immediately after update to confirm success.
# 3. STATUS: Hardened against silent failures.

from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict, Any
from pymongo.database import Database
from pymongo import ReturnDocument
import logging

from ..models.admin import UserUpdateRequest, AdminUserOut
from ..models.user import UserInDB

logger = logging.getLogger(__name__)

USER_COLLECTION = "users"
CASE_COLLECTION = "cases"
DOCUMENT_COLLECTION = "documents"

def get_all_users(db: Database) -> List[Dict[str, Any]]:
    pipeline = [
        {"$lookup": {"from": CASE_COLLECTION, "localField": "_id", "foreignField": "owner_id", "as": "owned_cases"}},
        {"$lookup": {"from": DOCUMENT_COLLECTION, "localField": "_id", "foreignField": "owner_id", "as": "owned_documents"}},
        {"$addFields": {
            "id": {"$toString": "$_id"},
            "case_count": {"$size": "$owned_cases"},
            "document_count": {"$size": "$owned_documents"}
        }},
        {"$project": {
            "_id": 0, 
            "owned_cases": 0, 
            "owned_documents": 0, 
            "hashed_password": 0
        }}
    ]
    users_data = list(db[USER_COLLECTION].aggregate(pipeline))
    return users_data

def find_user_in_aggregate(user_id: str, db: Database) -> Optional[AdminUserOut]:
    try: oid = ObjectId(user_id)
    except: return None

    pipeline = [
        {"$match": {"_id": oid}},
        {"$lookup": {"from": CASE_COLLECTION, "localField": "_id", "foreignField": "owner_id", "as": "owned_cases"}},
        {"$lookup": {"from": DOCUMENT_COLLECTION, "localField": "_id", "foreignField": "owner_id", "as": "owned_documents"}},
        {"$addFields": {
            "id": {"$toString": "$_id"},
            "case_count": {"$size": "$owned_cases"},
            "document_count": {"$size": "$owned_documents"}
        }},
        {"$project": {
            "_id": 0, 
            "owned_cases": 0, 
            "owned_documents": 0, 
            "hashed_password": 0
        }}
    ]
    
    result = list(db[USER_COLLECTION].aggregate(pipeline))
    if not result: return None
    return AdminUserOut.model_validate(result[0])

def update_user_details(user_id: str, update_data: UserUpdateRequest, db: Database) -> Optional[AdminUserOut]:
    # PHOENIX FIX: Dump as dict, then explicitly check status
    payload = update_data.model_dump(exclude_unset=True)
    
    # If the frontend sent a status, FORCE it into the payload
    if update_data.status:
        payload['status'] = update_data.status.lower()

    logger.info(f"--- [ADMIN] Updating User {user_id} ---")
    logger.info(f"--- [ADMIN] Final Payload: {payload} ---")

    if not payload:
        return find_user_in_aggregate(user_id, db)

    try:
        updated_user_doc = db.users.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": payload},
            return_document=ReturnDocument.AFTER
        )
        
        if not updated_user_doc:
            logger.error(f"User {user_id} not found during update.")
            raise FileNotFoundError("User not found")
            
        logger.info(f"--- [ADMIN] Success. DB Status is now: {updated_user_doc.get('status')} ---")
        
        return find_user_in_aggregate(user_id, db)
    except Exception as e:
        logger.error(f"Update failed: {e}")
        raise e

def expire_subscriptions(db: Database) -> int:
    now = datetime.utcnow()
    result = db.users.update_many(
        {"subscription_status": "active", "subscription_expiry_date": {"$lt": now}},
        {"$set": {"subscription_status": "expired"}}
    )
    return result.modified_count