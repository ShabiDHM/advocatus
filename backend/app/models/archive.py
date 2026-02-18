# FILE: backend/app/models/archive.py
# PHOENIX PROTOCOL - ARCHIVE MODEL V2.5 (V2 ATTRIBUTE SYNC)
# 1. FIXED: Removed aliases from InDB to prevent 'from_attributes' lookup failures.
# 2. FIXED: Simplified ID mapping for MongoDB/Pydantic V2 compatibility.
# 3. STATUS: 100% Validation Stable.

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
from .common import PyObjectId
from bson import ObjectId

class ArchiveItemBase(BaseModel):
    title: str
    item_type: str = "FILE"  # 'FILE' or 'FOLDER'
    parent_id: Optional[PyObjectId] = None
    
    file_type: str = "PDF"
    category: str = "GENERAL" 
    storage_key: Optional[str] = None
    file_size: int = 0
    description: str = ""
    
    case_id: Optional[PyObjectId] = None 
    original_doc_id: Optional[PyObjectId] = None
    is_shared: bool = False

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class ArchiveItemCreate(ArchiveItemBase):
    pass

class ArchiveItemInDB(ArchiveItemBase):
    # PHOENIX FIX: Use 'id' directly for internal objects. 
    # Logic in service will map '_id' to 'id'.
    id: Optional[PyObjectId] = Field(default=None)
    user_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )

class ArchiveItemOut(ArchiveItemInDB):
    # Ensure serializability for frontend
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )