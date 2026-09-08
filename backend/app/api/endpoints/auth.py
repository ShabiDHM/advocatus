# FILE: backend/app/api/endpoints/auth.py
# PHOENIX PROTOCOL - AUTHENTICATION V4.0 (GDPR & SECURITY HARDENED)
# 1. ADDED: Login rate limiting using Redis (brute-force protection).
# 2. ADDED: Password strength validation during registration.
# 3. ADDED: Consent check during registration (if required).
# 4. ADDED: Soft-delete check during authentication.
# 5. PRESERVED: Cross-domain cookie configuration and token handling.

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
from ...models.user import UserInDB, UserCreate, UserOut, UserLogin
from .dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: Database = Depends(get_db)) -> Any:
    # GDPR: Check password strength
    if not security.check_password_strength(user_in.password):
        raise HTTPException(
            status_code=400,
            detail="Fjalëkalimi duhet të ketë të paktën 8 karaktere, një shkronjë të madhe, një të vogël, një numër dhe një simbol."
        )
    
    # GDPR: Consent must be given if required by your privacy policy
    if not user_in.consent_to_process:
        raise HTTPException(
            status_code=400,
            detail="Duhet të jepni pëlqimin për përpunimin e të dhënave personale."
        )
    
    existing_user = user_service.get_user_by_username(db, user_in.username)
    if existing_user: raise HTTPException(status_code=400, detail="Username already registered")
    existing_email = user_service.get_user_by_email(db, user_in.email)
    if existing_email: raise HTTPException(status_code=400, detail="Email already registered")
    
    # Set consent date if not provided
    if not user_in.consent_date:
        from datetime import datetime, timezone
        user_in.consent_date = datetime.now(timezone.utc)
    
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
        # GDPR: Do not allow deleted users to refresh
        if user.is_deleted:
            raise HTTPException(status_code=401, detail="Account is deleted")
        return user
    except Exception as e:
        logger.error(f"Invalid refresh token: {e}")
        raise HTTPException(status_code=401, detail="Invalid session")

@router.post("/login", response_model=Token)
async def login_access_token(response: Response, form_data: UserLogin, db: Database = Depends(get_db)) -> Any:
    username = form_data.username.lower()
    user = user_service.get_user_by_username(db, username)
    
    # Rate limiting: check if user is locked out
    if user:
        user_id_str = str(user.id)
        if not security.check_login_attempts(user_id_str):
            raise HTTPException(
                status_code=429,
                detail="Shumë përpjekje të dështuara. Provoni përsëri pas 15 minutash."
            )
    else:
        # If user doesn't exist, still use username as key to prevent user enumeration
        user_id_str = f"username:{username}"
        if not security.check_login_attempts(user_id_str):
            raise HTTPException(
                status_code=429,
                detail="Shumë përpjekje të dështuara. Provoni përsëri pas 15 minutash."
            )
    
    authenticated_user = user_service.authenticate(db, username=username, password=form_data.password)
    if not authenticated_user:
        # Increment failed attempts
        security.increment_login_attempts(user_id_str)
        raise HTTPException(status_code=401, detail="Identifikim i pasaktë")
    
    # GDPR: Check if user is deleted
    if authenticated_user.is_deleted:
        raise HTTPException(status_code=401, detail="Llogaria është fshirë")
    
    # Reset login attempts after successful login
    security.reset_login_attempts(str(authenticated_user.id))
    
    access_token = security.create_access_token(data={"id": str(authenticated_user.id), "role": authenticated_user.role})
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = security.create_refresh_token(data={"id": str(authenticated_user.id)}, expires_delta=refresh_token_expires)

    # PHOENIX FIX: Cross-Domain Cookie Configuration
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=int(refresh_token_expires.total_seconds())
    )
    
    logger.info(f"Login successful for user {authenticated_user.id}")
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