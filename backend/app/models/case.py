# FILE: backend/app/models/case.py
# PHOENIX PROTOCOL - MODEL ALIGNMENT
# 1. ADDED: 'ClientData' to handle ad-hoc client info (Name, Email, Phone).
# 2. UPDATED: 'CaseCreate' now accepts clientName/Email/Phone inputs.
# 3. UPDATED: 'CaseOut' now returns a structured 'client' object matching Frontend types.

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
    case_number: Optional[str] = None # Made optional, auto-generated if missing
    title: str
    description: Optional[str] = None
    status: str = "OPEN"
    client_id: Optional[PyObjectId] = None # Reference to registered user (optional)
    
    # Optional metadata
    court_name: Optional[str] = None
    judge_name: Optional[str] = None
    opponent_name: Optional[str] = None

# Create - Accepts Form Data
class CaseCreate(CaseBase):
    # Ad-hoc client fields sent by Frontend Form
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
    
    # Embedded client data (for ad-hoc clients)
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
    
    # Structure matching frontend { name, email, phone }
    client: Optional[ClientData] = None

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