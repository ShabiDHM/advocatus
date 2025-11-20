# FILE: backend/app/models/support.py
# PHOENIX PROTOCOL - NEW MODEL
# Defines the schema for support messages stored in MongoDB.

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from .common import PyObjectId

class ContactRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    message: str

class ContactMessageInDB(ContactRequest):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "UNREAD" # UNREAD, READ, ARCHIVED

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )