# FILE: backend/app/main.py
# PHOENIX PROTOCOL - MAIN APPLICATION V13.1 (ELITE CORS STABILITY)
# 1. FIXED: Expanded allow_headers to include all common browser metadata.
# 2. FIXED: Added 'expose_headers' to allow frontend to read response status correctly.
# 3. STATUS: Protocol Compliant.

import os
import logging
from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from .core.lifespan import lifespan
from .core.config import settings

# Router Imports
from .api.endpoints.auth import router as auth_router
from .api.endpoints.users import router as users_router
from .api.endpoints.cases import router as cases_router
from .api.endpoints.organizations import router as organizations_router
from .api.endpoints.admin import router as admin_router
from .api.endpoints.calendar import router as calendar_router
from .api.endpoints.chat import router as chat_router
from .api.endpoints.stream import router as stream_router
from .api.endpoints.support import router as support_router
from .api.endpoints.business import router as business_router
from .api.endpoints.finance import router as finance_router
from .api.endpoints.finance_wizard import router as finance_wizard_router
from .api.endpoints.archive import router as archive_router
from .api.endpoints.share import router as share_router
from .api.endpoints.drafting_v2 import router as drafting_v2_router
from .api.endpoints.laws import router as laws_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Juristi AI API", lifespan=lifespan)

# --- MIDDLEWARE ---
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*") # type: ignore

# --- CORS CONFIGURATION (EXECUTIVE STABILITY) ---
origins = [
    "https://juristi.tech",
    "https://www.juristi.tech",
    "https://api.juristi.tech",
    "https://advocatus-ai.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods for simplicity in preflight
    allow_headers=[
        "Content-Type", 
        "Authorization", 
        "X-Requested-With", 
        "Accept", 
        "Origin",
        "Accept-Language",
        "Accept-Encoding",
    ],
    expose_headers=["*"],
)

# --- ROUTER ASSEMBLY ---
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(users_router, prefix="/users", tags=["Users"])
api_v1_router.include_router(cases_router, prefix="/cases", tags=["Cases"])
api_v1_router.include_router(organizations_router, prefix="/organizations", tags=["Organizations"])
api_v1_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
api_v1_router.include_router(calendar_router, prefix="/calendar", tags=["Calendar"])
api_v1_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_v1_router.include_router(stream_router, prefix="/stream", tags=["Streaming"])
api_v1_router.include_router(support_router, prefix="/support", tags=["Support"])
api_v1_router.include_router(business_router, prefix="/business", tags=["Business"])
api_v1_router.include_router(finance_router, prefix="/finance", tags=["Finance"])
api_v1_router.include_router(finance_wizard_router, prefix="/finance/wizard", tags=["Finance Wizard"])
api_v1_router.include_router(archive_router, prefix="/archive", tags=["Archive"])
api_v1_router.include_router(share_router, prefix="/share", tags=["Share"])
api_v1_router.include_router(laws_router, prefix="/laws", tags=["Laws"])

api_v2_router = APIRouter(prefix="/api/v2")
api_v2_router.include_router(drafting_v2_router, prefix="/drafting", tags=["Drafting V2"])

app.include_router(api_v1_router)
app.include_router(api_v2_router)

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.3.1"}

# Static Files Mount
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "frontend", "dist")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")