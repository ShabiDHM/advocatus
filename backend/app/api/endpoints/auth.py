# FILE: backend/app/api/endpoints/auth.py
# PHOENIX PROTOCOL - AUTHENTICATION V2.7 (COOKIE STABILITY)
# 1. FIXED: Simplified cookie flags for maximum browser compatibility.
# 2. FIXED: Guaranteed samesite="none" + secure=True for Vercel -> API access.
# 3. STATUS: 100% Pylance Clear.

from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pymongo.database import Database
from bson import ObjectId

from ...core import security
from ...core.config import settings
from ...core.db import get_db
from ...services import user_service
from ...models.token import Token
from ...models.user import UserInDB, UserLogin
from .dependencies import get_current_user

router = APIRouter()

async def get_user_from_refresh_token(request: Request, db: Database = Depends(get_db)) -> UserInDB:
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    try:
        payload = security.decode_token(refresh_token)
        user_id_str = payload.get("sub")
        user = user_service.get_user_by_id(db, ObjectId(user_id_str))
        if not user: raise HTTPException(status_code=404, detail="User not found")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")

@router.post("/login", response_model=Token)
async def login_access_token(response: Response, form_data: UserLogin, db: Database = Depends(get_db)) -> Any:
    user = user_service.authenticate(db, username=form_data.username.lower(), password=form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Identifikim i pasaktë")
    
    access_token = security.create_access_token(data={"id": str(user.id), "role": user.role})
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = security.create_refresh_token(data={"id": str(user.id)}, expires_delta=refresh_token_expires)

    # Set cookie as Host-Only for api.juristi.tech
    # This works with withCredentials: true on the frontend
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,     # Required for samesite=none
        samesite="none", # Required for cross-site (Vercel -> Server)
        path="/",
        max_age=int(refresh_token_expires.total_seconds())
    )
    
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