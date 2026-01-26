# FILE: backend/app/services/admin_service.py
# PHOENIX PROTOCOL - ADMIN SERVICE V9.0 (UNIFIED LOGIC)
# 1. ADDED: 'update_user_and_subscription' to handle the unified PUT request.
# 2. ADDED: 'get_all_users_with_details' to provide clean data to the new admin UI.
# 3. DEPRECATED: Old, fragmented update/delete methods are no longer used by the new API.

from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone
from pymongo.database import Database
import logging

logger = logging.getLogger(__name__)

class AdminService:
    
    def get_all_organizations(self, db: Database) -> List[Dict[str, Any]]:
        # This function can be simplified or deprecated later, as user objects now contain all data.
        # For now, it provides a compatible output for any other services that might use it.
        org_users = list(db.users.find({"account_type": "ORGANIZATION"}))
        org_list = []
        for user in org_users:
            org_list.append({
                "id": str(user["_id"]),
                "name": user.get("organization_name", user["username"]),
                "owner_id": str(user["_id"]),
                "tier": "TIER_2" if user.get("subscription_tier") == "PRO" else "TIER_1", # Simplified mapping
                "plan": user.get("product_plan", "SOLO_PLAN"),
                "status": user.get("subscription_status", "INACTIVE"),
                "expiry": user.get("subscription_expiry"),
                "created_at": user.get("created_at"),
                "owner_email": user.get("email"),
                "seat_limit": 5 if user.get("product_plan") == "TEAM_PLAN" else 1,
                "seat_count": db.users.count_documents({"org_id": user.get("org_id", user["_id"])}),
            })
        return org_list

    def get_all_users_with_details(self, db: Database) -> List[Dict[str, Any]]:
        """
        Retrieves all users and formats them for the V11.0 Admin Dashboard.
        This is the new standard method for fetching user list data.
        """
        users = list(db.users.find({}).sort("created_at", -1))
        # The UserAdminView model on the frontend will handle parsing, so we can return the raw dicts.
        return users

    def update_user_and_subscription(self, db: Database, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Unified function to update any user attribute, including the new subscription matrix fields.
        This is called by the PUT /admin/users/{user_id} endpoint.
        """
        try:
            oid = ObjectId(user_id)
            logger.info(f"--- [ADMIN V9.0] Updating user {user_id} with data: {update_data}")

            # Ensure 'updated_at' is always set on an update
            if "updated_at" not in update_data:
                update_data["updated_at"] = datetime.now(timezone.utc)

            result = db.users.update_one(
                {"_id": oid},
                {"$set": update_data}
            )

            if result.matched_count == 0:
                logger.warning(f"--- [ADMIN V9.0] Update failed: User {user_id} not found.")
                return None
            
            logger.info(f"--- [ADMIN V9.0] Update successful for {user_id}. Modified count: {result.modified_count}")
            
            # Return the updated document
            return db.users.find_one({"_id": oid})
        except Exception as e:
            logger.error(f"--- [ADMIN V9.0] Exception during user update for {user_id}: {e}")
            return None

    def delete_user_and_data(self, db: Database, user_id: str) -> bool:
        """
        New standard delete function.
        """
        try:
            oid = ObjectId(user_id)
            # Add deletion for all user-related data across collections
            db.cases.delete_many({"user_id": oid})
            db.documents.delete_many({"user_id": oid})
            db.business_profiles.delete_one({"user_id": oid})
            # ... add any other collections as needed ...
            
            result = db.users.delete_one({"_id": oid})
            
            logger.info(f"--- [ADMIN V9.0] Deletion for user {user_id}. Deleted count: {result.deleted_count}")
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"--- [ADMIN V9.0] Exception during user deletion for {user_id}: {e}")
            return False

admin_service = AdminService()