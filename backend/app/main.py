# FILE: backend/app/main.py
# PHOENIX PROTOCOL - FINAL ROUTER ASSEMBLY
# 1. ACTIVATED: 'business_router' for Graph Visualization & Firm Settings.
# 2. FIX: Added type ignore to ProxyHeadersMiddleware to silence Pylance false positive.

from fastapi import FastAPI, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
import logging
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
# PHOENIX FIX: Now active
from app.api.endpoints.business import router as business_router

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
# PHOENIX FIX: Added type: ignore because Uvicorn middleware typing doesn't match FastAPI expectation exactly
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"]) # type: ignore

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|.*\.vercel\.app|.*\.duckdns\.org|juristi\.tech|.*\.juristi\.tech)(:\d+)?",
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
# PHOENIX FIX: Registered
api_v1_router.include_router(business_router, prefix="/business", tags=["Business"])

app.include_router(api_v1_router)

# --- V2 ROUTER ASSEMBLY ---
if drafting_v2_router:
    api_v2_router = APIRouter(prefix="/api/v2")
    api_v2_router.include_router(drafting_v2_router)
    app.include_router(api_v2_router)

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health Check"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}