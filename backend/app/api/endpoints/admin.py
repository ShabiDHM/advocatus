# backend/app/api/endpoints/admin.py
# DEFINITIVE VERSION 5.0 (TYPE/LINT CORRECTION):
# 1. Corrected the @router.get path definition to use two separate decorators
#    instead of a List[str] to satisfy static type checkers (Pylance) and remove
#    the build-time error, while preserving the functional fix (allowing both /users/ and /users).
# 2. Previous argument order fix remains.

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Annotated
from pymongo.database import Database

from ...services import admin_service
from ...models.user import UserInDB
from ...models.admin import SubscriptionUpdate, UserAdminView
from .dependencies import get_current_admin_user, get_db


router = APIRouter(prefix="/users", tags=["Administrator"])

# PHOENIX PROTOCOL FIX: Use two decorators to allow both paths without a linter error.
@router.get("/", response_model=List[UserAdminView])
@router.get("", response_model=List[UserAdminView])
def get_all_users(
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """Retrieves a list of all users. (Admin only)"""
    return admin_service.get_all_users(db=db)

@router.put("/{user_id}/subscription", response_model=UserAdminView)
def update_user_subscription(
    user_id: str,
    subscription_data: SubscriptionUpdate,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """Updates a user's subscription details. (Admin only)"""
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