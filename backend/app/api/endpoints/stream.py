# FILE: backend/app/api/endpoints/stream.py
# PHOENIX PROTOCOL - SSE IMPLEMENTATION V5.1 (MULTI-CHANNEL CASE-AWARE)
# V5.1: CASE-AWARE — /stream/updates?case_id=X abonohet në:
#         - user:{user_id}:updates (personal)
#         - case:{case_id}:updates (case-scoped, për të gjithë anëtarët)
#       Verifikon aksesin në case përmes case_service.get_case_for_user().
#       Heq izolimin e SSE-it — admin + guest + anëtarë org marrin të njëjtat updates.
# V5.0: Singleton async pool + retry + graceful fallback.

import asyncio
import logging
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Path, Request, Query
from fastapi.responses import StreamingResponse
from jose import jwt, JWTError
from pydantic import BaseModel, ValidationError
from bson import ObjectId
import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════
# V5.0: SINGLETON ASYNC REDIS POOL
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
        max_connections=20,
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
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
        except Exception as e:
            logger.error(f"❌ [SSE] Unexpected subscribe error for {channel}: {e}")
            return False
    return False


class TokenPayload(BaseModel):
    sub: Optional[str] = None


def get_current_user_sse(request: Request) -> Optional[str]:
    """Synchronous token validation supporting both query parameter and Authorization header."""
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


def _verify_case_access(user_id: str, case_id: str) -> bool:
    """
    V5.1: Kontrollon nëse user-i ka akses në case (org-aware).
    Përdor case_service.get_case_for_user për konsistencë me router-in.
    """
    try:
        from app.core.db import get_db_instance
        from app.models.user import UserInDB
        from app.services.case_service import get_case_for_user

        if not ObjectId.is_valid(case_id):
            return False

        db = get_db_instance()
        case_oid = ObjectId(case_id)

        user_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        user_doc = db.users.find_one({"_id": user_oid})
        if not user_doc:
            return False

        user = UserInDB.model_validate(user_doc)
        case_doc = get_case_for_user(db, case_oid, user)
        return case_doc is not None
    except Exception as e:
        logger.warning(f"⚠️ [SSE] Case access check failed (user={user_id}, case={case_id}): {e}")
        return False


async def _heartbeat_only_fallback(
    channels: List[str],
    user_id: Optional[str] = None,
    send_connected_event: bool = True,
) -> AsyncGenerator[str, None]:
    """V5.0: Fallback nëse Redis nuk përgjigjet."""
    channels_str = ",".join(channels)
    logger.warning(f"🟡 [SSE] Fallback heartbeat-only aktiv për channels: {channels_str}")

    try:
        if send_connected_event:
            yield 'event: connected\ndata: {"status": "connected_no_pubsub"}\n\n'

        while True:
            yield 'event: ping\ndata: {}\n\n'
            await asyncio.sleep(5.0)
    except asyncio.CancelledError:
        logger.info(f"SSE: heartbeat fallback closed for {channels_str}")
        raise
    finally:
        logger.info(f"SSE: heartbeat fallback cleanup done for {channels_str}")


