# FILE: backend/app/services/user_service.py
# PHOENIX PROTOCOL - USER SERVICE V3.0 (FULL CASCADE + GDPR COMPLIANT)
# V3.0: TOTAL WIPEOUT — mbulon TË GJITHA entitetet:
#       - user_vectors (embeddings të user-it, owner-agnostic)
#       - media_evidence (DB + B2 + embeddings)
#       - documents embeddings (jo vetëm storage)
#       - alerts, chat_feedback, case_orders
#       - Fallback për case_id si string (legacy data)
#       - Kalon case_id te delete_document_embeddings V67.0
# V2.0: GDPR — is_deleted check, consent_date, archive cleanup.

from pymongo.database import Database
from bson import ObjectId
from fastapi import HTTPException
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import logging
import re

from app.core.security import verify_password, get_password_hash
from app.models.user import UserInDB, UserCreate
from app.services import storage_service, vector_store_service

logger = logging.getLogger(__name__)


def _log_user_audit(db: Database, action: str, user_id: ObjectId, details: Optional[Dict[str, Any]] = None):
    """Regjistron një ngjarje auditimi për veprime të ndjeshme të përdoruesit."""
    try:
        audit_entry = {
            "action": action,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc),
            "details": details or {}
        }
        db.user_audit.insert_one(audit_entry)
    except Exception as e:
        logger.error(f"Failed to write user audit log: {e}")


def get_user_by_username(db: Database, username: str) -> Optional[UserInDB]:
    query = {"username": {"$regex": f"^{re.escape(username)}$", "$options": "i"}}
    user_dict = db.users.find_one(query)
    if user_dict:
        return UserInDB.model_validate(user_dict)
    return None


