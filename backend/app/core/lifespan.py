# PHOENIX PROTOCOL - INDEPENDENT LIFESPAN V6.0
# STATUS: 100% Haveri-Independent / 8GB RAM Optimized
# LOGIC: Uses Local Persistence for ChromaDB (No Docker/Server Required)

import os
import logging
import chromadb
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .db import connect_to_mongo, connect_to_redis, close_mongo_connections, close_redis_connection

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- [Lifespan] STARTING INDEPENDENT BOOT ---")
    
    # 1. MongoDB Atlas Connectivity
    try:
        _, db_instance = connect_to_mongo()
        app.state.mongo_db = db_instance
        logger.info("--- [Lifespan] ✅ MongoDB Atlas Handshake Success ---")
    except Exception as e:
        logger.error(f"--- [Lifespan] ❌ MongoDB Connection Failed: {e} ---")
        app.state.mongo_db = None

    # 2. Redis Cloud Connectivity
    try:
        connect_to_redis()
        logger.info("--- [Lifespan] ✅ Redis Cloud Handshake Success ---")
    except Exception as e:
        logger.warning(f"--- [Lifespan] ⚠️ Redis Offline (Cache Disabled): {e} ---")

    # 3. ChromaDB Local Persistence (Independence Logic)
    try:
        # Define the local path for the vector database
        persist_dir = os.path.join(os.getcwd(), "data", "chroma")
        if not os.path.exists(persist_dir):
            os.makedirs(persist_dir, exist_ok=True)
            
        # We use PersistentClient to avoid needing a separate background process
        app.state.chroma_client = chromadb.PersistentClient(path=persist_dir)
        logger.info(f"--- [Lifespan] ✅ ChromaDB Local Persistence Active at: {persist_dir} ---")
    except Exception as e:
        logger.error(f"--- [Lifespan] ❌ ChromaDB Local Initialization Failed: {e} ---")
        app.state.chroma_client = None

    logger.info("--- [Lifespan] SYSTEM STABILIZED. Opening Port 8000. ---")
    
    yield
    
    # --- Shutdown ---
    logger.info("--- [Lifespan] Shutdown Initiated... ---")
    close_mongo_connections()
    close_redis_connection()
    logger.info("--- [Lifespan] Shutdown Complete. ---")