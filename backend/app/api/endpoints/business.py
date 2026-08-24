# FILE: backend/app/api/endpoints/business.py
# PHOENIX PROTOCOL - BUSINESS ROUTER V2.0 (GRAPH EXCISED • CLEAN PROFILE & LOGO STREAMER)

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import Annotated, Optional
from pymongo.database import Database
import logging

from ...models.user import UserInDB
from ...models.business import BusinessProfileInDB, BusinessProfileUpdate
from ...services.business_service import BusinessService
from .dependencies import get_current_user, get_db

router = APIRouter(tags=["Business"])
logger = logging.getLogger(__name__)


def get_business_service(db: Database = Depends(get_db)) -> BusinessService:
    return BusinessService(db)


@router.get("/profile", response_model=BusinessProfileInDB)
async def get_business_profile(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    service: BusinessService = Depends(get_business_service)
):
    return service.get_or_create_profile(str(current_user.id))


@router.put("/profile", response_model=BusinessProfileInDB)
async def update_business_profile(
    data: BusinessProfileUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    service: BusinessService = Depends(get_business_service)
):
    return service.update_profile(str(current_user.id), data)


@router.put("/logo", response_model=BusinessProfileInDB)
async def upload_business_logo(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    service: BusinessService = Depends(get_business_service),
    file: UploadFile = File(...)
):
    return service.update_logo(str(current_user.id), file)


@router.get("/logo/{user_id}")
async def get_business_logo(
    user_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    service: BusinessService = Depends(get_business_service)
):
    stream, media_type = service.get_logo_stream(user_id)
    return StreamingResponse(stream, media_type=media_type)