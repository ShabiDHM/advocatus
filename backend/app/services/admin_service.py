# FILE: backend/app/services/admin_service.py
# PHOENIX PROTOCOL - ADMIN SERVICE V2.0 (TENANT AWARE)
# 1. NEW: get_all_organizations() to fetch firms with member counts.
# 2. NEW: update_organization_tier() to handle seat upgrades.
# 3. REFACTOR: Renamed old user-centric methods to '_legacy'.

from typing import List, Optional, Any
from bson import ObjectId
from datetime import datetime

from ..core.db import async_db_instance
from ..models.admin import UserAdminView, UserUpdateRequest
from ..models.organization import OrganizationOut
from ..services.organization_service import organization_service

class AdminService:
    # --- Lazy Connection Properties ---
    @property
    def db(self) -> Any:
        if async_db_instance is None:
            return None 
        return async_db_instance

    @property
    def org_collection(self) -> Any:
        if self.db is None: raise RuntimeError("Database not connected")
        return self.db["organizations"]

    @property
    def user_collection(self) -> Any:
        if self.db is None: raise RuntimeError("Database not connected")
        return self.db["users"]
    
    @property
    def case_collection(self) -> Any:
        if self.db is None: raise RuntimeError("Database not connected")
        return self.db["cases"]

    # --- NEW: Organization Management ---
    
    async def get_all_organizations(self) -> List[OrganizationOut]:
        """
        Fetches all organizations and enriches them with the current member count.
        """
        org_cursor = self.org_collection.find({})
        orgs = await org_cursor.to_list(length=1000)
        
        results = []
        for org_data in orgs:
            org_id = org_data["_id"]
            member_count = await self.user_collection.count_documents({"org_id": org_id})
            
            # Create the Pydantic model and add the dynamic count
            org_out = OrganizationOut(**org_data)
            org_out.current_member_count = member_count
            results.append(org_out)
            
        return results

    async def update_organization_tier(self, org_id: str, tier: str) -> Optional[OrganizationOut]:
        """
        Updates an organization's tier and max_seats.
        """
        seats = 5 if tier == "TIER_2" else 1
        
        result = await self.org_collection.find_one_and_update(
            {"_id": ObjectId(org_id)},
            {
                "$set": {
                    "tier": tier, 
                    "max_seats": seats, 
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )
        
        if not result:
            return None
            
        # Enrich with member count before returning
        member_count = await self.user_collection.count_documents({"org_id": ObjectId(org_id)})
        org_out = OrganizationOut(**result)
        org_out.current_member_count = member_count
        return org_out

    # --- LEGACY: User Management (Kept for now) ---
    
    async def get_all_users_legacy(self) -> List[UserAdminView]:
        users_cursor = self.user_collection.find({})
        users = await users_cursor.to_list(length=1000)
        return [UserAdminView(**user) for user in users]

    async def update_user_details_legacy(self, user_id: str, update_data: UserUpdateRequest) -> Optional[UserAdminView]:
        update_dict = update_data.model_dump(exclude_unset=True)
        
        if not update_dict:
            return await self.user_collection.find_one({"_id": ObjectId(user_id)})
        
        update_dict["updated_at"] = datetime.utcnow()
        
        updated_user = await self.user_collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": update_dict},
            return_document=True
        )
        
        if updated_user:
            return UserAdminView(**updated_user)
        return None

    async def delete_user_and_data_legacy(self, user_id: str) -> bool:
        user_oid = ObjectId(user_id)
        
        # This is a simplified deletion. A robust version would also delete related data.
        # For now, we just delete the user.
        delete_result = await self.user_collection.delete_one({"_id": user_oid})
        
        if delete_result.deleted_count > 0:
            # Also delete their cases
            await self.case_collection.delete_many({"user_id": user_oid})
            return True
        return False

admin_service = AdminService()