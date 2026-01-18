# FILE: backend/app/api/endpoints/admin.py
# PHOENIX PROTOCOL - ADMIN ROUTER V7.0 (VALIDATION FIX)
# 1. FIX: Removed manual Pydantic model instantiation.
# 2. LOGIC: Returns raw dictionaries; FastAPI 'response_model' handles validation.
# 3. STATUS: Resolves Pylance 'Arguments missing' and '** mapping' errors.

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Annotated, Any, Dict
from pymongo.database import Database
import asyncio

from app.services.admin_service import admin_service
from app.models.user import UserInDB
from app.models.admin import UserAdminView, UserUpdateRequest
from app.models.organization import OrganizationOut
from .dependencies import get_current_admin_user, get_db

router = APIRouter(tags=["Administrator"])

@router.get("/organizations", response_model=List[OrganizationOut])
async def get_all_organizations(
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """
    Retrieves a list of all organizations (tenants). (Admin only)
    """
    return await asyncio.to_thread(admin_service.get_all_organizations, db)

@router.put("/organizations/{org_id}/tier", response_model=OrganizationOut)
async def upgrade_organization_tier(
    org_id: str,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db),
    tier: str = Body(..., embed=True),
):
    """
    Upgrades an organization's tier and seat limit. (Admin only)
    """
    if tier not in ["TIER_1", "TIER_2"]:
        raise HTTPException(status_code=400, detail="Invalid tier specified.")
    
    updated_org = await asyncio.to_thread(admin_service.update_organization_tier, db, org_id, tier)
    if not updated_org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    return updated_org

@router.get("/users", response_model=List[UserAdminView])
async def get_all_users(
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """Retrieves a list of all users. (Admin only)"""
    # PHOENIX FIX: Return raw dicts. FastAPI validates against response_model.
    return await asyncio.to_thread(admin_service.get_all_users_legacy, db)

@router.put("/users/{user_id}", response_model=UserAdminView)
async def update_user(
    user_id: str,
    update_data: UserUpdateRequest,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """Updates a user's details. (Admin only)"""
    updated_user = await asyncio.to_thread(admin_service.update_user_details_legacy, db, user_id, update_data)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found.")
    # PHOENIX FIX: Return raw dict. FastAPI validates against response_model.
    return updated_user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """Permanently deletes a user and ALL their associated data."""
    if str(current_admin.id) == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account.")
    
    success = await asyncio.to_thread(admin_service.delete_user_and_data_legacy, db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found or delete failed.")
    return None