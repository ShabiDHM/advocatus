# FILE: backend/app/models/calendar.py
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
    PAYMENT = "PAYMENT"
    OTHER = "OTHER"

class EventCategory(str, Enum):
    # PHOENIX: Added to separate Agenda from Metadata
    AGENDA = "AGENDA"  # Appears in Calendar (Deadlines, seanca)
    FACT = "FACT"      # Metadata only (Birthdays, historical dates)

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
    category: EventCategory = EventCategory.AGENDA # PHOENIX: Default to Agenda
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
    is_public: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(populate_by_name=True)

class CalendarEventOut(CalendarEventInDB):
    working_days_remaining: Optional[int] = None
    severity: Optional[str] = None
    effective_deadline: Optional[datetime] = None
    is_extended: bool = False
    risk_level: Optional[str] = None