# FILE: backend/app/models/calendar.py
# PHOENIX PROTOCOL - MODEL ALIGNMENT V5.7 (FINANCIAL EVENT TYPE)
# 1. FEATURE: Added 'PAYMENT' to EventType Enum.
# 2. RESULT: Allows proper categorization of dates from financial documents.

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
    PAYMENT = "PAYMENT" # PHOENIX: Added for financial documents
    OTHER = "OTHER"

class EventPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    NORMAL = "NORMAL" 
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class EventStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    RESOLVED = "RESOLVED" 
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
    owner_id: PyObjectId 
    case_id: str 
    document_id: Optional[str] = None 
    status: EventStatus = EventStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(populate_by_name=True)

class CalendarEventOut(CalendarEventInDB):
    pass