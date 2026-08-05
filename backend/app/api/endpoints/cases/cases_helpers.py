# FILE: app/api/endpoints/cases/cases_helpers.py
from fastapi import HTTPException, Depends
from typing import List, Annotated, Dict, Any, Optional
from pydantic import BaseModel
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime

from app.models.user import UserInDB
from app.api.endpoints.dependencies import get_current_user
from app.models.chat import ChatMessage

def validate_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format.")

def json_serializable(data):
    if isinstance(data, list):
        return [json_serializable(item) for item in data]
    if isinstance(data, dict):
        return {k: json_serializable(v) for k, v in data.items()}
    if isinstance(data, datetime):
        return data.isoformat()
    if isinstance(data, ObjectId):
        return str(data)
    return data

def require_pro_tier(current_user: Annotated[UserInDB, Depends(get_current_user)]):
    return

class DeletedDocumentResponse(BaseModel):
    documentId: str
    deletedFindingIds: List[str]

class BulkDeleteDocumentsRequest(BaseModel):
    document_ids: Optional[List[str]] = None
    documentIds: Optional[List[str]] = None

class RenameDocumentRequest(BaseModel):
    new_name: str

class FinanceInterrogationRequest(BaseModel):
    question: str

class ArchiveStrategyRequest(BaseModel):
    legal_data: Dict[str, Any]
    deep_data: Dict[str, Any]

class ChatHistoryUpdate(BaseModel):
    chat_history: List[ChatMessage]

class UpdateCasePositionRequest(BaseModel):
    client_position: str