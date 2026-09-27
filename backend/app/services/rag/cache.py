# FILE: backend/app/services/rag/cache.py
# PHOENIX PROTOCOL - RAG CACHE V1.0
# V1.0: EKSTRAKTUAR nga albanian_rag_service.py V282.25.
#       Redis cache helpers për case_docs dhe case_chunks.
#       Zero varësi nga AlbanianRAGService.

import os
import json
import logging
import hashlib
from typing import List, Optional, Dict, Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


_redis_client: Optional[aioredis.Redis] = None

CACHE_TTL_CASE_DOCS = 600
CACHE_TTL_CASE_CHUNKS = 300


async def _get_redis() -> Optional[aioredis.Redis]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        redis_url = (
            getattr(settings, "REDIS_URL", None)
            or os.getenv("REDIS_URL", "")
        )
        if not redis_url:
            logger.info("[Cache] REDIS_URL nuk është konfiguruar — cache çaktivizuar")
            return None

        _redis_client = aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
        await _redis_client.ping()
        logger.info("✅ [Cache] Redis client initialized (async)")
        return _redis_client
    except Exception as e:
        logger.warning(f"⚠️ [Cache] Redis init failed — cache çaktivizuar: {e}")
        _redis_client = None
        return None


def _serialize_docs_for_cache(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for d in docs:
        d2 = dict(d)
        if "_id" in d2 and not isinstance(d2["_id"], str):
            d2["_id"] = str(d2["_id"])
        out.append(d2)
    return out


async def _get_cached_case_docs(case_id: str) -> Optional[List[Dict[str, Any]]]:
    client = await _get_redis()
    if not client:
        return None
    try:
        cache_key = f"case_docs_v1:{case_id}"
        cached = await client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.info(f"[Cache] get case_docs failed (fallback DB): {e}")
    return None


async def _set_cached_case_docs(
    case_id: str,
    docs: List[Dict[str, Any]],
    ttl: int = CACHE_TTL_CASE_DOCS,
) -> None:
    client = await _get_redis()
    if not client:
        return
    try:
        cache_key = f"case_docs_v1:{case_id}"
        payload = json.dumps(
            _serialize_docs_for_cache(docs),
            ensure_ascii=False,
            default=str,
        )
        await client.setex(cache_key, ttl, payload)
    except Exception as e:
        logger.info(f"[Cache] set case_docs failed (best-effort): {e}")


def _chunks_cache_key(
    case_id: str,
    user_id: str,
    query: str,
    document_ids: Optional[List[str]],
) -> str:
    src = f"{case_id}|{user_id}|{query.lower().strip()}|{','.join(sorted(document_ids or []))}"
    h = hashlib.sha1(src.encode("utf-8")).hexdigest()[:16]
    return f"case_chunks_v1:{h}"


async def _get_cached_chunks(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    client = await _get_redis()
    if not client:
        return None
    try:
        cached = await client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.info(f"[Cache] get chunks failed (fallback vector): {e}")
    return None


async def _set_cached_chunks(
    cache_key: str,
    chunks: List[Dict[str, Any]],
    ttl: int = CACHE_TTL_CASE_CHUNKS,
) -> None:
    client = await _get_redis()
    if not client:
        return
    try:
        payload = json.dumps(chunks, ensure_ascii=False, default=str)
        await client.setex(cache_key, ttl, payload)
    except Exception as e:
        logger.info(f"[Cache] set chunks failed (best-effort): {e}")