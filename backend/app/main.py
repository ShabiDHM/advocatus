# FILE: backend/app/main.py
# PHOENIX PROTOCOL - THE DEFINITIVE AND FINAL VERSION (APPLICATION ENTRY POINT)
# CORRECTION: The router import system has been re-architected to be explicit.
# Instead of importing each module, we now directly import the 'router' object from
# each module with a unique alias. This resolves the Pylance 'reportAttributeAccessIssue'
# and makes the application's dependency structure robust and unambiguous.

from fastapi import FastAPI, Request, status, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.lifespan import lifespan
from app.core.config import settings

# --- Explicit Router Imports ---
# This pattern is robust and resolves static analysis errors.
try:
    from app.api.endpoints.auth import router as auth_router
    from app.api.endpoints.cases import router as cases_router
    from app.api.endpoints.documents import router as documents_router
    from app.api.endpoints.chat import router as chat_router
    from app.api.endpoints.admin import router as admin_router
    from app.api.endpoints.search import router as search_router
    from app.api.endpoints.findings import router as findings_router
    from app.api.endpoints.drafting_v2 import router as drafting_v2_router
    from app.api.endpoints.api_keys import router as api_keys_router
    from app.api.endpoints.users import router as users_router
    from app.api.endpoints.calendar import router as calendar_router
    from app.api.endpoints.websockets import router as websockets_router
except ImportError as e:
    logging.error(f"FATAL: A router failed to import, the application cannot start. Error: {e}")
    raise

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
all_allowed_origins = list(set(known_origins + settings.BACKEND_CORS_ORIGINS))
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
    logger.error(f"Unhandled exception for request {request.method} {request.url}:")
    traceback.print_exc()
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal server error occurred."}
    )

# --- API Router Assembly ---
api_router = APIRouter(prefix="/api/v1")

# Include all the modular routers using their new, explicit aliases
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(cases_router)
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(search_router, prefix="/search", tags=["Search"])
api_router.include_router(findings_router, prefix="/findings", tags=["Findings"])
api_router.include_router(api_keys_router, prefix="/keys", tags=["API Keys"])
api_router.include_router(calendar_router, prefix="/calendar", tags=["Calendar"])
api_router.include_router(admin_router, prefix="/admin", tags=["Administrator"])
api_router.include_router(websockets_router)

app.include_router(api_router)
app.include_router(drafting_v2_router, prefix="/api/v2", tags=["Drafting V2"])

# --- Root and Health Check Endpoints ---
@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health Check"])
def health_check():
    return {"status": "ok"}

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Phoenix Protocol Backend is operational."}