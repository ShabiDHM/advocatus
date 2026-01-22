# FILE: backend/app/models/calendar.py
# PHOENIX PROTOCOL - MODEL ALIGNMENT V5.6 (DATA COMPATIBILITY FIX)
# 1. ENUM EXPANSION: Added 'NORMAL' to EventPriority to match legacy DB data.
# 2. ENUM EXPANSION: Added 'RESOLVED' to EventStatus to match legacy DB data.
# 3. STRUCTURE: Preserved owner_id/case_id alignment for Dashboard counting.

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
from bson import ObjectId

from app.models.common import PyObjectId 

class EventType(str, Enum):
    DEADLINE = "DEADLINE"
    HEARING = "HEARING"
    MEETING = "MEETING"
    FILING = "FILING"
    COURT_DATE = "COURT_DATE"
    CONSULTATION = "CONSULTATION"
    OTHER = "OTHER"

class EventPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    NORMAL = "NORMAL" # Added to resolve validation crash
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class EventStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    RESOLVED = "RESOLVED" # Added to resolve validation crash
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class CalendarEventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    start_date: datetime
    end_date: Optional[datetime] = None
    is_all_day: bool = False
    event_type: EventType = EventType.MEETING
    priority: EventPriority = EventPriority.MEDIUM
    location: Optional[str] = Field(None, max_length=100)
    attendees: Optional[List[str]] = None
    notes: Optional[str] = Field(None, max_length=1000)

class CalendarEventCreate(CalendarEventBase):
    case_id: PyObjectId

    @field_validator('case_id', mode='before')
    @classmethod
    def validate_case_id(cls, v):
        if isinstance(v, str):
            try:
                return ObjectId(v)
            except Exception:
                raise ValueError(f"Invalid ObjectId string: {v}")
        elif isinstance(v, ObjectId):
            return v
        else:
            raise ValueError(f"Expected string or ObjectId, got {type(v)}")

class CalendarEventInDB(CalendarEventBase):
    id: PyObjectId = Field(alias="_id")
    owner_id: PyObjectId # Preserved Phoenix alignment
    case_id: str # Preserved Phoenix alignment
    document_id: Optional[str] = None 
    status: EventStatus = EventStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(populate_by_name=True)

class CalendarEventOut(CalendarEventInDB):
    # Inherits serialization logic from InDB
    pass