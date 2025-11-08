# FILE: backend/app/models/findings.py
# PHOENIX PROTOCOL PHASE IV - MODIFICATION 2.0 (Data Contract Finalization)
# CORRECTION: Adjusted model fields to account for missing data from findings_service.py 
# (confidence_score and timestamp).

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Optional, Dict, Any
from .common import PyObjectId

class FindingOut(BaseModel):
    """
    Structured Pydantic model for a single Legal Finding, serving as the
    canonical data contract for all finding-related API endpoints.
    """
    id: str = Field(alias="_id")
    case_id: str
    source_text: str
    finding_text: str
    # MODIFIED: Made confidence_score optional and defaulted, as findings_service does not retrieve it.
    confidence_score: float = Field(0.0, ge=0.0, le=1.0) 
    # MODIFIED: Added extracted_at, defaulted, as findings_service does not retrieve it.
    extracted_at: datetime = Field(default_factory=datetime.utcnow) 
    page_number: Optional[int] = None
    document_name: Optional[str] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            PyObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )

class FindingsListOut(BaseModel):
    """Wrapper model for a list of findings, serving as the new endpoint contract."""
    findings: List[FindingOut]
    count: int