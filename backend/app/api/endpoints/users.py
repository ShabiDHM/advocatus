from fastapi import APIRouter, Depends, status
from typing import Annotated
from pymongo.database import Database

from ...models.user import UserOut, UserInDB
# PHOENIX PROTOCOL CURE: Corrected the import statements to resolve the Pylance error.
# Each dependency is now imported from its correct source module.
from .dependencies import get_current_user
from ...core.db import get_db
from ...services import user_service

router = APIRouter()

@router.get("/me", response_model=UserOut)
def get_current_user_profile(
    current_user: Annotated[UserInDB, Depends(get_current_user)]
):
    """
    Retrieves the profile for the currently authenticated user.
    """
    # PHOENIX FIX: Explicitly construct the UserOut model from the UserInDB object.
    # This ensures correct serialization and that all fields, including 'role', are included in the response.
    return UserOut.model_validate(current_user)

# PHOENIX FIX: Corrected the invalid status code to resolve the container startup crash.
@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_own_account(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """
    Permanently deletes the current user and all their associated data.
    This is an irreversible action.
    """
    user_service.delete_user_and_all_data(user=current_user, db=db)
    # On success, a 204 No Content response is returned automatically.