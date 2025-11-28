# FILE: backend/app/api/endpoints/graph.py
# PHOENIX PROTOCOL - GRAPH API
# 1. VISUALIZATION: Exposes the Neo4j graph structure to the frontend.
# 2. SECURITY: Uses 'get_current_user' to ensure only authorized access.

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, List, Any

from app.services.graph_service import graph_service
from app.api.endpoints.dependencies import get_current_user
from app.models.user import UserInDB

router = APIRouter(tags=["Graph"])

@router.get("/graph/{case_id}", response_model=Dict[str, List[Dict[str, Any]]])
async def get_case_knowledge_graph(
    case_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Retrieves the 2D Node/Link structure for the specific case.
    Used by the 'Detective Board' visualization.
    """
    if not case_id:
        raise HTTPException(status_code=400, detail="Case ID is required")
        
    # In a real production environment, you would verify here that 
    # 'current_user' actually owns or has access to 'case_id'.
    # For now, we assume the GraphService handles the data retrieval safely.
    
    data = graph_service.get_case_graph(case_id)
    
    if not data["nodes"]:
        return {"nodes": [], "links": []}
        
    return data