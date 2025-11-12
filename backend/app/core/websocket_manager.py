# FILE: backend/app/core/websocket_manager.py

import logging
from typing import Dict, Set
from fastapi import WebSocket
import asyncio

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages active WebSocket connections, organized by case_id.
    Ensures thread-safe operations for connect, disconnect, and broadcast.
    """
    def __init__(self):
        # Maps a case_id (str) to a set of active WebSockets.
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, case_id: str, user_id: str):
        """Accepts a new WebSocket connection and adds it to the appropriate case."""
        await websocket.accept()
        async with self._lock:
            if case_id not in self.active_connections:
                self.active_connections[case_id] = set()
            self.active_connections[case_id].add(websocket)
        logger.info(f"User {user_id} connected to WebSocket for case {case_id}")

    async def disconnect(self, websocket: WebSocket, case_id: str, user_id: str):
        """Removes a WebSocket connection from its case."""
        async with self._lock:
            if case_id in self.active_connections:
                self.active_connections[case_id].discard(websocket)
                if not self.active_connections[case_id]:
                    del self.active_connections[case_id]
        logger.info(f"User {user_id} disconnected from WebSocket for case {case_id}")

    async def broadcast_to_case(self, case_id: str, message: dict):
        """Broadcasts a JSON message to all clients connected to a specific case."""
        if case_id in self.active_connections:
            # Create a list of tasks to send messages concurrently
            tasks = [
                connection.send_json(message)
                for connection in self.active_connections[case_id]
            ]
            if tasks:
                logger.info(f"Broadcasting message to {len(tasks)} clients in case {case_id}")
                await asyncio.gather(*tasks, return_exceptions=True)

# Create a single, globally accessible instance of the manager
manager = ConnectionManager()