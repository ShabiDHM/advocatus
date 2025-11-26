# FILE: backend/app/services/business_service.py
# PHOENIX PROTOCOL - BUSINESS SERVICE (FIXED)
# 1. SAFETY: Added explicit checks for None before accessing profile.
# 2. STORAGE: Calls updated storage_service methods.

import structlog
from datetime import datetime
from bson import ObjectId
from pymongo.database import Database
from fastapi import UploadFile, HTTPException

from ..models.business import BusinessProfileUpdate
from ..services import storage_service

logger = structlog.get_logger(__name__)

def get_or_create_profile(db: Database, user_id: str) -> dict:
    """Retreives the user's firm profile or creates a default one."""
    profile = db.business_profiles.find_one({"user_id": user_id})
    
    if not profile:
        logger.info("business.profile_created", user_id=user_id)
        new_profile = {
            "user_id": user_id,
            "firm_name": "Zyra Ligjore (Pa Emër)",
            "branding_color": "#1f2937",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = db.business_profiles.insert_one(new_profile)
        profile = db.business_profiles.find_one({"_id": result.inserted_id})
    
    if not profile:
        raise HTTPException(500, "Failed to create profile.")

    # Safe Access
    logo = profile.get("logo_storage_key")
    addr = profile.get("address")
    name = profile.get("firm_name")
    is_complete = bool(logo and addr and name)
    
    return {
        **profile,
        "id": str(profile["_id"]),
        "is_complete": is_complete
    }

def update_profile(db: Database, user_id: str, data: BusinessProfileUpdate) -> dict:
    """Updates text fields of the profile."""
    profile = get_or_create_profile(db, user_id)
    
    update_data = data.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    db.business_profiles.update_one(
        {"_id": ObjectId(profile["id"])},
        {"$set": update_data}
    )
    
    return get_or_create_profile(db, user_id)

def update_logo(db: Database, user_id: str, file: UploadFile) -> dict:
    """Uploads a new logo and updates the profile record."""
    profile = get_or_create_profile(db, user_id)
    
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(400, "Format i pavlefshëm. Lejohen vetëm PNG, JPG, WEBP.")
    
    try:
        storage_key = storage_service.upload_file_raw(
            file=file,
            folder=f"branding/{user_id}"
        )
        
        db.business_profiles.update_one(
            {"_id": ObjectId(profile["id"])},
            {
                "$set": {
                    "logo_storage_key": storage_key,
                    "logo_url": f"/api/v1/business/logo/{user_id}?ts={int(datetime.now().timestamp())}",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return get_or_create_profile(db, user_id)
        
    except Exception as e:
        logger.error("business.logo_upload_failed", error=str(e))
        raise HTTPException(500, "Ngarkimi i logos dështoi.")