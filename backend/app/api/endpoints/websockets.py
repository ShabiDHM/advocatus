# FILE: backend/app/api/endpoints/websockets.py
# PHOENIX PROTOCOL DEFINITIVE VERSION 22.0 (SYNTAX & DEPLOYMENT CURE)
# 1. SYNTAX FIX: Imported 'Union' from 'typing' and updated type hints like 'str | None'
#    to the universally compatible 'Union[str, None]'. This resolves all Pylance static
#    analysis errors ('reportInvalidTypeForm') without changing the logic.
# 2. This file is now logically correct AND syntactically robust.

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Request
from pydantic import BaseModel
from pymongo.database import Database
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Union  # <-- PHOENIX CURE: Import Union for compatibility

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
    summary: Union[str, None] = None # <-- PHOENIX CURE: Use Union for compatibility

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