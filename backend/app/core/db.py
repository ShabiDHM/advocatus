# FILE: backend/app/core/db.py
# PHOENIX PROTOCOL - DATABASE CORE V5.5 (ENTERPRISE CONNECTION POOLING & RESILIENCE)

import os
import logging
from typing import Generator
from pymongo import MongoClient
from pymongo.database import Database
import redis
from redis.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from .config import settings

logger = logging.getLogger(__name__)

# --- GLOBAL CONNECTION POOLS & INSTANCES ---
_mongo_client: MongoClient | None = None
_mongo_db_instance: Database | None = None
_redis_pool: redis.ConnectionPool | None = None
_redis_client: redis.Redis | None = None


# --- MONGODB CONNECTION MANAGEMENT ---
def connect_to_mongo() -> tuple[MongoClient, Database]:
    global _mongo_client, _mongo_db_instance
    uri = settings.DATABASE_URI
    db_name = settings.MONGO_DB_NAME or "advocatus_db"
    
    if not uri:
        raise ValueError("DATABASE_URI missing from configuration.")
        
    try:
        if _mongo_client is None:
            _mongo_client = MongoClient(
                uri,
                maxPoolSize=50,
                minPoolSize=10,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
                retryWrites=True
            )
            _mongo_client.admin.command('ping')
            logger.info("✅ MongoDB connection pool successfully established.")
            
        _mongo_db_instance = _mongo_client[db_name]
        return _mongo_client, _mongo_db_instance
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        raise e


def close_mongo_connections() -> None:
    global _mongo_client, _mongo_db_instance
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        _mongo_db_instance = None
        logger.info("🛑 MongoDB connection pool closed.")


# --- REDIS CONNECTION MANAGEMENT (ENTERPRISE POOL & AUTO-RETRY) ---
def _init_redis_pool() -> redis.ConnectionPool:
    """Initializes a robust Redis connection pool with retry strategy and socket health checks."""
    redis_url = settings.REDIS_URL
    if not redis_url:
        raise ValueError("REDIS_URL missing from configuration.")
        
    retry_strategy = Retry(
        ExponentialBackoff(cap=2, base=0.1),
        retries=3
    )
    
    return redis.ConnectionPool.from_url(
        redis_url,
        max_connections=50,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
        socket_keepalive=True,
        health_check_interval=30,
        retry_on_timeout=True,
        retry=retry_strategy,
        retry_on_error=[ConnectionError, TimeoutError, ConnectionResetError],
        decode_responses=True
    )


def connect_to_redis() -> redis.Redis:
    global _redis_pool, _redis_client
    try:
        if _redis_pool is None:
            _redis_pool = _init_redis_pool()
            
        if _redis_client is None:
            _redis_client = redis.Redis(connection_pool=_redis_pool)
            _redis_client.ping()
            logger.info("✅ Redis connection pool successfully initialized and verified.")
            
        return _redis_client
    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis: {e}")
        # Reset references so subsequent calls attempt fresh pool creation
        _redis_client = None
        _redis_pool = None
        raise e


def close_redis_connection() -> None:
    global _redis_pool, _redis_client
    try:
        if _redis_client:
            _redis_client.close()
        if _redis_pool:
            _redis_pool.disconnect()
        logger.info("🛑 Redis connection pool closed.")
    finally:
        _redis_client = None
        _redis_pool = None


# --- FASTAPI DEPENDENCY INJECTIONS ---
def get_db() -> Database:
    """Dependency for FastAPI route handlers (MongoDB)."""
    try:
        if _mongo_db_instance is not None:
            return _mongo_db_instance
        _, db = connect_to_mongo()
        return db
    except Exception as e:
        logger.error(f"Database dependency error: {e}")
        raise


def get_redis_client() -> Generator[redis.Redis, None, None]:
    """Generator dependency for FastAPI route handlers (Redis)."""
    try:
        client = connect_to_redis()
        yield client
    except Exception as e:
        logger.error(f"Redis dependency error: {e}")
        raise


# --- SAAS DIRECT ACCESS HELPERS (NON-REQUEST CONTEXTS) ---
def get_db_instance() -> Database:
    """
    Direct access helper for SaaS operations outside FastAPI requests.
    Guarantees no circular imports by utilizing global instance.
    """
    global _mongo_db_instance
    if _mongo_db_instance is not None:
        return _mongo_db_instance
    try:
        _, db = connect_to_mongo()
        _mongo_db_instance = db
        return db
    except Exception as e:
        logger.error(f"Failed to get database instance: {e}")
        raise


def set_db_instance(db: Database) -> None:
    """Allows lifespan.py to inject the database instance at startup."""
    global _mongo_db_instance
    _mongo_db_instance = db
    logger.info("✅ Database instance set globally for SaaS operations.")


def get_redis_instance() -> redis.Redis:
    """Direct access helper for Redis outside FastAPI requests (e.g. background tasks / SSE)."""
    return connect_to_redis()