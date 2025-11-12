# FILE: backend/app/core/lifespan.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

# PHOENIX PROTOCOL CURE: Import the new, parameter-less shutdown functions.
# The connection logic now happens automatically when db.py is first imported.
from .db import close_mongo_connections, close_redis_connection

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Database and Redis connections are initialized globally in db.py upon import.
    This context's primary role is to ensure a clean shutdown.
    """
    # --- STARTUP ---
    # The connection logic has been centralized in db.py.
    # No explicit connection calls are needed here anymore.
    logger.info("--- [Lifespan] Application startup sequence initiated. ---")
    
    # The ConnectionManager is a simple singleton now and requires no setup.
    
    yield
    
    # --- SHUTDOWN ---
    logger.info("--- [Lifespan] Application shutdown sequence initiated. ---")
    
    # PHOENIX PROTOCOL CURE: Call the new, correct shutdown functions without arguments.
    close_mongo_connections()
    close_redis_connection()
    
    logger.info("--- [Lifespan] All connections closed gracefully. Shutdown complete. ---")