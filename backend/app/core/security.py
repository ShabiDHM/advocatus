# FILE: backend/app/core/security.py
# PHOENIX PROTOCOL - SECURITY V6.1 (CLOCK-DRIFT TOLERANT)
# 1. FIX: Added 120-second leeway to token decoding to prevent cross-cloud clock drift failures.
# 2. STATUS: Aligned with Render/Vercel distributed environments.

import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import jwt, JWTError

from fastapi import HTTPException, status
from ..core.config import settings

# --- Password Hashing ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

# --- JWT Token Functions ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    user_id = data.get("id")
    if not user_id or not isinstance(user_id, str):
        raise ValueError("User ID ('id') must be provided and must be a string")
    
    to_encode.update({
        "exp": expire, 
        "sub": user_id, 
        "type": "access"
    })
    
    if not settings.SECRET_KEY:
        raise ValueError("SECRET_KEY is not configured")
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
        
    user_id = data.get("id")
    if not user_id or not isinstance(user_id, str):
        raise ValueError("User ID ('id') must be provided and must be a string")
    
    to_encode.update({
        "exp": expire, 
        "sub": user_id, 
        "type": "refresh"
    })
    
    if not settings.SECRET_KEY:
        raise ValueError("SECRET_KEY is not configured")
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_invitation_token(org_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode = {
        "exp": expire,
        "sub": email,
        "org_id": org_id,
        "type": "invite"
    }
    if not settings.SECRET_KEY:
        raise ValueError("SECRET_KEY is not configured")
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict[str, Any]:
    """Decodes and verifies a JWT token with clock-drift tolerance."""
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token must be a non-empty string",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: SECRET_KEY not set",
        )
    
    try:
        # PHOENIX FIX: Added 'leeway' of 120 seconds to options.
        # This prevents token validation crashes caused by minor clock-drift between Vercel and Render.
        return jwt.decode(
            token, 
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"leeway": 120} # 2 minutes tolerance
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )