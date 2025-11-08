# FILE: backend/app/models/internal.py
# Contains Pydantic models for internal service-to-service communication.

from pydantic import BaseModel
from typing import Optional

class ChatBroadcast(BaseModel):
    """
    Payload for broadcasting a chat message chunk from a Celery worker
    to the main application via an internal HTTP call.
    """
    user_id: str
    case_id: str
    text: str
    type: str = "chat_response_chunk" # The type is fixed for this broadcast