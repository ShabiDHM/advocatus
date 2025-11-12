# FILE: backend/app/api/endpoints/websockets.py

import logging
import asyncio
# PHOENIX PROTOCOL CURE: Import Any to break the linter loop.
from typing import Annotated, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from pymongo.database import Database
from bson import ObjectId

from ...core.websocket_manager import manager
from ...models.user import UserInDB
from .dependencies import get_current_user_ws, get_db
from ...core.db import get_async_db
from ...services import case_service, chat_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws/case/{case_id}")
async def websocket_case_endpoint(
    websocket: WebSocket,
    case_id: str,
    user: Annotated[UserInDB, Depends(get_current_user_ws)],
    db: Database = Depends(get_db),
    # PHOENIX PROTOCOL CURE: Use 'Any' to definitively solve Pylance errors.
    async_db: Any = Depends(get_async_db)
):
    try:
        validated_case_id = ObjectId(case_id)
    except Exception:
        logger.warning(f"Invalid case_id format received: {case_id}")
        await websocket.close(code=status.WS_1007_INVALID_FRAMEWORK_PAYLOAD)
        return

    case = await asyncio.to_thread(
        case_service.get_case_by_id, db, validated_case_id, user
    )

    if not case:
        logger.warning(f"Unauthorized WebSocket access attempt by user {user.id} for case {case_id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id_str = str(user.id)
    await manager.connect(websocket, case_id, user_id_str)

    try:
        await websocket.send_json({
            "type": "connection_established",
            "message": f"Successfully connected to case {case_id}"
        })

        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "chat_message":
                payload = data.get("payload", {})
                text = payload.get("text")
                if text:
                    await chat_service.process_chat_message(
                        db=async_db,
                        manager=manager,
                        case_id=case_id,
                        user_query=text,
                        user_id=user_id_str
                    )

    except WebSocketDisconnect:
        logger.info(f"WebSocket received disconnect signal for case {case_id}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in WebSocket for case {case_id}: {e}", exc_info=True)
    finally:
        await manager.disconnect(websocket, case_id, user_id_str)
        logger.info(f"Cleaned up WebSocket connection for case {case_id}")

@router.post(
    "/internal/broadcast/document-update",
    status_code=status.HTTP_200_OK,
    tags=["Internal"],
    include_in_schema=False
)
async def broadcast_document_update(payload: dict):
    case_id = payload.get("case_id")
    if not case_id:
        logger.error("Broadcast failed: Missing case_id in payload")
        return {"status": "error", "message": "Missing case_id"}
    
    try:
        await manager.broadcast_to_case(case_id=case_id, message=payload)
        return {"status": "broadcasted", "case_id": case_id}
    except Exception as e:
        logger.error(f"Broadcast failed for case {case_id}: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}