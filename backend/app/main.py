# FILE: backend/app/main.py
# PHOENIX PROTOCOL - ROUTER REGISTRATION
# 1. ADDED: library_router for "Arkiva".
# 2. STATUS: All modules (Finance, Graph, Library) active.

from fastapi import FastAPI, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
import logging
import os
import json
from app.core.lifespan import lifespan

# --- Router Imports ---
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.users import router as users_router
from app.api.endpoints.cases import router as cases_router
from app.api.endpoints.admin import router as admin_router
from app.api.endpoints.calendar import router as calendar_router
from app.api.endpoints.chat import router as chat_router
from app.api.endpoints.stream import router as stream_router
from app.api.endpoints.support import router as support_router
from app.api.endpoints.business import router as business_router
from app.api.endpoints.finance import router as finance_router
from app.api.endpoints.graph import router as graph_router
from app.api.endpoints.library import router as library_router # <--- NEW

# Drafting V2 (Safe Import)
try:
    from app.api.endpoints.drafting_v2 import router as drafting_v2_router
except ImportError:
    drafting_v2_router = None
    logging.warning("Drafting V2 router not found. Skipping.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Juristi AI API", lifespan=lifespan)

# --- MIDDLEWARE ---
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"]) # type: ignore

origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://juristi.tech",
    "https://www.juristi.tech",
    "https://api.juristi.tech"
]

try:
    env_origins = os.getenv("BACKEND_CORS_ORIGINS")
    if env_origins:
        parsed = json.loads(env_origins)
        origins.extend(parsed)
except Exception:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://(.*\.vercel\.app|.*\.duckdns\.org)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- V1 ROUTER ASSEMBLY ---
api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(users_router, prefix="/users", tags=["Users"])
api_v1_router.include_router(cases_router, prefix="/cases", tags=["Cases"])
api_v1_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
api_v1_router.include_router(calendar_router, prefix="/calendar", tags=["Calendar"])
api_v1_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_v1_router.include_router(stream_router, prefix="/stream", tags=["Streaming"])
api_v1_router.include_router(support_router, prefix="/support", tags=["Support"])
api_v1_router.include_router(business_router, prefix="/business", tags=["Business"])
api_v1_router.include_router(finance_router, prefix="/finance", tags=["Finance"])
api_v1_router.include_router(graph_router, prefix="/graph", tags=["Graph"])
api_v1_router.include_router(library_router, prefix="/library", tags=["Library"]) # <--- NEW

app.include_router(api_v1_router)

# --- V2 ROUTER ASSEMBLY ---
if drafting_v2_router:
    api_v2_router = APIRouter(prefix="/api/v2")
    api_v2_router.include_router(drafting_v2_router)
    app.include_router(api_v2_router)

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health Check"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}