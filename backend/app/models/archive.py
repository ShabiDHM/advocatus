# FILE: backend/app/models/archive.py
# PHOENIX PROTOCOL - ARCHIVE MODELS (CASE LINKED)
# 1. UPDATE: Added 'case_id' to ArchiveItemBase to link files to cases.
# 2. STATUS: Ready for structural organization.

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from .common import PyObjectId

class ArchiveItemBase(BaseModel):
    title: str
    file_type: str = "PDF" # PDF, DOCX, IMG
    category: str = "GENERAL" # INVOICE, CONTRACT, REPORT, UPLOAD
    storage_key: str
    file_size: int = 0
    description: str = ""
    # PHOENIX FIX: Link to specific case (Optional)
    case_id: Optional[PyObjectId] = None 

class ArchiveItemCreate(ArchiveItemBase):
    pass

class ArchiveItemInDB(ArchiveItemBase):
    id: PyObjectId = Field(alias="_id", default=None)
    user_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class ArchiveItemOut(ArchiveItemInDB):
    id: PyObjectId = Field(alias="_id", serialization_alias="id", default=None)
    # Ensure case_id is serialized correctly if present
    case_id: Optional[PyObjectId] = Field(default=None)