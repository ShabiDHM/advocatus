# FILE: backend/app/api/endpoints/auth.py
# PHOENIX PROTOCOL - AUTHENTICATION V2.9 (ADD REGISTRATION ENDPOINT)
# 1. ADDED: /register endpoint to create new users.
# 2. INTEGRITY: All existing login, refresh, logout functionality preserved.
# 3. STATUS: Resolves 404 on registration.

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
from ...models.user import UserInDB, UserLogin, UserCreate, UserOut
from .dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: Database = Depends(get_db)) -> Any:
    """
    Register a new user.
    - Username and email must be unique.
    - Password is hashed before storage.
    - New user is created with subscription_status = "INACTIVE" (handled in service).
    """
    # Check if username already exists
    existing_user = user_service.get_user_by_username(db, user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    # Check if email already exists
    existing_email = user_service.get_user_by_email(db, user_in.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create the user
    new_user = user_service.create(db, obj_in=user_in)
    logger.info(f"New user registered: {new_user.id}")
    return new_user

async def get_user_from_refresh_token(request: Request, db: Database = Depends(get_db)) -> UserInDB:
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        logger.warning("Refresh token missing in request cookies")
        raise HTTPException(status_code=401, detail="Refresh token missing")
    try:
        payload = security.decode_token(refresh_token)
        user_id_str = payload.get("sub")
        user = user_service.get_user_by_id(db, ObjectId(user_id_str))
        if not user:
            logger.error(f"User not found for id: {user_id_str}")
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except Exception as e:
        logger.error(f"Invalid refresh token: {e}")
        raise HTTPException(status_code=401, detail="Invalid session")

@router.post("/login", response_model=Token)
async def login_access_token(response: Response, form_data: UserLogin, db: Database = Depends(get_db)) -> Any:
    user = user_service.authenticate(db, username=form_data.username.lower(), password=form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for username: {form_data.username}")
        raise HTTPException(status_code=401, detail="Identifikim i pasaktë")
    
    access_token = security.create_access_token(data={"id": str(user.id), "role": user.role})
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = security.create_refresh_token(data={"id": str(user.id)}, expires_delta=refresh_token_expires)

    # Set cookie with domain for cross-site access
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        domain=".juristi.tech",          # Allow subdomains
        path="/",
        max_age=int(refresh_token_expires.total_seconds())
    )
    
    logger.info(f"Login successful for user {user.id}, cookie set with domain .juristi.tech")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: UserInDB = Depends(get_user_from_refresh_token)) -> Any:
    new_access_token = security.create_access_token(data={"id": str(current_user.id), "role": current_user.role})
    logger.info(f"Token refreshed for user {current_user.id}")
    return {"access_token": new_access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="none",
        domain=".juristi.tech",
        path="/"
    )
    logger.info("Logout successful, cookie deleted")
    return {"message": "Logged out"}