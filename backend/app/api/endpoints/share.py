# FILE: backend/app/api/endpoints/share.py
# PHOENIX PROTOCOL - SMART SHARE ENDPOINT V2.0 (LANDING FIX)
# 1. FIX: Added '/landing/preview' endpoint to resolve 404 errors in social media parsers.
# 2. LOGIC: Redirects to the static PWA icon hosted by the frontend.
# 3. FEATURE: Retains dynamic case preview logic for bots.

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pymongo.database import Database
from typing import Optional
from bson import ObjectId

from app.api.endpoints.dependencies import get_db
from app.services import case_service

router = APIRouter()

# CONFIGURATION
FRONTEND_URL = "https://juristi.tech"
API_URL = "https://api.juristi.tech" 

# --- LANDING PREVIEW (Fixes 404) ---
@router.get("/landing/preview", include_in_schema=False)
async def get_landing_preview():
    """
    Redirects social media bots to the main high-res application icon.
    Used by index.html meta tags.
    """
    # Points to the static PWA asset served by Vercel/Frontend
    return RedirectResponse(url=f"{FRONTEND_URL}/pwa-512x512.png")

# --- CASE PREVIEW ---
@router.get("/{case_id}", response_class=HTMLResponse)
async def get_smart_share_preview(
    request: Request, 
    case_id: str, 
    db: Database = Depends(get_db)
):
    """
    Serves a static HTML page with Open Graph tags for Social Media Bots.
    Redirects real users to the React Client Portal.
    """
    # 1. Fetch Public Case Data
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

    # 2. Extract Data for Preview
    title = case_data.get("title", "Rast Ligjor")
    client = case_data.get("client_name", "Klient")
    case_number = case_data.get("case_number", "---")
    status = case_data.get("status", "OPEN").upper()
    org_name = case_data.get("organization_name", "Juristi Portal")
    
    # 3. Handle Logo URL
    logo_path = case_data.get("logo")
    logo_url = f"{FRONTEND_URL}/static/logo.png" 
    
    if logo_path:
        if logo_path.startswith("http"):
            logo_url = logo_path
        elif logo_path.startswith("/"):
            logo_url = f"{API_URL}{logo_path}"

    # 4. Construct the HTML Response
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