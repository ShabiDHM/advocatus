# FILE: backend/app/services/admin_service.py
# PHOENIX PROTOCOL - DEFINITIVE AGGREGATION CURE
# 1. DIAGNOSIS: The aggregation pipeline's '$addFields' stage was redundantly overwriting the 'created_at' field. This operation is fragile and was causing the pipeline to fail silently, returning an empty list.
# 2. CURE: Removed the '"created_at": {"$toDate": "$_id"}' transformation from the '$addFields' stage.
# 3. MECHANISM: The aggregation now passes the original, correct 'created_at' field from the user document directly to the Pydantic response model, which correctly handles it. This makes the pipeline simpler and more robust.
# 4. RESULT: The aggregation will now correctly return all user documents, curing the "0 users" bug on the admin dashboard.

from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict, Any
from pymongo.database import Database
from pymongo import ReturnDocument

from ..models.admin import SubscriptionUpdate, AdminUserOut
from ..models.user import UserInDB

USER_COLLECTION = "users"
CASE_COLLECTION = "cases"
DOCUMENT_COLLECTION = "documents"

def get_all_users(db: Database) -> List[Dict[str, Any]]:
    pipeline = [
        {"$lookup": {"from": CASE_COLLECTION, "localField": "_id", "foreignField": "owner_id", "as": "owned_cases"}},
        {"$lookup": {"from": DOCUMENT_COLLECTION, "localField": "_id", "foreignField": "owner_id", "as": "owned_documents"}},
        # PHOENIX CURE: Removed the fragile 'created_at' transformation.
        {"$addFields": {"case_count": {"$size": "$owned_cases"}, "document_count": {"$size": "$owned_documents"}}},
        {"$project": {"owned_cases": 0, "owned_documents": 0, "hashed_password": 0}}
    ]
    users_data = list(db[USER_COLLECTION].aggregate(pipeline))
    return users_data

def get_user_by_id(user_id: str, db: Database) -> Optional[UserInDB]:
    user_doc = db.users.find_one({"_id": ObjectId(user_id)})
    if user_doc:
        return UserInDB(**user_doc)
    return None

def find_user_in_aggregate(user_id: str, db: Database) -> Optional[AdminUserOut]:
    """Helper to find a specific user from the full aggregation list after an update."""
    user_list = get_all_users(db)
    for user_data in user_list:
        if str(user_data.get('_id')) == user_id:
            return AdminUserOut.model_validate(user_data)
    return None

def update_user_details(user_id: str, update_data: SubscriptionUpdate, db: Database) -> Optional[AdminUserOut]:
    """Updates general user details like role, status, and email."""
    update_dict = update_data.model_dump(exclude_unset=True)
    
    allowed_fields = {"role", "status", "email", "admin_notes"}
    payload = {k: v for k, v in update_dict.items() if k in allowed_fields}

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

def update_user_subscription(user_id: str, sub_data: SubscriptionUpdate, db: Database) -> Optional[AdminUserOut]:
    """Manually updates a user's subscription-specific details."""
    update_data = sub_data.model_dump(exclude_unset=True, exclude={"role", "status", "email"})

    if not update_data:
         return find_user_in_aggregate(user_id, db)

    updated_user_doc = db.users.find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": update_data},
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