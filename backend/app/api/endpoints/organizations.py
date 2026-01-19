# FILE: backend/app/api/endpoints/organizations.py
# PHOENIX PROTOCOL - ORGANIZATIONS ROUTER V3.2 (MEMBER REMOVAL)
# 1. ADDED: 'DELETE /members/{member_id}' endpoint.
# 2. STATUS: Allows owners to remove staff safely.

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, Optional, List
from pymongo.database import Database
from pydantic import BaseModel, EmailStr, Field
import asyncio

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

@router.get("/me", response_model=Optional[OrganizationOut])
async def get_my_organization(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    org = await asyncio.to_thread(organization_service.get_organization_for_user, db, current_user)
    return org

@router.get("/members", response_model=List[UserOut])
async def get_organization_members(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    members = await asyncio.to_thread(organization_service.get_members, db, current_user)
    return members

@router.post("/invite", status_code=status.HTTP_200_OK)
async def invite_organization_member(
    invite_data: InviteRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    try:
        result = await asyncio.to_thread(organization_service.invite_member, db, owner=current_user, invitee_email=invite_data.email)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/accept-invite", status_code=status.HTTP_200_OK)
async def accept_invitation(
    request_data: AcceptInviteRequest,
    db: Database = Depends(get_db)
):
    try:
        result = await asyncio.to_thread(organization_service.accept_invitation, db, token=request_data.token, password=request_data.password, username=request_data.username)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to activate account.")

@router.delete("/members/{member_id}", status_code=status.HTTP_200_OK)
async def remove_organization_member(
    member_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """
    Owner removes a member. Data is transferred to Owner.
    """
    try:
        result = await asyncio.to_thread(organization_service.remove_member, db, owner=current_user, member_id=member_id)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))