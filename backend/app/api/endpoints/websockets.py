# FILE: backend/app/api/endpoints/websockets.py
# PHOENIX PROTOCOL DEFINITIVE VERSION 22.5 (TYPE-SAFE FIX)
# 1. TYPE SAFETY: Fixed Pylance type error by using Optional[str] with proper import
# 2. ABSOLUTE IMPORTS: Maintained absolute import paths for reliability
# 3. CLEAN STRUCTURE: Removed all type annotation issues

import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Request
from pydantic import BaseModel

router = APIRouter(tags=["WebSockets"])
logger = logging.getLogger(__name__)

class DocumentUpdatePayload(BaseModel):
    id: str
    case_id: str
    status: str
    file_name: str
    uploadedAt: str
    summary: Optional[str] = None  # FIXED: Now type-safe with Optional

class BroadcastPayload(BaseModel):
    type: str = "document_update"
    payload: DocumentUpdatePayload


@router.websocket("/ws/case/{case_id}")
async def websocket_case_endpoint(
    websocket: WebSocket,
    case_id: str,
    token: str
):
    """WebSocket endpoint for real-time case updates and chat."""
    
    # Import services with absolute paths and error handling
    try:
        from app.services.user_service import get_user_from_token
    except ImportError as e:
        logger.error(f"Failed to import user_service: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    try:
        from app.services import chat_service
    except ImportError as e:
        logger.error(f"Failed to import chat_service: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    # Get dependencies from app state
    sync_db = websocket.app.state.db
    async_motor_client = websocket.app.state.motor_client
    async_db = async_motor_client.get_database()
    manager = websocket.app.state.websocket_manager

    user = None
    try:
        # Authenticate user using token
        user = get_user_from_token(db=sync_db, token=token, expected_token_type="access")
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        user_id = str(user.id)
        await manager.connect(websocket, case_id, user_id)
        logger.info(f"User {user.username} connected to case {case_id} via WebSocket")

        # Main message handling loop
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "chat_message":
                query_text = data.get("payload", {}).get("text")
                if query_text:
                    await chat_service.process_chat_message(
                        db=async_db, 
                        manager=manager, 
                        case_id=case_id,
                        user_query=query_text, 
                        user_id=user_id
                    )

    except WebSocketDisconnect:
        logger.info(f"User disconnected from case {case_id}")
    except Exception as e:
        logger.error(f"WebSocket error for case {case_id}: {e}", exc_info=True)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass
    finally:
        if user:
            manager.disconnect(case_id, str(user.id))
            logger.info(f"Cleaned up WebSocket connection for user {user.username}")


@router.post(
    "/internal/broadcast/document-update",
    status_code=status.HTTP_200_OK,
    tags=["Internal"],
    include_in_schema=False
)
async def broadcast_document_update(request: Request, payload: DocumentUpdatePayload):
    """Internal endpoint to broadcast document updates to connected clients."""
    manager = request.app.state.websocket_manager
    broadcast_message = BroadcastPayload(payload=payload).model_dump()

    await manager.broadcast_to_case(
        case_id=payload.case_id,
        message=broadcast_message
    )
    logger.info(f"Broadcast document update for case {payload.case_id}")
    return {"status": "broadcast scheduled"}