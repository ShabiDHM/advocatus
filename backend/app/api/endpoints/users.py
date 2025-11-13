# FILE: backend/app/api/endpoints/users.py

from fastapi import APIRouter, Depends, status
from typing import Annotated
from pymongo.database import Database

from ...models.user import UserOut, UserInDB
# PHOENIX PROTOCOL CURE: Changed the imported dependency to the correct one.
from .dependencies import get_current_user, get_db
from ...services import user_service

router = APIRouter()

@router.get("/me", response_model=UserOut)
def get_current_user_profile(
    # PHOENIX PROTOCOL CURE: Switched dependency from the overly restrictive
    # get_current_active_user to get_current_user. Any authenticated user,
    # regardless of subscription status, must be able to view their own profile.
    current_user: Annotated[UserInDB, Depends(get_current_user)]
):
    """
    Retrieves the profile for the currently authenticated user.
    """
    return current_user

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_own_account(
    # PHOENIX PROTOCOL CURE: Aligned the dependency for the delete action as well.
    # A user should be able to delete their account without an active subscription.
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """
    Permanently deletes the current user and all their associated data.
    This is an irreversible action.
    """
    user_service.delete_user_and_all_data(user=current_user, db=db)
    # On success, a 204 No Content response is returned automatically.