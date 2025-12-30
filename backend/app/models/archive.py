# FILE: backend/app/models/archive.py
# PHOENIX PROTOCOL - REVERT TO STABLE V2
# 1. REVERT: Removed 'indexing_status' and 'indexing_error' fields.
# 2. LOGIC: Restores the schema to be a simple file archive, not an AI knowledge base.

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
    is_shared: bool = False

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