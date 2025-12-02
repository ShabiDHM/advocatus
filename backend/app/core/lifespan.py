# FILE: backend/app/core/lifespan.py
# PHOENIX PROTOCOL - DATA INTEGRITY FIX
# 1. ADDED: ChromaDB initialization logic to the application startup sequence.
# 2. BEHAVIOR: On startup, the application now connects to ChromaDB and uses 'get_or_create_collection'
#    to ensure the critical 'legal_knowledge_base' collection always exists.
# 3. ROBUSTNESS: This resolves the 'NotFoundError' and makes the system resilient to ChromaDB state resets.

from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging
import chromadb

from .db import connect_to_motor, close_mongo_connections, close_redis_connection
from .config import settings

logger = logging.getLogger(__name__)

def initialize_chromadb():
    """
    Connects to ChromaDB and ensures the essential collections exist.
    This is a synchronous operation suitable for startup.
    """
    try:
        logger.info("--- [Lifespan] Initializing ChromaDB connection... ---")
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        
        # Idempotent operation: gets the collection if it exists, creates it if it doesn't.
        collection = client.get_or_create_collection(name="legal_knowledge_base")
        
        logger.info(f"--- [Lifespan] ✅ Successfully connected to ChromaDB. ---")
        logger.info(f"--- [Lifespan] ✅ Collection 'legal_knowledge_base' is available with {collection.count()} documents. ---")

    except Exception as e:
        logger.error(f"--- [Lifespan] ❌ FAILED to initialize ChromaDB: {e} ---", exc_info=True)
        # Depending on system design, you might want to raise the exception
        # to prevent the application from starting in a broken state.
        # raise e

async def perform_shutdown():
    """Asynchronously executes the synchronous shutdown procedures."""
    logger.info("--- [Lifespan] Application shutdown sequence initiated. ---")
    close_mongo_connections()
    close_redis_connection()
    logger.info("--- [Lifespan] All connections closed gracefully. Shutdown complete. ---")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager. Handles startup and shutdown of all resources.
    """
    # --- STARTUP ---
    logger.info("--- [Lifespan] Application startup sequence initiated. ---")
    
    # Initialize synchronous resources like ChromaDB
    initialize_chromadb()
    
    # Initialize asynchronous resources like Motor
    await connect_to_motor()
    
    logger.info("--- [Lifespan] All resources initialized. Application is ready. ---")
    
    yield
    
    # --- SHUTDOWN ---
    await perform_shutdown()