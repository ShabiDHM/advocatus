# FILE: backend/app/services/admin_service.py
# PHOENIX PROTOCOL - DEFINITIVE AGGREGATION FIX
# 1. DIAGNOSIS: The aggregation pipeline was returning documents with '_id: ObjectId' which caused a response validation error.
# 2. FIX: The pipeline now uses '$addFields' to create a string 'id' from the '_id' and '$project' to remove the original '_id'.
# 3. RESULT: The data shape produced by this service now perfectly matches the API response model, resolving the "0 users" bug.

from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict, Any
from pymongo.database import Database
from pymongo import ReturnDocument

from ..models.admin import UserUpdateRequest, AdminUserOut
from ..models.user import UserInDB

USER_COLLECTION = "users"
CASE_COLLECTION = "cases"
DOCUMENT_COLLECTION = "documents"

def get_all_users(db: Database) -> List[Dict[str, Any]]:
    pipeline = [
        {"$lookup": {"from": CASE_COLLECTION, "localField": "_id", "foreignField": "owner_id", "as": "owned_cases"}},
        {"$lookup": {"from": DOCUMENT_COLLECTION, "localField": "_id", "foreignField": "owner_id", "as": "owned_documents"}},
        # PHOENIX FIX: Create the 'id' field as a string and ensure counts exist.
        {"$addFields": {
            "id": {"$toString": "$_id"},
            "case_count": {"$size": "$owned_cases"},
            "document_count": {"$size": "$owned_documents"}
        }},
        # PHOENIX FIX: Project the final, clean shape. Remove the original '_id' and temporary fields.
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
    # This function now works because get_all_users returns the correct shape
    user_list = get_all_users(db)
    for user_data in user_list:
        if user_data.get('id') == user_id:
            return AdminUserOut.model_validate(user_data)
    return None

def update_user_details(user_id: str, update_data: UserUpdateRequest, db: Database) -> Optional[AdminUserOut]:
    payload = update_data.model_dump(exclude_unset=True)
    if not payload:
        return find_user_in_aggregate(user_id, db)

    updated_user_doc = db.users.find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": payload},
        return_document=ReturnDocument.AFTER
    )
    
    if not updated_user_doc:
        raise FileNotFoundError("User not found")
        
    return find_user_in_aggregate(user_id, db)

def expire_subscriptions(db: Database) -> int:
    now = datetime.utcnow()
    result = db.users.update_many(
        {"subscription_status": "active", "subscription_expiry_date": {"$lt": now}},
        {"$set": {"subscription_status": "expired"}}
    )
    return result.modified_count