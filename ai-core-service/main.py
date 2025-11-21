from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config import settings
from routers import embeddings, reranking, ner
from services.embedding_manager import embedding_manager
from services.rerank_manager import rerank_manager
from services.ner_manager import ner_manager

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 {settings.PROJECT_NAME} Starting...")
    
    # Load ALL models on startup (The Brain is waking up)
    # 1. Embeddings (Vector Search)
    embedding_manager.load_model()
    
    # 2. Reranking (Relevance Sorting)
    rerank_manager.load_model()
    
    # 3. NER (Entity Extraction)
    ner_manager.load_model()
    
    yield
    logger.info(f"🛑 Shutting down {settings.PROJECT_NAME}...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(embeddings.router, prefix="/embeddings", tags=["Embeddings"])
app.include_router(reranking.router, prefix="/reranking", tags=["Reranking"])
app.include_router(ner.router, prefix="/ner", tags=["NER"])

@app.get("/")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "status": "operational", 
        "modules": ["embeddings", "reranking", "ner"]
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)