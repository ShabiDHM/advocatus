# FILE: backend/app/api/endpoints/stream.py
# PHOENIX PROTOCOL - SSE IMPLEMENTATION V5.0 (RESILIENT POOL + FALLBACK)
# V5.0: FIX KRITIK — Singleton async pool (jo connection per SSE), retry me
#       exponential backoff për subscribe, dhe graceful fallback nëse Redis
#       nuk përgjigjet (SSE vazhdon me heartbeat-only, pa live updates).
# V4.5: Pylance type fix.

import asyncio
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Path, Request
from fastapi.responses import StreamingResponse
from jose import jwt, JWTError
from pydantic import BaseModel, ValidationError
import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════
# V5.0: SINGLETON ASYNC REDIS POOL
# Një pool i vetëm për të gjitha SSE connections — shmang shterjen e lidhjeve.
# ═══════════════════════════════════════════════════════════════════════════

_async_redis_pool: Optional[aioredis.ConnectionPool] = None


def _get_async_redis_pool() -> aioredis.ConnectionPool:
    """Krijon (ose rikthen) pool-in singleton async Redis me retry strategy."""
    global _async_redis_pool

    if _async_redis_pool is not None:
        return _async_redis_pool

    redis_url = settings.REDIS_URL
    if not redis_url:
        raise ValueError("REDIS_URL missing from configuration.")

    _async_redis_pool = aioredis.ConnectionPool.from_url(
        redis_url,
        decode_responses=True,
        max_connections=20,              # kufi i arsyeshëm për free tier
        socket_timeout=10.0,
        socket_connect_timeout=5.0,
        socket_keepalive=True,
        health_check_interval=30,
        retry_on_timeout=True,
        retry_on_error=[RedisConnectionError, RedisTimeoutError],
    )
    logger.info("✅ [SSE] Async Redis pool initialized (max_connections=20)")
    return _async_redis_pool


async def _try_subscribe_with_retry(
    pubsub: aioredis.client.PubSub,
    channel: str,
    max_attempts: int = 3,
) -> bool:
    """Provo të subscribe me exponential backoff. Kthen True nëse sukses."""
    for attempt in range(1, max_attempts + 1):
        try:
            await asyncio.wait_for(pubsub.subscribe(channel), timeout=5.0)
            return True
        except (asyncio.TimeoutError, RedisConnectionError, RedisTimeoutError) as e:
            logger.warning(
                f"⚠️ [SSE] Subscribe attempt {attempt}/{max_attempts} failed for {channel}: "
                f"{type(e).__name__}: {e}"
            )
            if attempt < max_attempts:
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))  # 0.5s, 1s, 2s
        except Exception as e:
            logger.error(f"❌ [SSE] Unexpected subscribe error for {channel}: {e}")
            return False
    return False


class TokenPayload(BaseModel):
    sub: Optional[str] = None


def get_current_user_sse(request: Request) -> Optional[str]:
    """
    Synchronous token validation supporting both query parameter and Authorization header.
    Disables verify_exp specifically for this read-only stream connection to support long-lived browser tab reconnections.
    """
    token = request.query_params.get("token")

    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False}
        )
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
            return None
        return token_data.sub
    except (JWTError, ValidationError) as e:
        logger.warning(f"SSE token validation failed: {e}")
        return None


async def _heartbeat_only_fallback(
    channel: str,
    user_id: Optional[str] = None,
    send_connected_event: bool = True,
) -> AsyncGenerator[str, None]:
    """
    V5.0: Fallback nëse Redis nuk përgjigjet.
    SSE mbetet i hapur (pa live updates), duke dërguar vetëm ping-e.
    Kjo parandalon crash-in e ASGI + lejon frontend të vazhdojë.
    """
    logger.warning(f"🟡 [SSE] Fallback heartbeat-only aktiv për channel: {channel}")

    try:
        if send_connected_event:
            yield 'event: connected\ndata: {"status": "connected_no_pubsub"}\n\n'

        while True:
            yield 'event: ping\ndata: {}\n\n'
            await asyncio.sleep(5.0)
    except asyncio.CancelledError:
        logger.info(f"SSE: heartbeat fallback closed for {channel}")
        raise
    finally:
        logger.info(f"SSE: heartbeat fallback cleanup done for {channel}")


