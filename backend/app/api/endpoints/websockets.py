# FILE: backend/app/api/endpoints/websockets.py
# PHOENIX PROTOCOL DEFINITIVE VERSION 21.0 (CURE ADMINISTERED)
# 1. CRITICAL FIX: The line `bearer_token = f"Bearer {token}"` has been removed.
# 2. The `get_user_from_token` function now receives the raw, correct token directly
#    from the query parameter, aligning WebSocket auth with HTTP auth and curing the
#    connection failure. This is the definitive fix.

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Request
from pydantic import BaseModel
from pymongo.database import Database
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.services.user_service import get_user_from_token
from app.services import chat_service
from app.core.websocket_manager import ConnectionManager

router = APIRouter(tags=["WebSockets"])
logger = logging.getLogger(__name__)

class DocumentUpdatePayload(BaseModel):
    id: str
    case_id: str
    status: str
    file_name: str
    uploadedAt: str
    summary: str | None = None

class BroadcastPayload(BaseModel):
    type: str = "document_update"
    payload: DocumentUpdatePayload


@router.websocket("/ws/case/{case_id}")
async def websocket_case_endpoint(
    websocket: WebSocket,
    case_id: str,
    token: str,
):
    sync_db: Database = websocket.app.state.db
    async_motor_client: AsyncIOMotorClient = websocket.app.state.motor_client
    async_db: AsyncIOMotorDatabase = async_motor_client.get_database()
    manager: ConnectionManager = websocket.app.state.websocket_manager

    user = None
    try:
        # PHOENIX PROTOCOL FIX: The raw token is now passed directly. The erroneous
        # line that added a "Bearer " prefix has been removed.
        user = get_user_from_token(db=sync_db, token=token, expected_token_type="access")
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        user_id = str(user.id)
        await manager.connect(websocket, case_id, user_id)

        while True:
            data = await websocket.receive_json()
            if data.get("type") == "chat_message":
                query_text = data.get("payload", {}).get("text")
                if query_text:
                    await chat_service.process_chat_message(
                        db=async_db, manager=manager, case_id=case_id,
                        user_query=query_text, user_id=user_id
                    )

    except WebSocketDisconnect:
        if user: logger.info(f"User {user.username} disconnected from case {case_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket for case {case_id}: {e}", exc_info=True)
    finally:
        if user:
            manager.disconnect(case_id, str(user.id))

@router.post(
    "/internal/broadcast/document-update",
    status_code=status.HTTP_200_OK,
    tags=["Internal"],
    include_in_schema=False
)
async def broadcast_document_update(request: Request, payload: DocumentUpdatePayload):
    manager: ConnectionManager = request.app.state.websocket_manager
    broadcast_message = BroadcastPayload(payload=payload).model_dump()
    
    await manager.broadcast_to_case(
        case_id=payload.case_id,
        message=broadcast_message
    )
    return {"status": "broadcast scheduled"}