# FILE: backend/app/api/endpoints/auth.py
# PHOENIX PROTOCOL - AUTHENTICATION V2.6 (PORTABLE SESSION FIX)
# 1. FIXED: Removed 'domain' attribute to allow browser to accept cookie regardless of Vercel URL.
# 2. FIXED: Guaranteed SameSite="none" and Secure=True for Cross-Origin context.
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
    # Try to get refresh token from cookies
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
        
    try:
        payload = security.decode_token(refresh_token)
        if payload.get("type") != "refresh":
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
             
        user_id_str = payload.get("sub")
        user = user_service.get_user_by_id(db, ObjectId(user_id_str))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

@router.post("/login", response_model=Token)
async def login_access_token(response: Response, form_data: UserLogin, db: Database = Depends(get_db)) -> Any:
    user = user_service.authenticate(db, username=form_data.username.lower(), password=form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Identifikim i pasaktë")
    
    if user.subscription_status == "INACTIVE":
        raise HTTPException(status_code=403, detail="Llogaria juaj është në pritje të miratimit.")

    access_token = security.create_access_token(data={"id": str(user.id), "role": user.role})
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = security.create_refresh_token(data={"id": str(user.id)}, expires_delta=refresh_token_expires)

    # PHOENIX FIX: Remove domain restriction for Vercel compatibility
    # SameSite="none" + Secure=True allows cross-site cookie transmission
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
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