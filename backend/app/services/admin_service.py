# FILE: backend/app/services/admin_service.py
# PHOENIX PROTOCOL - ADMIN SERVICE V51.4 (ONE-TIME PASS REMOVED)
# V51.4: ONE-TIME PASS REMOVED —
#        - Hequr `unlock_case_by_admin` + `lock_case_by_admin`.
#        - Hequr `DEFAULT_UNLOCK_AMOUNT`.
#        - `get_all_cases_for_admin_dashboard`: hequr fushat is_unlocked,
#          unlocked_at, unlock_payment_method, unlock_amount.
#        - Modeli: vetëm abonim mujor (Solo 49.99€ / Team 99.99€).
# V51.3: PRICE ALIGNMENT (bazë historike).
# V51.2: Default amount: 9.99 → 99.00.
# V51.1: FIX — delete_user_and_data nuk perdor UserInDB.model_validate.
# V51.0: DELEGATED USER DELETE (delegon te user_service).

from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone
from pymongo.database import Database
from types import SimpleNamespace
import logging


from app.services import user_service

logger = logging.getLogger(__name__)


class AdminService:

    def get_all_users_for_dashboard(self, db: Database) -> List[Dict[str, Any]]:
        pipeline = [
            {"$lookup": {"from": "business_profiles", "localField": "_id", "foreignField": "user_id", "as": "business_profile_data"}},
            {"$unwind": {"path": "$business_profile_data", "preserveNullAndEmptyArrays": True}},
            {"$addFields": {"organization_name": "$business_profile_data.firm_name"}},
            {"$sort": {"created_at": -1}},
            {"$project": {"business_profile_data": 0}}
        ]
        try:
            users = list(db.users.aggregate(pipeline))
            return users
        except Exception as e:
            logger.error(f"--- [ADMIN V51.4] Failed to fetch users: {e}")
            return []

    def get_all_cases_for_admin_dashboard(self, db: Database) -> List[Dict[str, Any]]:
        """
        V51.4: Kthen të gjitha lëndët për panelin e Adminit.
        Hequr fushat e lidhura me One-Time Pass (is_unlocked, unlock_*).
        """
        pipeline = [
            {"$lookup": {"from": "users", "localField": "owner_id", "foreignField": "_id", "as": "owner_data"}},
            {"$unwind": {"path": "$owner_data", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {"from": "documents", "localField": "_id", "foreignField": "case_id", "as": "docs_list"}},
            {"$project": {
                "_id": {"$toString": "$_id"},
                "title": {"$ifNull": ["$title", "$name", "Lëndë e Pa-emërtuar"]},
                "client_name": {"$ifNull": ["$client_name", "$client.name", "Pala"]},
                "client_position": {"$ifNull": ["$client_position", "$client_role", "DEFENDANT"]},
                "owner_email": "$owner_data.email",
                "owner_name": {"$ifNull": ["$owner_data.full_name", "$owner_data.name", "Përdorues"]},
                "owner_role": "$owner_data.role",
                "document_count": {"$size": "$docs_list"},
                "created_at": "$created_at",
                "updated_at": "$updated_at"
            }},
            {"$sort": {"created_at": -1}}
        ]
        try:
            cases = list(db.cases.aggregate(pipeline))
            return cases
        except Exception as e:
            logger.error(f"--- [ADMIN V51.4] Failed to fetch cases for admin: {e}")
            return []

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
            logger.error(f"--- [ADMIN V51.4] User update error: {e}")
            return None

    def delete_user_and_data(self, db: Database, user_id: str) -> bool:
        """
        V51.1: Delegon te user_service.delete_user_and_all_data.
        """
        try:
            oid = ObjectId(user_id)
            user_doc = db.users.find_one({"_id": oid})
            if not user_doc:
                logger.warning(f"--- [ADMIN V51.4] delete_user_and_data: user {user_id} nuk u gjet")
                return False

            user = SimpleNamespace(
                id=user_doc["_id"],
                email=user_doc.get("email", ""),
                username=user_doc.get("username", ""),
            )

            user_service.delete_user_and_all_data(db, user)

            logger.info(f"✅ [ADMIN V51.4] User {user_id} u fshi me sukses.")
            return True

        except Exception as e:
            logger.error(f"--- [ADMIN V51.4] User deletion error: {e}", exc_info=True)
            return False


admin_service: AdminService = AdminService()