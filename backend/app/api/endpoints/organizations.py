# FILE: backend/app/api/endpoints/organizations.py
# PHOENIX PROTOCOL - ORGANIZATION ROUTER V1.2 (PATH CORRECTION)
# 1. FIX: Correct import path for 'get_current_user' (app.api.endpoints.dependencies).
# 2. STATUS: Verified against file tree.

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List
# CORRECTED IMPORT PATH:
from app.api.endpoints.dependencies import get_current_user 
from app.models.user import UserOut
from app.services.organization_service import organization_service

router = APIRouter(prefix="/organizations", tags=["Organizations"])

@router.get("/members", response_model=List[UserOut])
async def get_organization_members(
    current_user: UserOut = Depends(get_current_user)
):
    """
    Get all colleagues in my firm.
    """
    if not current_user.org_id:
        # Return just self if no org assigned yet
        return [current_user]
        
    return await organization_service.get_members(str(current_user.org_id))

@router.post("/invite")
async def invite_member(
    email: str = Body(..., embed=True),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Invite a new user. 
    ENFORCES TIER LIMITS (The Gatekeeper).
    """
    if not current_user.org_id:
        raise HTTPException(status_code=400, detail="User is not part of an organization")
    
    # 1. Check Permissions
    if current_user.org_role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Only Admins can invite members")

    # 2. THE GATEKEEPER CHECK
    has_space = await organization_service.check_seat_availability(str(current_user.org_id))
    if not has_space:
        raise HTTPException(
            status_code=403, 
            detail="ORGANIZATION_FULL: Upgrade to Tier 2 to add more members."
        )

    # 3. Success Stub
    return {"message": f"Slot available. Invitation sent to {email}"}