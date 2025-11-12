# FILE: backend/app/core/db.py

import pymongo
import redis
import asyncio
from pymongo.database import Database
from pymongo.mongo_client import MongoClient
from pymongo.errors import ConnectionFailure
from urllib.parse import urlparse
from typing import Generator, Tuple, Any

from .config import settings

def _connect_to_mongo() -> Tuple[MongoClient, Database]:
    """Establishes a synchronous connection to MongoDB."""
    print("--- [DB] Attempting to connect to Sync MongoDB... ---")
    try:
        client: MongoClient = pymongo.MongoClient(settings.DATABASE_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ismaster')
        db_name = urlparse(settings.DATABASE_URI).path.lstrip('/')
        if not db_name:
            raise ValueError("Database name not found in DATABASE_URI.")
        db: Database = client[db_name]
        print(f"--- [DB] Successfully connected to Sync MongoDB: '{db_name}' ---")
        return client, db
    except (ConnectionFailure, ValueError) as e:
        print(f"--- [DB] CRITICAL: Could not connect to Sync MongoDB: {e} ---")
        raise

async def _connect_to_motor() -> Tuple[Any, Any]:
    """Establishes an asynchronous connection to MongoDB using Motor."""
    print("--- [DB] Attempting to connect to Async MongoDB (Motor)... ---")
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(settings.DATABASE_URI, serverSelectionTimeoutMS=5000)
        await client.admin.command('ismaster')
        db_name = urlparse(settings.DATABASE_URI).path.lstrip('/')
        if not db_name:
            raise ValueError("Database name not found in DATABASE_URI.")
        db = client[db_name]
        print(f"--- [DB] Successfully connected to Async MongoDB (Motor): '{db_name}' ---")
        return client, db
    except (ConnectionFailure, ValueError) as e:
        print(f"--- [DB] CRITICAL: Could not connect to Async MongoDB (Motor): {e} ---")
        raise

def _connect_to_sync_redis() -> redis.Redis:
    """Establishes a synchronous connection to Redis."""
    print("--- [DB] Attempting to connect to Sync Redis... ---")
    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        print("--- [DB] Successfully connected to Sync Redis. ---")
        return client
    except redis.ConnectionError as e:
        print(f"--- [DB] CRITICAL: Could not connect to Sync Redis: {e} ---")
        raise

mongo_client, db_instance = _connect_to_mongo()
async_mongo_client, async_db_instance = asyncio.run(_connect_to_motor())
redis_sync_client = _connect_to_sync_redis()

def get_db() -> Generator[Database, None, None]:
    """FastAPI dependency that yields the global synchronous database instance."""
    yield db_instance

def get_async_db() -> Generator[Any, None, None]:
    """FastAPI dependency that yields the global asynchronous database instance."""
    yield async_db_instance

# PHOENIX PROTOCOL CURE: Add the missing dependency provider function for Redis.
def get_redis_client() -> Generator[redis.Redis, None, None]:
    """FastAPI dependency that yields the global sync Redis client instance."""
    yield redis_sync_client

def close_mongo_connections():
    if mongo_client:
        mongo_client.close()
        print("--- [DB] Sync MongoDB connection closed. ---")
    if async_mongo_client:
        async_mongo_client.close()
        print("--- [DB] Async MongoDB (Motor) connection closed. ---")

def close_redis_connection():
    if redis_sync_client:
        redis_sync_client.close()
        print("--- [DB] Sync Redis connection closed. ---")