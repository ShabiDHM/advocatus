# FILE: backend/app/api/endpoints/api_keys.py
# DEFINITIVE VERSION 3.3 (FINAL CORRECTION):
# Reordered function parameters to place non-default arguments before default
# arguments, resolving the 'Non-default argument follows default argument' SyntaxError.

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from typing import List, Annotated

from .dependencies import get_current_active_user, get_db
from ...models.user import UserInDB
from ...models.api_key import ApiKeyCreate, ApiKeyOut
from ...services import api_key_service
from ...models.common import PyObjectId

router = APIRouter()

@router.post("/", response_model=ApiKeyOut, status_code=status.HTTP_201_CREATED)
async def add_user_api_key(
    # --- PHOENIX PROTOCOL FIX: Reordered parameters ---
    key_data: ApiKeyCreate,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Database = Depends(get_db)
):
    """
    Adds a new API key for the current user.
    """
    is_valid, message = await api_key_service.validate_api_key(key_data.provider, key_data.api_key)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API key validation failed: {message}",
        )
    
    new_key = await api_key_service.create_and_store_key(
        key_data=key_data, 
        user=current_user, 
        db=db
    )
    return ApiKeyOut.model_validate(new_key)

@router.get("/", response_model=List[ApiKeyOut])
async def get_all_user_api_keys(
    # --- PHOENIX PROTOCOL FIX: Reordered parameters ---
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Database = Depends(get_db)
):
    """
    Retrieves a list of all API keys configured by the current user.
    """
    return api_key_service.get_user_keys(user=current_user, db=db)

@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_api_key(
    # --- PHOENIX PROTOCOL FIX: Reordered parameters ---
    key_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Database = Depends(get_db)
):
    """
    Deletes one of the user's API keys by its ID.
    """
    try:
        key_object_id = PyObjectId(key_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid key ID format.")

    if not api_key_service.delete_user_key(
        key_id=key_object_id, 
        user=current_user, 
        db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or you do not have permission to delete it.",
        )
    return None