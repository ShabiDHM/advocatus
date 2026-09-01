# FILE: backend/app/services/admin_service.py
# PHOENIX PROTOCOL - ADMIN SERVICE V50.0 (1-CLICK CASE UNLOCK & PAYMENT DASHBOARD)

from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone
from pymongo.database import Database
import logging
import json

logger = logging.getLogger(__name__)

class AdminService:
    
    def get_all_users_for_dashboard(self, db: Database) -> List[Dict[str, Any]]:
        pipeline = [
            {
                "$lookup": {
                    "from": "business_profiles",
                    "localField": "_id",
                    "foreignField": "user_id",
                    "as": "business_profile_data"
                }
            },
            {
                "$unwind": {
                    "path": "$business_profile_data",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$addFields": {
                    "organization_name": "$business_profile_data.firm_name"
                }
            },
            {
                "$sort": {"created_at": -1}
            },
            {
                "$project": {
                    "business_profile_data": 0
                }
            }
        ]
        try:
            users = list(db.users.aggregate(pipeline))
            return users
        except Exception as e:
            logger.error(f"--- [ADMIN V50.0] Failed to fetch users: {e}")
            return []

    def get_all_cases_for_admin_dashboard(self, db: Database) -> List[Dict[str, Any]]:
        """
        Kthen të gjitha lëndët me statusin e tyre të pagesës për panelin e Adminit.
        """
        pipeline = [
            {
                "$lookup": {
                    "from": "users",
                    "localField": "owner_id",
                    "foreignField": "_id",
                    "as": "owner_data"
                }
            },
            {
                "$unwind": {
                    "path": "$owner_data",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$lookup": {
                    "from": "documents",
                    "localField": "_id",
                    "foreignField": "case_id",
                    "as": "docs_list"
                }
            },
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "title": {"$ifNull": ["$title", "$name", "Lëndë e Pa-emërtuar"]},
                    "client_name": {"$ifNull": ["$client_name", "$client.name", "Pala"]},
                    "client_position": {"$ifNull": ["$client_position", "$client_role", "DEFENDANT"]},
                    "is_unlocked": {"$ifNull": ["$is_unlocked", False]},
                    "unlocked_at": "$unlocked_at",
                    "unlock_payment_method": "$unlock_payment_method",
                    "unlock_amount": "$unlock_amount",
                    "owner_email": "$owner_data.email",
                    "owner_name": {"$ifNull": ["$owner_data.full_name", "$owner_data.name", "Përdorues"]},
                    "owner_role": "$owner_data.role",
                    "document_count": {"$size": "$docs_list"},
                    "created_at": "$created_at",
                    "updated_at": "$updated_at"
                }
            },
            {
                "$sort": {"created_at": -1}
            }
        ]
        try:
            cases = list(db.cases.aggregate(pipeline))
            return cases
        except Exception as e:
            logger.error(f"--- [ADMIN V50.0] Failed to fetch cases for admin: {e}")
            return []

    def unlock_case_by_admin(
        self, 
        db: Database, 
        case_id: str, 
        payment_method: str = "CASH", 
        amount: float = 9.99, 
        admin_user_id: str = "", 
        note: str = "Zhbllokim me 1 klikim nga Admini"
    ) -> Dict[str, Any]:
        """
        Zhbllokon lëndën me 1 klikim nga paneli i adminit.
        """
        try:
            c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            case_doc = db.cases.find_one({"_id": c_oid})
            if not case_doc:
                return {"success": False, "message": "Lënda nuk u gjet."}

            now = datetime.now(timezone.utc)
            db.cases.update_one(
                {"_id": c_oid},
                {"$set": {
                    "is_unlocked": True,
                    "unlocked_at": now,
                    "unlock_payment_method": payment_method.upper(),
                    "unlock_amount": amount,
                    "updated_at": now
                }}
            )

            # Regjistro porosinë në arkivë
            order_record = {
                "case_id": c_oid,
                "owner_id": case_doc.get("owner_id"),
                "approved_by": admin_user_id,
                "amount": amount,
                "currency": "EUR",
                "payment_method": payment_method.upper(),
                "status": "COMPLETED",
                "note": note,
                "created_at": now
            }
            db.case_orders.insert_one(order_record)

            logger.info(f"✅ [Admin Unlock] Lënda {case_id} u zhbllokua nga Admini ({payment_method.upper()}).")
            return {
                "success": True, 
                "message": f"Lënda '{case_doc.get('title', '')}' u zhbllokua me sukses.",
                "case_id": str(case_id),
                "is_unlocked": True,
                "unlocked_at": now.isoformat()
            }
        except Exception as e:
            logger.error(f"--- [ADMIN V50.0] Unlock error: {e}")
            return {"success": False, "message": str(e)}

    def lock_case_by_admin(self, db: Database, case_id: str) -> Dict[str, Any]:
        try:
            c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            db.cases.update_one(
                {"_id": c_oid},
                {"$set": {
                    "is_unlocked": False,
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            return {"success": True, "message": "Lënda u bllokua përsëri.", "is_unlocked": False}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def update_user_and_subscription(self, db: Database, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            oid = ObjectId(user_id)
            if "updated_at" not in update_data:
                update_data["updated_at"] = datetime.now(timezone.utc)

            result = db.users.update_one({"_id": oid}, {"$set": update_data})
            if result.matched_count == 0:
                return None
            return db.users.find_one({"_id": oid})
        except Exception as e:
            logger.error(f"--- [ADMIN V50.0] User update error: {e}")
            return None

    def delete_user_and_data(self, db: Database, user_id: str) -> bool:
        try:
            oid = ObjectId(user_id)
            db.cases.delete_many({"owner_id": oid})
            db.documents.delete_many({"owner_id": oid})
            db.business_profiles.delete_one({"user_id": oid})
            db.archives.delete_many({"user_id": str(oid)})
            result = db.users.delete_one({"_id": oid})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"--- [ADMIN V50.0] User deletion error: {e}")
            return False

admin_service: AdminService = AdminService()