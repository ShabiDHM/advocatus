# FILE: backend/app/services/organization_service.py
# PHOENIX PROTOCOL - ORGANIZATION SERVICE V2.2 (AUTO-SYNC PATCH)
# 1. FIXED: Added auto-sync in 'get_organization_for_user' to align Org Tier with Owner Plan.


from typing import List, Optional, Dict
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from pymongo.database import Database
from fastapi import HTTPException
import uuid

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.organization import OrganizationInDB
from app.models.user import UserInDB, UserOut, ProductPlan, PLAN_LIMITS
from app.services import email_service

TIER_LIMITS = {
    "DEFAULT": 1,
    "GROWTH": 10
}

class OrganizationService:

    def _ensure_organization_sync(self, db: Database, owner_id: ObjectId) -> Dict:
        org_doc = db.organizations.find_one({"_id": owner_id})
        owner = db.users.find_one({"_id": owner_id}) or {}
        
        # Determine intended tier based on User.product_plan
        is_team = owner.get("product_plan") == ProductPlan.TEAM_PLAN
        intended_tier = "GROWTH" if is_team else "DEFAULT"
        intended_limit = TIER_LIMITS.get(intended_tier, 1)

        if not org_doc:
            profile = db.business_profiles.find_one({"user_id": owner_id}) or {}
            actual_count = db.users.count_documents({"org_id": owner_id})
            
            new_org = OrganizationInDB(
                name=profile.get("firm_name") or owner.get("username", "Organization"),
                owner_email=owner.get("email"),
                plan_tier=intended_tier,
                user_limit=intended_limit,
                current_active_users=actual_count,
                status=owner.get("subscription_status", "TRIAL")
            )
            
            org_data = new_org.model_dump(by_alias=True)
            org_data["_id"] = owner_id 
            db.organizations.update_one({"_id": owner_id}, {"$set": org_data}, upsert=True)
            return org_data
        
        # PHOENIX FIX: If Org doc exists but Tier is outdated compared to User Plan, AUTO-UPGRADE
        if org_doc.get("plan_tier") != intended_tier:
            db.organizations.update_one(
                {"_id": owner_id},
                {"$set": {"plan_tier": intended_tier, "user_limit": intended_limit}}
            )
            org_doc["plan_tier"] = intended_tier
            org_doc["user_limit"] = intended_limit
            
        return org_doc

    def get_organization_for_user(self, db: Database, user: UserInDB) -> Optional[Dict]:
        org_id_str = getattr(user, 'org_id', None)
        target_oid = user.id if not org_id_str else ObjectId(org_id_str)
        
        org_doc = self._ensure_organization_sync(db, target_oid)
        
        return {
            "id": str(target_oid),
            "name": org_doc.get("name"),
            "plan_tier": org_doc.get("plan_tier", "DEFAULT"),
            "user_limit": org_doc.get("user_limit", 1),
            "current_active_users": org_doc.get("current_active_users", 0),
            "created_at": org_doc.get("created_at")
        }

    def update_organization_plan(self, db: Database, org_id: ObjectId, new_plan_tier: str) -> bool:
        new_limit = TIER_LIMITS.get(new_plan_tier, 1)
        db.organizations.update_one(
            {"_id": org_id},
            {"$set": {"plan_tier": new_plan_tier, "user_limit": new_limit, "updated_at": datetime.now(timezone.utc)}}
        )
        return True

    def increment_active_users(self, db: Database, org_id: ObjectId):
        db.organizations.update_one({"_id": org_id}, {"$inc": {"current_active_users": 1}})

    def decrement_active_users(self, db: Database, org_id: ObjectId):
        db.organizations.update_one({"_id": org_id, "current_active_users": {"$gt": 0}}, {"$inc": {"current_active_users": -1}})

    def get_members(self, db: Database, current_user: UserInDB) -> List[Dict]:
        org_id = getattr(current_user, 'org_id', None) or current_user.id
        users_cursor = db.users.find({"$or": [{"org_id": ObjectId(org_id)}, {"_id": ObjectId(org_id)}]})
        return [UserOut.model_validate(u).model_dump() for u in users_cursor]

    def invite_member(self, db: Database, owner: UserInDB, invitee_email: str):
        org_id = getattr(owner, 'org_id', None) or owner.id
        org_doc = self._ensure_organization_sync(db, ObjectId(org_id))
        if org_doc.get("current_active_users", 0) >= org_doc.get("user_limit", 1):
            raise HTTPException(status_code=403, detail="Limit Reached")
        
        invitation_token = str(uuid.uuid4())
        db.users.insert_one({
            "email": invitee_email, "username": invitee_email.split('@')[0], "role": "STANDARD",
            "org_id": ObjectId(org_id), "status": "pending_invite", "invitation_token": invitation_token,
            "created_at": datetime.now(timezone.utc)
        })
        self.increment_active_users(db, ObjectId(org_id))
        return {"message": "Success"}

    def remove_member(self, db: Database, owner: UserInDB, member_id: str):
        m_oid = ObjectId(member_id)
        org_id = getattr(owner, 'org_id', None) or owner.id
        db.users.delete_one({"_id": m_oid, "org_id": ObjectId(org_id)})
        self.decrement_active_users(db, ObjectId(org_id))
        return {"message": "Removed"}

organization_service = OrganizationService()