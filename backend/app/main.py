# FILE: backend/app/main.py
# PHOENIX PROTOCOL DEFINITIVE CURE (CONFIGURATION ALIGNMENT)
# 1. CRITICAL FIX: The entire manual parsing block for CORS origins has been removed.
# 2. The `allow_origins` parameter now correctly and directly uses `settings.BACKEND_CORS_ORIGINS`.
# 3. This resolves the fundamental conflict between the Pydantic settings parser and the
#    application logic, permanently curing the CORS and WebSocket connection failures.

from fastapi import FastAPI, Request, status, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import List
import re

from app.core.lifespan import lifespan
from app.core.config import settings
from app.api.endpoints import (
    auth, cases, documents, chat, admin,
    websockets, search, findings, drafting_v2, api_keys,
    users,
    calendar
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Middleware to ensure FastAPI recognizes HTTPS scheme behind a reverse proxy.
class ForceHTTPSMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None: super().__init__(app)
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("x-forwarded-proto") == "https": request.scope["scheme"] = "https"
        return await call_next(request)

app = FastAPI(title="The Phoenix Protocol API", lifespan=lifespan)

# --- PHOENIX CURE: Simplified and Corrected CORS Configuration ---
# The settings object already parses the JSON string from .env into a Python list.
# We now use that list directly, eliminating the conflict.
ALLOWED_ORIGINS = settings.BACKEND_CORS_ORIGINS
VERCEL_PREVIEW_REGEX = r"^https:\/\/(localhost:\d+|[a-zA-Z0-9-]+\.(vercel\.app|shabans-projects-31c11eb7\.vercel\.app|advocatus-ai\.vercel\.app))"

try:
    re.compile(VERCEL_PREVIEW_REGEX)
except re.error:
    logger.error("CORS regex failed to compile. Check VERCEL_PREVIEW_REGEX.")
    VERCEL_PREVIEW_REGEX = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=VERCEL_PREVIEW_REGEX,
    expose_headers=["Content-Disposition"]
)
logger.info(f"FastAPI CORS middleware enabled for origins: {ALLOWED_ORIGINS} and regex: {VERCEL_PREVIEW_REGEX}")
# --- End of Cure ---

app.add_middleware(ForceHTTPSMiddleware)

@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Internal server error"})

# --- Routing Configuration ---
api_router = APIRouter(prefix="/api/v1")

api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(cases.router, prefix="/cases", tags=["Cases"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(findings.router, prefix="/findings", tags=["Findings"])
api_router.include_router(api_keys.router, prefix="/keys", tags=["API Keys"])
api_router.include_router(calendar.router, prefix="/calendar/events", tags=["Calendar"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administrator"])

app.include_router(api_router)
app.include_router(drafting_v2.router, prefix="/api/v2", tags=["Drafting V2"])
app.include_router(websockets.router)

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health Check"])
def health_check(): return {"message": "ok"}

@app.get("/", tags=["Root"])
async def read_root(): return {"message": "Phoenix Protocol Backend is operational."}