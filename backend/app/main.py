from fastapi import FastAPI, Request, status, APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Annotated
import json
from bson import ObjectId
import asyncio
# PHOENIX PROTOCOL CURE: Import the missing 'Database' type hint.
from pymongo.database import Database

from app.core.lifespan import lifespan
from app.core.config import settings
from app.core.websocket_manager import manager
from app.services import chat_service, case_service
from app.core.db import get_db
from app.models.user import UserInDB

# Import all endpoint routers
try:
    from app.api.endpoints import (
        auth, cases, documents, chat, admin,
        search, findings, drafting_v2, api_keys,
        users, calendar
    )
    from app.api.endpoints.dependencies import get_current_user_ws
except ImportError as e:
    logging.error(f"Router import error: {e}")
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
    traceback.print_exc()
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Internal server error"})

# PHOENIX PROTOCOL CURE: The final, syntactically correct, and architecturally sound WebSocket endpoint.
@app.websocket("/ws/case/{case_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user_ws)],
    db: Database = Depends(get_db)
):
    try:
        validated_case_id = ObjectId(case_id)
    except Exception:
        return

    case = await asyncio.to_thread(
        case_service.get_case_by_id, db, validated_case_id, current_user
    )
    if not case:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = str(current_user.id)
    await manager.connect(websocket, case_id, user_id)
    
    # PHOENIX PROTOCOL CURE: The try/except block is now complete and correctly indented.
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            if message_type == "chat_message":
                payload = data.get("payload", {})
                text = payload.get("text")
                if text:
                    await chat_service.process_chat_message(
                        db=db,
                        manager=manager,
                        case_id=case_id,
                        user_query=text,
                        user_id=user_id
                    )
    except WebSocketDisconnect:
        # This clause handles graceful disconnection.
        pass
    except Exception as e:
        # This clause handles unexpected errors.
        logger.error(f"Error in WebSocket for user {user_id} in case {case_id}: {e}", exc_info=True)
    finally:
        # This clause ensures cleanup happens regardless of how the connection closes.
        await manager.disconnect(websocket, case_id, user_id)


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(cases.router, prefix="", tags=["Cases"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(findings.router, prefix="/findings", tags=["Findings"])
api_router.include_router(api_keys.router, prefix="/keys", tags=["API Keys"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administrator"])

app.include_router(api_router)
app.include_router(drafting_v2.router, prefix="/api/v2", tags=["Drafting V2"])

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health Check"])
def health_check(): return {"message": "ok"}

@app.get("/", tags=["Root"])
async def read_root(): return {"message": "Phoenix Protocol Backend is operational."}