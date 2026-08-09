# FILE: backend/app/models/document.py
# PHOENIX PROTOCOL - DOCUMENT MODELS V4.0 (OPTIONAL RESILIENT FIELDS)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

from .common import PyObjectId

class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"

class DocumentBase(BaseModel):
    file_name: Optional[str] = "Dokument"
    status: Optional[str] = "PENDING"
    mime_type: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class DocumentInDB(DocumentBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    case_id: Optional[PyObjectId] = None
    owner_id: Optional[PyObjectId] = None
    storage_key: Optional[str] = ""
    processed_text_storage_key: Optional[str] = None
    preview_storage_key: Optional[str] = None
    error_message: Optional[str] = None
    category: Optional[str] = None
    
    # PHOENIX ENGINE: Persisted Strategic Analysis
    litigation_analysis: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        from_attributes=True,
        json_encoders={
            PyObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )

# Explicitly defining Output model to satisfy imports
class DocumentOut(DocumentInDB):
    pass