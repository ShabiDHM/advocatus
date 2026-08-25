# FILE: backend/app/models/case.py
# PHOENIX PROTOCOL - CASE MODEL V13.0 (EXPLICIT OPPOSING PARTY & LEGAL METADATA)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from .common import PyObjectId

# Sub-model for embedded client details
class ClientData(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

# Chat Message Model
class ChatMessage(BaseModel):
    role: str 
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Base Case Model
class CaseBase(BaseModel):
    case_number: Optional[str] = None 
    title: str
    description: Optional[str] = None
    status: str = "OPEN"
    client_id: Optional[PyObjectId] = None 
    org_id: Optional[PyObjectId] = None 
    client_position: Optional[str] = "DEFENDANT"
    
    # Real Party Names & Financials (Explicitly Preserved in API)
    client_name: Optional[str] = None
    opposing_party: Optional[Union[str, Dict[str, Any]]] = None
    court: Optional[str] = None
    court_name: Optional[str] = None
    judge_name: Optional[str] = None
    opponent_name: Optional[str] = None
    disputed_amount: Optional[float] = 0.0

# Create - Accepts Form Data
class CaseCreate(CaseBase):
    title: str
    clientName: Optional[str] = None
    clientEmail: Optional[str] = None
    clientPhone: Optional[str] = None
    opposingParty: Optional[str] = None

# Update
class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    client_position: Optional[str] = None
    client_name: Optional[str] = None
    opposing_party: Optional[Union[str, Dict[str, Any]]] = None
    court: Optional[str] = None
    court_name: Optional[str] = None
    judge_name: Optional[str] = None
    opponent_name: Optional[str] = None
    disputed_amount: Optional[float] = None
    client: Optional[ClientData] = None
    org_id: Optional[PyObjectId] = None

# DB Model
class CaseInDB(CaseBase):
    id: PyObjectId = Field(alias="_id", default=None)
    user_id: PyObjectId 
    client: Optional[ClientData] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    chat_history: List[Dict[str, Any]] = []
    latest_analysis: Optional[Dict[str, Any]] = None
    latest_deep_analysis: Optional[Dict[str, Any]] = None
    analyzed_doc_ids: Optional[List[str]] = None
    assigned_user_ids: List[str] = []

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

# Return Model
class CaseOut(CaseBase):
    id: PyObjectId = Field(alias="_id", serialization_alias="id")
    user_id: PyObjectId
    created_at: datetime
    updated_at: datetime
    
    client: Optional[ClientData] = None
    chat_history: Optional[List[ChatMessage]] = []
    latest_analysis: Optional[Dict[str, Any]] = None
    latest_deep_analysis: Optional[Dict[str, Any]] = None
    analyzed_doc_ids: Optional[List[str]] = None
    assigned_user_ids: Optional[List[str]] = []

    # Explicitly exposed counters
    document_count: int = 0
    alert_count: int = 0
    event_count: int = 0
    finding_count: int = 0

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )