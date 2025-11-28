# FILE: backend/app/api/endpoints/business.py
# PHOENIX PROTOCOL - BUSINESS ENDPOINTS (TYPE SAFE)
# 1. FIX: Added 'Optional' type hints.
# 2. FIX: Safe file name handling.
# 3. FIX: Driver connectivity check before session usage.

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import Annotated, Dict, Any, Optional
from pymongo.database import Database
import logging
import os
import boto3
from botocore.exceptions import NoCredentialsError

from ...models.user import UserInDB
from .dependencies import get_current_user, get_db
from ...services.graph_service import graph_service

router = APIRouter(tags=["Business"])
logger = logging.getLogger(__name__)

# B2 Config
B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APP_KEY = os.getenv("B2_APPLICATION_KEY")
B2_BUCKET = os.getenv("B2_BUCKET_NAME")
B2_ENDPOINT = os.getenv("B2_ENDPOINT_URL")

def get_b2_client():
    return boto3.client(
        's3',
        endpoint_url=B2_ENDPOINT,
        aws_access_key_id=B2_KEY_ID,
        aws_secret_access_key=B2_APP_KEY
    )

# --- FIRM MANAGEMENT ---

@router.get("/settings", response_model=Dict[str, Any])
async def get_business_settings(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    settings = db.business_settings.find_one({"user_id": current_user.id})
    if not settings:
        return {"firm_name": "My Law Firm", "setup_complete": False}
    return {k: v for k, v in settings.items() if k != "_id"}

@router.post("/settings", status_code=status.HTTP_200_OK)
async def update_business_settings(
    settings: Dict[str, Any],
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    db.business_settings.update_one(
        {"user_id": current_user.id},
        {"$set": settings},
        upsert=True
    )
    return {"status": "updated"}

@router.post("/logo", status_code=status.HTTP_200_OK)
async def upload_business_logo(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    file: UploadFile = File(...) # Moved to end to satisfy some linters, though FastAPI handles dependency order.
):
    """Uploads a business logo to B2 and updates settings."""
    if not B2_BUCKET or not B2_KEY_ID:
        raise HTTPException(status_code=500, detail="Storage not configured")

    try:
        s3 = get_b2_client()
        
        # PHOENIX FIX: Safe filename handling
        filename = file.filename or "logo.png"
        file_ext = filename.split(".")[-1] if "." in filename else "png"
        
        key = f"logos/{current_user.id}_logo.{file_ext}"
        
        s3.upload_fileobj(file.file, B2_BUCKET, key)
        
        # Simple URL construction
        logo_url = f"{B2_ENDPOINT}/{B2_BUCKET}/{key}".replace("s3.eu-central-003.backblazeb2.com", "f003.backblazeb2.com/file") 
        
        db.business_settings.update_one(
            {"user_id": current_user.id},
            {"$set": {"logo_url": logo_url}},
            upsert=True
        )
        
        return {"url": logo_url}

    except Exception as e:
        logger.error(f"Logo Upload Failed: {e}")
        raise HTTPException(status_code=500, detail="Logo upload failed")

# --- SENTIENT PARTNER ---

@router.get("/graph/visualize", response_model=Dict[str, Any])
async def get_graph_data(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    center_node: Optional[str] = None # PHOENIX FIX: Added Optional type hint
):
    try:
        query_center = center_node or current_user.username
        
        query = """
        MATCH (n)-[r]->(m)
        RETURN n, r, m
        LIMIT 50
        """
        
        # PHOENIX FIX: Explicit connection check
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