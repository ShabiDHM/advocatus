# FILE: backend/app/api/endpoints/organizations.py
# PHOENIX PROTOCOL - ORGANIZATION ROUTER V1.4 (JOIN ENDPOINT)
# 1. ADDED: /join endpoint to consume invitation tokens.
# 2. LOGIC: Validates token signature, type='invite', and creates user.

import os
from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List
from app.api.endpoints.dependencies import get_current_user 
from app.models.user import UserOut
from app.services.organization_service import organization_service
from app.core.security import create_invitation_token, decode_token, create_access_token

router = APIRouter(prefix="/organizations", tags=["Organizations"])

@router.get("/members", response_model=List[UserOut])
async def get_organization_members(
    current_user: UserOut = Depends(get_current_user)
):
    if not current_user.org_id:
        return [current_user]
    return await organization_service.get_members(str(current_user.org_id))

@router.post("/invite")
async def invite_member(
    email: str = Body(..., embed=True),
    current_user: UserOut = Depends(get_current_user)
):
    if not current_user.org_id:
        raise HTTPException(status_code=400, detail="User is not part of an organization")
    
    if current_user.org_role not in ["OWNER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Only Admins can invite members")

    has_space = await organization_service.check_seat_availability(str(current_user.org_id))
    if not has_space:
        raise HTTPException(
            status_code=403, 
            detail="ORGANIZATION_FULL: Upgrade to Tier 2 to add more members."
        )

    token = create_invitation_token(str(current_user.org_id), email)
    
    frontend_base = os.getenv("FRONTEND_URL", "http://localhost:5173")
    if frontend_base.endswith("/"):
        frontend_base = frontend_base[:-1]
        
    magic_link = f"{frontend_base}/join?token={token}"

    return {
        "message": "Invitation Link Generated",
        "invite_link": magic_link
    }

# PHOENIX NEW: The Join Endpoint
@router.post("/join")
async def join_organization(
    token: str = Body(...),
    username: str = Body(...),
    password: str = Body(...)
):
    """
    Register a new user via a valid invitation token.
    """
    # 1. Decode & Validate Token
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation token")
    
    if payload.get("type") != "invite":
        raise HTTPException(status_code=400, detail="Invalid token type")
        
    org_id = payload.get("org_id")
    email = payload.get("sub")
    
    if not org_id or not email:
        raise HTTPException(status_code=400, detail="Corrupt token data")

    # 2. Execute Join
    user = await organization_service.join_organization(org_id, email, username, password)
    
    # 3. Auto-Login (Return Access Token)
    access_token = create_access_token({"id": str(user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "org_id": str(user.org_id)
        }
    }