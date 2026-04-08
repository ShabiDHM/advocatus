# FILE: backend/app/models/chat.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal
from bson import ObjectId

class ChatFeedback(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    case_id: str
    user_id: str
    message_index: int
    feedback: Literal["up", "down"]
    message_preview: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}

# NEW MODEL for chat history persistence
class ChatMessage(BaseModel):
    role: Literal["user", "ai"]
    content: str
    timestamp: str  # ISO format string

    class Config:
        # Allow extra fields if needed, but keep strict
        extra = "forbid"