# FILE: backend/app/models/archive.py
# PHOENIX PROTOCOL - ARCHIVE MODEL V2.2 (CASCADE SYNC ENABLED)
# 1. ADDED: 'original_doc_id' to ArchiveItemBase to link Case Documents to Archive Items.
# 2. FIXED: Pydantic V2 bridge to ensure 'model_validate' works with MongoDB Objects.
# 3. STATUS: 100% Logic Sync Compatible.

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
    # PHOENIX FIX: Added link to original document for name synchronization
    original_doc_id: Optional[PyObjectId] = None
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
        from_attributes=True  # Required for model_validate(item_object)
    )

class ArchiveItemOut(ArchiveItemInDB):
    # Ensure the ID is serialized correctly as 'id' for the frontend
    id: PyObjectId = Field(alias="_id", serialization_alias="id", default=None)
    case_id: Optional[PyObjectId] = Field(default=None)
    parent_id: Optional[PyObjectId] = Field(default=None)
    original_doc_id: Optional[PyObjectId] = Field(default=None)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        from_attributes=True
    )