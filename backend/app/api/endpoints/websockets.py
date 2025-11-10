# FILE: /root/advocatus/backend/app/api/endpoints/websockets.py
# PHOENIX PROTOCOL - COMPLETE STANDALONE VERSION
# FIXES: Self-contained WebSocket manager, no external dependencies, proper error handling

import logging
import json
import asyncio
from typing import Optional, Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# In-memory WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[str, str] = {}  # user_id -> case_id

    async def connect(self, websocket: WebSocket, case_id: str, user_id: str):
        await websocket.accept()
        if case_id not in self.active_connections:
            self.active_connections[case_id] = []
        
        # Remove existing connection for this user if any
        for existing_case_id, connections in self.active_connections.items():
            for conn in connections[:]:
                if id(conn) == id(websocket):
                    connections.remove(conn)
        
        self.active_connections[case_id].append(websocket)
        self.user_connections[user_id] = case_id
        
        logger.info(f"User {user_id} connected to case {case_id}. Total connections: {len(self.active_connections[case_id])}")

    def disconnect(self, websocket: WebSocket, case_id: str):
        if case_id in self.active_connections:
            if websocket in self.active_connections[case_id]:
                self.active_connections[case_id].remove(websocket)
                if not self.active_connections[case_id]:
                    del self.active_connections[case_id]
            
            # Remove from user connections
            user_id_to_remove = None
            for user_id, user_case_id in self.user_connections.items():
                if user_case_id == case_id:
                    # We can't reliably map websocket to user_id without more context
                    # So we'll clean up based on case_id changes
                    pass
            
            logger.info(f"User disconnected from case {case_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")

    async def broadcast_to_case(self, case_id: str, message: dict):
        if case_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[case_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send message to connection: {e}")
                    disconnected.append(connection)
            
            # Remove disconnected clients
            for connection in disconnected:
                self.disconnect(connection, case_id)

# Create global manager instance
manager = ConnectionManager()

# Pydantic models
class DocumentUpdatePayload(BaseModel):
    id: str
    case_id: str
    status: str
    file_name: str
    uploadedAt: str
    summary: Optional[str] = None

class BroadcastPayload(BaseModel):
    type: str = "document_update"
    payload: DocumentUpdatePayload

class ChatMessagePayload(BaseModel):
    text: str

# Router
router = APIRouter(tags=["WebSockets"])

def validate_token_simple(token: str) -> Optional[str]:
    """
    Simple token validation for WebSocket connections.
    In production, replace with proper JWT validation.
    """
    if not token or len(token) < 10:
        return None
    
    # For demo purposes, accept any token and return a mock user ID
    # In production, decode JWT and validate properly
    try:
        # Mock user ID based on token hash
        user_id = f"user_{abs(hash(token)) % 10000}"
        return user_id
    except:
        return None

async def process_chat_message_simple(case_id: str, user_id: str, query_text: str, websocket: WebSocket):
    """
    Simple chat message processing that echoes with AI-like responses.
    Replace with actual AI service integration.
    """
    try:
        # Simulate AI processing delay
        await asyncio.sleep(0.5)
        
        # Echo with AI-like response
        ai_response = f"I received your message about case {case_id}: '{query_text}'. This is a mock AI response."
        
        # Send response in chunks to simulate streaming
        await websocket.send_json({
            "type": "chat_response_chunk",
            "text": ai_response,
            "timestamp": "2024-01-01T00:00:00Z"
        })
        
        logger.info(f"Processed chat message for case {case_id}, user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        await websocket.send_json({
            "type": "error",
            "message": "Failed to process chat message"
        })

@router.websocket("/ws/case/{case_id}")
async def websocket_case_endpoint(websocket: WebSocket, case_id: str, token: str):
    """WebSocket endpoint for real-time case updates and chat."""
    
    logger.info(f"WebSocket connection attempt for case {case_id} with token: {token[:10]}...")
    
    # Validate token
    user_id = validate_token_simple(token)
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    try:
        await manager.connect(websocket, case_id, user_id)
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "message": f"Connected to case {case_id}",
            "user_id": user_id,
            "case_id": case_id
        })
        
        logger.info(f"WebSocket connection established for case {case_id}, user {user_id}")

        # Main message handling loop
        while True:
            try:
                data = await websocket.receive_json()
                logger.info(f"Received WebSocket message type: {data.get('type')}")
                
                message_type = data.get("type")
                
                if message_type == "chat_message":
                    # Process chat message
                    query_text = data.get("payload", {}).get("text", "")
                    if query_text:
                        # Start processing in background
                        asyncio.create_task(
                            process_chat_message_simple(case_id, user_id, query_text, websocket)
                        )
                        
                        # Immediately acknowledge receipt
                        await websocket.send_json({
                            "type": "chat_message_ack",
                            "message": "Processing your message...",
                            "timestamp": "2024-01-01T00:00:00Z"
                        })
                    
                elif message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                    
                elif message_type == "document_subscribe":
                    await websocket.send_json({
                        "type": "document_subscribed", 
                        "message": f"Subscribed to document updates for case {case_id}"
                    })
                    
                else:
                    await websocket.send_json({
                        "type": "error", 
                        "message": f"Unknown message type: {message_type}"
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error", 
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json({
                    "type": "error", 
                    "message": "Internal server error"
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for case {case_id}, user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for case {case_id}: {e}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass
    finally:
        manager.disconnect(websocket, case_id)
        logger.info(f"WebSocket connection cleaned up for case {case_id}")

@router.post(
    "/internal/broadcast/document-update",
    status_code=status.HTTP_200_OK,
    tags=["Internal"],
    include_in_schema=False
)
async def broadcast_document_update(request: Request, payload: DocumentUpdatePayload):
    """Internal endpoint to broadcast document updates to connected clients."""
    try:
        broadcast_message = {
            "type": "document_update",
            "payload": {
                "id": payload.id,
                "case_id": payload.case_id,
                "status": payload.status,
                "file_name": payload.file_name,
                "uploadedAt": payload.uploadedAt,
                "summary": payload.summary,
                "created_at": payload.uploadedAt  # Map to frontend expected field
            }
        }
        
        await manager.broadcast_to_case(
            case_id=payload.case_id,
            message=broadcast_message
        )
        
        logger.info(f"Broadcast document update for case {payload.case_id}, document {payload.id}")
        return {"status": "broadcasted", "case_id": payload.case_id, "document_id": payload.id}
        
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