# FILE: backend/app/api/endpoints/admin.py
# PHOENIX PROTOCOL - ADMIN ROUTER V2.1 (DIRECT IMPORT FIX)
# 1. FIX: Changed module import to a direct relative path to resolve Pylance errors.

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Annotated

# DIRECT IMPORT: This is more robust against module resolution issues.
from app.services.admin_service import admin_service
from app.models.user import UserInDB
from app.models.admin import UserAdminView, UserUpdateRequest
from app.models.organization import OrganizationOut
from .dependencies import get_current_admin_user

# Prefix entire router with /admin
router = APIRouter(prefix="/admin", tags=["Administrator"])

# --- NEW: Organization Management ---

@router.get("/organizations", response_model=List[OrganizationOut])
async def get_all_organizations(
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
):
    """
    Retrieves a list of all organizations (tenants). (Admin only)
    """
    return await admin_service.get_all_organizations()

@router.put("/organizations/{org_id}/tier", response_model=OrganizationOut)
async def upgrade_organization_tier(
    org_id: str,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    tier: str = Body(..., embed=True), # Expects a simple {"tier": "TIER_2"}
):
    """
    Upgrades an organization's tier and seat limit. (Admin only)
    """
    if tier not in ["TIER_1", "TIER_2"]:
        raise HTTPException(status_code=400, detail="Invalid tier specified.")
        
    updated_org = await admin_service.update_organization_tier(org_id, tier)
    if not updated_org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    return updated_org

# --- LEGACY: User Management ---

@router.get("/users", response_model=List[UserAdminView])
async def get_all_users(
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
):
    """Retrieves a list of all users. (Admin only)"""
    return await admin_service.get_all_users_legacy()


@router.put("/users/{user_id}", response_model=UserAdminView)
async def update_user(
    user_id: str,
    update_data: UserUpdateRequest,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
):
    """Updates a user's details. (Admin only)"""
    updated_user = await admin_service.update_user_details_legacy(user_id, update_data)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return updated_user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
):
    """Permanently deletes a user and ALL their associated data."""
    if str(current_admin.id) == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account.")

    success = await admin_service.delete_user_and_data_legacy(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found or delete failed.")
    
    return None