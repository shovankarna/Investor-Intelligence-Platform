"""FastAPI Application Entry Point with CORS, Lifespan Hooks, and Healthcheck."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events.

    This is where we initialize singletons (e.g., loading local embedding
    models in-process) so they load ONCE at server startup instead of
    reloading on every request.
    """
    # Startup: Log initialization
    print(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")

    yield  # Application runs and handles requests here

    # Shutdown: Cleanup resources
    print("Shutting down backend service...")


# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Dual-path RAG and financial analytics engine for 10-K reports.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS (Cross-Origin Resource Sharing)
# Restricts frontend browser requests to allowed domains (AGENT.md §9)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
