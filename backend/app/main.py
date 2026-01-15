from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import upload, query

app = FastAPI(
    title="Semantic Query Cache POC",
    description="Document Q&A with semantic query caching",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api", tags=["Document Upload"])
app.include_router(query.router, prefix="/api", tags=["Query"])

@app.get("/")
async def root():
    return {
        "message": "Semantic Query Cache POC API",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        from app.services.redis_cache import redis_cache
        from app.services.qdrant_service import qdrant_service

        # Test Redis connection
        redis_cache.client.ping()

        # Test Qdrant connection
        qdrant_service.client.get_collections()

        return {
            "status": "healthy",
            "redis": "connected",
            "qdrant": "connected",
            "llm_provider": settings.LLM_PROVIDER
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
