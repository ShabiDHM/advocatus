# FILE: backend/app/services/admin_service.py
# DEFINITIVE VERSION 2.0 (LOGIC RELOCATION):
# 1. REPLACED: The old, simplistic 'get_all_users' function has been completely
#    replaced with the powerful MongoDB aggregation pipeline.
# 2. This ensures the correct, data-rich logic is executed when the admin endpoint
#    is called, curing the primary "missing data" disease.

from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict, Any
from pymongo.database import Database
from pymongo import ReturnDocument

from ..models.admin import SubscriptionUpdate, AdminUserOut
from ..models.user import UserInDB
from ..core.db import get_collection

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
                "let": { "user_id_str": { "$toString": "$_id" } },
                "pipeline": [
                    { "$match": { "$expr": { "$eq": ["$owner_id", "$$user_id_str"] } } }
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
        
    # We must run the full aggregation on the single updated user to get the counts
    # This is less efficient but ensures data consistency on the frontend after an update.
    user_list = get_all_users(db)
    for user in user_list:
        if str(user.get('_id')) == user_id:
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