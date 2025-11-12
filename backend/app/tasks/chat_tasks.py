# FILE: backend/app/tasks/chat_tasks.py

import asyncio
import logging
import httpx
from datetime import datetime, timezone

from ..celery_app import celery_app
from ..services import chat_service
# PHOENIX PROTOCOL CURE: Import the async database instance directly for use in the task.
from ..core.db import async_db_instance

logger = logging.getLogger(__name__)

# The broadcast endpoint is now consolidated in the websockets router.
BROADCAST_ENDPOINT = "http://backend:8000/internal/broadcast/document-update"

@celery_app.task(name="process_socratic_query_task")
def process_socratic_query_task(query_text: str, case_id: str, user_id: str):
    """
    This background task runs the full RAG pipeline and sends the final result back
    via a WebSocket broadcast by calling the internal broadcast API.
    """
    logger.info(f"Celery task 'process_socratic_query_task' started for user {user_id} in case {case_id}")
    
    broadcast_payload = {}
    try:
        # PHOENIX PROTOCOL CURE: Call the correct, existing service function for non-streaming chat.
        # We run the async function within the synchronous Celery task context.
        full_response = asyncio.run(
            chat_service.get_http_chat_response(
                db=async_db_instance,
                case_id=case_id,
                user_query=query_text,
                user_id=user_id
            )
        )
        
        # PHOENIX PROTOCOL CURE: Construct the exact payload the frontend expects for a final chat message.
        # The `type` field is critical for client-side routing.
        broadcast_payload = {
            "case_id": case_id,
            "type": "chat_message_out",
            "text": full_response,
            "sender": "AI",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Celery task failed during RAG pipeline for user {user_id} in case {case_id}: {e}", exc_info=True)
        # On failure, prepare an error message payload to send back to the user.
        broadcast_payload = {
            "case_id": case_id,
            "type": "chat_message_out",
            "text": "Ndodhi një gabim gjatë përpunimit të pyetjes suaj. Ju lutem provoni përsëri.",
            "sender": "AI",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    try:
        # Trigger the broadcast with the final result (either success or error message).
        with httpx.Client() as client:
            response = client.post(BROADCAST_ENDPOINT, json=broadcast_payload)
            response.raise_for_status() # Will raise an exception for 4xx/5xx responses
        
        logger.info(f"Celery task successfully triggered broadcast for user {user_id} in case {case_id}")

    except httpx.HTTPStatusError as e:
        logger.error(f"Celery task failed to broadcast chat response via HTTP. Status: {e.response.status_code}, Response: {e.response.text}",
                     extra={"payload": broadcast_payload})
    except Exception as e:
        logger.error(f"Celery task failed during HTTP broadcast of chat message: {e}", exc_info=True)