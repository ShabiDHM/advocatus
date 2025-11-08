# backend/app/services/notification_service.py
# DEFINITIVE VERSION V2.1: Corrects Redis exception handling.

import os
import json
import logging
import redis
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# --- Redis Pub/Sub Infrastructure ---
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    logger.warning("!!! WARNING: REDIS_URL environment variable not set. Real-time notifications will be disabled.")

_redis_client: Optional[redis.Redis] = None
STATUS_UPDATE_CHANNEL = "document_status_updates"

def get_redis_client() -> Optional[redis.Redis]:
    """Establishes and returns a Redis client connection, managed as a singleton."""
    global _redis_client
    if not REDIS_URL:
        return None
        
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(REDIS_URL)
            _redis_client.ping()
        # --- CORRECTED EXCEPTION PATH ---
        except redis.ConnectionError as e:
            logger.error(f"!!! CRITICAL: Could not connect to Redis. Real-time notifications will fail. Error: {e}")
            _redis_client = None
    return _redis_client

def send_status_update(doc_id: str, case_id: str, status: str, error_message: Optional[str] = None):
    """
    Publishes a document status update to the Redis Pub/Sub channel.
    """
    redis_client = get_redis_client()
    if not redis_client:
        logger.warning(f"Skipping Redis notification for doc {doc_id} because Redis is not configured or connected.")
        return

    payload = {
        "doc_id": doc_id,
        "case_id": case_id,
        "status": status,
        "error": error_message,
    }
    
    try:
        message = json.dumps(payload)
        redis_client.publish(STATUS_UPDATE_CHANNEL, message)
        logger.info(f"--- [Notification Service] Published status '{status}' for doc {doc_id} in case {case_id} to Redis channel '{STATUS_UPDATE_CHANNEL}'. ---")
    except Exception as e:
        logger.error(f"!!! FAILED to publish status update for doc {doc_id} to Redis. Error: {e}")

# --- ADDED FUNCTIONALITY: External Webhook Notifications ---
async def send_webhook_notification(webhook_url: str, message: Dict[str, Any]):
    """
    Sends a POST request with a JSON payload to a specified webhook URL.
    This is used for external alert subscriptions.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=message, timeout=30.0)
            response.raise_for_status() # Raise an exception for 4xx or 5xx status codes
            logger.info(f"--- [Notification Service] Successfully sent webhook notification to {webhook_url}. ---")
    except httpx.RequestError as e:
        logger.error(f"!!! FAILED to send webhook to {webhook_url}. Could not connect to the server. Error: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"!!! FAILED to send webhook to {webhook_url}. Server responded with status {e.response.status_code}. Response: {e.response.text}")
    except Exception as e:
        logger.error(f"!!! An unexpected error occurred while sending webhook to {webhook_url}. Error: {e}")