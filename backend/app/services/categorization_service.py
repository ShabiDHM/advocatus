# FILE: backend/app/services/organization_service.py
# PHOENIX PROTOCOL - ORGANIZATION SERVICE V1.5 (METHOD RESTORATION)
# 1. FIX: Re-adding 'join_organization' which was missing/unrecognized.
# 2. STATUS: Final Logic.

from typing import List, Optional, Any
from bson import ObjectId
from datetime import datetime
from fastapi import HTTPException
from app.core.db import async_db_instance
from app.models.organization import OrganizationInDB
from app.models.user import UserOut, UserInDB
from app.core.security import get_password_hash

class OrganizationService:
    # --- Lazy Connection Properties ---
    @property
    def db(self) -> Any:
        if async_db_instance is None:
            return None 
        return async_db_instance

    @property
    def org_collection(self) -> Any:
        if self.db is None:
            raise RuntimeError("Database not connected")
        return self.db["organizations"]

    @property
    def user_collection(self) -> Any:
        if self.db is None:
            raise RuntimeError("Database not connected")
        return self.db["users"]

    # --- Business Logic ---

    async def create_organization_for_user(self, user_id: str, user_name: str) -> OrganizationInDB:
        org_entry = OrganizationInDB(
            name=f"{user_name}'s Firm",
            owner_id=ObjectId(user_id), # type: ignore
            tier="TIER_1",
            max_seats=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        org_dict = org_entry.model_dump(by_alias=True, exclude={"id"})
        new_org = await self.org_collection.insert_one(org_dict)
        
        created_org = await self.get_organization_by_id(str(new_org.inserted_id))
        if not created_org:
            raise HTTPException(status_code=500, detail="Failed to create organization")
        return created_org

    async def get_organization_by_id(self, org_id: str) -> Optional[OrganizationInDB]:
        if not org_id:
            return None
        try:
            oid = ObjectId(org_id)
        except:
            return None
            
        org = await self.org_collection.find_one({"_id": oid})
        if org:
            return OrganizationInDB(**org)
        return None

    async def get_members(self, org_id: str) -> List[UserOut]:
        try:
            oid = ObjectId(org_id)
        except:
            return []

        users_cursor = self.user_collection.find({"org_id": oid})
        users = await users_cursor.to_list(length=100)
        return [UserOut(**u) for u in users]

    async def check_seat_availability(self, org_id: str) -> bool:
        org = await self.get_organization_by_id(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        current_count = await self.user_collection.count_documents({"org_id": ObjectId(org_id)})
        
        if current_count >= org.max_seats:
            return False
        return True

    async def upgrade_tier(self, org_id: str, new_tier: str):
        seats = 5 if new_tier == "TIER_2" else 1
        await self.org_collection.update_one(
            {"_id": ObjectId(org_id)},
            {"$set": {"tier": new_tier, "max_seats": seats, "updated_at": datetime.utcnow()}}
        )

    async def join_organization(self, org_id: str, email: str, username: str, password: str) -> UserInDB:
        """
        Registers a new user directly into an organization via invite token.
        """
        # 1. Final Gatekeeper Check
        if not await self.check_seat_availability(org_id):
             raise HTTPException(status_code=403, detail="Organization is full. Ask admin to upgrade.")
        
        # 2. Check if user already exists
        existing = await self.user_collection.find_one({"email": email})
        if existing:
             raise HTTPException(status_code=400, detail="Email already registered")

        # 3. Create Member User
        hashed = get_password_hash(password)
        new_user_data = UserInDB(
            username=username,
            email=email,
            hashed_password=hashed,
            role="STANDARD",
            org_id=ObjectId(org_id), # type: ignore
            org_role="MEMBER",
            status="active",
            subscription_status="ACTIVE",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        user_dict = new_user_data.model_dump(by_alias=True, exclude={"id"})
        result = await self.user_collection.insert_one(user_dict)
        
        new_user_data.id = result.inserted_id
        return new_user_data

organization_service = OrganizationService()