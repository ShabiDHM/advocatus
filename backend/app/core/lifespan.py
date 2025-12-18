# FILE: backend/app/core/lifespan.py
# PHOENIX PROTOCOL - LIFESPAN V2.1 (SPEED INDEXING)
# 1. OPTIMIZATION: Added automatic MongoDB index creation on startup.
# 2. PERFORMANCE: Ensures O(1) or O(log n) lookups for Cases, Docs, and Events.
# 3. STATUS: Optimized for high-load environments.

from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging
import chromadb
from pymongo import ASCENDING, DESCENDING # PHOENIX: Required for indexing

from .db import connect_to_motor, close_mongo_connections, close_redis_connection
from .config import settings
from .embeddings import JuristiRemoteEmbeddings

logger = logging.getLogger(__name__)

def initialize_chromadb():
    """
    Connects to ChromaDB and ensures the essential collections exist with the correct configuration.
    """
    try:
        logger.info("--- [Lifespan] Initializing ChromaDB connection... ---")
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        
        embedding_function = JuristiRemoteEmbeddings()
        collection = client.get_or_create_collection(
            name="legal_knowledge_base",
            embedding_function=embedding_function
        )
        
        logger.info(f"--- [Lifespan] ✅ Successfully connected to ChromaDB. ---")
        logger.info(f"--- [Lifespan] ✅ Collection 'legal_knowledge_base' is available with {collection.count()} documents. ---")

    except Exception as e:
        logger.error(f"--- [Lifespan] ❌ FAILED to initialize ChromaDB: {e} ---", exc_info=True)
        # We log but do not raise, allowing API to boot even if VectorStore is warming up

async def create_mongo_indexes(app: FastAPI):
    """
    Creates compound indexes to speed up the most frequent queries.
    This is critical for performance on servers with limited RAM (prevents collection scans).
    """
    try:
        # Access DB from app state (populated by connect_to_motor)
        if not hasattr(app.state, "mongo_db"):
            logger.warning("--- [Indexes] ⚠️ MongoDB not found in app.state. Skipping indexing. ---")
            return

        db = app.state.mongo_db
        logger.info("--- [Lifespan] 🚀 Optimizing Database Indexes... ---")

        # 1. Users: Instant Login
        await db.users.create_index([("email", ASCENDING)], unique=True)
        
        # 2. Cases: Fast Dashboard Loading (Filter by Owner + Sort by Date)
        await db.cases.create_index([("owner_id", ASCENDING), ("updated_at", DESCENDING)])
        await db.cases.create_index([("case_number", ASCENDING)])
        
        # 3. Documents: Fast Case View
        await db.documents.create_index([("case_id", ASCENDING), ("created_at", DESCENDING)])
        await db.documents.create_index([("owner_id", ASCENDING)])
        
        # 4. Calendar: Instant Event Fetching
        await db.calendar_events.create_index([("case_id", ASCENDING)])
        await db.calendar_events.create_index([("start_date", ASCENDING)])
        await db.calendar_events.create_index([("owner_id", ASCENDING)])
        
        logger.info("--- [Lifespan] ✅ Database Indexes Verified/Created. ---")
    except Exception as e:
        logger.error(f"--- [Lifespan] ❌ Index Creation Failed: {e} ---")

async def perform_shutdown():
    logger.info("--- [Lifespan] Application shutdown sequence initiated. ---")
    close_mongo_connections()
    close_redis_connection()
    logger.info("--- [Lifespan] All connections closed gracefully. Shutdown complete. ---")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- [Lifespan] Application startup sequence initiated. ---")
    
    # 1. Connect Databases
    initialize_chromadb()
    await connect_to_motor() # Sets app.state.mongo_db
    
    # 2. Optimize Performance (Create Indexes)
    await create_mongo_indexes(app)
    
    logger.info("--- [Lifespan] All resources initialized. Application is ready. ---")
    
    yield
    
    await perform_shutdown()