# FILE: /root/advocatus/backend/app/api/endpoints/websockets.py
# PHOENIX PROTOCOL - MINIMAL WORKING VERSION
# SIMPLIFIED: Removes complex validation to get basic WebSocket working first

import logging
import json
import asyncio
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, case_id: str):
        await websocket.accept()
        if case_id not in self.active_connections:
            self.active_connections[case_id] = []
        self.active_connections[case_id].append(websocket)
        logger.info(f"WebSocket connected to case {case_id}")

    def disconnect(self, websocket: WebSocket, case_id: str):
        if case_id in self.active_connections:
            self.active_connections[case_id].remove(websocket)
            logger.info(f"WebSocket disconnected from case {case_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_case(self, case_id: str, message: dict):
        if case_id in self.active_connections:
            for connection in self.active_connections[case_id]:
                await connection.send_json(message)

manager = ConnectionManager()
router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/case/{case_id}")
async def websocket_case_endpoint(websocket: WebSocket, case_id: str, token: str = ""):
    """Minimal WebSocket endpoint - basic connection test"""
    
    logger.info(f"WebSocket connection attempt for case {case_id}")
    
    # TEMPORARY: Accept all connections without authentication
    # This will help us isolate if the issue is authentication or something else
    try:
        await manager.connect(websocket, case_id)
        
        # Send immediate connection confirmation
        await websocket.send_json({
            "type": "connection_established", 
            "message": f"Connected to case {case_id}",
            "case_id": case_id
        })
        
        logger.info(f"WebSocket connection established for case {case_id}")

        # Keep connection alive and handle messages
        while True:
            try:
                data = await websocket.receive_json()
                logger.info(f"Received: {data}")
                
                # Echo back for testing
                await websocket.send_json({
                    "type": "echo",
                    "received": data
                })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                await websocket.send_json({"type": "error", "message": str(e)})
                
    except Exception as e:
        logger.error(f"WebSocket connection failed: {e}")
    finally:
        manager.disconnect(websocket, case_id)
        logger.info(f"WebSocket cleaned up for case {case_id}")

# Keep the existing endpoints for compatibility
@router.websocket("/ws/test")
async def websocket_test(websocket: WebSocket):
    """Simple test endpoint without authentication"""
    await websocket.accept()
    await websocket.send_json({"message": "Test WebSocket is working!"})
    
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        logger.info("Test WebSocket disconnected")