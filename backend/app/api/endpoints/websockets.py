# FILE: backend/app/api/endpoints/websockets.py
# PHOENIX PROTOCOL - PHASE 2 (SECURE & SCOPED)

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from typing import Dict, List

from ...api.endpoints.dependencies import get_current_user_ws
from ...models.user import UserInDB

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    """Manages active WebSocket connections on a per-case basis."""
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, case_id: str):
        await websocket.accept(subprotocol=websocket.scope['subprotocols'][0])
        if case_id not in self.active_connections:
            self.active_connections[case_id] = []
        self.active_connections[case_id].append(websocket)
        logger.info(f"New connection added to case_id: {case_id}. Total connections for case: {len(self.active_connections[case_id])}")

    def disconnect(self, websocket: WebSocket, case_id: str):
        if case_id in self.active_connections:
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

@router.websocket("/comms/case/{case_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    case_id: str,
    user: UserInDB = Depends(get_current_user_ws)
):
    """
    Authenticated, case-specific WebSocket endpoint.
    - Uses get_current_user_ws dependency to ensure the user is authenticated.
    - Manages connections per case_id.
    - Broadcasts messages to all clients connected to the same case.
    """
    # NOTE: The dependency will raise an exception if the user is not valid,
    # so we can trust the 'user' object is present and authenticated.
    
    await manager.connect(websocket, case_id)
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info(f"User '{user.email}' (ID: {user.id}) connected to case '{case_id}' from {client_host}")

    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Message from '{user.email}' for case '{case_id}': {data}")
            # For now, we broadcast the raw data. Phase 3 will involve structured messages.
            await manager.broadcast(f"User {user.id} says: {data}", case_id, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, case_id)
        logger.info(f"User '{user.email}' disconnected from case '{case_id}'")
    except Exception as e:
        logger.error(f"Error for user '{user.email}' in case '{case_id}': {e}", exc_info=True)
        manager.disconnect(websocket, case_id)