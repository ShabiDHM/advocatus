# FILE: backend/app/core/lifespan.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

# PHOENIX PROTOCOL CURE: Import all necessary connection and shutdown functions.
from .db import connect_to_motor, close_mongo_connections, close_redis_connection

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles the startup and shutdown of asynchronous resources.
    Synchronous connections are initialized when the 'db' module is imported.
    """
    # --- STARTUP ---
    logger.info("--- [Lifespan] Application startup sequence initiated. ---")
    
    # PHOENIX PROTOCOL CURE: Await the asynchronous database connection here.
    # This runs within the event loop started by Uvicorn, resolving the RuntimeError.
    await connect_to_motor()
    
    logger.info("--- [Lifespan] Asynchronous resources initialized. Application is ready. ---")
    
    yield
    
    # --- SHUTDOWN ---
    logger.info("--- [Lifespan] Application shutdown sequence initiated. ---")
    
    # Call the shutdown functions to close all connections.
    close_mongo_connections()
    close_redis_connection()
    
    logger.info("--- [Lifespan] All connections closed gracefully. Shutdown complete. ---")