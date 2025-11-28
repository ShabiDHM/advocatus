# FILE: backend/app/services/business_service.py
# PHOENIX PROTOCOL - BUSINESS SERVICE (ALIGNMENT FIX)
# 1. CONSISTENCY: Uses ObjectId(user_id) to match other modules.
# 2. TYPE SAFETY: Returns Pydantic models instead of raw dicts.
# 3. FIX: Resolves 500 Error on logo upload.

import structlog
from datetime import datetime, timezone
from bson import ObjectId
from pymongo.database import Database
from fastapi import UploadFile, HTTPException

from ..models.business import BusinessProfileUpdate, BusinessProfileInDB
from ..services import storage_service

logger = structlog.get_logger(__name__)

class BusinessService:
    def __init__(self, db: Database):
        self.db = db

    def get_or_create_profile(self, user_id: str) -> BusinessProfileInDB:
        """Retrieves the user's firm profile or creates a default one."""
        # PHOENIX FIX: Use ObjectId for query
        profile = self.db.business_profiles.find_one({"user_id": ObjectId(user_id)})
        
        if not profile:
            logger.info("business.profile_created", user_id=user_id)
            new_profile = {
                "user_id": ObjectId(user_id), # Store as ObjectId
                "firm_name": "Zyra Ligjore",
                "branding_color": "#1f2937",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            self.db.business_profiles.insert_one(new_profile)
            # new_profile now contains '_id', just unpack it
            return BusinessProfileInDB(**new_profile)
        
        # PHOENIX FIX: Return Pydantic model directly
        return BusinessProfileInDB(**profile)

    def update_profile(self, user_id: str, data: BusinessProfileUpdate) -> BusinessProfileInDB:
        """Updates text fields of the profile."""
        # Ensure profile exists first
        current_profile = self.get_or_create_profile(user_id)
        
        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        result = self.db.business_profiles.find_one_and_update(
            {"_id": ObjectId(current_profile.id)},
            {"$set": update_data},
            return_document=True
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Profile not found after update.")
            
        return BusinessProfileInDB(**result)

    def update_logo(self, user_id: str, file: UploadFile) -> BusinessProfileInDB:
        """Uploads a new logo and updates the profile record."""
        current_profile = self.get_or_create_profile(user_id)
        
        if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise HTTPException(400, "Format i pavlefshëm. Lejohen vetëm PNG, JPG, WEBP.")
        
        try:
            # Upload to MinIO/S3 via Storage Service
            storage_key = storage_service.upload_file_raw(
                file=file,
                folder=f"branding/{user_id}"
            )
            
            # Construct public URL (adjust based on your serving logic)
            # Adding timestamp to force frontend cache refresh
            logo_url = f"/api/v1/business/logo/{user_id}?ts={int(datetime.now().timestamp())}"
            
            result = self.db.business_profiles.find_one_and_update(
                {"_id": ObjectId(current_profile.id)},
                {
                    "$set": {
                        "logo_storage_key": storage_key,
                        "logo_url": logo_url,
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
                return_document=True
            )
            
            return BusinessProfileInDB(**result)
            
        except Exception as e:
            logger.error("business.logo_upload_failed", error=str(e))
            raise HTTPException(500, "Ngarkimi i logos dështoi.")

# Export a helper to be used by dependencies if needed, 
# though usually, we instantiate this in the endpoint.