# FILE: backend/app/models/case.py
# PHOENIX PROTOCOL - MODEL RESTORATION
# 1. RESTORED: 'ChatMessage' (Required by chat_service.py).
# 2. MAINTAINED: All previous fixes (ClientDetailsOut, Serialization aliases).

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from .common import PyObjectId

# Base Case Model
class CaseBase(BaseModel):
    case_number: str
    title: str
    description: Optional[str] = None
    status: str = "OPEN" # OPEN, CLOSED, PENDING
    client_id: Optional[PyObjectId] = None
    
    # Optional metadata
    court_name: Optional[str] = None
    judge_name: Optional[str] = None
    opponent_name: Optional[str] = None

# Create
class CaseCreate(CaseBase):
    pass

# Update
class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    court_name: Optional[str] = None
    judge_name: Optional[str] = None
    opponent_name: Optional[str] = None

# DB Model
class CaseInDB(CaseBase):
    id: PyObjectId = Field(alias="_id", default=None)
    user_id: PyObjectId 
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    chat_history: List[Dict[str, Any]] = []

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

# Return Model
class CaseOut(CaseBase):
    id: PyObjectId = Field(alias="_id", serialization_alias="id")
    created_at: datetime
    updated_at: datetime
    client_name: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

# Required by case_service.py
class ClientDetailsOut(BaseModel):
    id: PyObjectId = Field(alias="_id", serialization_alias="id")
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

# PHOENIX RESTORATION: Required by chat_service.py
class ChatMessage(BaseModel):
    role: str # "user" or "ai"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)