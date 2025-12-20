# FILE: backend/app/api/endpoints/share.py
# PHOENIX PROTOCOL - SMART SHARE ENDPOINT
# 1. FEATURE: Generates Open Graph (OG) Metadata for Social Media Previews.
# 2. LOGIC: Bots see the Case Card; Humans are redirected to Client Portal.

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pymongo.database import Database
from typing import Optional
from bson import ObjectId

from app.api.endpoints.dependencies import get_db
from app.services import case_service

router = APIRouter()

# CONFIGURATION
FRONTEND_URL = "https://juristi.tech"
API_URL = "https://api.juristi.tech" # Adjust if your API domain is different

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
        # If case is private or doesn't exist, redirect to home
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
    
    # 3. Handle Logo URL (Must be Absolute for WhatsApp)
    logo_path = case_data.get("logo")
    logo_url = f"{FRONTEND_URL}/static/logo.png" # Default fallback
    
    if logo_path:
        if logo_path.startswith("http"):
            logo_url = logo_path
        elif logo_path.startswith("/"):
            # Construct absolute API URL for the logo
            logo_url = f"{API_URL}{logo_path}"

    # 4. Construct the HTML Response
    # The 'og:' tags are what WhatsApp/Viber read.
    # The <script> window.location is what redirects the user.
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="sq">
    <head>
        <meta charset="UTF-8">
        <title>{title} | {org_name}</title>
        
        <!-- Open Graph / Facebook / WhatsApp -->
        <meta property="og:type" content="website" />
        <meta property="og:url" content="{FRONTEND_URL}/portal/{case_id}" />
        <meta property="og:title" content="{title} (#{case_number})" />
        <meta property="og:description" content="Klient: {client} | Status: {status} | {org_name}" />
        <meta property="og:image" content="{logo_url}" />
        <meta property="og:image:width" content="300" />
        <meta property="og:image:height" content="300" />
        
        <!-- Twitter -->
        <meta property="twitter:card" content="summary" />
        <meta property="twitter:title" content="{title} (#{case_number})" />
        <meta property="twitter:description" content="Klient: {client} | Status: {status}" />
        <meta property="twitter:image" content="{logo_url}" />

        <!-- Automatic Redirect for Humans -->
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