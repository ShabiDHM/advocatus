# FILE: backend/app/services/admin_service.py
# PHOENIX PROTOCOL - GATEKEEPER LOGIC FIX
# 1. FIX: The 'update_user_details' function no longer filters out 'subscription_status'.
# 2. BEHAVIOR: The function now correctly processes all fields from the new UserUpdateRequest model.
# 3. RESULT: Administrators can now successfully change a user's status from 'INACTIVE' to 'ACTIVE'.

from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict, Any
from pymongo.database import Database
from pymongo import ReturnDocument

# PHOENIX FIX: Import the new unified model
from ..models.admin import AdminUserOut, UserUpdateRequest
from ..models.user import UserInDB

USER_COLLECTION = "users"
CASE_COLLECTION = "cases"
DOCUMENT_COLLECTION = "documents"

def get_all_users(db: Database) -> List[Dict[str, Any]]:
    pipeline = [
        {"$lookup": {"from": CASE_COLLECTION, "localField": "_id", "foreignField": "owner_id", "as": "owned_cases"}},
        {"$lookup": {"from": DOCUMENT_COLLECTION, "localField": "_id", "foreignField": "owner_id", "as": "owned_documents"}},
        {"$addFields": {"case_count": {"$size": "$owned_cases"}, "document_count": {"$size": "$owned_documents"}}},
        {"$project": {"owned_cases": 0, "owned_documents": 0, "hashed_password": 0}}
    ]
    users_data = list(db[USER_COLLECTION].aggregate(pipeline))
    return users_data

def find_user_in_aggregate(user_id: str, db: Database) -> Optional[AdminUserOut]:
    user_list = get_all_users(db)
    for user_data in user_list:
        if str(user_data.get('_id')) == user_id:
            return AdminUserOut.model_validate(user_data)
    return None

# PHOENIX FIX: This function now handles all updates, including the critical subscription_status.
def update_user_details(user_id: str, update_data: UserUpdateRequest, db: Database) -> Optional[AdminUserOut]:
    """Updates all user details sent from the admin panel."""
    
    # PHOENIX FIX: The faulty filtering is removed. We now process all provided fields.
    payload = update_data.model_dump(exclude_unset=True)

    if not payload:
        # If the payload is empty, do nothing and return the current user state.
        return find_user_in_aggregate(user_id, db)

    updated_user_doc = db.users.find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": payload},
        return_document=ReturnDocument.AFTER
    )
    
    if not updated_user_doc:
        raise FileNotFoundError("User not found")
        
    # Return the updated user data using the consistent aggregation pipeline
    return find_user_in_aggregate(user_id, db)

# PHOENIX FIX: This function is no longer needed and can be considered deprecated.
def update_user_subscription(user_id: str, sub_data: UserUpdateRequest, db: Database) -> Optional[AdminUserOut]:
    """DEPRECATED: This logic is now handled by update_user_details."""
    return update_user_details(user_id, sub_data, db)

def expire_subscriptions(db: Database) -> int:
    now = datetime.utcnow()
    result = db.users.update_many(
        {"subscription_status": "active", "subscription_expiry_date": {"$lt": now}},
        {"$set": {"subscription_status": "expired"}}
    )
    return result.modified_count