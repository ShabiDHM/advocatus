# FILE: backend/app/models/archive.py
# PHOENIX PROTOCOL - ARCHIVE MODELS
# 1. FILE TRACKING: Stores references to physical files in MinIO/S3.
# 2. CATEGORIZATION: Distinguishes between Invoices, Contracts, and Reports.

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from .common import PyObjectId

class ArchiveItemBase(BaseModel):
    title: str
    file_type: str = "PDF" # PDF, DOCX, IMG
    category: str = "GENERAL" # INVOICE, CONTRACT, REPORT, UPLOAD
    storage_key: str
    file_size: int = 0
    description: str = ""

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