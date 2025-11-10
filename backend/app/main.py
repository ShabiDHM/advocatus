# FILE: backend/app/main.py
# PHOENIX PROTOCOL CURE 51.2 (REFINED ROUTER ISOLATION DIAGNOSTIC):
# 1. AUTH and USERS routers have been re-enabled to allow login and testing.
# 2. CALENDAR router remains enabled.
# 3. All other routers remain disabled to continue the path collision test.

from fastapi import FastAPI, Request, status, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import re

from app.core.lifespan import lifespan
from app.core.config import settings

# Import the necessary routers for this diagnostic
from app.api.endpoints import auth, users, calendar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ForceHTTPSMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("x-forwarded-proto") == "https":
            request.scope["scheme"] = "https"
        return await call_next(request)

app = FastAPI(title="The Phoenix Protocol API - REFINED DIAGNOSTIC MODE", lifespan=lifespan)
ALLOWED_ORIGINS = settings.BACKEND_CORS_ORIGINS
VERCEL_PREVIEW_REGEX = r"^https:\/\/(localhost:\d+|([a-zA-Z0-9-]+\.)?(vercel\.app|shabans-projects-31c11eb7\.vercel\.app|advocatus-ai\.vercel\.app))"

app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"], allow_origin_regex=VERCEL_PREVIEW_REGEX, expose_headers=["Content-Disposition"])
app.add_middleware(ForceHTTPSMiddleware)

@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Internal server error"})

api_router = APIRouter(prefix="/api/v1")

# --- REFINED ROUTER ISOLATION ---
# Login, User, and Calendar routers are enabled. All others are disabled.
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])

# --- Potentially Conflicting Routers (DISABLED) ---
# from app.api.endpoints import cases, documents, chat, admin, search, findings, api_keys
# api_router.include_router(cases.router, prefix="/cases", tags=["Cases"])
# api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
# api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
# api_router.include_router(search.router, prefix="/search", tags=["Search"])
# api_router.include_router(findings.router, prefix="/findings", tags=["Findings"])
# api_router.include_router(api_keys.router, prefix="/keys", tags=["API Keys"])
# api_router.include_router(admin.router, prefix="/admin", tags=["Administrator"])

app.include_router(api_router)

# --- Other Routers (DISABLED) ---
# from app.api.endpoints import drafting_v2
# from app.api.endpoints.websockets import router as websockets_router
# app.include_router(drafting_v2.router, prefix="/api/v2", tags=["Drafting V2"])
# app.include_router(websockets_router)

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health Check"])
def health_check(): return {"message": "ok"}

@app.get("/", tags=["Root"])
async def read_root(): return {"message": "Phoenix Protocol Backend is operational."}