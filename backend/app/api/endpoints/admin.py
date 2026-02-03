# FILE: backend/app/api/endpoints/admin.py
# PHOENIX PROTOCOL - ADMIN ROUTER V9.0 (TIER EXPANSION COMPLETE)
# 1. IMPLEMENTED: 'PUT /organizations/{org_id}/tier' to bridge Admin UI to Organization Service.
# 2. INTEGRATED: 'organization_service' for capacity management.
# 3. STATUS: 100% Functional End-to-End.

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Annotated, Optional
from pymongo.database import Database
from enum import Enum
from bson import ObjectId
import asyncio
from pydantic import BaseModel

# Service Layer
from app.services.admin_service import admin_service
from app.services.organization_service import organization_service

# Domain Models
from app.models.user import UserInDB
from app.models.admin import UserAdminView, UserUpdateRequest 
from .dependencies import get_current_admin_user, get_db

router = APIRouter(tags=["Administrator"])

# --- MODELS ---

class TierUpdateRequest(BaseModel):
    tier: str # 'DEFAULT' or 'GROWTH'

# --- ENDPOINTS ---

@router.get("/users", response_model=List[UserAdminView])
async def get_all_users(
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """
    Retrieves all users with flattened organization data for the dashboard.
    """
    return await asyncio.to_thread(admin_service.get_all_users_for_dashboard, db)

@router.put("/users/{user_id}", response_model=UserAdminView)
async def update_user(
    user_id: str,
    update_data: UserUpdateRequest,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """
    Unified endpoint to update both user details and their complete subscription state.
    """
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Convert Enums to values for MongoDB storage
    for key, value in update_dict.items():
        if isinstance(value, Enum):
            update_dict[key] = value.value
            
    updated_user = await asyncio.to_thread(
        admin_service.update_user_and_subscription, db, user_id, update_dict
    )
    
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or update failed.")
    
    return updated_user

@router.put("/organizations/{org_id}/tier")
async def upgrade_organization_tier(
    org_id: str,
    tier_data: TierUpdateRequest,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """
    Allows Admin to explicitly change an organization's plan tier and user limits.
    """
    try:
        oid = ObjectId(org_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid Organization ID format.")

    try:
        # PHOENIX: Trigger the organization service upgrade logic
        success = await asyncio.to_thread(
            organization_service.update_organization_plan, 
            db, 
            oid, 
            tier_data.tier
        )
        return {"success": success, "message": f"Organization updated to {tier_data.tier}"}
    except HTTPException as e:
        # Pass through specific capacity check errors (e.g., "Cannot downgrade...")
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """
    Permanently deletes a user and all associated data.
    """
    if str(current_admin.id) == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account.")
    
    success = await asyncio.to_thread(admin_service.delete_user_and_data, db, user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="User not found or delete failed.")
    
    return None