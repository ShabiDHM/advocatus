# FILE: backend/app/api/endpoints/organizations.py
# PHOENIX PROTOCOL - ORGANIZATIONS ROUTER V4.1 (ROBUST GRANULAR RBAC PERSISTENCE)

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, Optional, List, Dict, Any
from pymongo.database import Database
from pydantic import BaseModel, EmailStr, Field
import asyncio
from bson import ObjectId

from app.models.user import UserInDB, UserOut
from app.models.organization import OrganizationOut
from app.api.endpoints.dependencies import get_current_user, get_db
from app.services.organization_service import organization_service

router = APIRouter()

class InviteRequest(BaseModel):
    email: EmailStr

class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8)
    username: str = Field(..., min_length=3)

class AccessUpdateRequest(BaseModel):
    org_access_level: str
    assigned_case_ids: List[str]

@router.get("/me", response_model=Optional[OrganizationOut])
async def get_my_organization(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    return await asyncio.to_thread(organization_service.get_organization_for_user, db, current_user)

@router.get("/members", response_model=List[UserOut])
async def get_organization_members(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    return await asyncio.to_thread(organization_service.get_members, db, current_user)

@router.put("/members/{member_id}/access", status_code=status.HTTP_200_OK)
async def update_member_access(
    member_id: str,
    data: AccessUpdateRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """
    Pronari ose Admini i zyrës përditëson autorizimet e qasjes për anëtarin.
    """
    is_owner = (
        current_user.org_role == "OWNER" or 
        current_user.role in ["ADMIN", "SUPER_ADMIN"]
    )
    if not is_owner:
        raise HTTPException(status_code=403, detail="Vetëm Pronari ose Admini mund të ndryshojë qasjen.")
    
    try:
        member_oid = ObjectId(member_id) if ObjectId.is_valid(member_id) else member_id
        
        # Pastrimi i ID-ve të lëndëve
        clean_case_ids = [str(cid).strip() for cid in data.assigned_case_ids if str(cid).strip()]

        org_id = getattr(current_user, "org_id", None)
        org_filter_conditions = []
        if org_id:
            org_filter_conditions.extend([{"org_id": org_id}, {"org_id": str(org_id)}])
            if ObjectId.is_valid(str(org_id)):
                org_filter_conditions.append({"org_id": ObjectId(str(org_id))})

        query = {"_id": member_oid}
        if org_filter_conditions:
            query["$or"] = org_filter_conditions

        # Përditësojmë MongoDB-në direkt
        db.users.update_one(
            query,
            {"$set": {
                "org_access_level": data.org_access_level,
                "assigned_case_ids": clean_case_ids
            }}
        )
        return {"status": "success", "org_access_level": data.org_access_level, "assigned_case_ids": clean_case_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/invite", status_code=status.HTTP_200_OK)
async def invite_organization_member(
    invite_data: InviteRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    try:
        return await asyncio.to_thread(organization_service.invite_member, db, owner=current_user, invitee_email=invite_data.email)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/accept-invite", status_code=status.HTTP_200_OK)
async def accept_invitation(request_data: AcceptInviteRequest, db: Database = Depends(get_db)):
    try:
        return await asyncio.to_thread(organization_service.accept_invitation, db, token=request_data.token, password=request_data.password, username=request_data.username)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to activate account.")

@router.delete("/members/{member_id}", status_code=status.HTTP_200_OK)
async def remove_organization_member(
    member_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    try:
        return await asyncio.to_thread(organization_service.remove_member, db, owner=current_user, member_id=member_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))