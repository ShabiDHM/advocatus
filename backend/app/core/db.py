# FILE: backend/app/core/db.py
# PHOENIX PROTOCOL - DATABASE CORE V5.4 (NO CIRCULAR IMPORT - GLOBAL INSTANCE)

import os
import logging
from pymongo import MongoClient
from pymongo.database import Database
import redis

from .config import settings

logger = logging.getLogger(__name__)

# --- GLOBAL CONNECTION POOLS ---
_mongo_client = None
_redis_client = None
_mongo_db_instance = None  # PHOENIX FIX: Global reference to avoid circular import

# --- MONGODB CONNECTION ---
def connect_to_mongo() -> tuple[MongoClient, Database]:
    global _mongo_client, _mongo_db_instance
    uri = settings.DATABASE_URI
    db_name = settings.MONGO_DB_NAME or "advocatus_db"
    if not uri: raise ValueError("DATABASE_URI missing.")
    try:
        if _mongo_client is None:
            _mongo_client = MongoClient(uri, maxPoolSize=50, serverSelectionTimeoutMS=5000)
            _mongo_client.admin.command('ping')
        # PHOENIX FIX: Store the database instance globally
        _mongo_db_instance = _mongo_client[db_name]
        return _mongo_client, _mongo_db_instance
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        raise e

def close_mongo_connections():
    global _mongo_client, _mongo_db_instance
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        _mongo_db_instance = None

# --- REDIS CONNECTION ---
def connect_to_redis() -> redis.Redis:
    global _redis_client
    redis_url = settings.REDIS_URL
    if not redis_url: raise ValueError("REDIS_URL missing.")
    try:
        if _redis_client is None:
            _redis_client = redis.from_url(redis_url, socket_timeout=5, decode_responses=True)
            _redis_client.ping()
        return _redis_client
    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis: {e}")
        raise e

def close_redis_connection():
    global _redis_client
    if _redis_client:
        _redis_client.close()
        _redis_client = None

# --- FASTAPI DEPENDENCY INJECTIONS ---
def get_db() -> Database:
    """Dependency for FastAPI route handlers (MongoDB)."""
    try:
        # PHOENIX FIX: Return the global instance if available, otherwise connect
        if _mongo_db_instance is not None:
            return _mongo_db_instance
        _, db = connect_to_mongo()
        return db
    except Exception as e:
        logger.error(f"Database dependency error: {e}")
        raise

def get_redis_client():
    """Generator dependency for FastAPI route handlers (Redis)."""
    try:
        client = connect_to_redis()
        yield client
    except Exception as e:
        logger.error(f"Redis dependency error: {e}")
        raise

# --- SAAS DIRECT ACCESS HELPER ---
def get_db_instance() -> Database:
    """
    PHOENIX PROTOCOL - FIXED:
    Helper for direct access during SaaS operations without FastAPI requests.
    No circular import - uses global instance stored in connect_to_mongo().
    """
    global _mongo_db_instance
    
    # 1. If the global instance already exists, return it immediately
    if _mongo_db_instance is not None:
        return _mongo_db_instance
    
    # 2. Otherwise, establish a new connection
    try:
        _, db = connect_to_mongo()
        _mongo_db_instance = db
        return db
    except Exception as e:
        logger.error(f"Failed to get database instance: {e}")
        raise

def set_db_instance(db: Database):
    """
    PHOENIX PROTOCOL - NEW FUNCTION:
    Allows lifespan.py to set the database instance during startup.
    This ensures all modules use the same connection pool.
    """
    global _mongo_db_instance
    _mongo_db_instance = db
    logger.info("✅ Database instance set globally for SaaS operations.")