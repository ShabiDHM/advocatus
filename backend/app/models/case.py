# FILE: backend/app/models/case.py
# PHOENIX PROTOCOL - MODEL REPAIR (RESTORED MISSING CLASS)
# 1. RESTORED: 'ClientDetailsOut' which is required by 'case_service.py'.
# 2. MAINTAINED: Serialization fixes for dropdown IDs.

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
    user_id: PyObjectId # The lawyer/user who owns the case
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    chat_history: List[Dict[str, Any]] = []

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

# Return Model
class CaseOut(CaseBase):
    # PHOENIX FIX: Ensure 'id' is sent to frontend
    id: PyObjectId = Field(alias="_id", serialization_alias="id")
    created_at: datetime
    updated_at: datetime
    
    # Flattened client details (optional)
    client_name: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

# PHOENIX RESTORATION: Required by case_service.py
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