# FILE: backend/app/core/lifespan.py
# DEFINITIVE VERSION 5.1 (FINAL CORRECTION):
# Corrected the instantiation of 'ConnectionManager' by passing the required
# 'async_redis_client', resolving the fatal 'TypeError' on startup.

from contextlib import asynccontextmanager
from fastapi import FastAPI
from .db import (
    connect_to_mongo,
    connect_to_motor,
    connect_to_sync_redis,
    connect_to_async_redis,
    close_mongo_connections,
    close_redis_connections,
)
from .websocket_manager import ConnectionManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for robust database connections and WebSocket management.
    """
    # --- STARTUP ---
    app.state.mongo_client, app.state.db = connect_to_mongo()
    app.state.motor_client = await connect_to_motor()
    app.state.sync_redis_client = connect_to_sync_redis()
    app.state.async_redis_client = await connect_to_async_redis()
    
    # --- PHOENIX PROTOCOL FIX: Pass the required redis_client to the constructor ---
    # The ConnectionManager uses the *async* client for its pub/sub listener.
    app.state.websocket_manager = ConnectionManager(redis_client=app.state.async_redis_client)
    
    yield
    
    # --- SHUTDOWN ---
    close_mongo_connections(
        sync_client=app.state.mongo_client, 
        async_client=app.state.motor_client
    )
    
    await close_redis_connections(
        async_client=app.state.async_redis_client, 
        sync_client=app.state.sync_redis_client
    )