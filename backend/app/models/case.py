# FILE: backend/app/models/case.py
# PHOENIX PROTOCOL - CHAT PERSISTENCE ENABLED
# 1. Added 'chat_history' to CaseOut. This allows the frontend to receive 
#    stored messages when loading the case (fixing the "disappearing chat" bug).

from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from typing import Optional, Any, List, Literal

from .common import PyObjectId

# --- Chat Message Models ---
class ChatMessage(BaseModel):
    """
    Represents a single chat message stored within the CaseInDB document.
    """
    sender_id: str
    sender_type: Literal["user", "ai"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatMessageOut(ChatMessage):
    """
    Public-facing model for broadcasting a chat message via WebSocket.
    Ensures timestamps are serialized correctly for the frontend.
    """
    model_config = ConfigDict(
        json_encoders={datetime: lambda dt: dt.isoformat()}
    )

# --- Client Details Model ---
class ClientDetailsOut(BaseModel):
    name: Optional[str] = Field(None)
    email: Optional[str] = Field(None)
    phone: Optional[str] = Field(None)

# --- Base Case Models ---
class CaseBase(BaseModel):
    case_name: str = Field(..., min_length=3, max_length=150)
    status: str = "active"

class CaseCreate(CaseBase):
    clientName: Optional[str] = None
    clientEmail: Optional[str] = None
    clientPhone: Optional[str] = None

class CaseInDB(CaseBase):
    id: PyObjectId = Field(alias="_id", default=None)
    owner_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    client: Optional[ClientDetailsOut] = Field(None)

    # Persist chat history in the database
    chat_history: List[ChatMessage] = Field(default_factory=list)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class CaseOut(BaseModel):
    id: str
    case_name: str
    client: Optional[ClientDetailsOut] = Field(None)
    klienti_emri: Optional[str] = Field(None)

    @field_validator('klienti_emri', mode='before')
    @classmethod
    def populate_client_name(cls, v: Any, info: Any) -> Optional[str]:
        if info.data and info.data.get('client') and info.data['client'].get('name'):
            return info.data['client']['name']
        return None

    status: str
    owner_id: str
    created_at: datetime
    document_count: int
    alert_count: int
    event_count: int
    finding_count: int
    
    # PHOENIX FIX: Include chat history in the public API response
    chat_history: List[ChatMessage] = Field(default_factory=list)

    @field_validator('id', 'owner_id', mode='before')
    @classmethod
    def objectid_to_str(cls, v: Any) -> str:
        return str(v)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )