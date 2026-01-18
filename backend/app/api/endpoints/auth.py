# FILE: backend/app/api/endpoints/admin.py
# PHOENIX PROTOCOL - ADMIN ROUTER V4.1 (ASYNC THREADING)
# 1. FIX: Uses 'asyncio.to_thread' to run sync service methods non-blockingly.
# 2. STATUS: Aligned with 'case_service' architecture.

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Annotated
from pymongo.database import Database
import asyncio

# Service & Model Imports
from app.services.admin_service import admin_service
from app.models.user import UserInDB
from app.models.admin import UserAdminView, UserUpdateRequest
from app.models.organization import OrganizationOut

# Dependency Imports
from .dependencies import get_current_admin_user, get_db

router = APIRouter(tags=["Administrator"])

# --- NEW: Organization Management ---

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

# --- LEGACY: User Management ---

@router.get("/users", response_model=List[UserAdminView])
async def get_all_users(
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """Retrieves a list of all users. (Admin only)"""
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
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