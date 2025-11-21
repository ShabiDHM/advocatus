from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config import settings
from routers import embeddings
from services.embedding_manager import embedding_manager

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load Models
    logger.info("🚀 Advocatus AI Core Starting...")
    embedding_manager.load_model()
    yield
    # Shutdown: Cleanup
    logger.info("🛑 Shutting down AI Core...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
# We prefix with /embeddings to organize, but we can alias if needed
app.include_router(embeddings.router, prefix="/embeddings", tags=["Embeddings"])

@app.get("/")
def root():
    return {
        "service": "Advocatus AI Core",
        "status": "operational", 
        "modules": ["embeddings"]
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)