async def event_generator(
    channel: str,
    user_id: Optional[str] = None,
    send_connected_event: bool = True
) -> AsyncGenerator[str, None]:
    """
    Asynchronous SSE generator using redis.asyncio Pub/Sub.
    V5.0: Singleton pool + retry + graceful fallback.
    """
    redis_client = None
    pubsub = None
    subscribed = False

    try:
        # ─── 1. Krijo klient nga pool-i singleton ───
        try:
            pool = _get_async_redis_pool()
            redis_client = aioredis.Redis(connection_pool=pool)
            pubsub = redis_client.pubsub()
        except Exception as e:
            logger.error(f"❌ [SSE] Failed to get Redis client for {channel}: {e}")
            async for chunk in _heartbeat_only_fallback(channel, user_id, send_connected_event):
                yield chunk
            return

        # ─── 2. Retry subscribe ───
        subscribed = await _try_subscribe_with_retry(pubsub, channel, max_attempts=3)

        if not subscribed:
            logger.error(
                f"❌ [SSE] Could not subscribe to {channel} after retries — "
                f"fallback to heartbeat-only"
            )
            # Pastro pubsub-in para fallback
            try:
                if pubsub:
                    await pubsub.aclose()
            except Exception:
                pass
            async for chunk in _heartbeat_only_fallback(channel, user_id, send_connected_event):
                yield chunk
            return

        logger.info(f"SSE: Subscribed asynchronously to channel: {channel} (user_id: {user_id})")

        # ─── 3. Stream i normal ───
        if send_connected_event:
            yield 'event: connected\ndata: {"status": "connected"}\n\n'

        # Clear subscription acknowledgment
        try:
            await pubsub.get_message(timeout=1.0)
        except Exception as e:
            logger.debug(f"SSE: initial get_message skipped: {e}")

        while True:
            message = await pubsub.get_message(timeout=1.0, ignore_subscribe_messages=True)
            if message and message.get('type') == 'message':
                yield f"event: update\ndata: {message['data']}\n\n"
            else:
                yield 'event: ping\ndata: {}\n\n'

            await asyncio.sleep(0.5)

    except asyncio.CancelledError:
        logger.info(f"SSE: Connection closed by client for channel: {channel}")
        raise
    except Exception as e:
        # V5.0: NUK e hedhim më exception — vazhdojmë në fallback për stabilitet
        logger.error(f"SSE generator error for channel {channel}: {type(e).__name__}: {e}")
        try:
            yield f'event: error\ndata: {{"error": "stream_error", "channel": "{channel}"}}\n\n'
            # Vazhdon me heartbeat vetëm
            while True:
                yield 'event: ping\ndata: {}\n\n'
                await asyncio.sleep(5.0)
        except Exception:
            pass

    finally:
        # ─── Cleanup i sigurt ───
        try:
            if pubsub is not None and subscribed:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            elif pubsub is not None:
                await pubsub.aclose()
        except Exception as cleanup_err:
            logger.warning(f"SSE pubsub cleanup error on channel {channel}: {cleanup_err}")

        try:
            if redis_client is not None:
                await redis_client.aclose()
        except Exception as cleanup_err:
            logger.warning(f"SSE redis cleanup error on channel {channel}: {cleanup_err}")

        logger.info(f"SSE: Cleaned up subscription for channel: {channel}")


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
            "Cache-Control": "no-cache, no-transform",
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
            "Cache-Control": "no-cache, no-transform",
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
        yield 'event: connected\ndata: {"status": "test connected"}\n\n'
        for i in range(5):
            yield f'event: test\ndata: {{"message": "Test message {i}", "stream_id": "{stream_id}"}}\n\n'
            await asyncio.sleep(1)
        yield 'event: complete\ndata: {"status": "test completed"}\n\n'

    return StreamingResponse(
        test_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive"
        }
    )