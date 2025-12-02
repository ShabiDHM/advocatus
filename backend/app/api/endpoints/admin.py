# FILE: backend/app/api/endpoints/admin.py
# PHOENIX PROTOCOL - ADMIN DELETE FIX
# 1. FEATURE: Added missing DELETE /{user_id} endpoint.
# 2. LOGIC: Wires the delete action to 'user_service.delete_user_and_all_data' for cascading cleanup.
# 3. SAFETY: Validates ObjectId and checks existence before deletion.

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Annotated
from pymongo.database import Database
from bson import ObjectId
from bson.errors import InvalidId

from ...services import admin_service, user_service
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

# PHOENIX ADDITION: The Missing Delete Endpoint
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    current_admin: Annotated[UserInDB, Depends(get_current_admin_user)],
    db: Database = Depends(get_db)
):
    """
    Permanently deletes a user and ALL their associated data (Cases, Files, Findings).
    (Admin only)
    """
    # 1. Validate ID format
    try:
        oid = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid User ID format")

    # 2. Prevent Admin Suicide (Optional but recommended)
    if str(current_admin.id) == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account from here.")

    # 3. Find User
    user_to_delete = user_service.get_user_by_id(db, oid)
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")

    # 4. Perform Cascading Delete
    try:
        user_service.delete_user_and_all_data(db=db, user=user_to_delete)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
        
    return None