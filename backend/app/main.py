"""
Main FastAPI Application Entry Point

This module creates and configures the FastAPI application instance,
includes all routers, and sets up middleware.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes.main_routes import app as main_app

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

# Include routers from main_routes
app.include_router(main_app.router)

@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.environment}")
    print(f"Debug mode: {settings.debug}")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    print("Shutting down application")
