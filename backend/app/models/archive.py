# FILE: backend/app/models/archive.py
# PHOENIX PROTOCOL - ARCHIVE V3.0 (AI STATUS)
# 1. SCHEMA: Added 'indexing_status' to track AI processing (PENDING, PROCESSING, COMPLETED, FAILED).
# 2. DEBUG: Added 'indexing_error' to store reasons for failure.

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from .common import PyObjectId

class ArchiveItemBase(BaseModel):
    title: str
    item_type: str = "FILE" # 'FILE' or 'FOLDER'
    parent_id: Optional[PyObjectId] = None 
    
    file_type: str = "PDF"
    category: str = "GENERAL" 
    storage_key: Optional[str] = None
    file_size: int = 0
    description: str = ""
    
    case_id: Optional[PyObjectId] = None 
    
    # PHOENIX: AI Brain Status
    is_shared: bool = False
    indexing_status: str = "PENDING" # PENDING, PROCESSING, COMPLETED, FAILED
    indexing_error: Optional[str] = None

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
    case_id: Optional[PyObjectId] = Field(default=None)
    parent_id: Optional[PyObjectId] = Field(default=None)