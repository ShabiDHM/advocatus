# FILE: backend/app/core/security.py
# DEFINITIVE VERSION 1.5 - PHOENIX PROTOCOL ARCHITECTURAL VALIDATION:
# Removed flawed manual Base64 padding logic from decode_token, which was corrupting the JWT
# and causing the 'Signature verification failed' error. The JOSE library handles this internally.

from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import jwt, JWTError

from fastapi import HTTPException, status
from ..core.config import settings

# --- Password Hashing Context ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks if the plain password matches the hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes the plain password."""
    return pwd_context.hash(password)

# --- JWT Token Functions ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "sub": data.get("id"), "type": "access"})
    
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT refresh token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire, "sub": data.get("id"), "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def decode_token(token: str) -> dict[str, Any]:
    """
    Decodes and verifies a JWT token, relying on the JOSE library for correct validation.
    """
    try:
        # --- PHOENIX PROTOCOL FINAL FIX: REMOVED ALL MANUAL PADDING LOGIC ---
        # The python-jose library correctly handles Base64Url decoding and padding.
        # Manually altering the token string before decoding invalidates the signature.
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as e:
        # Raise a standard HTTPException to be handled by FastAPI endpoints.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )