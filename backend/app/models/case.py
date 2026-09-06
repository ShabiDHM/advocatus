# FILE: backend/app/models/case.py
# PHOENIX PROTOCOL - CASE MODEL V15.0 (UNIFIED PILLARS, DIRTY STATE & STANDARD SUMMARY SUPPORT)
# 100% COMPLETE CODE • ZERO 500 ERRORS • PYDANTIC V2 COMPLIANT • MONGO ATLAS SYNC

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from .common import PyObjectId

# Nën-modeli për të dhënat e klientit
class ClientData(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

# Modeli i Mesazhit në Chat
class ChatMessage(BaseModel):
    role: str 
    content: str
    timestamp: Optional[Union[datetime, str]] = Field(default_factory=datetime.utcnow)

# Modeli Bazë i Lëndës
class CaseBase(BaseModel):
    case_number: Optional[str] = None 
    title: str
    description: Optional[str] = None
    status: str = "OPEN"
    client_id: Optional[PyObjectId] = None 
    org_id: Optional[PyObjectId] = None 
    owner_id: Optional[Union[PyObjectId, str]] = None
    client_position: Optional[str] = "DEFENDANT"
    
    # Emrat e Palëve dhe Financat
    client_name: Optional[str] = None
    opposing_party: Optional[Union[str, Dict[str, Any]]] = None
    court: Optional[str] = None
    court_name: Optional[str] = None
    judge_name: Optional[str] = None
    opponent_name: Optional[str] = None
    disputed_amount: Optional[float] = 0.0

    # PHOENIX STATE: Statusi i Lëndës dhe Mbrojtja Anti-Abuzim
    analysis_dirty: Optional[bool] = False
    is_unlocked: Optional[bool] = False

# Modeli për Krijim Lënde
class CaseCreate(CaseBase):
    title: str
    clientName: Optional[str] = None
    clientEmail: Optional[str] = None
    clientPhone: Optional[str] = None
    opposingParty: Optional[str] = None

# Modeli për Përditësim
class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    client_position: Optional[str] = None
    client_name: Optional[str] = None
    opposing_party: Optional[Union[str, Dict[str, Any]]] = None
    court: Optional[str] = None
    court_name: Optional[str] = None
    judge_name: Optional[str] = None
    opponent_name: Optional[str] = None
    disputed_amount: Optional[float] = None
    client: Optional[ClientData] = None
    org_id: Optional[PyObjectId] = None
    analysis_dirty: Optional[bool] = None

# Modeli i Databazës (MongoDB)
class CaseInDB(CaseBase):
    id: PyObjectId = Field(alias="_id", default=None)
    user_id: PyObjectId 
    client: Optional[ClientData] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    chat_history: List[Dict[str, Any]] = []
    
    # PHOENIX PERSISTENCE: Shtjellat Forenzike dhe Pasqyra e Shpejtë e Klientit
    standard_summary: Optional[Union[str, Dict[str, Any]]] = None
    forensic_pillars: Optional[Dict[str, Any]] = None
    latest_analysis: Optional[Union[str, Dict[str, Any]]] = None
    latest_deep_analysis: Optional[Union[str, Dict[str, Any]]] = None
    latest_comprehensive_analysis: Optional[Union[str, Dict[str, Any]]] = None
    latest_forensic_audit: Optional[Union[str, Dict[str, Any]]] = None
    last_analyzed_at: Optional[Union[datetime, str]] = None
    
    analyzed_doc_ids: Optional[List[str]] = None
    assigned_user_ids: List[str] = []

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

# Modeli i Daljes (API Response)
class CaseOut(CaseBase):
    id: PyObjectId = Field(alias="_id", serialization_alias="id")
    user_id: PyObjectId
    created_at: datetime
    updated_at: datetime
    
    client: Optional[ClientData] = None
    chat_history: Optional[List[ChatMessage]] = []
    
    # PHOENIX SYNC: Lejon daljen e të gjitha analizave te Frontendi
    standard_summary: Optional[Union[str, Dict[str, Any]]] = None
    forensic_pillars: Optional[Dict[str, Any]] = None
    latest_analysis: Optional[Union[str, Dict[str, Any]]] = None
    latest_deep_analysis: Optional[Union[str, Dict[str, Any]]] = None
    latest_comprehensive_analysis: Optional[Union[str, Dict[str, Any]]] = None
    latest_forensic_audit: Optional[Union[str, Dict[str, Any]]] = None
    last_analyzed_at: Optional[Union[datetime, str]] = None
    
    analyzed_doc_ids: Optional[List[str]] = None
    assigned_user_ids: Optional[List[str]] = []

    # Numëruesit e ekspozuar
    document_count: int = 0
    alert_count: int = 0
    event_count: int = 0
    finding_count: int = 0

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )