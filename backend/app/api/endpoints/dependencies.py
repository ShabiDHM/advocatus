# FILE: backend/app/api/endpoints/dependencies.py

from fastapi import Depends, HTTPException, status, WebSocket, Query
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated, Optional
from pymongo.database import Database
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError
from bson import ObjectId

from ...core.db import get_db
from ...core.config import settings
from ...services import user_service
from ...models.user import UserInDB

class TokenData(BaseModel):
    id: Optional[str] = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Database = Depends(get_db)
) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    secret_key = settings.SECRET_KEY
    if not secret_key:
        raise HTTPException(status_code=500, detail="Server misconfiguration: SECRET_KEY not set.")

    try:
        payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
        user_id: Optional[str] = payload.get("id")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(id=user_id)
    except (JWTError, ValidationError):
        raise credentials_exception
    
    user = user_service.get_user_by_id(db, ObjectId(token_data.id))
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(
    current_user: Annotated[UserInDB, Depends(get_current_user)]
) -> UserInDB:
    if current_user.subscription_status != 'active':
        raise HTTPException(status_code=403, detail="User subscription is not active.")
    return current_user

def get_current_refresh_user(
    refresh_token: str,
    db: Database = Depends(get_db)
) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-authenticate": "Bearer"},
    )
    
    secret_key = settings.SECRET_KEY
    if not secret_key:
        raise HTTPException(status_code=500, detail="Server misconfiguration: SECRET_KEY not set.")

    try:
        payload = jwt.decode(refresh_token, secret_key, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise credentials_exception
        user_id: Optional[str] = payload.get("id")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(id=user_id)
    except (JWTError, ValidationError):
        raise credentials_exception
    
    user = user_service.get_user_by_id(db, ObjectId(token_data.id))
    
    if user is None or user.subscription_status != 'active':
        raise credentials_exception
    return user

async def get_current_user_ws(
    token: str = Query(...),
    db: Database = Depends(get_db)
) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials for WebSocket"
    )
    if not token:
        raise credentials_exception

    secret_key = settings.SECRET_KEY
    if not secret_key:
        raise credentials_exception

    try:
        payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
        user_id: Optional[str] = payload.get("id")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(id=user_id)
    except (JWTError, ValidationError):
        raise credentials_exception
    
    user = user_service.get_user_by_id(db, ObjectId(token_data.id))
    
    if user is None or user.subscription_status != 'active':
        raise credentials_exception
        
    return user