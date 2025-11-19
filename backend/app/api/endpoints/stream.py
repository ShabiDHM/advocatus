# FILE: backend/app/api/endpoints/stream.py
# PHOENIX PROTOCOL - SSE IMPLEMENTATION
import asyncio
import json
import logging
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, Query
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

async def event_generator(user_id: Optional[str]) -> AsyncGenerator[str, None]:
    if not user_id:
        yield "event: error\ndata: Invalid Credentials\n\n"
        return
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    user_channel = f"user:{user_id}:updates"
    await pubsub.subscribe(user_channel)
    logger.info(f"SSE: User {user_id} connected to {user_channel}")
    try:
        yield "event: connected\ndata: {\"status\": \"connected\"}\n\n"
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                yield f"event: update\ndata: {message['data']}\n\n"
            yield ": keep-alive\n\n"
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        logger.info(f"SSE: User {user_id} disconnected.")
    finally:
        await pubsub.unsubscribe()
        await redis.close()

@router.get("/updates", response_class=StreamingResponse)
async def stream_updates(user_id: Optional[str] = Depends(get_current_user_sse)):
    if user_id is None:
        async def unauthorized(): yield "event: error\ndata: Unauthorized\n\n"
        return StreamingResponse(unauthorized(), media_type="text/event-stream")
    return StreamingResponse(event_generator(user_id), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})