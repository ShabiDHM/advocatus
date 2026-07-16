# FILE: backend/app/api/endpoints/auth.py
# PHOENIX PROTOCOL - AUTHENTICATION V3.1 (CROSS-DOMAIN & LINTER CLEAN)
# 1. FIX: Added missing UserLogin import.
# 2. FIX: Removed hardcoded 'domain' constraint to allow Render <-> Vercel cookies.
# 3. FIX: Enforced SameSite='none' for cross-origin authentication.
# 4. STATUS: Stable session persistence.

from datetime import timedelta
from typing import Any
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pymongo.database import Database
from bson import ObjectId

from ...core import security
from ...core.config import settings
from ...core.db import get_db
from ...services import user_service
from ...models.token import Token
# PHOENIX FIX: Added UserLogin to the import list
from ...models.user import UserInDB, UserCreate, UserOut, UserLogin
from .dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: Database = Depends(get_db)) -> Any:
    existing_user = user_service.get_user_by_username(db, user_in.username)
    if existing_user: raise HTTPException(status_code=400, detail="Username already registered")
    existing_email = user_service.get_user_by_email(db, user_in.email)
    if existing_email: raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = user_service.create(db, obj_in=user_in)
    return new_user

async def get_user_from_refresh_token(request: Request, db: Database = Depends(get_db)) -> UserInDB:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        logger.warning("Refresh token missing in request cookies")
        raise HTTPException(status_code=401, detail="Refresh token missing")
    try:
        payload = security.decode_token(refresh_token)
        user_id_str = payload.get("sub")
        user = user_service.get_user_by_id(db, ObjectId(user_id_str))
        if not user: raise HTTPException(status_code=404, detail="User not found")
        return user
    except Exception as e:
        logger.error(f"Invalid refresh token: {e}")
        raise HTTPException(status_code=401, detail="Invalid session")

@router.post("/login", response_model=Token)
async def login_access_token(response: Response, form_data: UserLogin, db: Database = Depends(get_db)) -> Any:
    user = user_service.authenticate(db, username=form_data.username.lower(), password=form_data.password)
    if not user: raise HTTPException(status_code=401, detail="Identifikim i pasaktë")
    
    access_token = security.create_access_token(data={"id": str(user.id), "role": user.role})
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = security.create_refresh_token(data={"id": str(user.id)}, expires_delta=refresh_token_expires)

    # PHOENIX FIX: Cross-Domain Cookie Configuration
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,          # Required for HTTPS (Render/Vercel)
        samesite="none",      # Required for Cross-Domain
        path="/",
        max_age=int(refresh_token_expires.total_seconds())
    )
    
    logger.info(f"Login successful for user {user.id}")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: UserInDB = Depends(get_user_from_refresh_token)) -> Any:
    new_access_token = security.create_access_token(data={"id": str(current_user.id), "role": current_user.role})
    return {"access_token": new_access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="none",
        path="/"
    )
    return {"message": "Logged out"}