# FILE: backend/app/main.py
# PHOENIX PROTOCOL - HTTPS/PROXY FIX
# 1. Added ProxyHeadersMiddleware to fix Mixed Content errors.
# 2. Registered SSE Stream Router.

from fastapi import FastAPI, Request, status, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
import traceback
import logging
from app.core.lifespan import lifespan
from app.core.config import settings

# --- Router Imports ---
try:
    from app.api.endpoints.auth import router as auth_router
    from app.api.endpoints.users import router as users_router
    from app.api.endpoints.cases import router as cases_router
    from app.api.endpoints.admin import router as admin_router
    from app.api.endpoints.calendar import router as calendar_router
    from app.api.endpoints.api_keys import router as api_keys_router
    from app.api.endpoints.chat import router as chat_router
    from app.api.endpoints.search import router as search_router
    from app.api.endpoints.stream import router as stream_router
    
    try:
        from app.api.endpoints.drafting_v2 import router as drafting_v2_router
    except ImportError:
        drafting_v2_router = None
        logging.warning("Drafting V2 router not found. Skipping.")
        
except ImportError as e:
    logging.error(f"FATAL: A router failed to import. Traceback: {traceback.format_exc()}")
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Advocatus AI API", lifespan=lifespan)

# --- MIDDLEWARE ASSEMBLY ---
# 1. Trust the Proxy (Caddy/Nginx/Cloudflare)
# This fixes the "http://" redirect bug.
# PHOENIX FIX: Added type: ignore to silence strict Pylance checks (runtime correct)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"]) # type: ignore

# 2. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- V1 API Router Assembly ---
api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(users_router, prefix="/users", tags=["Users"])
api_v1_router.include_router(cases_router, prefix="/cases", tags=["Cases"])
api_v1_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
api_v1_router.include_router(calendar_router, prefix="/calendar", tags=["Calendar"])
api_v1_router.include_router(api_keys_router, prefix="/api-keys", tags=["API Keys"])
api_v1_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_v1_router.include_router(search_router, prefix="/search", tags=["Search"])
api_v1_router.include_router(stream_router, prefix="/stream", tags=["Streaming"])

app.include_router(api_v1_router)

# --- V2 API Router Assembly ---
if drafting_v2_router:
    api_v2_router = APIRouter(prefix="/api/v2")
    # Drafting router already has prefix="/drafting", so we don't add it here
    api_v2_router.include_router(drafting_v2_router)
    app.include_router(api_v2_router)

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health Check"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}