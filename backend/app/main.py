# FILE: backend/app/main.py
# PHOENIX PROTOCOL - MAIN APPLICATION V7.4 (MOBILE CORS COMPLETE FIX)
# 1. FIX: Uses correct config attribute BACKEND_CORS_ORIGINS
# 2. FIX: Enhanced CORS for mobile devices
# 3. FIX: Removed restrictive regex, added proper IP support

from fastapi import FastAPI, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
import logging
import re
from app.core.lifespan import lifespan
from app.core.config import settings

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
from app.api.endpoints import finance_wizard
from app.api.endpoints.graph import router as graph_router
from app.api.endpoints.archive import router as archive_router
from app.api.endpoints.drafting_v2 import router as drafting_v2_router
from app.api.endpoints.share import router as share_router
from app.api.endpoints.organizations import router as organizations_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Juristi AI API", lifespan=lifespan)

# --- MIDDLEWARE ---
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")  # type: ignore

# --- MOBILE CORS VALIDATION FUNCTION ---
def is_valid_origin(origin: str) -> bool:
    """Validate origin with multiple patterns for mobile and desktop support"""
    
    # Allow empty origin (for mobile apps, curl, etc.)
    if not origin:
        return True
    
    # Common patterns to allow
    patterns = [
        # Localhost with any port
        r"https?://localhost(:\d+)?",
        r"https?://127\.0\.0\.1(:\d+)?",
        
        # Local network IPs (for mobile devices on same network)
        r"https?://192\.168\.\d+\.\d+(:\d+)?",
        r"https?://10\.\d+\.\d+\.\d+(:\d+)?",
        r"https?://172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+(:\d+)?",
        
        # Your domains
        r"https?://([\w-]+\.)?juristi\.tech",
        r"https?://([\w-]+\.)?vercel\.app",
        
        # Development patterns
        r"https?://[\w-]+\.local(:\d+)?",
        
        # Server IPs (if accessing directly)
        r"https?://\d+\.\d+\.\d+\.\d+(:\d+)?",
    ]
    
    for pattern in patterns:
        if re.match(pattern, origin, re.IGNORECASE):
            return True
    
    return False

# --- CORS CONFIGURATION ---
# Use config from settings
allowed_origins = settings.BACKEND_CORS_ORIGINS

# Add common mobile/development origins if not already present
common_origins = [
    "http://localhost:3000",
    "http://localhost:5173", 
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

for origin in common_origins:
    if origin not in allowed_origins:
        allowed_origins.append(origin)

logger.info(f"CORS Configuration - Allowed Origins: {allowed_origins}")
logger.info(f"CORS Configuration - Environment: {settings.ENVIRONMENT}")

# Primary CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Custom middleware for dynamic mobile origin validation
@app.middleware("http")
async def mobile_cors_middleware(request, call_next):
    """Additional CORS handling for mobile devices"""
    origin = request.headers.get("origin")
    
    if origin:
        # Check if origin is already allowed
        is_allowed = origin in allowed_origins
        
        # If not in list, validate with mobile patterns
        if not is_allowed and is_valid_origin(origin):
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response
        
        # For development, be more permissive
        if not is_allowed and settings.ENVIRONMENT == "development":
            logger.info(f"Allowing origin in development: {origin}")
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response
    
    return await call_next(request)

# --- ROUTER ASSEMBLY ---
api_v1_router = APIRouter(prefix="/api/v1")

# Core Modules
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

# Finance Modules
api_v1_router.include_router(finance_router, prefix="/finance", tags=["Finance"])
api_v1_router.include_router(finance_wizard.router, prefix="/finance/wizard", tags=["Finance Wizard"])

# Advanced Modules
api_v1_router.include_router(graph_router, prefix="/graph", tags=["Graph"])
api_v1_router.include_router(archive_router, prefix="/archive", tags=["Archive"])
api_v1_router.include_router(share_router, prefix="/share", tags=["Share"])

# V2 Modules
api_v2_router = APIRouter(prefix="/api/v2")
api_v2_router.include_router(drafting_v2_router, prefix="/drafting", tags=["Drafting V2"])

# Register Routers
app.include_router(api_v1_router)
app.include_router(api_v2_router)

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health Check"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}

# --- DIAGNOSTIC: PRINT ROUTES ON STARTUP ---
@app.on_event("startup")
async def log_all_routes():
    logger.info("PHOENIX PROTOCOL - ROUTE AUDIT")
    logger.info("------------------------------")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"CORS Origins: {len(allowed_origins)} configured")
    logger.info(f"Mobile CORS: Enabled")
    for route in app.routes:
        if isinstance(route, APIRoute):
            logger.info(f"Route: {route.path} [{','.join(route.methods)}]")
    logger.info("------------------------------")