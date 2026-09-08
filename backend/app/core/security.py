# FILE: backend/app/core/security.py
# PHOENIX PROTOCOL - SECURITY V8.0 (CENTRALIZED REDIS & BRUTE-FORCE PROTECTION)
# 1. ENHANCED: Uses get_redis_instance() from core/db.py for better connection pool management.
# 2. ENHANCED: Added password strength validation and secure random string generation.
# 3. PRESERVED: All existing JWT functions with clock-drift tolerance and bcrypt password hashing.
# 4. STATUS: Production-ready, GDPR-aligned.

import bcrypt
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import jwt, JWTError

from fastapi import HTTPException, status
from ..core.config import settings

logger = logging.getLogger(__name__)

# --- Redis client retrieval ---
def get_redis_client():
    """
    Returns a Redis client using the centralized pool from core/db.py.
    Returns None if Redis is not configured or connection fails.
    """
    try:
        from .db import get_redis_instance
        return get_redis_instance()
    except Exception as e:
        logger.warning(f"Redis unavailable: {e}. Disabling rate limiting.")
        return None

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

def check_password_strength(password: str) -> bool:
    """
    Validates password strength for GDPR compliance.
    Requires at least 8 characters, one uppercase, one lowercase, one digit, one special character.
    Returns True if strong, False otherwise.
    """
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    if not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?/" for c in password):
        return False
    return True

# --- Secure Random String Generation ---

def generate_secure_random_string(length: int = 32) -> str:
    """Generate a URL-safe, cryptographically secure random string."""
    return secrets.token_urlsafe(length)

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
        return jwt.decode(
            token, 
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"leeway": 120}
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

# --- Brute-Force Protection (Rate Limiting via Redis) ---

LOGIN_ATTEMPTS_KEY = "login_attempts:{user_id}"
MAX_LOGIN_ATTEMPTS = 5
LOGIN_ATTEMPTS_WINDOW = 15 * 60  # 15 minutes in seconds

def increment_login_attempts(user_id: str) -> int:
    """
    Increment and return the number of failed login attempts for a user.
    Uses Redis with expiration window.
    """
    client = get_redis_client()
    if not client:
        logger.warning("Redis not available; login attempt limiting disabled.")
        return 0
    key = LOGIN_ATTEMPTS_KEY.format(user_id=user_id)
    try:
        attempts = client.incr(key)
        if attempts == 1:
            client.expire(key, LOGIN_ATTEMPTS_WINDOW)
        return attempts
    except Exception as e:
        logger.error(f"Failed to increment login attempts: {e}")
        return 0

def check_login_attempts(user_id: str) -> bool:
    """
    Returns True if the user is allowed to attempt login (i.e., under the limit).
    """
    client = get_redis_client()
    if not client:
        return True  # No Redis, no limit
    key = LOGIN_ATTEMPTS_KEY.format(user_id=user_id)
    try:
        attempts = client.get(key)
        if attempts is None:
            return True
        return int(attempts) < MAX_LOGIN_ATTEMPTS
    except Exception as e:
        logger.error(f"Failed to check login attempts: {e}")
        return True  # Fail open if Redis error

def reset_login_attempts(user_id: str):
    """Reset login attempts after successful authentication."""
    client = get_redis_client()
    if not client:
        return
    key = LOGIN_ATTEMPTS_KEY.format(user_id=user_id)
    try:
        client.delete(key)
    except Exception as e:
        logger.error(f"Failed to reset login attempts: {e}")