# FILE: backend/app/api/endpoints/users.py
# PHOENIX PROTOCOL - USERS V2.1 (WHITELIST — IDENTITY ONLY)
# V2.1: `get_current_user` → `get_current_user_identity` — useri mund të
#       shohë/fshijë profilin edhe pa abonim aktiv (UX: shoh statusin "në shqyrtim").
from fastapi import APIRouter, Depends, status
from typing import Annotated
from pymongo.database import Database

from ...models.user import UserOut, UserInDB
from .dependencies import get_current_user_identity
from ...core.db import get_db
from ...services import user_service

router = APIRouter()


@router.get("/me", response_model=UserOut)
def get_current_user_profile(
    current_user: Annotated[UserInDB, Depends(get_current_user_identity)]
):
    """
    Retrieves the profile for the currently authenticated user.
    V2.1: Lëre të hapur për user me INACTIVE — shoh statusin e abonimit.
    """
    return UserOut.model_validate(current_user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_own_account(
    current_user: Annotated[UserInDB, Depends(get_current_user_identity)],
    db: Database = Depends(get_db)
):
    """
    Permanently deletes the current user and all their associated data.
    V2.1: Lëre të hapur — user mund të fshijë llogarinë pa abonim.
    """
    user_service.delete_user_and_all_data(user=current_user, db=db)