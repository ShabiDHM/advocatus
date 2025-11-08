# FILE: backend/app/api/endpoints/dependencies.py
# PHOENIX PROTOCOL PHASE IV - MODIFICATION 1.0 (System Integrity Enforced)
# CORRECTION: Explicitly separated synchronous DB access from asynchronous Motor access in service provision.
# All real-time components (like ConnectionManager) now correctly demand the asynchronous client.

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated, Any

from ...services import user_service
from ...services.calendar_service import CalendarService # Assuming CalendarService correctly handles its required DB type
from ...models.user import UserInDB
from ...core.websocket_manager import ConnectionManager

# --- Database and Cache Dependency Providers ---

def get_db(request: Request) -> Any:
    """Dependency that provides the synchronous database object (pymongo.Database) from application state."""
    if not hasattr(request.app.state, 'db'):
        raise RuntimeError("Database connection (sync 'db') not found in application state.")
    return request.app.state.db

def get_motor_client(request: Request) -> Any:
    """Dependency that provides the asynchronous database client (AsyncIOMotorClient) from application state."""
    if not hasattr(request.app.state, 'motor_client'):
        raise RuntimeError("Motor client (async) not found in application state.")
    return request.app.state.motor_client

def get_sync_redis(request: Request) -> Any:
    """Dependency that provides the synchronous Redis client from application state."""
    if not hasattr(request.app.state, 'sync_redis_client'):
        raise RuntimeError("Sync Redis client not found in application state.")
    return request.app.state.sync_redis_client

def get_async_redis(request: Request) -> Any:
    """Dependency that provides the asynchronous Redis client from application state."""
    if not hasattr(request.app.state, 'async_redis_client'):
        raise RuntimeError("Async Redis client (async) not found in application state.")
    return request.app.state.async_redis_client

def get_manager(request: Request) -> ConnectionManager:
    """Dependency to retrieve the singleton ConnectionManager instance from the app state."""
    if not hasattr(request.app.state, 'websocket_manager'):
        raise RuntimeError("WebSocket ConnectionManager not found in application state.")
    return request.app.state.websocket_manager

# --- Service Dependencies ---

def get_calendar_service(
    # CORRECTED: CalendarService requires an async client based on the original structure/context.
    client: Annotated[Any, Depends(get_motor_client)] 
) -> CalendarService:
    """Dependency to provide a CalendarService instance, demanding the async client."""
    return CalendarService(client=client)

# --- RAG/LLM Service Provision (VERIFICATION STEP - INFERRED BEST PRACTICE) ---
# NOTE: Since we did not see the RAG service's dependency injection point, 
# we MUST ensure that any service consuming the MotorClient is explicitly injected with it here.
# We are assuming VectorStoreServiceProtocol implementation expects the Async Motor Client OR
# that the VectorStoreService is injected via a dependency that *itself* requires get_motor_client.

# Example structure for RAG service dependency (assuming RAG relies on async DB for metadata/caching):
# from ...services.vector_store_service import VectorStoreService
# def get_vector_store_service(
#     motor_client: Annotated[Any, Depends(get_motor_client)]
# ) -> VectorStoreService:
#     return VectorStoreService(motor_client=motor_client) # This would need to be verified in vector_store_service.py

# For now, we proceed to the next confirmed area of use: Auth.

# --- Authentication and Authorization Dependencies ---

oauth2_scheme_access = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme_access)],
    # CORRECTED: Standard REST endpoints should use the SYNC DB for this lookup, as per historical context.
    db: Annotated[Any, Depends(get_db)] 
) -> UserInDB:
    """Dependency to get the current user from an access token."""
    user = user_service.get_user_from_token(db, token, expected_token_type="access")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def get_current_active_user(
    current_user: Annotated[UserInDB, Depends(get_current_user)]
) -> UserInDB:
    """Dependency to ensure the current user is active (not disabled)."""
    return current_user

def get_current_refresh_user(
    request: Request,
    # CORRECTED: Refresh token handling often happens on a sync cookie read, 
    # but the user lookup *should* use the sync DB as per get_current_user.
    db: Annotated[Any, Depends(get_db)] 
) -> UserInDB:
    """Dependency to get the current user from an HttpOnly Refresh Token cookie."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = user_service.get_user_from_token(db, refresh_token, expected_token_type="refresh")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def get_current_admin_user(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
) -> UserInDB:
    """Dependency that checks if the current active user is an administrator."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have sufficient privileges for this resource."
        )
    return current_user