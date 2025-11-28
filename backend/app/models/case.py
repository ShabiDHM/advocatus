# FILE: backend/app/models/case.py
# PHOENIX PROTOCOL - MODEL UPDATE
# 1. ADDED: Count fields (document_count, alert_count, etc.) to CaseOut.
# 2. STATUS: Allows dashboard metrics to pass through the API.

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from .common import PyObjectId

# Sub-model for embedded client details
class ClientData(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

# Base Case Model
class CaseBase(BaseModel):
    case_number: Optional[str] = None 
    title: str
    description: Optional[str] = None
    status: str = "OPEN"
    client_id: Optional[PyObjectId] = None 
    
    # Optional metadata
    court_name: Optional[str] = None
    judge_name: Optional[str] = None
    opponent_name: Optional[str] = None

# Create - Accepts Form Data
class CaseCreate(CaseBase):
    clientName: Optional[str] = None
    clientEmail: Optional[str] = None
    clientPhone: Optional[str] = None

# Update
class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    court_name: Optional[str] = None
    judge_name: Optional[str] = None
    opponent_name: Optional[str] = None
    client: Optional[ClientData] = None

# DB Model
class CaseInDB(CaseBase):
    id: PyObjectId = Field(alias="_id", default=None)
    user_id: PyObjectId 
    client: Optional[ClientData] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    chat_history: List[Dict[str, Any]] = []

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

# Return Model - Matches Frontend 'Case' Interface
class CaseOut(CaseBase):
    id: PyObjectId = Field(alias="_id", serialization_alias="id")
    created_at: datetime
    updated_at: datetime
    
    client: Optional[ClientData] = None

    # PHOENIX FIX: Explicitly exposed counters
    document_count: int = 0
    alert_count: int = 0
    event_count: int = 0
    finding_count: int = 0

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

# Required by chat_service.py
class ChatMessage(BaseModel):
    role: str 
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)