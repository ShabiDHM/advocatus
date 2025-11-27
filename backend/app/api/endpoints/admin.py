# FILE: backend/app/api/endpoints/admin.py
# PHOENIX PROTOCOL - API ROUTING FIX
# 1. ROUTING FIX: The general update endpoint 'PUT /{user_id}' now calls the new 'update_user_details' service function.
# 2. SEMANTICS: The dedicated '/{user_id}/subscription' endpoint remains, correctly calling the subscription function.
# 3. RESULT: The API layer is now architecturally correct and routes requests to the proper business logic.

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Annotated
from pymongo.database import Database

from ...services import admin_service
from ...models.user import UserInDB
from ...models.admin import SubscriptionUpdate, UserAdminView
from .dependencies import get_current_admin_user, get_db

router = APIRouter(prefix="/users", tags=["Administrator"])

@router.get("", response_model=List[UserAdminView])
def get_all_users(
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """Retrieves a list of all users. (Admin only)"""
    return admin_service.get_all_users(db=db)

@router.put("/{user_id}", response_model=UserAdminView)
def update_user(
    user_id: str,
    update_data: SubscriptionUpdate,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """Updates a user's general details (role, status, email). (Admin only)"""
    try:
        # --- CORRECTED FUNCTION CALL ---
        updated_user = admin_service.update_user_details(
            user_id=user_id, 
            update_data=update_data, 
            db=db
        )
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return updated_user
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.put("/{user_id}/subscription", response_model=UserAdminView)
def update_user_subscription(
    user_id: str,
    subscription_data: SubscriptionUpdate,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """Updates a user's subscription-specific details. (Admin only)"""
    try:
        updated_user = admin_service.update_user_subscription(
            user_id=user_id, 
            sub_data=subscription_data, 
            db=db
        )
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return updated_user
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))