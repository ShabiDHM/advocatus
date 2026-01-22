# FILE: backend/app/services/admin_service.py
# PHOENIX PROTOCOL - ADMIN SERVICE V8.1 (ROBUST UPDATE)
# 1. LOGIC: Forced 'plan_tier' update when promoting.
# 2. DEBUG: Added print statements to trace the update flow in Docker logs.


from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone
from pymongo.database import Database

class AdminService:
    
    # --- DASHBOARD DATA ---
    def get_all_organizations(self, db: Database) -> List[Dict[str, Any]]:
        orgs = []
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
            return []

        for user in users:
            if not user: continue
            
            profile = user.get("profile") or {}
            sub_status = user.get("subscription_status", "INACTIVE")
            expiry = user.get("subscription_expiry")
            plan = user.get("plan_tier", "SOLO")
            
            org_data = {
                "id": str(user.get("_id")),
                "name": profile.get("firm_name") or profile.get("company_name") or user.get("username", "Unknown"),
                "plan": plan,
                "tier": "TIER_2" if plan in ["STARTUP", "GROWTH", "ENTERPRISE"] else "TIER_1",
                "status": sub_status,
                "expiry": expiry,
                "created_at": user.get("created_at"),
                "owner_email": user.get("email"),
                "seat_limit": 1
            }
            
            if plan == "STARTUP": org_data["seat_limit"] = 5
            elif plan == "GROWTH": org_data["seat_limit"] = 10
            elif plan == "ENTERPRISE": org_data["seat_limit"] = 50
            
            org_id = user.get("org_id") or user.get("_id")
            org_data["seat_count"] = db.users.count_documents({"org_id": org_id})
            
            orgs.append(org_data)
            
        return orgs

    # --- MANAGEMENT ACTIONS ---

    def update_subscription(self, db: Database, user_id: str, status: str, expiry_date: Optional[datetime], plan_tier: Optional[str]) -> bool:
        try:
            oid = ObjectId(user_id)
            print(f"--- [ADMIN] Updating Subscription for {user_id} ---")
            print(f"--- [ADMIN] Target Status: {status}, Plan: {plan_tier} ---")

            update_data = {
                "subscription_status": status,
                "updated_at": datetime.now(timezone.utc)
            }
            
            if expiry_date:
                update_data["subscription_expiry"] = expiry_date
            
            if plan_tier:
                update_data["plan_tier"] = plan_tier
                
                # Auto-Promote Logic
                if plan_tier in ["STARTUP", "GROWTH", "ENTERPRISE"]:
                    user = db.users.find_one({"_id": oid})
                    
                    if user:
                        # Ensure Org Owner Role
                        update_data["org_id"] = oid
                        update_data["organization_role"] = "OWNER"
                        
                        # Create Profile if missing
                        username = user.get("username", "Law Firm")
                        db.business_profiles.update_one(
                            {"user_id": oid},
                            {
                                "$setOnInsert": {
                                    "firm_name": f"{username} Legal",
                                    "created_at": datetime.now(timezone.utc)
                                },
                                "$set": {
                                    "updated_at": datetime.now(timezone.utc),
                                    # Force update name if it was generic before? No, keep user data safe.
                                }
                            },
                            upsert=True
                        )

            result = db.users.update_one({"_id": oid}, {"$set": update_data})
            print(f"--- [ADMIN] Update Result: {result.modified_count} modified ---")
            return True
        except Exception as e:
            print(f"Update Sub Error: {e}")
            return False

    def promote_to_firm(self, db: Database, user_id: str, firm_name: str, plan: str) -> bool:
        try:
            oid = ObjectId(user_id)
            db.users.update_one(
                {"_id": oid}, 
                {"$set": {
                    "plan_tier": plan, 
                    "org_id": oid,
                    "organization_role": "OWNER",
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            db.business_profiles.update_one(
                {"user_id": oid},
                {"$set": {
                    "firm_name": firm_name,
                    "updated_at": datetime.now(timezone.utc)
                }},
                upsert=True
            )
            return True
        except Exception:
            return False

    # --- LEGACY METHODS ---
    def get_all_users_legacy(self, db: Database) -> List[Any]:
        return list(db.users.find({}).sort("created_at", -1))

    def update_user_details_legacy(self, db: Database, user_id: str, update_data: Any) -> Optional[Any]:
        try:
            oid = ObjectId(user_id)
            data = update_data.model_dump(exclude_unset=True)
            db.users.update_one({"_id": oid}, {"$set": data})
            return db.users.find_one({"_id": oid})
        except: return None

    def delete_user_and_data_legacy(self, db: Database, user_id: str) -> bool:
        try:
            oid = ObjectId(user_id)
            db.cases.delete_many({"user_id": oid})
            db.documents.delete_many({"user_id": oid})
            db.business_profiles.delete_many({"user_id": oid})
            result = db.users.delete_one({"_id": oid})
            return result.deleted_count > 0
        except: return False

admin_service = AdminService()