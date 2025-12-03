# FILE: backend/app/models/archive.py
# PHOENIX PROTOCOL - ARCHIVE V2 (FOLDERS)
# 1. SCHEMA: Added 'item_type' (FILE/FOLDER) and 'parent_id' for hierarchical structure.
# 2. LOGIC: Made 'storage_key' optional, as folders do not have physical files.
# 3. COMPATIBILITY: Preserves existing fields for backward compatibility.

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from .common import PyObjectId

class ArchiveItemBase(BaseModel):
    title: str
    # PHOENIX: Hierarchical Structure
    item_type: str = "FILE" # 'FILE' or 'FOLDER'
    parent_id: Optional[PyObjectId] = None # Pointer to parent folder (null = root)
    
    # File Metadata (Optional for Folders)
    file_type: str = "PDF" # PDF, DOCX, IMG, FOLDER
    category: str = "GENERAL" 
    storage_key: Optional[str] = None # Folders don't have this
    file_size: int = 0
    description: str = ""
    
    # Context
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
    case_id: Optional[PyObjectId] = Field(default=None)
    parent_id: Optional[PyObjectId] = Field(default=None)