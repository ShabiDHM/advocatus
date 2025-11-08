# backend/app/services/admin_service.py
# DEFINITIVE VERSION V1.1: Corrects relative imports to resolve ModuleNotFoundError.

from bson import ObjectId
from datetime import datetime
from typing import List, Optional
from pymongo.database import Database
from pymongo import ReturnDocument

# --- CORRECTED IMPORTS ---
# Use relative imports (..) to traverse up from the 'services' directory to the 'app' root.
from ..models.admin import SubscriptionUpdate, UserAdminView
from ..models.user import UserInDB

def get_all_users(db: Database) -> List[UserAdminView]:
    """Retrieves a list of all users for the admin panel."""
    users_cursor = db.users.find({})
    return [UserAdminView.model_validate(user) for user in users_cursor]

def get_user_by_id(user_id: str, db: Database) -> Optional[UserInDB]:
    """Retrieves a single user by their ID."""
    user_doc = db.users.find_one({"_id": ObjectId(user_id)})
    if user_doc:
        return UserInDB(**user_doc)
    return None

def update_user_subscription(user_id: str, sub_data: SubscriptionUpdate, db: Database) -> UserAdminView:
    """Manually updates a user's subscription details."""
    update_data = sub_data.model_dump(exclude_unset=True)
    
    updated_user_doc = db.users.find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )
    
    if not updated_user_doc:
        raise FileNotFoundError("User not found")
        
    return UserAdminView.model_validate(updated_user_doc)

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