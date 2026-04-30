"""
Main FastAPI Application Entry Point

This module creates and configures the FastAPI application instance,
includes all routers, and sets up middleware.
"""

import logging
from datetime import datetime
from typing import Any, Dict
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time
import uuid

from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.core.exceptions import ValuationException
from app.api.routes.v1.search_routes import router as search_router_v1
from app.api.routes.v1.valuation_routes import router as valuation_router_v1
from app.api.routes.v1.pdf_extraction_routes import router as pdf_extraction_router_v1
from app.api.routes.vietnamese_reports_routes import router as vietnamese_reports_router

# Setup structured logging at application startup
setup_logging(
    level=settings.log_level,
    log_format=settings.log_format,
    log_file=settings.log_file,
)

logger = get_logger(__name__)


def generate_request_id() -> str:
    """Generate a unique request ID for tracing."""
    return str(uuid.uuid4())


# Create the main application instance with API versioning
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Financial Valuation Platform with DCF, DuPont, and Comps analysis",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    root_path=settings.api_root_path or ""
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
    
    # Generate or extract request ID for tracing
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    
    # Log request
    logger.info(
        "Incoming request",
        extra={
            "request_id": request_id,
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
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
        }
    )
    
    # Add processing time and request ID headers
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
    response.headers["X-Request-ID"] = request_id
    
    return response


# Custom exception handlers for structured error responses
@app.exception_handler(ValuationException)
async def valuation_exception_handler(request: Request, exc: ValuationException):
    """Handle custom valuation exceptions with structured responses."""
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    
    logger.warning(
        f"Valuation exception: {exc.error_code}",
        extra={
            "request_id": request_id,
            "error_code": exc.error_code,
            "details": exc.details,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "type": exc.__class__.__name__,
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with structured responses."""
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    
    logger.warning(
        "Request validation failed",
        extra={
            "request_id": request_id,
            "errors": exc.errors(),
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors(),
                "type": "RequestValidationError",
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with structured responses."""
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    
    logger.error(
        f"Unexpected exception: {str(exc)}",
        extra={
            "request_id": request_id,
            "exception_type": exc.__class__.__name__,
        },
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {"exception_type": exc.__class__.__name__} if settings.debug else {},
                "type": "InternalError",
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


# In-memory session store (TODO: Replace with Redis in production)
sessions_store: dict = {}


def get_session_store() -> dict:
    """Get session store instance. Allows future replacement with Redis."""
    return sessions_store


# Include routers with API versioning
# Version 1 routes
app.include_router(search_router_v1, prefix="/api/v1")
app.include_router(valuation_router_v1, prefix="/api/v1")
app.include_router(pdf_extraction_router_v1, prefix="/api/v1/pdf")
app.include_router(vietnamese_reports_router, prefix="/api/v1")

# Legacy routes (for backward compatibility)
app.include_router(search_router_v1, prefix="/api")
app.include_router(valuation_router_v1, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    logger.info(
        f"Starting {settings.app_name} v{settings.app_version}",
        extra={
            "environment": settings.environment,
            "debug_mode": settings.debug,
            "log_level": settings.log_level,
            "api_versions": ["v1"],
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
