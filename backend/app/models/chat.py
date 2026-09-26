# FILE: backend/app/models/chat.py
# PHOENIX PROTOCOL - CHAT MODELS V1.1
# V1.1: PYDANTIC V2 — Konvertuar `class Config` në `model_config = ConfigDict(...)`:
#       - ChatFeedback: `allow_population_by_field_name = True` → `populate_by_name=True`.
#       - Hequr `json_encoders = {ObjectId: str}` (deprecated në V2 + i papërdorur;
#         ChatFeedback nuk ka fusha ObjectId).
#       - ChatMessage: `extra = "forbid"` → `model_config = ConfigDict(extra="forbid")`.
#       Zero ndryshim funksional — vetëm eliminim i warning-ut në startup.
# V1.0: Modelet fillestare për feedback + chat history.

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Literal


class ChatFeedback(BaseModel):
    # V1.1: Pydantic V2 style — `populate_by_name` (jo `allow_population_by_field_name`)
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(None, alias="_id")
    case_id: str
    user_id: str
    message_index: int
    feedback: Literal["up", "down"]
    message_preview: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatMessage(BaseModel):
    # V1.1: Pydantic V2 style
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "ai"]
    content: str
    timestamp: str  # ISO format string