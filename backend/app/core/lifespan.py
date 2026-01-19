# FILE: backend/app/core/lifespan.py
# PHOENIX PROTOCOL - LIFESPAN V3.2 (IMPORT FIX)
# 1. FIX: Added missing 'Database' import from 'pymongo.database'.
# 2. STATUS: No Pylance errors.

from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging
import chromadb
from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database # PHOENIX FIX: Added missing import

from .db import connect_to_mongo, connect_to_redis, close_mongo_connections, close_redis_connection
from .config import settings
from .embeddings import JuristiRemoteEmbeddings

logger = logging.getLogger(__name__)

def initialize_chromadb():
    try:
        logger.info("--- [Lifespan] Initializing ChromaDB connection... ---")
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        embedding_function = JuristiRemoteEmbeddings()
        collection = client.get_or_create_collection(name="legal_knowledge_base", embedding_function=embedding_function)
        logger.info(f"--- [Lifespan] ✅ ChromaDB connection successful. Collection has {collection.count()} documents. ---")
    except Exception as e:
        logger.error(f"--- [Lifespan] ❌ FAILED to initialize ChromaDB: {e} ---")

def create_mongo_indexes(db: Database):
    try:
        logger.info("--- [Lifespan] 🚀 Optimizing Database Indexes... ---")

        db.users.create_index([("email", ASCENDING)], unique=True)
        db.cases.create_index([("owner_id", ASCENDING), ("updated_at", DESCENDING)])
        db.cases.create_index([("case_number", ASCENDING)])
        db.documents.create_index([("case_id", ASCENDING), ("created_at", DESCENDING)])
        db.documents.create_index([("owner_id", ASCENDING)])
        db.calendar_events.create_index([("case_id", ASCENDING)])
        db.calendar_events.create_index([("start_date", ASCENDING)])
        db.calendar_events.create_index([("owner_id", ASCENDING)])
        
        logger.info("--- [Lifespan] ✅ Database Indexes Verified/Created. ---")
    except Exception as e:
        logger.error(f"--- [Lifespan] ❌ Index Creation Failed: {e} ---")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- [Lifespan] Application startup sequence initiated. ---")
    
    # 1. Connect Databases (Synchronous)
    initialize_chromadb()
    _, db_instance = connect_to_mongo()
    app.state.mongo_db = db_instance # Attach db to state for indexing
    
    try:
        connect_to_redis()
    except Exception as e:
        logger.warning(f"--- [Lifespan] ⚠️ Redis connection skipped: {e} ---")

    # 2. Optimize Performance (Create Indexes)
    if hasattr(app.state, "mongo_db") and app.state.mongo_db is not None:
        create_mongo_indexes(app.state.mongo_db)
    else:
        logger.warning("--- [Indexes] ⚠️ MongoDB not found in app.state. Skipping indexing. ---")

    logger.info("--- [Lifespan] All resources initialized. Application is ready. ---")
    
    yield
    
    # --- Shutdown Sequence ---
    logger.info("--- [Lifespan] Application shutdown sequence initiated. ---")
    close_mongo_connections()
    close_redis_connection()
    logger.info("--- [Lifespan] All connections closed gracefully. Shutdown complete. ---")