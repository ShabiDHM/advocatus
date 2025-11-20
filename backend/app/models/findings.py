# FILE: backend/app/models/findings.py
# PHOENIX PROTOCOL - PYDANTIC INHERITANCE FIX
# 1. Removed 'document_id' from FindingBase to prevent non-default argument errors.
# 2. Explicitly defined 'document_id' in FindingInDB and FindingOut.

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from .common import PyObjectId

class FindingBase(BaseModel):
    finding_text: str
    source_text: str
    page_number: Optional[int] = None
    document_name: Optional[str] = None
    # Removed document_id from here to avoid conflict with defaults
    confidence_score: float = 0.0

class FindingInDB(FindingBase):
    id: PyObjectId = Field(alias="_id")
    case_id: str
    document_id: str # Required here
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class FindingOut(FindingBase):
    id: str
    case_id: str
    document_id: str # Required here for frontend filtering
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

class FindingsListOut(BaseModel):
    findings: List[FindingOut]
    count: int