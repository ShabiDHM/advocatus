# FILE: backend/app/api/endpoints/admin.py
# PHOENIX PROTOCOL - ADMIN ROUTER V50.4 (ONE-TIME PASS REMOVED)
# V50.4: ONE-TIME PASS REMOVED —
#        - Hequr `/cases/{case_id}/unlock` dhe `/cases/{case_id}/lock`.
#        - Hequr `UnlockActionRequest` model.
#        - Hequr `DEFAULT_CASE_UNLOCK_PRICE_EUR`.
#        - `/cases` mbetet (listim), `/users` mbetet, `/organizations` mbetet.
#        - Modeli: vetëm abonim mujor (Solo 49.99€ / Team 99.99€).
# V50.3: PRICE ALIGNMENT — Default unlock price: 99.00 → 99.99.
# V50.2: Default unlock price: 9.99 → 99.00.
# V50.1: `{org_id}` → `{organization_id}` në URL/parametrin e upgrade_organization_tier.
# V50.0: 1-CLICK CASE UNLOCK & INSTANT ACTIVATION.

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Annotated, Optional
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


# =========================================================================
# 📋 LISTIMI I LËNDËVE PËR ADMININ
# =========================================================================

@router.get("/cases")
async def get_all_cases_admin(
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """V50.4: Kthen listën e të gjitha lëndëve (pa fusha unlock)."""
    return await asyncio.to_thread(admin_service.get_all_cases_for_admin_dashboard, db)


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


@router.put("/organizations/{organization_id}/tier")
async def upgrade_organization_tier(
    organization_id: str,
    tier_data: TierUpdateRequest,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    try:
        oid = ObjectId(organization_id)
    except Exception:
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