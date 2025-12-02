# FILE: backend/app/core/lifespan.py
# PHOENIX PROTOCOL - CORRECTED DATA INITIALIZATION
# 1. FIX: Now imports the centralized JuristiRemoteEmbeddings class from the new core/embeddings.py file.
# 2. BEHAVIOR: Creates the 'legal_knowledge_base' collection with the CORRECT custom embedding function.
# 3. CONSISTENCY: Resolves the conflict between application startup and data ingestion scripts.

from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging
import chromadb

from .db import connect_to_motor, close_mongo_connections, close_redis_connection
from .config import settings
from .embeddings import JuristiRemoteEmbeddings # PHOENIX FIX: Import the new canonical class

logger = logging.getLogger(__name__)

def initialize_chromadb():
    """
    Connects to ChromaDB and ensures the essential collections exist with the correct configuration.
    """
    try:
        logger.info("--- [Lifespan] Initializing ChromaDB connection... ---")
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        
        # PHOENIX FIX: Use the shared, canonical embedding function during creation.
        embedding_function = JuristiRemoteEmbeddings()
        collection = client.get_or_create_collection(
            name="legal_knowledge_base",
            embedding_function=embedding_function
        )
        
        logger.info(f"--- [Lifespan] ✅ Successfully connected to ChromaDB. ---")
        logger.info(f"--- [Lifespan] ✅ Collection 'legal_knowledge_base' is available with {collection.count()} documents. ---")

    except Exception as e:
        logger.error(f"--- [Lifespan] ❌ FAILED to initialize ChromaDB: {e} ---", exc_info=True)
        raise e

async def perform_shutdown():
    logger.info("--- [Lifespan] Application shutdown sequence initiated. ---")
    close_mongo_connections()
    close_redis_connection()
    logger.info("--- [Lifespan] All connections closed gracefully. Shutdown complete. ---")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- [Lifespan] Application startup sequence initiated. ---")
    
    initialize_chromadb()
    await connect_to_motor()
    
    logger.info("--- [Lifespan] All resources initialized. Application is ready. ---")
    
    yield
    
    await perform_shutdown()