async def event_generator(
    channels: List[str],
    user_id: Optional[str] = None,
    send_connected_event: bool = True,
) -> AsyncGenerator[str, None]:
    """
    V5.1: Asynchronous SSE generator — abonohet në SHUMË kanale njëkohësisht.
    """
    redis_client = None
    pubsub = None
    subscribed_channels: List[str] = []

    channels_str = ",".join(channels)

    try:
        # ─── 1. Krijo klient nga pool-i singleton ───
        try:
            pool = _get_async_redis_pool()
            redis_client = aioredis.Redis(connection_pool=pool)
            pubsub = redis_client.pubsub()
        except Exception as e:
            logger.error(f"❌ [SSE] Failed to get Redis client for {channels_str}: {e}")
            async for chunk in _heartbeat_only_fallback(channels, user_id, send_connected_event):
                yield chunk
            return

        # ─── 2. Retry subscribe PËR ÇDO KANAL ───
        for ch in channels:
            ok = await _try_subscribe_with_retry(pubsub, ch, max_attempts=3)
            if ok:
                subscribed_channels.append(ch)
                logger.info(f"SSE: Subscribed asynchronously to channel: {ch} (user_id: {user_id})")
            else:
                logger.warning(f"⚠️ [SSE] Skipped channel {ch} (subscribe failed)")

        if not subscribed_channels:
            logger.error(
                f"❌ [SSE] Could not subscribe to ANY channel from {channels_str} — "
                f"fallback to heartbeat-only"
            )
            try:
                if pubsub:
                    await pubsub.aclose()
            except Exception:
                pass
            async for chunk in _heartbeat_only_fallback(channels, user_id, send_connected_event):
                yield chunk
            return

        # ─── 3. Stream i normal ───
        if send_connected_event:
            yield 'event: connected\ndata: {"status": "connected"}\n\n'

        # Pastro ack-u e subscribe-ve
        try:
            await pubsub.get_message(timeout=0.2)
        except Exception:
            pass

        while True:
            message = await pubsub.get_message(timeout=1.0, ignore_subscribe_messages=True)
            if message and message.get('type') == 'message':
                yield f"event: update\ndata: {message['data']}\n\n"
            else:
                yield 'event: ping\ndata: {}\n\n'

            await asyncio.sleep(0.5)

    except asyncio.CancelledError:
        logger.info(f"SSE: Connection closed by client for channels: {channels_str}")
        raise
    except Exception as e:
        logger.error(f"SSE generator error for channels {channels_str}: {type(e).__name__}: {e}")
        try:
            yield f'event: error\ndata: {{"error": "stream_error"}}\n\n'
            while True:
                yield 'event: ping\ndata: {}\n\n'
                await asyncio.sleep(5.0)
        except Exception:
            pass

    finally:
        # ─── Cleanup ───
        try:
            if pubsub is not None:
                for ch in subscribed_channels:
                    try:
                        await pubsub.unsubscribe(ch)
                    except Exception:
                        pass
                await pubsub.aclose()
        except Exception as cleanup_err:
            logger.warning(f"SSE pubsub cleanup error on {channels_str}: {cleanup_err}")

        try:
            if redis_client is not None:
                await redis_client.aclose()
        except Exception as cleanup_err:
            logger.warning(f"SSE redis cleanup error on {channels_str}: {cleanup_err}")

        logger.info(f"SSE: Cleaned up subscription for channels: {channels_str}")


@router.get("/updates")
async def stream_updates(
    request: Request,
    case_id: Optional[str] = Query(None, description="Optional: case-scoped channel for cross-user sync"),
):
    """
    V5.1: User-level SSE + optional case-scoped SSE.
    Nëse case_id jepet dhe user ka akses, abonohet në të dyja:
      - user:{user_id}:updates (personal)
      - case:{case_id}:updates (për të gjithë anëtarët e case-it)
    """
    user_id = get_current_user_sse(request)

    if user_id is None:
        async def unauthorized() -> AsyncGenerator[str, None]:
            yield "event: error\ndata: Unauthorized\n\n"
        return StreamingResponse(unauthorized(), media_type="text/event-stream")

    channels: List[str] = [f"user:{user_id}:updates"]

    if case_id:
        if _verify_case_access(user_id, case_id):
            channels.append(f"case:{case_id}:updates")
            logger.info(f"✅ [SSE] Case channel added: user={user_id}, case={case_id}")
        else:
            logger.warning(f"🚫 [SSE] Access denied to case={case_id} for user={user_id}")

    logger.info(f"SSE: Opening stream with {len(channels)} channel(s) for user {user_id}")

    return StreamingResponse(
        event_generator(channels, user_id=user_id, send_connected_event=True),
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
    """Entity-level SSE: updates for a specific entity."""
    user_id = get_current_user_sse(request)

    if user_id is None:
        async def unauthorized() -> AsyncGenerator[str, None]:
            yield "event: error\ndata: Unauthorized\n\n"
        return StreamingResponse(unauthorized(), media_type="text/event-stream")

    entity_channel = f"entity:{stream_id}:updates"
    return StreamingResponse(
        event_generator([entity_channel], user_id=user_id, send_connected_event=False),
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
    """Test endpoint for SSE connectivity."""
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