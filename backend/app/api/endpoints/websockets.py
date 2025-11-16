# FILE: backend/app/api/endpoints/websockets.py
# PHOENIX PROTOCOL - PHASE 2 (DEFINITIVE AUTHENTICATION FIX)

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from typing import Dict, List, Optional
from pymongo.database import Database
from bson import ObjectId
from jose import JWTError, jwt

from ...api.endpoints.dependencies import get_db, TokenData
from ...models.user import UserInDB
from ...services import user_service
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    """Manages active WebSocket connections on a per-case basis."""
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, case_id: str, subprotocol: Optional[str]):
        # Accept the connection first with the provided subprotocol.
        # This is critical to prevent 1006 errors on auth failure.
        await websocket.accept(subprotocol=subprotocol)
        
        if case_id not in self.active_connections:
            self.active_connections[case_id] = []
        self.active_connections[case_id].append(websocket)
        logger.info(f"Connection accepted for case_id: {case_id}. Total connections for case: {len(self.active_connections[case_id])}")

    def disconnect(self, websocket: WebSocket, case_id: str):
        if case_id in self.active_connections and websocket in self.active_connections[case_id]:
            self.active_connections[case_id].remove(websocket)
            logger.info(f"Connection removed from case_id: {case_id}. Remaining: {len(self.active_connections[case_id])}")
            if not self.active_connections[case_id]:
                del self.active_connections[case_id]

    async def broadcast(self, message: str, case_id: str, sender: WebSocket):
        if case_id in self.active_connections:
            for connection in self.active_connections[case_id]:
                if connection != sender:
                    await connection.send_text(message)

manager = ConnectionManager()

async def get_user_from_websocket(websocket: WebSocket, db: Database) -> Optional[UserInDB]:
    """
    Manually authenticates a user from a WebSocket connection.
    Returns the user object on success, None on failure.
    """
    try:
        token = websocket.scope['subprotocols'][0]
    except IndexError:
        logger.warning("Authentication failed: No token provided in subprotocols.")
        return None

    secret_key = settings.SECRET_KEY
    if not secret_key:
        logger.error("FATAL: Server misconfiguration: SECRET_KEY not set.")
        return None

    try:
        payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
        user_id: Optional[str] = payload.get("id")
        if user_id is None:
            logger.warning(f"Authentication failed: Token is missing user ID. Payload: {payload}")
            return None
        token_data = TokenData(id=user_id)
        user = user_service.get_user_by_id(db, ObjectId(token_data.id))
        if user is None:
            logger.warning(f"Authentication failed: User with ID '{token_data.id}' not found.")
            return None
        return user
    except JWTError as e:
        logger.warning(f"Authentication failed: JWTError during token decoding: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during WebSocket authentication: {e}")
        return None

@router.websocket("/comms/case/{case_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    case_id: str,
    db: Database = Depends(get_db)
):
    """
    Accept-First, Authenticate-Second WebSocket Endpoint.
    This pattern is crucial for providing meaningful error codes to the client.
    """
    subprotocol = websocket.scope['subprotocols'][0] if websocket.scope['subprotocols'] else None
    await manager.connect(websocket, case_id, subprotocol)
    
    user = await get_user_from_websocket(websocket, db)

    if not user:
        # If authentication fails, close with a specific code and reason.
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid authentication token.")
        manager.disconnect(websocket, case_id) # Clean up the connection
        return

    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info(f"User '{user.email}' (ID: {user.id}) successfully authenticated for case '{case_id}' from {client_host}")

    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Message from '{user.email}' for case '{case_id}': {data}")
            await manager.broadcast(f"User {user.id} says: {data}", case_id, websocket)
    except WebSocketDisconnect:
        logger.info(f"User '{user.email}' disconnected from case '{case_id}'")
    except Exception as e:
        logger.error(f"An unexpected error occurred for user '{user.email}' in case '{case_id}': {e}", exc_info=True)
    finally:
        # Ensure cleanup happens regardless of how the loop exits.
        manager.disconnect(websocket, case_id)