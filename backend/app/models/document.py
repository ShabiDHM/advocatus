from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

from .common import PyObjectId

class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    FAILED = "FAILED"

class DocumentBase(BaseModel):
    file_name: str
    status: DocumentStatus = DocumentStatus.PENDING
    mime_type: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DocumentInDB(DocumentBase):
    id: PyObjectId = Field(alias="_id")
    case_id: PyObjectId
    owner_id: PyObjectId
    storage_key: str
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