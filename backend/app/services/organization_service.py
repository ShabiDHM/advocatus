# FILE: backend/app/services/organization_service.py
# PHOENIX PROTOCOL - ORGANIZATION SERVICE V3.0 (FULL IMPLEMENTATION)
# 1. LOGIC: 'invite_member' now saves a unique token and expiry date to the user document.
# 2. LOGIC: Added 'accept_invitation' to verify a token, set a password, and activate the user.
# 3. INTEGRATION: Calls the real 'email_service' to dispatch an HTML invitation.

from typing import List, Optional, Dict
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

class OrganizationService:

    def get_organization_for_user(self, db: Database, user: UserInDB) -> Optional[Dict]:
        org_id = getattr(user, 'org_id', None)
        if not org_id:
            profile = db.business_profiles.find_one({"user_id": user.id})
            if profile:
                return { "id": str(user.id), "name": profile.get("firm_name") or user.username, "plan": "TIER_1", "status": user.subscription_status, "seat_limit": 1, "seat_count": 1, "created_at": user.created_at }
            return None
            
        try: oid = ObjectId(org_id)
        except: return None
        
        profile = db.business_profiles.find_one({"user_id": oid}) or {}
        owner = db.users.find_one({"_id": oid}) or {}

        return { "id": str(oid), "name": profile.get("firm_name") or owner.get("username", "Unknown Firm"), "plan": "TIER_2" if owner.get("subscription_status") == "ACTIVE" else "TIER_1", "status": owner.get("subscription_status"), "owner_email": owner.get("email"), "seat_limit": 5, "seat_count": db.users.count_documents({"org_id": oid}), "created_at": owner.get("created_at") }

    def get_members(self, db: Database, current_user: UserInDB) -> List[Dict]:
        org_id = getattr(current_user, 'org_id', None) or current_user.id
        try: oid = ObjectId(org_id)
        except: return []

        users_cursor = db.users.find({"$or": [{"org_id": oid}, {"_id": oid}]})
        return [UserOut.model_validate(u).model_dump() for u in users_cursor]

    def invite_member(self, db: Database, owner: UserInDB, invitee_email: str):
        org_id = getattr(owner, 'org_id', None) or owner.id
        
        current_members_count = db.users.count_documents({"org_id": org_id, "status": "active"})
        if current_members_count >= 5: # Assuming TIER_2 has 5 seats
            raise HTTPException(status_code=403, detail="Seat limit reached.")

        existing_user = db.users.find_one({"email": invitee_email})
        if existing_user and existing_user.get("org_id"):
            raise HTTPException(status_code=409, detail="User is already part of an organization.")

        invitation_token = str(uuid.uuid4())
        token_expiry = datetime.now(timezone.utc) + timedelta(days=3)
        
        update_fields = {
            "org_id": org_id,
            "invitation_token": invitation_token,
            "invitation_token_expiry": token_expiry,
            "status": "pending_invite"
        }

        if existing_user:
            db.users.update_one({"_id": existing_user["_id"]}, {"$set": update_fields})
        else:
            db.users.insert_one({
                "email": invitee_email,
                "username": invitee_email.split('@')[0],
                "hashed_password": None,
                "role": "STANDARD",
                "subscription_status": "INACTIVE",
                **update_fields
            })
            
        invite_link = f"{settings.FRONTEND_URL}/accept-invite?token={invitation_token}"
        
        # Dispatch the actual email
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

organization_service = OrganizationService()