# FILE: backend/app/api/endpoints/business.py
# PHOENIX PROTOCOL - BUSINESS API (FIXED)
# 1. SYNTAX: Fixed argument ordering in upload_logo.
# 2. LOGIC: Connects to business_service correctly.

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from typing import Annotated
from pymongo.database import Database

from ...services import business_service, storage_service
from ...models.user import UserInDB
from ...models.business import BusinessProfileOut, BusinessProfileUpdate
from .dependencies import get_current_user, get_db

router = APIRouter(tags=["Business"])

@router.get("/profile", response_model=BusinessProfileOut)
async def get_profile(
    current_user: Annotated[UserInDB, Depends(get_current_user)], 
    db: Database = Depends(get_db)
):
    return business_service.get_or_create_profile(db, str(current_user.id))

@router.put("/profile", response_model=BusinessProfileOut)
async def update_profile(
    data: BusinessProfileUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_user)], 
    db: Database = Depends(get_db)
):
    return business_service.update_profile(db, str(current_user.id), data)

@router.post("/logo", response_model=BusinessProfileOut)
async def upload_logo(
    current_user: Annotated[UserInDB, Depends(get_current_user)], 
    db: Database = Depends(get_db),
    file: UploadFile = File(...)
):
    return business_service.update_logo(db, str(current_user.id), file)

@router.get("/logo/{user_id}")
async def get_logo_image(
    user_id: str,
    db: Database = Depends(get_db)
):
    profile = db.business_profiles.find_one({"user_id": user_id})
    if not profile or not profile.get("logo_storage_key"):
        raise HTTPException(404, "Logo not found")
    
    try:
        file_stream = storage_service.get_file_stream(profile["logo_storage_key"])
        return Response(content=file_stream.read(), media_type="image/png")
    except Exception:
        raise HTTPException(404, "Logo file missing")