# FILE: /root/advocatus/backend/app/api/endpoints/websockets.py
# PHOENIX PROTOCOL - MINIMAL WORKING VERSION (NO DATABASE DEPENDENCIES)
# FIX: Completely removed database dependencies for WebSocket endpoints

import logging
import json
import asyncio
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

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
            if websocket in self.active_connections[case_id]:
                self.active_connections[case_id].remove(websocket)
                logger.info(f"WebSocket disconnected from case {case_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_case(self, case_id: str, message: dict):
        if case_id in self.active_connections:
            for connection in self.active_connections[case_id]:
                await connection.send_json(message)

manager = ConnectionManager()
router = APIRouter()

@router.websocket("/ws/test")
async def websocket_test(websocket: WebSocket):
    """Test WebSocket endpoint without authentication"""
    logger.info("WebSocket test endpoint called")
    await websocket.accept()
    
    try:
        await websocket.send_json({"status": "connected", "message": "Test WebSocket is working!"})
        
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
            
    except Exception as e:
        logger.error(f"WebSocket test error: {e}")
    finally:
        logger.info("WebSocket test connection closed")

@router.websocket("/ws/case/{case_id}")
async def websocket_case_endpoint(websocket: WebSocket, case_id: str, token: str = ""):
    """WebSocket endpoint for case updates - minimal version without auth"""
    logger.info(f"WebSocket connection attempt for case {case_id}")
    
    # Accept connection without authentication for now
    await websocket.accept()
    
    try:
        await manager.connect(websocket, case_id)
        
        await websocket.send_json({
            "type": "connection_established",
            "message": f"Connected to case {case_id}",
            "case_id": case_id
        })
        
        logger.info(f"WebSocket connection established for case {case_id}")

        while True:
            try:
                data = await websocket.receive_json()
                logger.info(f"Received WebSocket message: {data}")
                
                # Echo back for testing
                await websocket.send_json({
                    "type": "echo",
                    "received": data
                })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json({
                    "type": "error", 
                    "message": "Internal server error"
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for case {case_id}")
    except Exception as e:
        logger.error(f"WebSocket error for case {case_id}: {e}")
    finally:
        manager.disconnect(websocket, case_id)
        logger.info(f"WebSocket connection cleaned up for case {case_id}")

# HTTP endpoints for broadcasting
@router.post(
    "/internal/broadcast/document-update",
    status_code=status.HTTP_200_OK,
    tags=["Internal"],
    include_in_schema=False
)
async def broadcast_document_update(payload: dict):
    """Internal endpoint to broadcast document updates to connected clients."""
    try:
        case_id = payload.get("case_id")
        if case_id:
            await manager.broadcast_to_case(
                case_id=case_id,
                message=payload
            )
            logger.info(f"Broadcast document update for case {case_id}")
            return {"status": "broadcasted", "case_id": case_id}
        else:
            return {"status": "error", "message": "Missing case_id"}
        
    except Exception as e:
        logger.error(f"Broadcast failed: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/ws/debug/connections")
async def debug_connections():
    """Debug endpoint to check active WebSocket connections."""
    return {
        "active_cases": list(manager.active_connections.keys()),
        "connection_counts": {case_id: len(connections) for case_id, connections in manager.active_connections.items()},
        "total_connections": sum(len(connections) for connections in manager.active_connections.values())
    }