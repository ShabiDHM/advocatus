# FILE: backend/app/core/db.py
# PHOENIX PROTOCOL - DB V2.1 (TYPE SAFETY)
# 1. FIX: Changed implicit boolean check to explicit 'is not None' to satisfy Pylance.
# 2. STATUS: Fully synchronous and type-safe.

import pymongo
import redis
from pymongo.database import Database
from pymongo.mongo_client import MongoClient
from pymongo.errors import ConnectionFailure
from urllib.parse import urlparse
from typing import Generator, Tuple

from .config import settings

# --- Global Sync Clients (Initialized during lifespan) ---
mongo_client: MongoClient | None = None
db_instance: Database | None = None
redis_sync_client: redis.Redis | None = None

# --- Connection Management Functions ---
def connect_to_mongo() -> Tuple[MongoClient, Database]:
    """Establishes a synchronous connection to MongoDB and returns the client and database."""
    global mongo_client, db_instance
    
    # PHOENIX FIX: Explicit None check for type safety
    if mongo_client is not None and db_instance is not None:
        return mongo_client, db_instance
        
    print("--- [DB] Attempting to connect to Sync MongoDB... ---")
    try:
        client = pymongo.MongoClient(settings.DATABASE_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ismaster')
        db_name = urlparse(settings.DATABASE_URI).path.lstrip('/')
        if not db_name:
            raise ValueError("Database name not found in DATABASE_URI.")
        
        mongo_client = client
        db_instance = client[db_name]
        print(f"--- [DB] Successfully connected to Sync MongoDB: '{db_name}' ---")
        return mongo_client, db_instance
    except (ConnectionFailure, ValueError) as e:
        print(f"--- [DB] CRITICAL: Could not connect to Sync MongoDB: {e} ---")
        raise

def connect_to_redis() -> redis.Redis:
    """Establishes a synchronous connection to Redis."""
    global redis_sync_client
    if redis_sync_client is not None:
        return redis_sync_client

    print("--- [DB] Attempting to connect to Sync Redis... ---")
    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        redis_sync_client = client
        print(f"--- [DB] Successfully connected to Sync Redis. ---")
        return redis_sync_client
    except redis.ConnectionError as e:
        print(f"--- [DB] CRITICAL: Could not connect to Sync Redis: {e} ---")
        raise

def close_mongo_connections():
    global mongo_client
    if mongo_client:
        mongo_client.close()
        print("--- [DB] Sync MongoDB connection closed. ---")

def close_redis_connection():
    global redis_sync_client
    if redis_sync_client:
        redis_sync_client.close()
        print("--- [DB] Sync Redis connection closed. ---")

# --- Dependency Providers ---
def get_db() -> Generator[Database, None, None]:
    if db_instance is None:
        raise RuntimeError("Database is not connected. Check application lifespan.")
    yield db_instance

def get_redis_client() -> Generator[redis.Redis, None, None]:
    if redis_sync_client is None:
        raise RuntimeError("Redis is not connected. Check application lifespan.")
    yield redis_sync_client