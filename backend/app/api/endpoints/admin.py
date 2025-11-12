# FILE: backend/app/api/endpoints/admin.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Annotated
from pymongo.database import Database

from ...services import admin_service
from ...models.user import UserInDB
from ...models.admin import SubscriptionUpdate, UserAdminView
from .dependencies import get_current_admin_user, get_db

router = APIRouter(prefix="/users", tags=["Administrator"])

@router.get("/", response_model=List[UserAdminView], include_in_schema=False)
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