# FILE: backend/app/models/calendar.py
# DEFINITIVE VERSION (ARCHITECTURAL CONSISTENCY):
# 1. Changed the import for PyObjectId from a relative path to an absolute path.
#    This resolves the "unknown import symbol" error by creating a robust and
#    unambiguous import path from the application root.
# 2. All ID fields continue to be consistently typed with the robust 'PyObjectId'.
# 3. PHOENIX PROTOCOL FIX: Added field validator to handle string case_id from frontend

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
from bson import ObjectId

from app.models.common import PyObjectId # CURE: Changed to absolute import path.

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

    # PHOENIX PROTOCOL FIX: Handle both string and ObjectId case_id inputs
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
    user_id: PyObjectId
    case_id: PyObjectId
    status: EventStatus = EventStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(populate_by_name=True)

class CalendarEventOut(CalendarEventInDB):
    # The new PyObjectId class's serialization logic handles the conversion.
    pass