# FILE: backend/app/api/endpoints/share.py
# PHOENIX PROTOCOL - SHARE ENDPOINT V1.2 (EXPLICIT IMPORT)
# 1. FIX: Changed import to direct function import to resolve Pylance attribute error.
# 2. STATUS: Static Analysis Safe.

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, RedirectResponse, HTMLResponse
from typing import Annotated
from bson import ObjectId
from pymongo.database import Database

# PHOENIX FIX: Explicit import from the module file, bypassing __init__
from app.services.social_service import generate_social_card
from ...models.user import UserInDB
from .dependencies import get_db, get_current_user

router = APIRouter(tags=["Social"])

@router.get("/c/{case_id}/image")
async def get_case_social_image(
    case_id: str,
    db: Database = Depends(get_db)
):
    """
    Generates the PNG image for the social card.
    """
    try:
        # Public access allowed for the image (Metadata only)
        case = db.cases.find_one({"_id": ObjectId(case_id)})
        if not case: return Response(status_code=404)
        
        title = case.get("title", "Rast Ligjor")
        client = case.get("client", {}).get("name", "Anonim")
        status = "Hapur" 
        
        # Call function directly
        img_bytes = generate_social_card(title, client, status)
        return Response(content=img_bytes, media_type="image/png")
    except Exception:
        return Response(status_code=404)

@router.get("/c/{case_id}")
async def share_case_link(
    request: Request,
    case_id: str,
    db: Database = Depends(get_db)
):
    """
    The Smart Link.
    - If User-Agent is a Bot (WhatsApp/FB): Returns HTML with Meta Tags.
    - If User-Agent is Human: Redirects to Frontend.
    """
    user_agent = request.headers.get("user-agent", "").lower()
    
    # Detect social bots
    bots = ['facebookexternalhit', 'whatsapp', 'twitterbot', 'telegrambot', 'linkedinbot']
    is_bot = any(bot in user_agent for bot in bots)

    # TODO: Configure your actual frontend URL here
    FRONTEND_URL = "https://juristi.tech" 
    API_URL = "https://api.juristi.tech/api/v1" 

    if is_bot:
        case = db.cases.find_one({"_id": ObjectId(case_id)})
        title = case.get("title", "Rast Ligjor") if case else "Rast Ligjor"
        desc = f"Shiko detajet e rastit {title} në platformën e sigurt Juristi AI."
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta property="og:title" content="{title} | Juristi AI" />
            <meta property="og:description" content="{desc}" />
            <meta property="og:image" content="{API_URL}/share/c/{case_id}/image" />
            <meta property="og:type" content="website" />
            <meta name="twitter:card" content="summary_large_image" />
        </head>
        <body>
            <h1>Redirecting...</h1>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    
    # If human, go to the portal
    return RedirectResponse(url=f"{FRONTEND_URL}/portal/{case_id}")