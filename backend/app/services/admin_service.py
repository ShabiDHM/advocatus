# FILE: backend/app/services/admin_service.py
# PHOENIX PROTOCOL - ADMIN SERVICE V5.0 (SYNC ARCHITECTURE)
# 1. FIX: Converted to synchronous 'def' to match PyMongo driver.
# 2. FIX: Added explicit 'None' checks to resolve Pylance subscript errors.
# 3. STATUS: 100% Type Safe.

from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone
from pymongo.database import Database

from ..models.user import UserInDB
from ..models.admin import UserAdminView, UserUpdateRequest

class AdminService:
    
    # --- ORGANIZATION MANAGEMENT ---

    def get_all_organizations(self, db: Database) -> List[Dict[str, Any]]:
        """
        Fetches all organizations/tenants.
        Aggregates Users + Business Profiles to form "Organizations".
        """
        orgs = []
        
        # Pipeline to merge User owner with Business Profile
        pipeline = [
            {"$match": {"role": {"$ne": "ADMIN"}}},
            {"$lookup": {
                "from": "business_profiles",
                "localField": "_id",
                "foreignField": "user_id",
                "as": "profile"
            }},
            {"$unwind": {"path": "$profile", "preserveNullAndEmptyArrays": True}},
            {"$sort": {"created_at": -1}}
        ]
        
        # Synchronous execution
        users = list(db.users.aggregate(pipeline))

        for user in users:
            if not user: continue
            
            profile = user.get("profile") or {}
            org_id = user.get("org_id") or user.get("_id")
            
            sub_status = user.get("subscription_status", "TRIAL")
            
            org_data = {
                "id": str(org_id),
                "name": profile.get("firm_name") or profile.get("company_name") or user.get("username", "Unknown"),
                "plan": "TIER_2" if sub_status == "ACTIVE" else "TIER_1", 
                "status": sub_status,
                "created_at": user.get("created_at"),
                "owner_email": user.get("email"),
                "seat_limit": 5 if sub_status == "ACTIVE" else 1,
                "seat_count": 1
            }
            orgs.append(org_data)
            
        return orgs

    def update_organization_tier(self, db: Database, org_id: str, tier: str) -> Optional[Dict[str, Any]]:
        sub_status = "ACTIVE" if tier == "TIER_2" else "TRIAL"
        
        try:
            oid = ObjectId(org_id)
            
            result = db.users.update_one(
                {"_id": oid},
                {"$set": {
                    "subscription_status": sub_status, 
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            
            if result.matched_count == 0:
                return None
                
            # Fetch updated data
            user = db.users.find_one({"_id": oid})
            if not user: return None
            
            profile = db.business_profiles.find_one({"user_id": oid}) or {}
            
            return {
                "id": str(user["_id"]),
                "name": profile.get("firm_name") or user.get("username"),
                "plan": tier,
                "status": sub_status,
                "created_at": user.get("created_at"),
                "owner_email": user.get("email"),
                "seat_limit": 5 if tier == "TIER_2" else 1,
                "seat_count": 1
            }
        except Exception as e:
            print(f"Error updating tier: {e}")
            return None

    # --- LEGACY USER MANAGEMENT ---

    def get_all_users_legacy(self, db: Database) -> List[UserAdminView]:
        users = list(db.users.find({}).sort("created_at", -1))
        return [UserAdminView(**u) for u in users]

    def update_user_details_legacy(self, db: Database, user_id: str, update_data: UserUpdateRequest) -> Optional[UserAdminView]:
        try:
            oid = ObjectId(user_id)
            data = update_data.model_dump(exclude_unset=True)
            if not data: return None
            
            data["updated_at"] = datetime.now(timezone.utc)
            
            db.users.update_one({"_id": oid}, {"$set": data})
            
            updated_user = db.users.find_one({"_id": oid})
            return UserAdminView(**updated_user) if updated_user else None
        except:
            return None

    def delete_user_and_data_legacy(self, db: Database, user_id: str) -> bool:
        from app.services import storage_service
        
        try:
            oid = ObjectId(user_id)
            # 1. Delete Cases
            db.cases.delete_many({"user_id": oid})
            # 2. Delete Docs
            db.documents.delete_many({"user_id": oid})
            # 3. Delete User
            result = db.users.delete_one({"_id": oid})
            
            return result.deleted_count > 0
        except:
            return False

# Instantiate Service
admin_service = AdminService()