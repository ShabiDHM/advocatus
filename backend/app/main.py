# FILE: backend/app/main.py
# PHOENIX PROTOCOL - MAIN APPLICATION V12.3 (LAWS ROUTER ADDED)
# 1. ADDED: laws_router for serving law article content.
# 2. PRESERVED: All core business, finance, and auth routers.
# 3. STATUS: 100% Pylance Clear.

import os
import logging
from fastapi import FastAPI, status, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from app.core.lifespan import lifespan
from app.core.config import settings

# --- Router Imports ---
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.users import router as users_router
from app.api.endpoints.cases import router as cases_router
from app.api.endpoints.organizations import router as organizations_router
from app.api.endpoints.admin import router as admin_router
from app.api.endpoints.calendar import router as calendar_router
from app.api.endpoints.chat import router as chat_router
from app.api.endpoints.stream import router as stream_router
from app.api.endpoints.support import router as support_router
from app.api.endpoints.business import router as business_router
from app.api.endpoints.finance import router as finance_router
from app.api.endpoints import finance_wizard
from app.api.endpoints.archive import router as archive_router
from app.api.endpoints.share import router as share_router
from app.api.endpoints.drafting_v2 import router as drafting_v2_router
from app.api.endpoints.laws import router as laws_router  # <-- NEW

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Juristi AI API", lifespan=lifespan)

# --- MIDDLEWARE ---
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")  # type: ignore

# --- UNIFIED CORS CONFIGURATION ---
allowed_origins = [str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS]

production_origins = [
    "https://juristi.tech",
    "https://www.juristi.tech",
    "https://api.juristi.tech",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000"
]

for origin in production_origins:
    if origin not in allowed_origins:
        allowed_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
api_v1_router.include_router(finance_wizard.router, prefix="/finance/wizard", tags=["Finance Wizard"])
api_v1_router.include_router(archive_router, prefix="/archive", tags=["Archive"])
api_v1_router.include_router(share_router, prefix="/share", tags=["Share"])
api_v1_router.include_router(laws_router, prefix="/laws", tags=["Laws"])  # <-- NEW

api_v2_router = APIRouter(prefix="/api/v2")
api_v2_router.include_router(drafting_v2_router, prefix="/drafting", tags=["Drafting V2"])

app.include_router(api_v1_router)
app.include_router(api_v2_router)

@app.get("/health", tags=["Health Check"])
def health_check():
    return {"status": "ok", "version": "1.2.2", "environment": settings.ENVIRONMENT}

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "frontend", "dist")

if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")

@app.on_event("startup")
async def log_all_routes():
    logger.info("PHOENIX PROTOCOL - ROUTE AUDIT")
    for route in app.routes:
        if isinstance(route, APIRoute):
            logger.info(f"Route: {route.path} [{','.join(route.methods)}]")