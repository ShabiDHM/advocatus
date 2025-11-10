# FILE: backend/app/api/endpoints/users.py
# DEFINITIVE VERSION 2.1 (ADMIN ENDPOINT):
# 1. ADDED: New admin-only security dependency 'get_current_admin_user' to protect routes.
# 2. ADDED: New 'GET /admin/users' endpoint to provide the full, detailed user list.
# 3. This endpoint uses the new service function and 'AdminUserOut' response model to
#    securely deliver the complete data required by the admin dashboard.

from fastapi import APIRouter, Depends, status, HTTPException
from typing import Annotated, List
from pymongo.database import Database

from ...models.user import UserOut, UserInDB, AdminUserOut
from .dependencies import get_current_active_user, get_db
from ...services import user_service

router = APIRouter()

# --- Security Dependency for Admin-Only Routes ---
def get_current_admin_user(current_user: Annotated[UserInDB, Depends(get_current_active_user)]):
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have sufficient privileges for this resource"
        )
    return current_user

# --- Admin Routes ---
@router.get(
    "/admin/users",
    response_model=List[AdminUserOut],
    dependencies=[Depends(get_current_admin_user)]
)
def get_all_users_for_admin(db: Database = Depends(get_db)):
    """
    [ADMIN] Retrieves a detailed list of all users in the system, including
    case and document counts.
    """
    users_with_details = user_service.get_all_users_with_details(db=db)
    return users_with_details


# --- General User Routes ---
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