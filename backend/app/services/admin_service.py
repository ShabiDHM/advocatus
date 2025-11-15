# FILE: backend/app/services/admin_service.py

from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict, Any
from pymongo.database import Database
from pymongo import ReturnDocument

from ..models.admin import SubscriptionUpdate, AdminUserOut
from ..models.user import UserInDB
# PHOENIX PROTOCOL CURE: Removed the import of the deprecated 'get_collection' function.

USER_COLLECTION = "users"
CASE_COLLECTION = "cases"
DOCUMENT_COLLECTION = "documents"

def get_all_users(db: Database) -> List[Dict[str, Any]]:
    """
    Retrieves all users with aggregated details like case and document counts
    using a MongoDB aggregation pipeline. This is the definitive function for the admin dashboard.
    """
    pipeline = [
        {
            "$lookup": {
                "from": CASE_COLLECTION,
                "localField": "_id",
                "foreignField": "owner_id",
                "as": "owned_cases"
            }
        },
        {
            "$lookup": {
                "from": DOCUMENT_COLLECTION,
                "localField": "_id",
                "foreignField": "owner_id",
                "as": "owned_documents"
            }
        },
        {
            "$addFields": {
                "id": "$_id",
                "created_at": { "$toDate": "$_id" },
                "case_count": { "$size": "$owned_cases" },
                "document_count": { "$size": "$owned_documents" }
            }
        },
        {
            "$project": {
                "owned_cases": 0,
                "owned_documents": 0,
                "hashed_password": 0
            }
        }
    ]
    # PHOENIX PROTOCOL CURE: Access the collection directly from the 'db' instance.
    users_data = list(db[USER_COLLECTION].aggregate(pipeline))
    return users_data


def get_user_by_id(user_id: str, db: Database) -> Optional[UserInDB]:
    """Retrieves a single user by their ID."""
    user_doc = db.users.find_one({"_id": ObjectId(user_id)})
    if user_doc:
        return UserInDB(**user_doc)
    return None

def update_user_subscription(user_id: str, sub_data: SubscriptionUpdate, db: Database) -> AdminUserOut:
    """Manually updates a user's subscription details."""
    update_data = sub_data.model_dump(exclude_unset=True)
    
    updated_user_doc = db.users.find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )
    
    if not updated_user_doc:
        raise FileNotFoundError("User not found")
        
    # PHOENIX PROTOCOL FIX: Corrected user ID comparison logic
    # Convert both IDs to ObjectId for proper comparison, or compare string representations consistently
    user_list = get_all_users(db)
    for user in user_list:
        user_obj_id = user.get('_id')
        # Compare ObjectId with ObjectId, or string with string
        if (isinstance(user_obj_id, ObjectId) and user_obj_id == ObjectId(user_id)) or str(user_obj_id) == user_id:
            return AdminUserOut.model_validate(user)
    
    raise FileNotFoundError("User not found after update and re-aggregation.")


def expire_subscriptions(db: Database) -> int:
    """
    Finds all active users whose expiry date is in the past and sets their status to 'expired'.
    Returns the number of users whose subscriptions were expired.
    """
    now = datetime.utcnow()
    result = db.users.update_many(
        {
            "subscription_status": "active",
            "subscription_expiry_date": {"$lt": now}
        },
        {"$set": {"subscription_status": "expired"}}
    )
    return result.modified_count