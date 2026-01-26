# FILE: backend/app/api/endpoints/stream.py
# PHOENIX PROTOCOL - SSE IMPLEMENTATION V2 (TYPE SAFE)
# FIX: Added '/{stream_id}' endpoint to support per‑entity streaming.
import asyncio
import json
import logging
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, Query, Path
from fastapi.responses import StreamingResponse
from jose import jwt, JWTError
from pydantic import BaseModel, ValidationError
from redis.asyncio import Redis
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

class TokenPayload(BaseModel):
    sub: Optional[str] = None

async def get_current_user_sse(token: str = Query(..., description="JWT Access Token")) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
        if token_data.sub is None: return None
        return token_data.sub
    except (JWTError, ValidationError):
        return None

async def event_generator(
    channel: str,
    user_id: Optional[str] = None,
    send_connected_event: bool = True
) -> AsyncGenerator[str, None]:
    """
    Generic SSE generator for any Redis channel.
    :param channel: Redis channel to subscribe to.
    :param user_id: Optional user ID for logging.
    :param send_connected_event: If True, sends a 'connected' event at start.
    """
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)
    logger.info(f"SSE: Subscribed to {channel} (user={user_id})")
    try:
        if send_connected_event:
            yield "event: connected\ndata: {\"status\": \"connected\"}\n\n"
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                yield f"event: update\ndata: {message['data']}\n\n"
            yield ": keep-alive\n\n"
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        logger.info(f"SSE: Disconnected from {channel}")
    finally:
        await pubsub.unsubscribe()
        await redis.close()

@router.get("/updates", response_class=StreamingResponse)
async def stream_updates(user_id: Optional[str] = Depends(get_current_user_sse)):
    """
    User‑level SSE: all updates for the authenticated user.
    """
    if user_id is None:
        async def unauthorized(): yield "event: error\ndata: Unauthorized\n\n"
        return StreamingResponse(unauthorized(), media_type="text/event-stream")
    
    # User‑specific channel
    user_channel = f"user:{user_id}:updates"
    return StreamingResponse(
        event_generator(user_channel, user_id=user_id, send_connected_event=True),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/{stream_id}", response_class=StreamingResponse)
async def stream_entity(
    stream_id: str = Path(..., description="Entity ID (case, document, etc.)"),
    user_id: Optional[str] = Depends(get_current_user_sse)
):
    """
    Entity‑level SSE: updates for a specific entity.
    The stream_id can be a case ID, document ID, etc.
    """
    if user_id is None:
        async def unauthorized(): yield "event: error\ndata: Unauthorized\n\n"
        return StreamingResponse(unauthorized(), media_type="text/event-stream")
    
    # Entity‑specific channel (e.g., 'case:696620f2e2d3a1819a2cce19:updates')
    entity_channel = f"entity:{stream_id}:updates"
    return StreamingResponse(
        event_generator(entity_channel, user_id=user_id, send_connected_event=False),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )