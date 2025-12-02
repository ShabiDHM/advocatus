# FILE: backend/app/api/endpoints/auth.py
# PHOENIX PROTOCOL - GATEKEEPER RESTORED
# 1. LOGIC: Reverted registration status to 'INACTIVE'.
# 2. SECURITY: Users cannot login until Admin sets them to 'ACTIVE'.

from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from pymongo.database import Database

from app.core import security
from app.core.config import settings
from app.core.db import get_db
from app.services import user_service
from app.models.token import Token
from app.models.user import UserInDB, UserCreate, UserLogin
from app.api.endpoints.dependencies import get_current_user

router = APIRouter()

# --- Local Schemas ---
class ChangePasswordSchema(BaseModel):
    old_password: str
    new_password: str

@router.post("/login", response_model=Token)
async def login_access_token(
    form_data: UserLogin,
    db: Database = Depends(get_db)
) -> Any:
    user = user_service.authenticate(
        db, username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    # PHOENIX: Gatekeeper Check
    if user.subscription_status == "INACTIVE":
        raise HTTPException(status_code=403, detail="Llogaria juaj është në pritje të miratimit nga Administratori.")
    
    user_service.update_last_login(db, str(user.id))

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    token_payload = {
        "sub": str(user.id),
        "id": str(user.id), 
        "role": user.role
    }

    token = security.create_access_token(
        data=token_payload,
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
    }

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    db: Database = Depends(get_db)
) -> Any:
    user = user_service.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(status_code=409, detail="A user with this email already exists.")
    
    user_by_username = user_service.get_user_by_username(db, username=user_in.username)
    if user_by_username:
        raise HTTPException(status_code=409, detail="A user with this username already exists.")
    
    # PHOENIX FIX: Default to INACTIVE to enforce Gatekeeper Protocol
    user_in.subscription_status = "INACTIVE" 
    
    user = user_service.create(db, obj_in=user_in)
    return user

@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: UserInDB = Depends(get_current_user)
) -> Any:
    if current_user.subscription_status == "INACTIVE":
        raise HTTPException(status_code=403, detail="ACCOUNT_PENDING")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    token_payload = {
        "sub": str(current_user.id),
        "id": str(current_user.id),
        "role": current_user.role
    }

    token = security.create_access_token(
        data=token_payload,
        expires_delta=access_token_expires
    )
    return {
        "access_token": token,
        "token_type": "bearer",
    }

@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordSchema, 
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    user_service.change_password(db, str(current_user.id), password_data.old_password, password_data.new_password)
    return {"message": "Password updated successfully"}