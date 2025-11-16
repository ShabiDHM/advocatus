# FILE: backend/app/api/endpoints/websockets.py
# PHOENIX PROTOCOL - PATH ALIGNMENT

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/comms")
async def websocket_endpoint(websocket: WebSocket):
    """
    Baseline WebSocket endpoint.
    Path aligned to /api/v1/comms as required by Caddyfile routing.
    Accepts a connection, echoes any message received, and handles disconnection.
    """
    await websocket.accept()
    
    client_host = websocket.client.host if websocket.client else "unknown client"
    
    logger.info(f"WebSocket connection accepted from: {client_host} on /api/v1/comms")
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received message from {client_host}: {data}")
            await websocket.send_text(f"Message text was: {data}")
            logger.info(f"Echoed message to {client_host}")
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for: {client_host}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in WebSocket for {client_host}: {e}")
        await websocket.close(code=1011) # Internal Error