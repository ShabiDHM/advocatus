# FILE: backend/app/core/lifespan.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

from .db import connect_to_motor, close_mongo_connections, close_redis_connection

logger = logging.getLogger(__name__)

# PHOENIX PROTOCOL CURE: Define an async wrapper for the synchronous shutdown tasks.
async def perform_shutdown():
    """Asynchronously executes the synchronous shutdown procedures."""
    logger.info("--- [Lifespan] Application shutdown sequence initiated. ---")
    
    # These are synchronous functions, but they are called from within an
    # async function, which satisfies the lifespan context's requirements.
    close_mongo_connections()
    close_redis_connection()
    
    logger.info("--- [Lifespan] All connections closed gracefully. Shutdown complete. ---")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager. Handles the startup and shutdown of asynchronous resources.
    Synchronous connections are initialized when the 'db' module is imported.
    """
    # --- STARTUP ---
    logger.info("--- [Lifespan] Application startup sequence initiated. ---")
    
    # Await the asynchronous database connection here.
    await connect_to_motor()
    
    logger.info("--- [Lifespan] Asynchronous resources initialized. Application is ready. ---")
    
    yield
    
    # --- SHUTDOWN ---
    # PHOENIX PROTOCOL CURE: Await the async wrapper. This resolves the 
    # "'None' is not awaitable" type error because we are now awaiting a
    # proper coroutine.
    await perform_shutdown()