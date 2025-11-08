# FILE: backend/app/tasks/chat_tasks.py
# DEFINITIVE VERSION 2.0 (FINAL): Corrected the broadcast payload to match the internal API's expected schema.

import asyncio
import logging
import httpx
from typing import Optional, List

from ..celery_app import celery_app
from ..services import chat_service

logger = logging.getLogger(__name__)

INTERNAL_API_URL = "http://backend:8000" 
CHAT_BROADCAST_ENDPOINT = f"{INTERNAL_API_URL}/internal/broadcast/chat-message"

def trigger_chat_websocket_broadcast(user_id: str, case_id: str, response_text: str):
    """
    Triggers a WebSocket broadcast by POSTing to the internal API endpoint.
    This function now constructs the exact payload the endpoint expects.
    """
    try:
        # --- DEFINITIVE FIX ---
        # Construct the flat JSON payload that matches the `ChatBroadcast` Pydantic model in main.py.
        # The final message type should be 'chat_message_out' to let the frontend know the stream is complete.
        broadcast_payload = {
            "user_id": user_id,
            "case_id": case_id,
            "text": response_text,
            "type": "chat_message_out" 
        }
        
        with httpx.Client() as client:
            # The `json=` parameter correctly serializes the dictionary to JSON.
            response = client.post(CHAT_BROADCAST_ENDPOINT, json=broadcast_payload)
        
        if response.status_code != 200:
            logger.error(f"Failed to broadcast chat response via HTTP. Status: {response.status_code}, Response: {response.text}",
                         extra={"payload": broadcast_payload})
        else:
            logger.info(f"Successfully triggered chat response broadcast for user {user_id} in case {case_id}")
            
    except Exception as e:
        logger.error(f"Error during HTTP broadcast of chat message: {e}", exc_info=True)


@celery_app.task(name="process_socratic_query_task")
def process_socratic_query_task(query_text: str, case_id: str, user_id: str, document_ids: Optional[List[str]]):
    """
    This background task runs the full RAG pipeline and sends the final result back via WebSocket broadcast.
    """
    logger.info(f"Celery task started for user {user_id} in case {case_id}")
    
    # Run the async RAG pipeline. This blocks the Celery worker until the full response is generated.
    full_response = asyncio.run(
        chat_service._run_rag_pipeline(query_text, case_id, user_id, document_ids)
    )
    
    # Trigger the broadcast with the final, complete AI response.
    trigger_chat_websocket_broadcast(user_id, case_id, full_response)
    
    logger.info(f"Celery task finished and broadcasted chat response for user {user_id}")