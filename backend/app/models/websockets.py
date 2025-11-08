# FILE: backend/app/models/websockets.py
# DEFINITIVE VERSION 1.0 (PHOENIX PROTOCOL: BROADCAST CONTRACT)
# 1. Defines the data model for internal document status updates.
# 2. Uses standard field names ('case_id', 'id') to ensure a stable contract
#    between the Celery worker and the main application's WebSocket manager.

from pydantic import BaseModel, Field
from typing import Optional
import datetime

class DocumentUpdatePayload(BaseModel):
    """
    Defines the strict data contract for internal document updates
    sent from a background worker to the main application for broadcasting.
    """
    id: str
    case_id: str
    status: str
    file_name: str
    upload_timestamp: datetime.datetime = Field(..., alias="uploadedAt")
    summary: Optional[str] = None

    class Config:
        populate_by_name = True # Allows population from aliases like 'uploadedAt'
        json_encoders = {datetime.datetime: lambda dt: dt.isoformat()}