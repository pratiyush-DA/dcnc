"""
FastAPI Application
===================
Main FastAPI application for DCNC API
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import (
    API_TITLE,
    API_VERSION,
    API_DESCRIPTION,
    CORS_ORIGINS,
    LOG_LEVEL
)
from .routes import classification, correction, health, auth

# Import tenant middleware for multi-tenancy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from backend.middleware.auth_middleware import tenant_middleware

# Setup logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {API_TITLE} v{API_VERSION}")
    logger.info("Initializing services...")
    
    # TODO: Initialize services (database, cache, etc.)
    
    yield
    
    # Shutdown
    logger.info("Shutting down API...")
    # TODO: Cleanup resources


# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenant middleware (for multi-tenancy - sets client context)
# Import here to avoid circular imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from backend.middleware.auth_middleware import tenant_middleware
    app.middleware("http")(tenant_middleware)
except ImportError:
    logger.warning("Tenant middleware not available (PostgreSQL dependencies may be missing)")

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(classification.router, prefix="/api/v1", tags=["Classification"])
app.include_router(correction.router, prefix="/api/v1", tags=["Correction"])


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "detail": str(exc) if LOG_LEVEL == "DEBUG" else "An error occurred"
        }
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": API_TITLE,
        "version": API_VERSION,
        "status": "operational",
        "docs": "/api/docs"
    }
