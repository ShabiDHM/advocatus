# FILE: backend/app/models/document.py
# PHOENIX PROTOCOL - DOCUMENT MODELS V7.0
# V7.0: Shtuar DocumentStatus.READY_WITH_WARNINGS — për dokumente që janë
#       procesuar, por ingestion i vektorëve nuk ishte 100% i suksesshëm.
# V6.0: Hequr latest_forensic_audit + litigation_analysis (të vdekura).

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

from .common import PyObjectId


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    READY_WITH_WARNINGS = "READY_WITH_WARNINGS"  # V7.0: ingestion i pjesshëm
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class DocumentBase(BaseModel):
    file_name: Optional[str] = "Dokument"
    status: Optional[str] = "PENDING"
    mime_type: Optional[str] = None
    summary: Optional[str] = None
    page_count: Optional[int] = 1
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class DocumentInDB(DocumentBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    case_id: Optional[PyObjectId] = None
    owner_id: Optional[PyObjectId] = None
    storage_key: Optional[str] = ""
    processed_text_storage_key: Optional[str] = None
    preview_storage_key: Optional[str] = None
    error_message: Optional[str] = None
    category: Optional[str] = None
    progress_percent: Optional[int] = 100
    progress_message: Optional[str] = None
    is_shared: Optional[bool] = False

    # V7.0: Statistika të ingestion (për diagnozë)
    ingestion_stats: Optional[Dict[str, Any]] = None

    # PHOENIX CACHE: Ruajtja e Analizës për Hapje të Shpejtë
    latest_analysis: Optional[str] = None
    last_audited_at: Optional[datetime] = None
    
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
    pass