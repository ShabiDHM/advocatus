# FILE: backend/app/api/endpoints/dependencies.py
# PHOENIX PROTOCOL - CASE SENSITIVITY FIX
# 1. CRITICAL FIX: Role checks are now case-insensitive (.upper()).
# 2. RESULT: 'admin' (lowercase) correctly matches 'ADMIN' (uppercase).

from fastapi import Depends, HTTPException, status, WebSocket, Cookie
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated, Optional, Generator
from pymongo.database import Database
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError
from bson import ObjectId
import redis

from ...core.db import get_db, get_redis_client, get_async_db
from ...core.config import settings
from ...services import user_service
from ...models.user import UserInDB

class TokenData(BaseModel):
    id: Optional[str] = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_sync_redis() -> Generator[redis.Redis, None, None]:
    client = next(get_redis_client())
    if client is None:
         raise HTTPException(status_code=500, detail="Redis client not initialized.")
    yield client

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
    """
    Validates that the user is allowed to access the system.
    """
    # FIX: Robust Case-Insensitive Check
    user_role = str(current_user.role).upper()
    
    # Admins are always considered 'active' regardless of subscription status.
    if user_role == 'ADMIN':
        return current_user

    # Regular users must have an active subscription
    # We also normalize the subscription status check just in case
    sub_status = str(current_user.subscription_status).upper() if current_user.subscription_status else ""
    
    if sub_status != 'ACTIVE':
        raise HTTPException(status_code=403, detail="User subscription is not active.")
        
    return current_user

def get_current_admin_user(
    current_user: Annotated[UserInDB, Depends(get_current_user)]
) -> UserInDB:
    """
    Validates that the user has ADMIN privileges.
    """
    # FIX: Robust Case-Insensitive Check
    user_role = str(current_user.role).upper()
    
    if user_role != 'ADMIN':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have sufficient privileges."
        )
    return current_user

def get_current_refresh_user(
    token_from_cookie: Annotated[Optional[str], Cookie(alias="refresh_token")] = None,
    db: Database = Depends(get_db)
) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-authenticate": "Bearer"},
    )

    if token_from_cookie is None:
        raise credentials_exception
    
    secret_key = settings.SECRET_KEY
    if not secret_key:
        raise HTTPException(status_code=500, detail="Server misconfiguration: SECRET_KEY not set.")

    try:
        payload = jwt.decode(token_from_cookie, secret_key, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise credentials_exception
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

async def get_current_user_ws(
    websocket: WebSocket,
    db: Database = Depends(get_db)
) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials for WebSocket"
    )
    
    try:
        token = websocket.scope['subprotocols'][0]
    except IndexError:
        raise credentials_exception

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