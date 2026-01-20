# FILE: backend/app/tasks/chat_tasks.py
# PHOENIX PROTOCOL - CHAT TASKS V2.0 (SYNC WORKER)
# 1. FIX: Replaced 'async_db_instance' with 'db_instance' (Synchronous).
# 2. STATUS: Resolves the ImportError that crashes the Celery Worker.

import asyncio
import logging
import httpx
from datetime import datetime, timezone

from ..celery_app import celery_app
from ..services import chat_service
# PHOENIX FIX: Import the synchronous database instance
from ..core.db import db_instance

logger = logging.getLogger(__name__)

BROADCAST_ENDPOINT = "http://backend:8000/internal/broadcast/document-update"

@celery_app.task(name="process_socratic_query_task")
def process_socratic_query_task(query_text: str, case_id: str, user_id: str):
    """
    This background task runs the full RAG pipeline and sends the final result back.
    """
    logger.info(f"Celery task 'process_socratic_query_task' started for user {user_id} in case {case_id}")
    
    broadcast_payload = {}
    try:
        if db_instance is None:
             raise RuntimeError("Database connection not initialized in Celery worker.")

        # PHOENIX FIX: Pass the synchronous db_instance.
        # We use asyncio.run() because the service method is 'async def' (it calls the AI).
        full_response = asyncio.run(
            chat_service.get_http_chat_response(
                db=db_instance,
                case_id=case_id,
                user_query=query_text,
                user_id=user_id
            )
        )
        
        broadcast_payload = {
            "case_id": case_id,
            "type": "chat_message_out",
            "text": full_response,
            "sender": "AI",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Celery task failed during RAG pipeline for user {user_id} in case {case_id}: {e}", exc_info=True)
        broadcast_payload = {
            "case_id": case_id,
            "type": "chat_message_out",
            "text": "Ndodhi një gabim gjatë përpunimit të pyetjes suaj. Ju lutem provoni përsëri.",
            "sender": "AI",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    try:
        with httpx.Client() as client:
            response = client.post(BROADCAST_ENDPOINT, json=broadcast_payload)
            response.raise_for_status() 
        
        logger.info(f"Celery task successfully triggered broadcast for user {user_id} in case {case_id}")

    except httpx.HTTPStatusError as e:
        logger.error(f"Celery task failed to broadcast chat response via HTTP. Status: {e.response.status_code}, Response: {e.response.text}",
                     extra={"payload": broadcast_payload})
    except Exception as e:
        logger.error(f"Celery task failed during HTTP broadcast of chat message: {e}", exc_info=True)