"""FastAPI Application Entry Point with CORS, Lifespan Hooks, and Mounted Routers."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.metrics import router as metrics_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    print(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    yield
    print("Shutting down backend service...")


# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Dual-path RAG and financial analytics engine for 10-K reports.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Resource Routers (AGENT.md §4)
app.include_router(documents_router, prefix="/api/documents", tags=["Documents"])
app.include_router(metrics_router, prefix="/api/metrics", tags=["Metrics & Ratios"])
app.include_router(chat_router, prefix="/api/chat", tags=["Conversational RAG"])


@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, str]:
    """Basic health check endpoint to verify backend API availability."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


@app.get("/", tags=["System"])
async def root() -> Dict[str, str]:
    """Root endpoint welcoming the user and pointing to interactive docs."""
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs_url": "/docs",
        "health_check": "/health",
    }
