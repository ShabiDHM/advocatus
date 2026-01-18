# FILE: backend/app/services/admin_service.py
# PHOENIX PROTOCOL - ADMIN SERVICE V6.1 (PROMOTION LOGIC)
# 1. FEATURE: 'update_organization_tier' now auto-creates a BusinessProfile.
# 2. LOGIC: This ensures upgraded users appear as "Firms" in the dashboard.
# 3. FIX: Helper methods standardized.

from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone
from pymongo.database import Database

class AdminService:
    
    # --- ORGANIZATION MANAGEMENT ---

    def get_all_organizations(self, db: Database) -> List[Dict[str, Any]]:
        orgs = []
        # Fetch ALL users who might be organizations (excluding Super Admins if desired, 
        # but for testing we might want to see everyone)
        # To see everyone, remove the $match or adjust it.
        # For now, let's keep Admins hidden from the "Firms" list to avoid clutter,
        # UNLESS they have a profile.
        
        pipeline = [
            {"$lookup": {
                "from": "business_profiles",
                "localField": "_id",
                "foreignField": "user_id",
                "as": "profile"
            }},
            {"$unwind": {"path": "$profile", "preserveNullAndEmptyArrays": True}},
            {"$sort": {"created_at": -1}}
        ]
        
        try:
            users = list(db.users.aggregate(pipeline))
        except Exception as e:
            print(f"Admin Service Error: {e}")
            return []

        for user in users:
            if not user: continue
            
            # PHOENIX LOGIC: Only show as "Organization" if they are TIER_2 OR have a profile
            profile = user.get("profile") or {}
            sub_status = user.get("subscription_status", "TRIAL")
            
            # Filter: If you want ONLY Tier 2 to show as Orgs:
            # if sub_status != "ACTIVE" and not profile: continue 

            org_id = user.get("org_id") or user.get("_id")
            
            orgs.append({
                "id": str(org_id),
                "name": profile.get("firm_name") or profile.get("company_name") or user.get("username", "Unknown"),
                "plan": "TIER_2" if sub_status == "ACTIVE" else "TIER_1", 
                "status": sub_status,
                "created_at": user.get("created_at"),
                "owner_email": user.get("email"),
                "seat_limit": 5 if sub_status == "ACTIVE" else 1,
                "seat_count": 1
            })
            
        return orgs

    def update_organization_tier(self, db: Database, org_id: str, tier: str) -> Optional[Dict[str, Any]]:
        sub_status = "ACTIVE" if tier == "TIER_2" else "TRIAL"
        try:
            oid = ObjectId(org_id)
            
            # 1. Update User Status
            result = db.users.update_one(
                {"_id": oid},
                {"$set": {
                    "subscription_status": sub_status, 
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            
            # 2. PROMOTION LOGIC: If upgrading to TIER_2, ensure Business Profile exists
            if tier == "TIER_2":
                existing_profile = db.business_profiles.find_one({"user_id": oid})
                if not existing_profile:
                    user = db.users.find_one({"_id": oid})
                    username = user.get("username", "Law Firm") if user else "Law Firm"
                    
                    db.business_profiles.insert_one({
                        "user_id": oid,
                        "firm_name": f"{username} Legal", # Default name
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    })

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

    def get_all_users_legacy(self, db: Database) -> List[Any]:
        users = list(db.users.find({}).sort("created_at", -1))
        return users

    def update_user_details_legacy(self, db: Database, user_id: str, update_data: Any) -> Optional[Any]:
        try:
            oid = ObjectId(user_id)
            data = update_data.model_dump(exclude_unset=True)
            if not data: return None
            data["updated_at"] = datetime.now(timezone.utc)
            db.users.update_one({"_id": oid}, {"$set": data})
            return db.users.find_one({"_id": oid})
        except:
            return None

    def delete_user_and_data_legacy(self, db: Database, user_id: str) -> bool:
        try:
            oid = ObjectId(user_id)
            db.cases.delete_many({"user_id": oid})
            db.documents.delete_many({"user_id": oid})
            db.business_profiles.delete_many({"user_id": oid}) # Cleanup profile too
            result = db.users.delete_one({"_id": oid})
            return result.deleted_count > 0
        except:
            return False

admin_service = AdminService()