# FILE: backend/app/api/endpoints/websockets.py
# PHOENIX PROTOCOL PHASE XI - MODIFICATION 13.0 (Architectural Restoration)
# CORRECTION: The endpoint now correctly assumes responsibility for the connection
# lifecycle. It calls 'await websocket.accept()' after the user dependency is
# resolved. The non-standard 'subprotocol' argument is removed from the accept
# call, restoring correct WebSocket protocol handling and resolving the 1006 error.

import logging
import asyncio
from typing import Annotated, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status, HTTPException
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
    # The 'get_current_user_ws' dependency now runs BEFORE the connection is accepted.
    # If it fails, FastAPI will handle closing the connection correctly.
    user: Annotated[UserInDB, Depends(get_current_user_ws)],
    db: Database = Depends(get_db),
    async_db: Any = Depends(get_async_db)
):
    # This is the new, correct location for accepting the connection.
    # It only happens if the user dependency above succeeds.
    await websocket.accept()

    try:
        validated_case_id = ObjectId(case_id)
    except Exception:
        logger.warning(f"Invalid case_id format received: {case_id}")
        await websocket.close(code=status.WS_1007_INVALID_FRAMEWORK_PAYLOAD)
        return

    # Case authorization check remains the same.
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
        raise HTTPException(status_code=400, detail="Missing case_id")
    
    try:
        await manager.broadcast_to_case(case_id=case_id, message=payload)
        return {"status": "broadcasted", "case_id": case_id}
    except Exception as e:
        logger.error(f"Broadcast failed for case {case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))