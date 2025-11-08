# FILE: backend/app/core/websocket_manager.py
# PHOENIX PROTOCOL MODIFICATION 2.0 (MERGED FUNCTIONALITY)
# 1. CONSTRUCTOR FIX: The `__init__` method now correctly accepts the `redis_client`.
# 2. FUNCTIONALITY MERGE: Restores the `redis_listener` to preserve the document
#    update feature, and includes the new generic `broadcast_to_case` for chat.
# 3. This creates a single, feature-complete, and robust connection manager.

import asyncio
import json
import logging
from typing import Dict, Any
from fastapi import WebSocket
import redis.asyncio as redis
from redis.exceptions import ConnectionError
from datetime import datetime

logger = logging.getLogger(__name__)

def json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

class ConnectionManager:
    # --- PHOENIX PROTOCOL FIX: This constructor correctly accepts the redis_client ---
    def __init__(self, redis_client: redis.Redis):
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        self.redis_client = redis_client
    # --- END FIX ---

    async def connect(self, websocket: WebSocket, case_id: str, user_id: str):
        await websocket.accept()
        if case_id not in self.active_connections:
            self.active_connections[case_id] = {}
        self.active_connections[case_id][user_id] = websocket
        logger.info(f"User {user_id} connected to case {case_id}.")

    def disconnect(self, case_id: str, user_id: str):
        if case_id in self.active_connections and user_id in self.active_connections[case_id]:
            del self.active_connections[case_id][user_id]
            if not self.active_connections[case_id]:
                del self.active_connections[case_id]
            logger.info(f"User {user_id} disconnected from case {case_id}.")

    async def broadcast_to_case(self, case_id: str, message: Dict[str, Any]):
        if case_id in self.active_connections:
            message_str = json.dumps(message, default=json_serializer)
            tasks = [ws.send_text(message_str) for ws in self.active_connections[case_id].values()]
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"Broadcasted chat update to {len(tasks)} clients for case {case_id}.")

    async def redis_listener(self):
        """Listens to Redis for messages to broadcast (e.g., document status updates)."""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("document_status_updates")
        logger.info("--- [WebSocket Manager] Redis listener started. ---")
        while True:
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        data = json.loads(message["data"])
                        case_id = data.get("case_id")
                        if case_id in self.active_connections:
                            # Re-serialize for broadcasting to all users in the case
                            message_to_send = json.dumps(data, default=json_serializer)
                            await self.broadcast_to_case(case_id, json.loads(message_to_send))
            except ConnectionError:
                logger.warning("--- [WebSocket Manager] Redis connection lost. Reconnecting... ---")
                await asyncio.sleep(5)
            except Exception:
                logger.error("--- [WebSocket Manager] Error in redis_listener. Restarting... ---")
                await asyncio.sleep(5)