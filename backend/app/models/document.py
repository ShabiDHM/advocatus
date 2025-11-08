# FILE: backend/app/models/document.py
# PHOENIX PROTOCOL MODIFICATION V4.0 (STATE MACHINE SIMPLIFICATION):
# 1. LOGIC SIMPLIFICATION: The DocumentStatus Enum has been re-architected to a
#    simpler three-state system as requested: PENDING, READY, FAILED.
# 2. CONTRACT UPDATE: The 'PROCESSING' and 'COMPLETED' states have been completely
#    removed, simplifying the business logic for the entire application.
# 3. ROBUSTNESS: The 'status' field in DocumentBase is still strictly typed to the
#    new, simpler Enum, maintaining architectural integrity.
#
# FINAL PRODUCTION VERSION V2.0: Enforces ISO 8601 date format.

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum

from .common import PyObjectId

# --- PHOENIX PROTOCOL: Define the new, simplified authoritative source of truth ---
class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    FAILED = "FAILED"


class DocumentBase(BaseModel):
    file_name: str
    # --- PHOENIX PROTOCOL: Enforce the simplified contract using the Enum ---
    status: DocumentStatus = DocumentStatus.PENDING
    mime_type: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DocumentInDB(DocumentBase):
    id: PyObjectId = Field(alias="_id")
    case_id: PyObjectId
    owner_id: PyObjectId
    storage_key: str
    processed_text_storage_key: Optional[str] = None
    error_message: Optional[str] = None
    category: Optional[str] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        from_attributes=True,
        # --- DEFINITIVE FIX: Ensure all dates are sent in a standard format ---
        json_encoders={
            PyObjectId: str,
            # This forces all datetime objects to be converted to ISO 8601 strings
            # e.g., "2025-10-15T19:30:00", which JavaScript can always parse.
            datetime: lambda v: v.isoformat()
        }
    )

class DocumentOut(DocumentInDB):
    # This model inherits the simplified DocumentStatus enum, ensuring the API
    # contract is consistent with the new three-state logic.
    pass