# FILE: backend/app/api/endpoints/business.py
# PHOENIX PROTOCOL - BUSINESS ROUTER
# 1. IMPORTS: Validated path to models.
# 2. ENDPOINTS: Includes GET /logo/{user_id}.

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import Annotated, Dict, Any, Optional
from pymongo.database import Database
import logging

from ...models.user import UserInDB
from ...models.business import BusinessProfileInDB, BusinessProfileUpdate
from ...services.business_service import BusinessService
from ...services.graph_service import graph_service
from .dependencies import get_current_user, get_db

router = APIRouter(tags=["Business"])
logger = logging.getLogger(__name__)

def get_business_service(db: Database = Depends(get_db)) -> BusinessService:
    return BusinessService(db)

@router.get("/profile", response_model=BusinessProfileInDB)
async def get_business_profile(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    service: BusinessService = Depends(get_business_service)
):
    return service.get_or_create_profile(str(current_user.id))

@router.put("/profile", response_model=BusinessProfileInDB)
async def update_business_profile(
    data: BusinessProfileUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    service: BusinessService = Depends(get_business_service)
):
    return service.update_profile(str(current_user.id), data)

@router.put("/logo", response_model=BusinessProfileInDB)
async def upload_business_logo(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    service: BusinessService = Depends(get_business_service),
    file: UploadFile = File(...)
):
    return service.update_logo(str(current_user.id), file)

@router.get("/logo/{user_id}")
async def get_business_logo(
    user_id: str,
    # Auth required to view logo via this API route
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    service: BusinessService = Depends(get_business_service)
):
    stream, media_type = service.get_logo_stream(user_id)
    return StreamingResponse(stream, media_type=media_type)

# --- GRAPH VISUALIZATION ---
@router.get("/graph/visualize", response_model=Dict[str, Any])
async def get_graph_data(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    center_node: Optional[str] = None
):
    try:
        query = """
        MATCH (n)-[r]->(m)
        RETURN n, r, m
        LIMIT 50
        """
        
        graph_service._connect()
        if not graph_service._driver:
             return {"nodes": [], "links": [], "error": "Graph DB unavailable"}

        with graph_service._driver.session() as session:
            result = session.run(query)
            nodes = {}
            links = []
            
            for record in result:
                n, m = record["n"], record["m"]
                nodes[n.element_id] = {"id": n.element_id, "name": n.get("name", "Unknown"), "label": list(n.labels)[0] if n.labels else "Entity"}
                nodes[m.element_id] = {"id": m.element_id, "name": m.get("name", "Unknown"), "label": list(m.labels)[0] if m.labels else "Entity"}
                links.append({"source": n.element_id, "target": m.element_id, "label": record["r"].type})
            
            return {
                "nodes": list(nodes.values()),
                "links": links
            }

    except Exception as e:
        logger.error(f"Graph Viz Error: {e}")
        return {"nodes": [], "links": [], "error": str(e)}