# FILE: backend/app/api/endpoints/dependencies.py
# PHOENIX PROTOCOL - DEPENDENCIES V4.0 (CLEAN GENERATOR & RESILIENT REDIS INJECTION)

from fastapi import Depends, HTTPException, status, WebSocket, Cookie
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated, Optional, Generator
from pymongo.database import Database
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone
import logging
import redis

from ...core.db import get_db, connect_to_redis
from ...core.config import settings
from ...services import user_service
from ...models.user import UserInDB

logger = logging.getLogger(__name__)

class TokenData(BaseModel):
    id: Optional[str] = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_sync_redis() -> Generator[redis.Redis, None, None]:
    """
    PHOENIX PROTOCOL - FIXED:
    Safely injects Redis client without trapping downstream route exceptions.
    Prevents storage/SSE route errors from being masked as Redis failures.
    """
    try:
        client = connect_to_redis()
    except Exception as e:
        logger.error(f"❌ Failed to obtain Redis client: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Redis service unavailable."
        )
    
    # Yield client directly so endpoint exceptions propagate naturally
    yield client


def is_subscription_expired(expiry_val) -> bool:
    """Helper function to check if subscription date has passed (UTC aware)."""
    if not expiry_val:
        return False  # "Pa Skadim" / Null means unlimited access
    
    try:
        if isinstance(expiry_val, datetime):
            expiry_date = expiry_val
        elif isinstance(expiry_val, str):
            clean_str = expiry_val.replace("Z", "+00:00")
            expiry_date = datetime.fromisoformat(clean_str)
        else:
            return False

        # Ensure timezone awareness
        if expiry_date.tzinfo is None:
            expiry_date = expiry_date.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        return now > expiry_date
    except Exception as e:
        logger.error(f"Error checking subscription expiry date: {e}")
        return False


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
        user_id_str: Optional[str] = payload.get("sub") or payload.get("id")
        
        # PHOENIX FIX: Check for empty string, not just None
        if not user_id_str:
            raise credentials_exception
        
        try:
            user_oid = ObjectId(user_id_str)
        except InvalidId:
            raise credentials_exception

    except (JWTError, ValidationError):
        raise credentials_exception
    
    user = user_service.get_user_by_id(db, user_oid)
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(
    current_user: Annotated[UserInDB, Depends(get_current_user)]
) -> UserInDB:
    user_role = str(getattr(current_user, 'role', '')).upper()
    
    # 1. System administrators are immune to expiration locks
    if user_role == 'ADMIN':
        return current_user

    # 2. Check manual account status flags
    account_status = str(getattr(current_user, 'status', 'active')).lower()
    if account_status == 'inactive':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aksesi i llogarisë suaj është çaktivizuar nga administratori."
        )

    sub_status = str(getattr(current_user, 'subscription_status', '')).upper()
    if sub_status != 'ACTIVE':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Abonimi juaj nuk është aktiv. Ju lutem kontaktoni administratorin ose renovoni planin."
        )

    # 3. Check automatic date expiration (UTC-aware)
    expiry_val = getattr(current_user, 'subscription_expiry', None)
    if is_subscription_expired(expiry_val):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Abonimi juaj ka skaduar. Ju lutem renovoni planin tuaj në Juristi.tech për të vazhduar."
        )
        
    return current_user


def get_current_admin_user(
    current_user: Annotated[UserInDB, Depends(get_current_user)]
) -> UserInDB:
    user_role = str(getattr(current_user, 'role', '')).upper()
    
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
        headers={"WWW-Authenticate": "Bearer"},
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
        user_id_str: Optional[str] = payload.get("sub") or payload.get("id")
        
        # PHOENIX FIX: Check for empty string, not just None
        if not user_id_str:
            raise credentials_exception
        
        try:
            user_oid = ObjectId(user_id_str)
        except InvalidId:
            raise credentials_exception

    except (JWTError, ValidationError):
        raise credentials_exception
    
    user = user_service.get_user_by_id(db, user_oid)
    
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
        token = websocket.query_params.get('token') or (websocket.scope.get('subprotocols') and websocket.scope['subprotocols'][0])
        if not token:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    secret_key = settings.SECRET_KEY
    if not secret_key:
        raise HTTPException(status_code=500, detail="Server misconfiguration: SECRET_KEY not set.")

    try:
        payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
        user_id_str: Optional[str] = payload.get("sub") or payload.get("id")
        
        # PHOENIX FIX: Check for empty string, not just None
        if not user_id_str:
            raise credentials_exception
        
        try:
            user_oid = ObjectId(user_id_str)
        except InvalidId:
            raise credentials_exception
            
    except (JWTError, ValidationError):
        raise credentials_exception
    
    user = user_service.get_user_by_id(db, user_oid)
    if user is None:
        raise credentials_exception
    
    return user