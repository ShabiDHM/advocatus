# FILE: backend/app/api/endpoints/stream.py
# PHOENIX PROTOCOL - SYNCHRONOUS SSE IMPLEMENTATION V3.1
# FIX: Corrected Request parameter injection (FastAPI dependency)
# FIX: Type-safe synchronous implementation for PyMongo architecture

import json
import logging
import time
from typing import Generator, Optional
from fastapi import APIRouter, Depends, Query, Path, Request, HTTPException
from fastapi.responses import StreamingResponse
from jose import jwt, JWTError
from pydantic import BaseModel, ValidationError
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

class TokenPayload(BaseModel):
    sub: Optional[str] = None

def get_current_user_sse(request: Request) -> Optional[str]:
    """
    Synchronous token validation supporting both query param and Authorization header
    """
    # Try query parameter first (for SSE/EventSource compatibility)
    token = request.query_params.get("token")
    
    # If no query param, try Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
            return None
        return token_data.sub
    except (JWTError, ValidationError) as e:
        logger.warning(f"Token validation failed: {e}")
        return None

def event_generator(
    channel: str,
    user_id: Optional[str] = None,
    send_connected_event: bool = True
) -> Generator[str, None, None]:
    """
    Synchronous SSE generator using Redis pubsub.
    Compatible with PyMongo synchronous architecture.
    """
    redis_client = redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=10,
        socket_keepalive=True
    )
    
    pubsub = redis_client.pubsub()
    pubsub.subscribe(channel)
    logger.info(f"SSE: Subscribed to {channel} (user={user_id})")
    
    try:
        if send_connected_event:
            yield "event: connected\ndata: {\"status\": \"connected\"}\n\n"
        
        # Initial message to confirm subscription
        pubsub.get_message(timeout=1.0)
        
        while True:
            message = pubsub.get_message(timeout=1.0, ignore_subscribe_messages=True)
            if message and message.get('type') == 'message':
                yield f"event: update\ndata: {message['data']}\n\n"
            else:
                # Send keep-alive comment
                yield ": keep-alive\n\n"
            
            # Small sleep to prevent CPU spinning
            time.sleep(0.1)
            
    except Exception as e:
        logger.error(f"SSE generator error for channel {channel}: {e}")
        yield f"event: error\ndata: {{\"error\": \"Connection lost: {str(e)}\"}}\n\n"
    finally:
        try:
            pubsub.unsubscribe(channel)
            redis_client.close()
        except:
            pass

@router.get("/updates")
def stream_updates(request: Request):
    """
    User-level SSE: all updates for the authenticated user.
    """
    user_id = get_current_user_sse(request)
    
    if user_id is None:
        def unauthorized() -> Generator[str, None, None]:
            yield "event: error\ndata: Unauthorized\n\n"
        return StreamingResponse(unauthorized(), media_type="text/event-stream")
    
    # User-specific channel
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
def stream_entity(
    request: Request,
    stream_id: str = Path(..., description="Entity ID (case, document, etc.)")
):
    """
    Entity-level SSE: updates for a specific entity.
    The stream_id can be a case ID, document ID, etc.
    """
    user_id = get_current_user_sse(request)
    
    if user_id is None:
        def unauthorized() -> Generator[str, None, None]:
            yield "event: error\ndata: Unauthorized\n\n"
        return StreamingResponse(unauthorized(), media_type="text/event-stream")
    
    # Entity-specific channel
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
def test_stream_entity(
    stream_id: str = Path(...)
):
    """
    Test endpoint for SSE connectivity without authentication.
    Returns a simple test stream.
    """
    def test_generator() -> Generator[str, None, None]:
        yield "event: connected\ndata: {\"status\": \"test connected\"}\n\n"
        for i in range(5):
            yield f"event: test\ndata: {{\"message\": \"Test message {i}\", \"stream_id\": \"{stream_id}\"}}\n\n"
            time.sleep(1)
        yield "event: complete\ndata: {\"status\": \"test completed\"}\n\n"
    
    return StreamingResponse(
        test_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )