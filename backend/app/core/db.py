# FILE: backend/app/core/db.py
# PHOENIX PROTOCOL - DATABASE CORE V5.0 (RECOVERY)
# 1. RESTORED: Core connection functions (connect_to_mongo, connect_to_redis).
# 2. RESTORED: Dependency injection helper (get_db).
# 3. ADDED: SaaS direct access helper (get_db_instance).

import os
import logging
from pymongo import MongoClient
from pymongo.database import Database
import redis

logger = logging.getLogger(__name__)

# --- GLOBAL CONNECTION POOLS ---
_mongo_client = None
_redis_client = None

# --- MONGODB CONNECTION ---
def connect_to_mongo() -> tuple[MongoClient, Database]:
    global _mongo_client
    
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    
    if not uri:
        raise ValueError("DATABASE_URI environment variable is missing.")
        
    try:
        if _mongo_client is None:
            # We use a connection pool to handle multiple requests efficiently
            _mongo_client = MongoClient(
                uri, 
                maxPoolSize=50, 
                serverSelectionTimeoutMS=5000
            )
            # Verify connection
            _mongo_client.admin.command('ping')
            
        return _mongo_client, _mongo_client[db_name]
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        raise e

def close_mongo_connections():
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        logger.info("MongoDB connection closed.")

# --- FASTAPI DEPENDENCY INJECTION ---
def get_db() -> Database:
    """Dependency for FastAPI route handlers."""
    try:
        _, db = connect_to_mongo()
        return db
    except Exception as e:
        logger.error(f"Database dependency error: {e}")
        raise

# --- SAAS DIRECT ACCESS HELPER ---
def get_db_instance() -> Database:
    """Helper for direct access during SaaS operations without FastAPI requests."""
    from ..main import app
    if hasattr(app.state, "mongo_db") and app.state.mongo_db is not None:
        return app.state.mongo_db
    
    # Fallback if state is empty
    _, db = connect_to_mongo()
    return db

# --- REDIS CONNECTION ---
def connect_to_redis() -> redis.Redis:
    global _redis_client
    
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.warning("⚠️ REDIS_URL missing. Cache features disabled.")
        raise ValueError("REDIS_URL missing.")
        
    try:
        if _redis_client is None:
            # Use SSL/TLS parameters safely based on the URL scheme
            _redis_client = redis.from_url(
                redis_url, 
                socket_timeout=5, 
                decode_responses=True
            )
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
        logger.info("Redis connection closed.")