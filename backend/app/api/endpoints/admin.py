# FILE: backend/app/api/endpoints/admin.py
# PHOENIX PROTOCOL - ADMIN ROUTER V8.1 (IMPORT FIX)
# 1. FIXED: Corrected 'pantic' typo to 'pydantic'.
# 2. FIXED: Added missing 'Enum' import.
# 3. STATUS: Now fully synchronized with Admin Service V9.0.

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Annotated, Optional
from pymongo.database import Database
from pydantic import BaseModel
from datetime import datetime
from enum import Enum # PHOENIX FIX: Added missing import
import asyncio

from app.services.admin_service import admin_service
from app.models.user import UserInDB, AccountType, SubscriptionTier, ProductPlan
from app.models.admin import UserAdminView
from app.models.organization import OrganizationOut
from .dependencies import get_current_admin_user, get_db

router = APIRouter(tags=["Administrator"])

# --- UNIFIED USER UPDATE REQUEST MODEL ---
class UserUpdateRequest(BaseModel):
    # User Details
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    
    # Subscription Matrix
    account_type: Optional[AccountType] = None
    subscription_tier: Optional[SubscriptionTier] = None
    product_plan: Optional[ProductPlan] = None
    
    # Lifecycle
    subscription_status: Optional[str] = None
    subscription_expiry: Optional[datetime] = None

# --- ENDPOINTS ---

@router.get("/organizations", response_model=List[OrganizationOut])
async def get_all_organizations(
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    return await asyncio.to_thread(admin_service.get_all_organizations, db)

@router.get("/users", response_model=List[UserAdminView])
async def get_all_users(
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    return await asyncio.to_thread(admin_service.get_all_users_with_details, db)

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
    
    for key, value in update_dict.items():
        if isinstance(value, Enum):
            update_dict[key] = value.value
            
    updated_user = await asyncio.to_thread(
        admin_service.update_user_and_subscription, db, user_id, update_dict
    )
    
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or update failed.")
    
    return updated_user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    if str(current_admin.id) == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account.")
    
    success = await asyncio.to_thread(admin_service.delete_user_and_data, db, user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="User not found or delete failed.")
    
    return None