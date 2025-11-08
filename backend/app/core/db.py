# FILE: backend/app/core/db.py
# DEFINITIVE CANONICAL VERSION 9.0

import pymongo
import redis
import redis.asyncio as aredis
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure
from urllib.parse import urlparse
from typing import Any, Tuple

from .config import settings

def connect_to_mongo() -> Tuple[Any, Any]:
    print("--- [DB] Attempting to connect to Sync MongoDB... ---")
    try:
        client = pymongo.MongoClient(settings.DATABASE_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ismaster')
        db_name = urlparse(settings.DATABASE_URI).path.lstrip('/')
        if not db_name: raise ValueError("Database name not found in DATABASE_URI.")
        db = client[db_name]
        print(f"--- [DB] Successfully connected to Sync MongoDB: '{db_name}' ---")
        return client, db
    except (ConnectionFailure, ValueError) as e:
        print(f"--- [DB] CRITICAL: Could not connect to Sync MongoDB: {e} ---")
        raise

async def connect_to_motor() -> Any:
    print("--- [DB] Attempting to connect to Async MongoDB (Motor)... ---")
    try:
        client = AsyncIOMotorClient(settings.DATABASE_URI, serverSelectionTimeoutMS=5000)
        await client.admin.command('ismaster')
        print("--- [DB] Successfully connected to Async MongoDB (Motor). ---")
        return client
    except ConnectionFailure as e:
        print(f"--- [DB] CRITICAL: Could not connect to Async MongoDB (Motor): {e} ---")
        raise

def close_mongo_connections(sync_client: Any, async_client: Any):
    if sync_client: sync_client.close(); print("--- [DB] Sync MongoDB connection closed. ---")
    if async_client: async_client.close(); print("--- [DB] Async MongoDB (Motor) connection closed. ---")

async def connect_to_async_redis() -> aredis.Redis:
    client = aredis.from_url(settings.REDIS_URL, decode_responses=True)
    await client.ping()
    print("--- [DB] Successfully connected to Async Redis. ---")
    return client

def connect_to_sync_redis() -> redis.Redis:
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    client.ping()
    print("--- [DB] Successfully connected to Sync Redis. ---")
    return client

async def close_redis_connections(async_client: Any, sync_client: Any):
    """Closes BOTH Redis connections."""
    if async_client: await async_client.close(); print("--- [DB] Async Redis connection closed. ---")
    if sync_client: sync_client.close(); print("--- [DB] Sync Redis connection closed. ---")

def get_collection(db_instance: Any, collection_name: str) -> Any:
    return db_instance[collection_name]