# FILE: backend/app/api/endpoints/users.py
# DEFINITIVE VERSION 2.0 (ARCHITECTURAL CORRECTION):
# Corrected the import path for 'get_db' to align with the centralized
# dependency architecture, resolving the final 'ImportError' startup crash.

from fastapi import APIRouter, Depends, status
from typing import Annotated
from pymongo.database import Database

from ...models.user import UserOut, UserInDB
# --- PHOENIX PROTOCOL FIX: Import all dependencies from the correct, centralized location ---
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