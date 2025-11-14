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

from app.core.lifespan import lifespan
from app.core.config import settings
from app.core.websocket_manager import manager
# PHOENIX PROTOCOL CURE: We now import all necessary services and dependencies directly into main.
from app.services import chat_service, case_service
from app.core.db import get_async_db, get_db
from app.models.user import UserInDB

# Import all endpoint routers
try:
    from app.api.endpoints import (
        auth, cases, documents, chat, admin,
        search, findings, drafting_v2, api_keys,
        users, calendar
    )
    # This is the sole dependency needed for the live websocket endpoint.
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
# This remains correct.
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

# PHOENIX PROTOCOL CURE: THE FINAL, CORRECT WEBSOCKET ARCHITECTURE
# The endpoint is restored directly on the `app` object, which fixes the hanging API requests.
# The URL path `/ws/case/{case_id}` now correctly matches the frontend's hardcoded URL.
# It uses the re-architected, secure `get_current_user_ws` dependency.
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
        # No need to close, get_current_user_ws already accepted. The endpoint can just return.
        return

    # Check user has access to the case
    case = await asyncio.to_thread(
        case_service.get_case_by_id, db, validated_case_id, current_user
    )
    if not case:
        # The connection is already accepted, so we must close it gracefully.
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = str(current_user.id)
    await manager.connect(websocket, case_id, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            # Logic from websockets.py is integrated here.
            message_type = data.get("type")
            if message_type == "chat_message":
                payload = data.get("payload", {})
                text = payload.get("text")
                if text:
                    # Using db directly, no need for async_db dependency here to simplif