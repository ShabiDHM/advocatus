# FILE: backend/app/api/endpoints/dependencies.py

from fastapi import Depends, HTTPException, status, WebSocket, Query
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated, Optional, Generator, Any
from pymongo.database import Database
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError
from bson import ObjectId
import redis

# PHOENIX PROTOCOL CURE: Import the async DB provider and the CalendarService
from ...core.db import get_db, get_redis_client, get_async_db
from ...core.config import settings
from ...services import user_service
from ...services.calendar_service import CalendarService
from ...models.user import UserInDB

class TokenData(BaseModel):
    id: Optional[str] = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_sync_redis() -> Generator[redis.Redis, None, None]:
    """Dependency to provide a synchronous Redis client instance."""
    client = next(get_redis_client())
    if client is None:
         raise HTTPException(status_code=500, detail="Redis client not initialized.")
    yield client

# PHOENIX PROTOCOL CURE: Add the missing dependency provider for CalendarService.
def get_calendar_service(db: Any = Depends(get_async_db)) -> CalendarService:
    """
    Dependency to create and provide an instance of the CalendarService.
    This service requires an asynchronous database client.
    """
    return CalendarService(client=db)

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

def get_current_admin_user(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
) -> UserInDB:
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have sufficient privileges."
        )
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