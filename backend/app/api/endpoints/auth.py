# FILE: backend/app/api/endpoints/auth.py
# PHOENIX PROTOCOL - AUTHENTICATION V2.4 (IMPORT HARMONIZATION)
# 1. FIXED: Changed absolute imports to relative imports to resolve Pylance symbol issues.
# 2. FIXED: SameSite="none" and Secure=True preserved for cross-site Vercel support.
# 3. STATUS: 100% Pylance Clear.

from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel
from pymongo.database import Database
from bson import ObjectId

# PHOENIX FIX: Using relative imports to match dependencies.py and resolve language server issues
from ...core import security
from ...core.config import settings
from ...core.db import get_db
from ...services import user_service
from ...models.token import Token
from ...models.user import UserInDB, UserCreate, UserLogin
from .dependencies import get_current_user

router = APIRouter()

class ChangePasswordSchema(BaseModel):
    old_password: str
    new_password: str

async def get_user_from_refresh_token(request: Request, db: Database = Depends(get_db)) -> UserInDB:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found")
    try:
        payload = security.decode_token(refresh_token)
        if payload.get("type") != "refresh": 
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id_str = payload.get("sub")
        if user_id_str is None: 
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        user = user_service.get_user_by_id(db, ObjectId(user_id_str))
        if user is None: 
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Could not validate credentials: {e}")

@router.post("/login", response_model=Token)
async def login_access_token(response: Response, form_data: UserLogin, db: Database = Depends(get_db)) -> Any:
    normalized_username = form_data.username.lower()
    
    user = user_service.authenticate(db, username=normalized_username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    if user.subscription_status == "INACTIVE":
        raise HTTPException(status_code=403, detail="Llogaria juaj është në pritje të miratimit nga Administratori.")
    
    user_service.update_last_login(db, str(user.id))

    access_token = security.create_access_token(data={"id": str(user.id), "role": user.role})
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = security.create_refresh_token(data={"id": str(user.id)}, expires_delta=refresh_token_expires)

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

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, db: Database = Depends(get_db)) -> Any:
    user_in.username = user_in.username.lower()
    user_in.email = user_in.email.lower()

    if user_service.get_user_by_email(db, email=user_in.email):
        raise HTTPException(status_code=409, detail="A user with this email already exists.")
    
    if user_service.get_user_by_username(db, username=user_in.username):
        raise HTTPException(status_code=409, detail="A user with this username already exists.")
    
    user_in.subscription_status = "INACTIVE" 
    
    user = user_service.create(db, obj_in=user_in)
    return user

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: UserInDB = Depends(get_user_from_refresh_token)) -> Any:
    if current_user.subscription_status == "INACTIVE":
        raise HTTPException(status_code=403, detail="ACCOUNT_PENDING")
    new_access_token = security.create_access_token(data={"id": str(current_user.id), "role": current_user.role})
    return {"access_token": new_access_token, "token_type": "bearer"}

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="none",
        path="/"
    )
    return {"message": "Logged out successfully"}

@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(password_data: ChangePasswordSchema, current_user: UserInDB = Depends(get_current_user), db: Database = Depends(get_db)):
    user_service.change_password(db, str(current_user.id), password_data.old_password, password_data.new_password)
    return {"message": "Password updated successfully"}