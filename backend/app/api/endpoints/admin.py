# FILE: backend/app/api/endpoints/admin.py
# PHOENIX PROTOCOL - ADMIN ROUTER V7.0 (MANAGEMENT API)
# 1. ADDED: 'update_subscription' endpoint for Date/Status changes.
# 2. ADDED: 'promote_user' endpoint for Firm upgrades.
# 3. STATUS: Synced with Admin Service V7.0.

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Annotated, Optional
from pymongo.database import Database
from pydantic import BaseModel
from datetime import datetime
import asyncio

from app.services.admin_service import admin_service
from app.models.user import UserInDB
from app.models.admin import UserAdminView, UserUpdateRequest
from app.models.organization import OrganizationOut
from .dependencies import get_current_admin_user, get_db

router = APIRouter(tags=["Administrator"])

# --- REQUEST MODELS ---
class SubscriptionUpdate(BaseModel):
    status: str # ACTIVE, INACTIVE, SUSPENDED
    expiry_date: Optional[datetime] = None
    plan_tier: Optional[str] = None

class PromoteRequest(BaseModel):
    firm_name: str
    plan_tier: str = "STARTUP" # Default to Startup (5 seats)

# --- ENDPOINTS ---

@router.get("/organizations", response_model=List[OrganizationOut])
def get_all_organizations(
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    # Sync call - FastAPI threads it
    return admin_service.get_all_organizations(db)

@router.post("/users/{user_id}/subscription", status_code=status.HTTP_200_OK)
async def update_user_subscription(
    user_id: str,
    data: SubscriptionUpdate,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """
    Updates a user's subscription status, expiry date, and plan.
    """
    success = await asyncio.to_thread(
        admin_service.update_subscription, 
        db, user_id, data.status, data.expiry_date, data.plan_tier
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update subscription.")
    return {"message": "Subscription updated successfully"}

@router.post("/users/{user_id}/promote", status_code=status.HTTP_200_OK)
async def promote_user_to_firm(
    user_id: str,
    data: PromoteRequest,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """
    Promotes a user to a Firm Owner (Organization).
    """
    success = await asyncio.to_thread(
        admin_service.promote_to_firm,
        db, user_id, data.firm_name, data.plan_tier
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to promote user.")
    return {"message": "User promoted to Firm successfully"}

# --- LEGACY COMPATIBILITY ---

@router.put("/organizations/{org_id}/tier", response_model=OrganizationOut)
def upgrade_organization_tier(
    org_id: str,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db),
    tier: str = Body(..., embed=True),
):
    # This is kept for backward compatibility if frontend still calls it
    # We map 'TIER_2' to 'STARTUP' logic internally if needed
    admin_service.update_subscription(db, org_id, "ACTIVE", None, "STARTUP" if tier == "TIER_2" else "SOLO")
    # Return dummy/updated org to satisfy response model
    return OrganizationOut(id=org_id, name="Updated", plan="STARTUP") 

@router.get("/users", response_model=List[UserAdminView])
def get_all_users(
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    return admin_service.get_all_users_legacy(db)

@router.put("/users/{user_id}", response_model=UserAdminView)
def update_user(
    user_id: str,
    update_data: UserUpdateRequest,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    updated_user = admin_service.update_user_details_legacy(db, user_id, update_data)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return updated_user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    if str(current_admin.id) == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account.")
    success = admin_service.delete_user_and_data_legacy(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found or delete failed.")
    return None