def get_user_by_email(db: Database, email: str) -> Optional[UserInDB]:
    query = {"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}}
    user_dict = db.users.find_one(query)
    if user_dict:
        return UserInDB.model_validate(user_dict)
    return None


def get_user_by_id(db: Database, user_id: ObjectId) -> Optional[UserInDB]:
    user_dict = db.users.find_one({"_id": user_id})
    if user_dict:
        return UserInDB.model_validate(user_dict)
    return None


def authenticate(db: Database, username: str, password: str) -> Optional[UserInDB]:
    user = get_user_by_username(db, username)
    if not user:
        user = get_user_by_email(db, username)
        
    if not user:
        return None

    # GDPR: nuk lejohet hyrja për përdorues të fshirë
    if user.is_deleted:
        return None
        
    # PHOENIX FIX V1.5: Check if hashed_password is None before attempting verification.
    if user.hashed_password is None:
        return None
        
    if not verify_password(password, user.hashed_password):
        return None
        
    return user


def create(db: Database, obj_in: UserCreate) -> UserInDB:
    user_data = obj_in.model_dump()
    password = user_data.pop("password")
    hashed_password = get_password_hash(password)
    
    user_data["hashed_password"] = hashed_password
    user_data["created_at"] = datetime.now(timezone.utc)
    user_data["updated_at"] = datetime.now(timezone.utc)
    
    # GDPR: nëse consent_date nuk është dhënë, vendose tani
    if not user_data.get("consent_date"):
        user_data["consent_date"] = datetime.now(timezone.utc)
    
    # Explicitly set status for Gatekeeper
    user_data["subscription_status"] = "INACTIVE"
    
    result = db.users.insert_one(user_data)
    new_user = db.users.find_one({"_id": result.inserted_id})
    
    if not new_user:
        raise HTTPException(status_code=500, detail="User creation failed")
        
    return UserInDB.model_validate(new_user)


def update_last_login(db: Database, user_id: str):
    try:
        oid = ObjectId(user_id)
        db.users.update_one({"_id": oid}, {"$set": {"last_login": datetime.now(timezone.utc)}})
    except Exception:
        pass


def change_password(db: Database, user_id: str, old_pass: str, new_pass: str):
    try:
        oid = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user_dict = db.users.find_one({"_id": oid})
    if not user_dict:
        raise HTTPException(status_code=404, detail="User not found")
    
    # GDPR: mos lejo ndryshim fjalëkalimi për përdorues të fshirë
    if user_dict.get("is_deleted"):
        raise HTTPException(status_code=403, detail="Account is deleted")
    
    if not verify_password(old_pass, user_dict["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid old password")

    new_hash = get_password_hash(new_pass)
    db.users.update_one({"_id": oid}, {"$set": {"hashed_password": new_hash}})


def _delete_storage_safely(storage_key: Optional[str], context: str) -> None:
    """V3.0: Helper për fshirje të sigurt të një skedari nga B2."""
    if not storage_key:
        return
    try:
        storage_service.delete_file(storage_key)
    except Exception as e:
        logger.warning(f"⚠️ [User Delete] B2 delete failed ({context}): {storage_key} — {e}")


def _delete_embeddings_safely(
    user_id_str: str,
    document_id: str,
    case_id: Optional[str],
    context: str
) -> int:
    """V3.0: Helper për fshirje të sigurt të embeddings me fallback."""
    try:
        deleted = vector_store_service.delete_document_embeddings(
            user_id=user_id_str,
            document_id=document_id,
            case_id=case_id
        )
        if deleted > 0:
            logger.debug(f"✅ [User Delete] {deleted} embeddings fshinë për {context}: {document_id}")
        return deleted
    except Exception as e:
        logger.warning(f"⚠️ [User Delete] Embeddings delete failed ({context}): {document_id} — {e}")
        return 0


def delete_user_and_all_data(db: Database, user: UserInDB):
    """
    V3.0: TOTAL CASCADE WIPEOUT

    Fshin plotësisht:
      - Të gjitha cases me owner_id == user.id
      - Documents + storage (B2) + embeddings
      - Media evidence + storage + embeddings
      - Findings
      - Calendar events + alerts
      - Archives + storage
      - chat_feedback, case_orders
      - user_vectors (të gjitha embeddings e user-it, owner-agnostic)
      - business_profiles
      - User record
      - Audit log
    """
    user_id = user.id
    user_id_str = str(user_id)
    deleted_stats = {
        "cases": 0, "documents": 0, "media": 0, "findings": 0,
        "events": 0, "alerts": 0, "archives": 0, "user_vectors": 0,
        "chat_feedback": 0, "case_orders": 0,
    }

    try:
        # 1. GJEJ TË GJITHA CASE-ET E USER-IT
        cases_to_delete = list(db.cases.find({
            "$or": [
                {"owner_id": user_id},
                {"owner_id": user_id_str},
                {"user_id": user_id},
                {"user_id": user_id_str}
            ]
        }))
        case_ids = [c["_id"] for c in cases_to_delete]
        case_ids_str = [str(cid) for cid in case_ids]

        logger.info(f"🗑️ [User Delete] Filloi cascade për user {user_id_str}: {len(case_ids)} cases")

        # 2. DOCUMENTS — storage + embeddings
        if case_ids:
            docs_filter = {
                "$or": [
                    {"case_id": {"$in": case_ids}},
                    {"case_id": {"$in": case_ids_str}}
                ]
            }
            documents = list(db.documents.find(docs_filter))
            for doc in documents:
                doc_id_str = str(doc["_id"])
                _delete_storage_safely(doc.get("storage_key"), "doc.storage_key")
                _delete_storage_safely(doc.get("preview_storage_key"), "doc.preview_storage_key")
                _delete_storage_safely(doc.get("processed_text_storage_key"), "doc.processed_text_storage_key")
                _delete_embeddings_safely(
                    user_id_str=user_id_str,
                    document_id=doc_id_str,
                    case_id=str(doc.get("case_id")) if doc.get("case_id") else None,
                    context="document"
                )
            deleted_stats["documents"] = len(documents)

        # 3. MEDIA EVIDENCE — storage + embeddings
        if case_ids:
            media_filter = {
                "$or": [
                    {"case_id": {"$in": case_ids}},
                    {"case_id": {"$in": case_ids_str}}
                ]
            }
            media_items = list(db.media_evidence.find(media_filter))
            for media in media_items:
                media_id_str = str(media["_id"])
                _delete_storage_safely(media.get("storage_key"), "media.storage_key")
                _delete_embeddings_safely(
                    user_id_str=user_id_str,
                    document_id=media_id_str,
                    case_id=str(media.get("case_id")) if media.get("case_id") else None,
                    context="media"
                )
            deleted_stats["media"] = len(media_items)

        # 4. FINDINGS
        if case_ids:
            findings_filter = {
                "$or": [
                    {"case_id": {"$in": case_ids}},
                    {"case_id": {"$in": case_ids_str}}
                ]
            }
            findings_result = db.findings.delete_many(findings_filter)
            deleted_stats["findings"] = findings_result.deleted_count

        # 5. CALENDAR EVENTS + ALERTS
        if case_ids:
            events_filter = {
                "$or": [
                    {"case_id": {"$in": case_ids}},
                    {"case_id": {"$in": case_ids_str}}
                ]
            }
            events_result = db.calendar_events.delete_many(events_filter)
            deleted_stats["events"] = events_result.deleted_count

            try:
                alerts_result = db.alerts.delete_many(events_filter)
                deleted_stats["alerts"] = alerts_result.deleted_count
            except Exception as e:
                logger.warning(f"⚠️ [User Delete] Alerts cleanup: {e}")

        # 6. CHAT FEEDBACK + CASE ORDERS
        try:
            chat_filter = {
                "$or": [
                    {"user_id": user_id_str},
                    {"user_id": user_id},
                ]
            }
            if case_ids_str:
                chat_filter["$or"].extend([
                    {"case_id": {"$in": case_ids_str}},
                    {"case_id": {"$in": case_ids}}
                ])
            chat_result = db.chat_feedback.delete_many(chat_filter)
            deleted_stats["chat_feedback"] = chat_result.deleted_count
        except Exception as e:
            logger.warning(f"⚠️ [User Delete] Chat feedback cleanup: {e}")

        try:
            orders_filter = {
                "$or": [
                    {"user_id": user_id},
                    {"user_id": user_id_str},
                    {"owner_id": user_id},
                    {"approved_by": user_id},
                ]
            }
            orders_result = db.case_orders.delete_many(orders_filter)
            deleted_stats["case_orders"] = orders_result.deleted_count
        except Exception as e:
            logger.warning(f"⚠️ [User Delete] Case orders cleanup: {e}")

        # 7. USER_VECTORS — TË GJITHA embeddings e user-it
        try:
            vectors_filter = {
                "$or": [
                    {"owner_id": user_id_str},
                    {"owner_id": user_id if isinstance(user_id, ObjectId) else ObjectId(user_id_str)},
                ]
            }
            vectors_result = db.user_vectors.delete_many(vectors_filter)
            deleted_stats["user_vectors"] = vectors_result.deleted_count
        except Exception as e:
            logger.warning(f"⚠️ [User Delete] user_vectors cleanup: {e}")

        # 8. DELETIMI I ENTITETEVE PRIND
        if case_ids:
            any_filter = {
                "$or": [
                    {"case_id": {"$in": case_ids}},
                    {"case_id": {"$in": case_ids_str}}
                ]
            }
            db.documents.delete_many(any_filter)
            db.media_evidence.delete_many(any_filter)
            db.cases.delete_many({"_id": {"$in": case_ids}})
            deleted_stats["cases"] = len(case_ids)

        # 9. BUSINESS PROFILE
        db.business_profiles.delete_one({"user_id": user_id_str})
        db.business_profiles.delete_one({"user_id": user_id})

        # 10. ARCHIVES — storage + DB
        archive_items = list(db.archives.find({
            "$or": [
                {"user_id": user_id},
                {"user_id": user_id_str},
                {"owner_id": user_id},
                {"owner_id": user_id_str}
            ]
        }))
        for item in archive_items:
            _delete_storage_safely(item.get("storage_key"), "archive.storage_key")
            db.archives.delete_one({"_id": item["_id"]})
        deleted_stats["archives"] = len(archive_items)

        # 11. FSHIRJE E USER RECORD
        db.users.delete_one({"_id": user_id})

        # 12. AUDIT LOG
        _log_user_audit(db, "USER_DELETED", user_id, {
            "email": user.email,
            "username": user.username,
            "stats": deleted_stats,
        })

        logger.info(f"🧹 [User Delete] Cascade përfundoi për {user_id_str}: {deleted_stats}")
        
    except Exception as e:
        logger.error(f"❌ Failed during cascading delete for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="A failure occurred during the account deletion process.")