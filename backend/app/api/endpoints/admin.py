# FILE: backend/app/api/endpoints/admin.py
# PHOENIX PROTOCOL - ADMIN ROUTER V50.0 (1-CLICK CASE UNLOCK & INSTANT ACTIVATION)

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Annotated, Optional, Dict, Any
from pymongo.database import Database
from enum import Enum
from bson import ObjectId
import asyncio
from pydantic import BaseModel, Field

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
    tier: str

class UnlockActionRequest(BaseModel):
    payment_method: str = Field("CASH", description="CASH, MBANKING, ose CARD")
    amount: float = Field(9.99)
    note: Optional[str] = "Zhbllokuar nga Paneli i Adminit"


# =========================================================================
# 💰 MENAXHIMI ME 1 KLIKIM I LËNDËVE & PAGESAVE (PËR SUPER ADMININ)
# =========================================================================

@router.get("/cases")
async def get_all_cases_admin(
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """
    Kthen listën e të gjitha lëndëve me statusin e bllokimit dhe pagesës për Panelin e Adminit.
    """
    return await asyncio.to_thread(admin_service.get_all_cases_for_admin_dashboard, db)


@router.post("/cases/{case_id}/unlock")
async def unlock_case_1click(
    case_id: str,
    body: Optional[UnlockActionRequest] = Body(default=None),
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)] = None,
    db: Database = Depends(get_db)
):
    """
    ZHBLLOKON LËNDËN ME 1 KLIKIM:
    Përdoret kur klienti ju paguan me Cash në zyrë ose ju dërgon para me m-Banking.
    """
    p_method = body.payment_method if body else "CASH"
    p_amount = body.amount if body else 9.99
    p_note = body.note if body else "Zhbllokim me 1 klikim nga Admini"
    admin_id = str(current_admin.id) if current_admin else "ADMIN"

    result = await asyncio.to_thread(
        admin_service.unlock_case_by_admin,
        db=db,
        case_id=case_id,
        payment_method=p_method,
        amount=p_amount,
        admin_user_id=admin_id,
        note=p_note
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Zhbllokimi dështoi."))

    return result


@router.post("/cases/{case_id}/lock")
async def lock_case_1click(
    case_id: str,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """
    E kthen lëndën në gjendje të bllokuar nëse është e nevojshme.
    """
    result = await asyncio.to_thread(admin_service.lock_case_by_admin, db, case_id)
    return result


# =========================================================================
# 👥 MENAXHIMI I PËRDORUESVE DHE ORGANIZATAVE
# =========================================================================

@router.get("/users", response_model=List[UserAdminView])
async def get_all_users(
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    return await asyncio.to_thread(admin_service.get_all_users_for_dashboard, db)


@router.put("/users/{user_id}", response_model=UserAdminView)
async def update_user(
    user_id: str,
    update_data: UserUpdateRequest,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if isinstance(value, Enum):
            update_dict[key] = value.value
            
    updated_user = await asyncio.to_thread(
        admin_service.update_user_and_subscription, db, user_id, update_dict
    )
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Përdoruesi nuk u gjet.")
    return updated_user


@router.put("/organizations/{org_id}/tier")
async def upgrade_organization_tier(
    org_id: str,
    tier_data: TierUpdateRequest,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    try:
        oid = ObjectId(org_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid Organization ID format.")

    try:
        success = await asyncio.to_thread(
            organization_service.update_organization_plan, 
            db, 
            oid, 
            tier_data.tier
        )
        return {"success": success, "message": f"Organizata u përditësua në {tier_data.tier}"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    if str(current_admin.id) == user_id:
        raise HTTPException(status_code=400, detail="Nuk mund të fshini llogarinë tuaj të adminit.")
    
    success = await asyncio.to_thread(admin_service.delete_user_and_data, db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Përdoruesi nuk u gjet.")
    return None