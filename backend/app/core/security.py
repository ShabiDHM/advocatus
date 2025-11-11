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
    
    # Type safety: Ensure we have required fields with proper types
    user_id = data.get("id")
    if not user_id or not isinstance(user_id, str):
        raise ValueError("User ID ('id') must be provided and must be a string")
    
    to_encode.update({
        "exp": expire, 
        "sub": user_id, 
        "type": "access"
    })
    
    # Type safety: Ensure SECRET_KEY is not None
    if not settings.SECRET_KEY:
        raise ValueError("SECRET_KEY is not configured")
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY,  # This is now guaranteed to be str
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT refresh token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
        
    # Type safety: Ensure we have required fields with proper types
    user_id = data.get("id")
    if not user_id or not isinstance(user_id, str):
        raise ValueError("User ID ('id') must be provided and must be a string")
    
    to_encode.update({
        "exp": expire, 
        "sub": user_id, 
        "type": "refresh"
    })
    
    # Type safety: Ensure SECRET_KEY is not None
    if not settings.SECRET_KEY:
        raise ValueError("SECRET_KEY is not configured")
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY,  # This is now guaranteed to be str
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def decode_token(token: str) -> dict[str, Any]:
    """
    Decodes and verifies a JWT token, relying on the JOSE library for correct validation.
    """
    # Type safety: Validate token parameter
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token must be a non-empty string",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Type safety: Ensure SECRET_KEY is not None
    if not settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: SECRET_KEY not set",
        )
    
    try:
        # The python-jose library correctly handles Base64Url decoding and padding.
        # Manually altering the token string before decoding invalidates the signature.
        return jwt.decode(
            token, 
            settings.SECRET_KEY,  # This is now guaranteed to be str
            algorithms=[settings.ALGORITHM]
        )
    except JWTError as e:
        # Raise a standard HTTPException to be handled by FastAPI endpoints.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )