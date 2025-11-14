# FILE: backend/app/main.py
# PHOENIX PROTOCOL PHASE XIII - MODIFICATION 16.0 (Final Integrity Check)
# CORRECTION: Restored the 'APIRouter' import from FastAPI. This was an inadvertent
# regression that caused a NameError, preventing the server from starting. The
# application's entry point is now syntactically correct and architecturally sound.

from fastapi import FastAPI, Request, status, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.lifespan import lifespan
from app.core.config import settings

# Import all endpoint routers from the central API module
try:
    from app.api.endpoints import (
        auth, cases, documents, chat, admin,
        search, findings, drafting_v2, api_keys,
        users, calendar, websockets
    )
except ImportError as e:
    logging.error(f"FATAL: A router failed to import, the application cannot start. Error: {e}")
    raise

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# This middleware is for handling reverse proxy scenarios (e.g., Traefik, Nginx)
class ForceHTTPSMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("x-forwarded-proto") == "https":
            request.scope["scheme"] = "https"
        return await call_next(request)

app = FastAPI(title="The Phoenix Protocol API", lifespan=lifespan)

# --- CORS Configuration ---
known_origins = [
    "https://advocatus-ai.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
]
# Combine settings from .env with hardcoded known origins
all_allowed_origins = list(set(known_origins + settings.BACKEND_CORS_ORIGINS))
# Regex for Vercel preview deployments
vercel_preview_regex = r"https:\/\/advocatus-ai-.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=all_allowed_origins,
    allow_origin_regex=vercel_preview_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.add_middleware(ForceHTTPSMiddleware)

@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    # Log the exception for debugging purposes
    logger.error(f"Unhandled exception for request {request.method} {request.url}:")
    traceback.print_exc()
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal server error occurred."}
    )

# --- API Router Assembly ---
# All API endpoints are organized under the /api/v1 prefix.
api_router = APIRouter(prefix="/api/v1")

# Include all the modular routers
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(cases.router) # Includes its own prefix
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(findings.router, prefix="/findings", tags=["Findings"])
api_router.include_router(api_keys.router, prefix="/keys", tags=["API Keys"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administrator"])
api_router.include_router(websockets.router) # The corrected WebSocket router is now included

# Mount the main API router into the app
app.include_router(api_router)

# Mount the V2 router separately
app.include_router(drafting_v2.router, prefix="/api/v2", tags=["Drafting V2"])

# --- Root and Health Check Endpoints ---
@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health Check"])
def health_check():
    return {"status": "ok"}

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Phoenix Protocol Backend is operational."}