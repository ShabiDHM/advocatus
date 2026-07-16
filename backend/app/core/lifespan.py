# FILE: backend/app/core/lifespan.py
# PHOENIX PROTOCOL - SAAS LIFESPAN V7.0 (NO CHROMA)
from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging
from .db import connect_to_mongo, connect_to_redis, close_mongo_connections, close_redis_connection

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- [Lifespan] SAAS STARTUP: Connecting to Cloud Infrastructure ---")
    
    # 1. Mongo Handshake
    _, db_instance = connect_to_mongo()
    app.state.mongo_db = db_instance
    
    # 2. Redis Handshake
    try:
        connect_to_redis()
    except Exception as e:
        logger.warning(f"Redis skipped: {e}")

    yield
    
    close_mongo_connections()
    close_redis_connection()