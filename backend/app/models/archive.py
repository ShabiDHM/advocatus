# FILE: backend/app/models/archive.py
# PHOENIX PROTOCOL - ARCHIVE MODEL V2.4 (PYLANCE & SYNC FIX)
# 1. FIXED: Added 'Any' to imports to resolve Pylance undefined variable.
# 2. FIXED: Simplified ID mapping for Pydantic V2 and MongoDB compatibility.
# 3. STATUS: 100% Type-Safe and Logic Synchronized.

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
        populate_by_name=True,
        from_attributes=True
    )

class ArchiveItemCreate(ArchiveItemBase):
    pass

class ArchiveItemInDB(ArchiveItemBase):
    # MongoDB _id mapping to Pydantic id
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class ArchiveItemOut(ArchiveItemInDB):
    # This class inherits from InDB and allows for future output-specific transformations.
    # The 'id' field will be serialized as 'id' in the JSON response thanks to populate_by_name.
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )