# FILE: backend/app/api/endpoints/stream.py
# PHOENIX PROTOCOL - ASYNCHRONOUS SSE IMPLEMENTATION V4.0
# FIX: Migrated to non-blocking redis.asyncio to prevent threadpool exhaustion on single-worker hosts
# FIX: Added 120-second JWT validation leeway to mitigate cross-cloud clock drift

import asyncio
import logging
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Path, Request
from fastapi.responses import StreamingResponse
from jose import jwt, JWTError
from pydantic import BaseModel, ValidationError
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

class TokenPayload(BaseModel):
    sub: Optional[str] = None

def get_current_user_sse(request: Request) -> Optional[str]:
    """
    Synchronous token validation supporting both query parameter and Authorization header.
    Includes a 120-second leeway to resolve cross-cloud clock drift issues.
    """
    token = request.query_params.get("token")
    
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        return None
    
    try:
        # Resolve clock drift issues with standard 120s leeway
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"leeway": 120}
        )
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
            return None
        return token_data.sub
    except (JWTError, ValidationError) as e:
        logger.warning(f"SSE token validation failed: {e}")
        return None

async def event_generator(
    channel: str,
    user_id: Optional[str] = None,
    send_connected_event: bool = True
) -> AsyncGenerator[str, None]:
    """
    Asynchronous SSE generator using redis.asyncio Pub/Sub.
    Keeps connections lightweight and prevents blocking the single-worker event loop.
    """
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=10,
        socket_keepalive=True
    )
    
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    logger.info(f"SSE: Subscribed asynchronously to channel: {channel} (user_id: {user_id})")
    
    try:
        if send_connected_event:
            yield "event: connected\ndata: {\"status\": \"connected\"}\n\n"
        
        # Clear the subscription acknowledgment message
        await pubsub.get_message(timeout=1.0)
        
        while True:
            # Fetch message asynchronously without blocking the loop
            message = await pubsub.get_message(timeout=1.0, ignore_subscribe_messages=True)
            if message and message.get('type') == 'message':
                yield f"event: update\ndata: {message['data']}\n\n"
            else:
                # Keep-alive comment to sustain connection and check health
                yield ": keep-alive\n\n"
            
            # Non-blocking sleep prevents execution-loop starvation
            await asyncio.sleep(0.5)
            
    except asyncio.CancelledError:
        logger.info(f"SSE: Connection closed by client for channel: {channel}")
    except Exception as e:
        logger.error(f"SSE generator error for channel {channel}: {e}")
        yield f"event: error\ndata: {{\"error\": \"Connection lost: {str(e)}\"}}\n\n"
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await redis_client.close()
            logger.info(f"SSE: Cleaned up subscription and Redis connection for channel: {channel}")
        except Exception as cleanup_err:
            logger.warning(f"SSE cleanup error on channel {channel}: {cleanup_err}")

@router.get("/updates")
async def stream_updates(request: Request):
    """
    User-level SSE: all updates for the authenticated user.
    """
    user_id = get_current_user_sse(request)
    
    if user_id is None:
        async def unauthorized() -> AsyncGenerator[str, None]:
            yield "event: error\ndata: Unauthorized\n\n"
        return StreamingResponse(unauthorized(), media_type="text/event-stream")
    
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

@router.get("/{stream_id}")
async def stream_entity(
    request: Request,
    stream_id: str = Path(..., description="Entity ID (case, document, etc.)")
):
    """
    Entity-level SSE: updates for a specific entity.
    """
    user_id = get_current_user_sse(request)
    
    if user_id is None:
        async def unauthorized() -> AsyncGenerator[str, None]:
            yield "event: error\ndata: Unauthorized\n\n"
        return StreamingResponse(unauthorized(), media_type="text/event-stream")
    
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

@router.get("/test/{stream_id}")
async def test_stream_entity(
    stream_id: str = Path(...)
):
    """
    Test endpoint for SSE connectivity without authentication validation.
    """
    async def test_generator() -> AsyncGenerator[str, None]:
        yield "event: connected\ndata: {\"status\": \"test connected\"}\n\n"
        for i in range(5):
            yield f"event: test\ndata: {{\"message\": \"Test message {i}\", \"stream_id\": \"{stream_id}\"}}\n\n"
            await asyncio.sleep(1)
        yield "event: complete\ndata: {\"status\": \"test completed\"}\n\n"
    
    return StreamingResponse(
        test_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )