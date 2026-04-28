"""
Main FastAPI Application Entry Point

This module creates and configures the FastAPI application instance,
includes all routers, and sets up middleware.
"""

import logging
from datetime import datetime
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import time

from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.api.routes.search_routes import router as search_router
from app.api.routes.valuation_routes import router as valuation_router

# Setup structured logging at application startup
setup_logging(
    level=settings.log_level,
    log_format=settings.log_format,
    log_file=settings.log_file,
)

logger = get_logger(__name__)

# Create the main application instance
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Financial Valuation Platform with DCF, DuPont, and Comps analysis",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """
    Structured logging middleware for request/response tracking.
    
    Logs:
    - Request method, path, and client info
    - Response status code and processing time
    """
    start_time = time.time()
    
    # Log request
    logger.info(
        "Incoming request",
        extra={
            "request_id": id(request),
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_host": request.client.host if request.client else "unknown",
        }
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log response
    logger.info(
        "Request completed",
        extra={
            "request_id": id(request),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
        }
    )
    
    # Add processing time header
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
    
    return response


# In-memory session store (TODO: Replace with Redis in production)
sessions_store: dict = {}


def get_session_store() -> dict:
    """Get session store instance. Allows future replacement with Redis."""
    return sessions_store


# Include routers
app.include_router(search_router)
app.include_router(valuation_router)


@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    logger.info(
        f"Starting {settings.app_name} v{settings.app_version}",
        extra={
            "environment": settings.environment,
            "debug_mode": settings.debug,
            "log_level": settings.log_level,
        }
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    logger.info("Shutting down application")


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health/ready")
async def readiness_check():
    """Readiness check - verifies all dependencies are available."""
    api_keys_status = settings.validate_api_keys()
    missing_keys = settings.get_missing_api_keys()
    
    return {
        "status": "ready" if not missing_keys else "degraded",
        "api_keys": api_keys_status,
        "missing_keys": missing_keys,
        "ai_fallback_available": settings.ai_fallback_enabled,
        "timestamp": datetime.now().isoformat()
    }
