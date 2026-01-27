# FILE: backend/app/models/evidence_map.py
# PHOENIX PROTOCOL - EVIDENCE MAP MODEL V2.0 (PHASE 5: LEGAL METADATA)
# 1. ADDED: Legal metadata fields to MapNodeData for tracking Exhibits, Authentication, and Claim Status.
# 2. STATUS: Backend schema ready for court-ready outputs.

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from .common import PyObjectId

# --- NODES ---
class MapNodeData(BaseModel):
    label: str
    content: Optional[str] = ""
    # Metadata for Claims/Evidence
    type: Optional[str] = "claim" # 'claim' | 'evidence'
    status: Optional[str] = "draft" # 'draft' | 'admitted' | 'disputed'
    
    # PHOENIX PHASE 5: LEGAL METADATA FIELDS
    exhibitNumber: Optional[str] = None      # e.g., "Ex. A-1", "Depo of J. Smith"
    isAuthenticated: Optional[bool] = None   # Evidence: Has it been authenticated?
    isAdmitted: Optional[str] = None         # Evidence: "Admitted" | "Stricken" | None
    isProven: Optional[bool] = None          # Claim: Is the claim proven by the current evidence?

    # Flexible dict for extra UI props to avoid schema breaks on frontend updates
    extras: Dict[str, Any] = {} 

class MapNode(BaseModel):
    id: str
    type: str # 'claimNode' | 'evidenceNode' (React Flow types)
    position: Dict[str, float] # {'x': 100.0, 'y': 200.0}
    data: MapNodeData
    
    # Dimensions for resizing
    width: Optional[float] = None
    height: Optional[float] = None
    selected: Optional[bool] = False
    dragging: Optional[bool] = False

# --- EDGES ---
class MapEdge(BaseModel):
    id: str
    source: str
    target: str
    type: Optional[str] = "default" # 'supports' | 'contradicts' | 'related'
    label: Optional[str] = None
    animated: Optional[bool] = False
    
    # Store line style logic here
    data: Optional[Dict[str, Any]] = {}

# --- MAIN DOCUMENT ---
class EvidenceMapInDB(BaseModel):
    id: PyObjectId = Field(alias="_id", default=None)
    case_id: PyObjectId
    org_id: PyObjectId # Inherited from Case for Multi-tenancy
    
    nodes: List[MapNode] = []
    edges: List[MapEdge] = []
    
    # Viewport State (Zoom/Pan)
    viewport: Dict[str, float] = {"x": 0, "y": 0, "zoom": 1}
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: PyObjectId

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

# --- API UPDATE MODEL ---
class EvidenceMapUpdate(BaseModel):
    nodes: List[MapNode]
    edges: List[MapEdge]
    viewport: Optional[Dict[str, float]] = None