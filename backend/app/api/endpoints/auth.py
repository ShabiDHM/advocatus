# FILE: backend/app/api/endpoints/auth.py
# DEFINITIVE VERSION 4.0 (PHOENIX PROTOCOL: FINAL CONFIGURATION LOCK)
# 1. CRITICAL FIX: The 'domain' parameter has been permanently removed from all 'set_cookie'
#    and 'delete_cookie' calls. This guarantees that the incorrect COOKIE_DOMAIN setting
#    from config.py can never be used, permanently resolving the 401 refresh error.

from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import Annotated
from pydantic import BaseModel
from pymongo.database import Database

from ...services import user_service
from ...models.user import UserInDB, UserCreate
from ...core.config import settings
from .dependencies import get_db, get_current_refresh_user

router = APIRouter(tags=["Authentication"])

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    username: str
    password: str

class MessageResponse(BaseModel):
    message: str

def set_auth_cookies(response: Response, tokens: dict):
    REFRESH_TOKEN_MAX_AGE_SECONDS = settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60
    
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        max_age=REFRESH_TOKEN_MAX_AGE_SECONDS,
        expires=REFRESH_TOKEN_MAX_AGE_SECONDS,
        path="/",
        # --- PHOENIX PROTOCOL FIX: DOMAIN PARAMETER REMOVED ---
        secure=True,
        httponly=True,
        samesite="none" 
    )

@router.post("/login", response_model=LoginResponse)
def login(
    response: Response,
    form_data: LoginRequest,
    db: Database = Depends(get_db)
):
    user = user_service.authenticate_user(form_data.username, form_data.password, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token_data = { "id": str(user.id), "role": user.role }
    tokens = user_service.create_both_tokens(data=token_data)
    set_auth_cookies(response, tokens)
    return LoginResponse(access_token=tokens["access_token"])

@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Database = Depends(get_db)):
    if user_service.get_user_by_username(db, user_in.username) or user_service.get_user_by_email(db, user_in.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username or email already exists."
        )
    user_service.create_user(db=db, user=user_in) 
    return MessageResponse(message="User successfully registered. Please log in.")

@router.post("/refresh", response_model=LoginResponse)
def refresh_access_token(
    response: Response,
    current_user: Annotated[UserInDB, Depends(get_current_refresh_user)]
):
    token_data = { "id": str(current_user.id), "role": current_user.role, "type": "refresh" }
    tokens = user_service.create_both_tokens(data=token_data)
    set_auth_cookies(response, tokens)
    return LoginResponse(access_token=tokens["access_token"])

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/",
        # --- PHOENIX PROTOCOL FIX: DOMAIN PARAMETER REMOVED ---
        secure=True,
        httponly=True,
        samesite="none"
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)