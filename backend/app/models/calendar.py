# FILE: backend/app/models/calendar.py
# DEFINITIVE VERSION 1.0 (FEATURE IMPLEMENTATION):
# Defines the database model and API schemas for Calendar Events.

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

from .common import PyObjectId

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
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class EventStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
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

class CalendarEventInDB(CalendarEventBase):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    case_id: PyObjectId
    status: EventStatus = EventStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CalendarEventOut(CalendarEventInDB):
    id: str = Field(..., alias="_id")
    user_id: str
    case_id: str

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            PyObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }