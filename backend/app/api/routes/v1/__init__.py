"""
API Routes Version 1

This package contains all API routes for version 1 (v1).
Future versions can be added in separate directories (v2, v3, etc.).
"""

from app.api.routes.v1.search_routes import router as search_router
from app.api.routes.v1.valuation_routes import router as valuation_router

__all__ = ["search_router", "valuation_router"]
