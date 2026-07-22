# FILE: backend/app/api/endpoints/share.py
# PHOENIX PROTOCOL - SMART SHARE ENDPOINT V3.1 (SAFE PUBLIC PORTAL API)

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from pymongo.database import Database
from typing import Optional
from bson import ObjectId
import logging

from app.api.endpoints.dependencies import get_db
from app.services import case_service, storage_service

router = APIRouter()
logger = logging.getLogger(__name__)

# CONFIGURATION
FRONTEND_URL = "https://juristi.tech"
API_URL = "https://api.juristi.tech" 

# --- LANDING PREVIEW (Fixes 404) ---
@router.get("/landing/preview", include_in_schema=False)
async def get_landing_preview():
    return RedirectResponse(url=f"{FRONTEND_URL}/pwa-512x512.png")

# --- PUBLIC CLIENT PORTAL ENDPOINTS ---
@router.get("/public/{case_id}/timeline")
async def get_public_case_timeline(
    case_id: str,
    db: Database = Depends(get_db)
):
    """
    Public endpoint for the Client Portal to fetch case timeline, shared documents, and basic metadata.
    """
    try:
        case_data = case_service.get_public_case_events(db, case_id)
        if not case_data:
            raise HTTPException(status_code=404, detail="Case not found or not public.")
        return JSONResponse(case_data)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error fetching public timeline for case {case_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/public/{case_id}/logo")
async def get_public_firm_logo(
    case_id: str,
    db: Database = Depends(get_db)
):
    try:
        case_oid = ObjectId(case_id)
        case = db.cases.find_one({"_id": case_oid})
        if not case:
            raise HTTPException(status_code=404)
        
        owner_id = case.get("owner_id") or case.get("user_id")
        if not owner_id:
            raise HTTPException(status_code=404)
            
        profile = db.business_profiles.find_one({"$or": [{"user_id": owner_id}, {"user_id": str(owner_id)}]})
        if not profile or not profile.get("logo_storage_key"):
            raise HTTPException(status_code=404)
            
        logo_key = profile["logo_storage_key"]
        stream = storage_service.get_file_stream(logo_key)
        if not stream:
            raise HTTPException(status_code=404)
            
        return StreamingResponse(stream, media_type="image/png")
    except Exception:
        raise HTTPException(status_code=404, detail="Logo not found.")

@router.get("/public/{case_id}/documents/{doc_id}/download")
async def download_public_shared_document(
    case_id: str,
    doc_id: str,
    source: str = "ACTIVE",
    db: Database = Depends(get_db)
):
    try:
        if source == "ARCHIVE":
            archive_item = db.archives.find_one({"_id": ObjectId(doc_id)})
            if not archive_item or not archive_item.get("is_shared"):
                raise HTTPException(status_code=403, detail="Access denied.")
            storage_key = archive_item.get("storage_key")
            filename = archive_item.get("title", "document.pdf")
        else:
            doc = db.documents.find_one({"_id": ObjectId(doc_id)})
            if not doc or not doc.get("is_shared"):
                raise HTTPException(status_code=403, detail="Access denied.")
            storage_key = doc.get("storage_key") or doc.get("preview_storage_key")
            filename = doc.get("file_name", "document.pdf")

        if not storage_key:
            raise HTTPException(status_code=404, detail="File not found in storage.")

        stream = storage_service.get_file_stream(storage_key)
        if not stream:
            raise HTTPException(status_code=404, detail="File stream error.")

        return StreamingResponse(
            stream,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=\"{filename}\"",
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

# --- CASE PREVIEW ---
@router.get("/{case_id}", response_class=HTMLResponse)
async def get_smart_share_preview(
    request: Request, 
    case_id: str, 
    db: Database = Depends(get_db)
):
    case_data = case_service.get_public_case_events(db, case_id)
    
    if not case_data:
        return f"""
        <html>
            <head>
                <meta http-equiv="refresh" content="0;url={FRONTEND_URL}" />
            </head>
            <body>Redirecting...</body>
        </html>
        """

    title = case_data.get("title", "Rast Ligjor")
    client = case_data.get("client_name", "Klient")
    case_number = case_data.get("case_number", "---")
    status = case_data.get("status", "OPEN").upper()
    org_name = case_data.get("organization_name", "Juristi Portal")
    
    logo_path = case_data.get("logo")
    logo_url = f"{FRONTEND_URL}/static/logo.png" 
    
    if logo_path:
        if logo_path.startswith("http"):
            logo_url = logo_path
        elif logo_path.startswith("/"):
            logo_url = f"{API_URL}{logo_path}"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="sq">
    <head>
        <meta charset="UTF-8">
        <title>{title} | {org_name}</title>
        
        <meta property="og:type" content="website" />
        <meta property="og:url" content="{FRONTEND_URL}/portal/{case_id}" />
        <meta property="og:title" content="{title} (#{case_number})" />
        <meta property="og:description" content="Klient: {client} | Status: {status} | {org_name}" />
        <meta property="og:image" content="{logo_url}" />
        <meta property="og:image:width" content="300" />
        <meta property="og:image:height" content="300" />
        
        <meta property="twitter:card" content="summary" />
        <meta property="twitter:title" content="{title} (#{case_number})" />
        <meta property="twitter:description" content="Klient: {client} | Status: {status}" />
        <meta property="twitter:image" content="{logo_url}" />

        <script>
            window.location.replace("{FRONTEND_URL}/portal/{case_id}");
        </script>
        
        <style>
            body {{ font-family: sans-serif; background: #0a0a0a; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .loader {{ border: 4px solid #333; border-top: 4px solid #6366f1; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        </style>
    </head>
    <body>
        <div class="loader"></div>
        <p style="margin-left: 15px;">Duke hapur dosjen...</p>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content, status_code=200)