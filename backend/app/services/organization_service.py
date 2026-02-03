# FILE: backend/app/services/organization_service.py
# PHOENIX PROTOCOL - ORGANIZATION SERVICE V2.0 (TIER EXPANSION)
# 1. IMPLEMENTED: 'Capacity Manager' logic (increment/decrement/upgrade).
# 2. MIGRATION: Auto-syncs legacy implicit orgs to new 'organizations' collection.
# 3. SAFETY: strict checks on invites and downgrades.

from typing import List, Optional, Dict, Literal
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from pymongo.database import Database
from fastapi import HTTPException
import uuid

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.organization import OrganizationInDB, OrganizationOut
from app.models.user import UserInDB, UserOut
from app.services import email_service

# Configuration for Tiers
TIER_LIMITS = {
    "DEFAULT": 5,
    "GROWTH": 10  # As per mandate
}

class OrganizationService:

    def _ensure_organization_sync(self, db: Database, owner_id: ObjectId) -> Dict:
        """
        Internal Helper: Ensures an Organization document exists for the given owner.
        Syncs state from legacy 'business_profiles' and 'users' if missing.
        """
        org_doc = db.organizations.find_one({"_id": owner_id})
        
        if not org_doc:
            # PHOENIX MIGRATION: Create Organization doc from legacy data
            profile = db.business_profiles.find_one({"user_id": owner_id}) or {}
            owner = db.users.find_one({"_id": owner_id}) or {}
            
            # Determine initial tier based on legacy subscription_status
            is_active = owner.get("subscription_status") == "ACTIVE"
            initial_tier = "GROWTH" if is_active else "DEFAULT"
            limit = TIER_LIMITS.get(initial_tier, 5)
            
            # Count actual users for initial sync
            actual_count = db.users.count_documents({"org_id": owner_id})
            
            new_org = OrganizationInDB(
                name=profile.get("firm_name") or owner.get("username", "Organization"),
                owner_email=owner.get("email"),
                plan_tier=initial_tier,
                user_limit=limit,
                current_active_users=actual_count,
                status=owner.get("subscription_status", "TRIAL")
            )
            
            # Force ID to match Owner ID for 1:1 mapping simplicity in this architecture
            org_data = new_org.model_dump(by_alias=True)
            org_data["_id"] = owner_id 
            
            db.organizations.update_one(
                {"_id": owner_id}, 
                {"$set": org_data}, 
                upsert=True
            )
            return org_data
            
        return org_doc

    def get_organization_for_user(self, db: Database, user: UserInDB) -> Optional[Dict]:
        """
        Retrieves organization details. 
        Auto-syncs if the explicit Organization document is missing.
        """
        # Determine the Organization ID (Owner's ID)
        org_id_str = getattr(user, 'org_id', None)
        
        if not org_id_str:
            # User is likely the owner
            target_oid = user.id
        else:
            try:
                target_oid = ObjectId(org_id_str)
            except:
                return None

        # Ensure the Organization document exists (Sync/Migration)
        org_doc = self._ensure_organization_sync(db, target_oid)
        
        # Return formatted data matching OrganizationOut
        return {
            "id": str(target_oid),
            "name": org_doc.get("name"),
            "owner_email": org_doc.get("owner_email"),
            "plan_tier": org_doc.get("plan_tier", "DEFAULT"),
            "status": org_doc.get("status"),
            
            # New Fields
            "user_limit": org_doc.get("user_limit", 5),
            "current_active_users": org_doc.get("current_active_users", 0),
            
            # Backward Compatibility for Frontend
            "seat_limit": org_doc.get("user_limit", 5),
            "seat_count": org_doc.get("current_active_users", 0),
            
            "created_at": org_doc.get("created_at")
        }

    def update_organization_plan(self, db: Database, org_id: ObjectId, new_plan_tier: str) -> bool:
        """
        Updates the plan tier and adjusts user limits.
        Prevents downgrades if current usage exceeds new limit.
        """
        new_limit = TIER_LIMITS.get(new_plan_tier)
        if new_limit is None:
            raise HTTPException(status_code=400, detail=f"Invalid plan tier: {new_plan_tier}")

        # Get current status
        org = self._ensure_organization_sync(db, org_id)
        current_users = org.get("current_active_users", 0)

        # CRITICAL CHECK: Downgrade Safety
        if current_users > new_limit:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot switch to {new_plan_tier} (Limit: {new_limit}). You have {current_users} active users."
            )

        db.organizations.update_one(
            {"_id": org_id},
            {
                "$set": {
                    "plan_tier": new_plan_tier,
                    "user_limit": new_limit,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return True

    def increment_active_users(self, db: Database, org_id: ObjectId):
        """Atomically increments the active user counter."""
        db.organizations.update_one(
            {"_id": org_id},
            {"$inc": {"current_active_users": 1}}
        )

    def decrement_active_users(self, db: Database, org_id: ObjectId):
        """Atomically decrements the active user counter."""
        # Prevent going below zero just in case
        db.organizations.update_one(
            {"_id": org_id, "current_active_users": {"$gt": 0}},
            {"$inc": {"current_active_users": -1}}
        )

    def get_members(self, db: Database, current_user: UserInDB) -> List[Dict]:
        org_id = getattr(current_user, 'org_id', None) or current_user.id
        try: oid = ObjectId(org_id)
        except: return []

        users_cursor = db.users.find({"$or": [{"org_id": oid}, {"_id": oid}]})
        return [UserOut.model_validate(u).model_dump() for u in users_cursor]

    def invite_member(self, db: Database, owner: UserInDB, invitee_email: str):
        # 1. Identify Organization ID
        org_id = getattr(owner, 'org_id', None) or owner.id
        
        # 2. Ensure Organization State
        org_doc = self._ensure_organization_sync(db, org_id)
        
        # 3. CRITICAL CHECK: Check Capacity using the Organization Document
        current_active = org_doc.get("current_active_users", 0)
        limit = org_doc.get("user_limit", 5)
        
        if current_active >= limit:
            raise HTTPException(
                status_code=403, 
                detail=f"Plan limit reached ({current_active}/{limit}). Upgrade to invite more users."
            )

        # 4. Check for existing user
        existing_user = db.users.find_one({"email": invitee_email})
        if existing_user and existing_user.get("org_id"):
            raise HTTPException(status_code=409, detail="User is already part of an organization.")

        # 5. Prepare Invite Data
        invitation_token = str(uuid.uuid4())
        token_expiry = datetime.now(timezone.utc) + timedelta(days=3)
        
        update_fields = {
            "org_id": org_id,
            "invitation_token": invitation_token,
            "invitation_token_expiry": token_expiry,
            "status": "pending_invite"
        }

        # 6. Execute Invite (Upsert User)
        if existing_user:
            db.users.update_one({"_id": existing_user["_id"]}, {"$set": update_fields})
        else:
            db.users.insert_one({
                "email": invitee_email,
                "username": invitee_email.split('@')[0],
                "hashed_password": None,
                "role": "STANDARD",
                "subscription_status": "INACTIVE",
                "created_at": datetime.now(timezone.utc),
                **update_fields
            })
            
        # 7. UPDATE STATE: Atomically Increment Counter
        # We count pending invites as occupying a seat
        self.increment_active_users(db, org_id)

        # 8. Send Email
        invite_link = f"{settings.FRONTEND_URL}/accept-invite?token={invitation_token}"
        subject = f"Ftesë për t'u bashkuar me {owner.username} në Juristi.tech"
        body = f"""
        <p>Përshëndetje,</p>
        <p>Jeni ftuar nga <b>{owner.username}</b> për t'u bashkuar me organizatën e tyre në Juristi.tech.</p>
        <p>Për të pranuar ftesën dhe për të krijuar llogarinë tuaj, ju lutemi klikoni butonin më poshtë:</p>
        <a href="{invite_link}" style="display: inline-block; padding: 12px 24px; background-color: #2563EB; color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">Prano Ftesën</a>
        <p style="font-size: 12px; color: #888;">Nëse nuk e prisnit këtë ftesë, mund ta injoroni këtë email.</p>
        """
        html_content = email_service._create_html_wrapper("Ftesë Bashkëpunimi", body)
        email_service.send_email_sync(invitee_email, subject, html_content)
        
        return {"message": f"Invitation successfully sent to {invitee_email}."}

    def accept_invitation(self, db: Database, token: str, password: str, username: str):
        user = db.users.find_one({
            "invitation_token": token,
            "invitation_token_expiry": {"$gt": datetime.now(timezone.utc)}
        })

        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired invitation token.")

        if db.users.find_one({"username": username}):
            raise HTTPException(status_code=409, detail="Username is already taken.")

        hashed_password = get_password_hash(password)
        db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "hashed_password": hashed_password,
                "username": username,
                "status": "active",
                "subscription_status": "ACTIVE",
                "invitation_token": None,
                "invitation_token_expiry": None
            }}
        )
        return {"message": "Account activated successfully. You can now log in."}
    
    def remove_member(self, db: Database, owner: UserInDB, member_id: str):
        try:
            m_oid = ObjectId(member_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid Member ID")

        member = db.users.find_one({"_id": m_oid})
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        
        org_id = getattr(owner, 'org_id', None) or owner.id
        if str(member.get("org_id")) != str(org_id):
             raise HTTPException(status_code=403, detail="Member does not belong to your organization.")
        
        # Transfer Assets
        db.cases.update_many({"owner_id": m_oid}, {"$set": {"owner_id": owner.id}})
        db.cases.update_many({"user_id": m_oid}, {"$set": {"user_id": owner.id}})
        db.documents.update_many({"owner_id": m_oid}, {"$set": {"owner_id": owner.id}})
        
        # Remove User
        db.users.delete_one({"_id": m_oid})
        
        # UPDATE STATE: Atomically Decrement Counter
        self.decrement_active_users(db, ObjectId(org_id))
        
        return {"message": "Member removed. Data transferred to Owner."}

# --- CRITICAL INSTANTIATION ---
organization_service = OrganizationService()