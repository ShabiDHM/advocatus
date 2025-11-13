# FILE: backend/app/models/document.py

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
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
    # PHOENIX PROTOCOL CURE: Added the new field to store the location of the generated PDF preview.
    preview_storage_key: Optional[str] = None
    error_message: Optional[str] = None
    category: Optional[str] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        from_attributes=True,
        json_encoders={
            PyObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )

class DocumentOut(DocumentInDB):
    # This model inherits the new `preview_storage_key` field, making it available in the API response.
    pass