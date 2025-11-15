# FILE: backend/app/api/endpoints/auth.py
# PHOENIX PROTOCOL - DEFINITIVE AND FINAL VERSION (IMPORT INTEGRITY)
# CORRECTION: The import statement for user models has been made explicit and absolute.
# This replaces the fragile relative import to resolve linter instability and align
# with best practices, ensuring all tools can reliably resolve the dependencies.

from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import Annotated
from pydantic import BaseModel
from pymongo.database import Database

# The corrected, absolute import path for robustness
from app.models.user import UserInDB, UserCreate
from app.services import user_service
from app.core.config import settings
from app.api.endpoints.dependencies import get_db, get_current_refresh_user

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
    current_user: Annotated[UserInDB, Depends(get_current_refresh_user)],
    db: Database = Depends(get_db)
):
    # PHOENIX PROTOCOL FIX: Fetch the latest user data from database to ensure role synchronization
    # This ensures token claims always reflect the current database state
    current_db_user = user_service.get_user_by_id(db, current_user.id)
    if not current_db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists"
        )
    
    token_data = { "id": str(current_db_user.id), "role": current_db_user.role }
    tokens = user_service.create_both_tokens(data=token_data)
    set_auth_cookies(response, tokens)
    return LoginResponse(access_token=tokens["access_token"])

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/",
        secure=True,
        httponly=True,
        samesite="none"
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)