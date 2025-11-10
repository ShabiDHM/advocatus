# FILE: backend/app/api/endpoints/users.py
# DEFINITIVE VERSION 3.0 (ARCHITECTURAL CLEANUP):
# 1. REMOVED: All admin-related endpoints have been removed from this file.
# 2. This eliminates the duplicate route and clarifies that this router's responsibility
#    is solely for general, authenticated user actions ('/me').

from fastapi import APIRouter, Depends, status
from typing import Annotated
from pymongo.database import Database

from ...models.user import UserOut, UserInDB
from .dependencies import get_current_active_user, get_db
from ...services import user_service

router = APIRouter()

@router.get("/me", response_model=UserOut)
def get_current_user_profile(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """
    Retrieves the profile for the currently authenticated user.
    """
    return current_user

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_own_account(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Database = Depends(get_db)
):
    """
    Permanently deletes the current user and all their associated data.
    This is an irreversible action.
    """
    user_service.delete_user_and_all_data(user=current_user, db=db)
    # On success, a 204 No Content response is returned automatically.