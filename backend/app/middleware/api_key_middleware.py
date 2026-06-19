"""
API Key Middleware - Handles per-request API key injection

This middleware extracts API keys from request headers and makes them available
to services via request state. This allows users to provide their own API keys
while maintaining server-side defaults as fallback.

Supported Headers:
    X-API-Key-AlphaVantage: AlphaVantage API key
    X-API-Key-FMP: Financial Modeling Prep API key
    X-API-Key-FRED: FRED API key
    X-API-Key-SECEdgar: SEC EDGAR email/identifier

Priority:
    1. Request header (highest priority)
    2. Environment variable (fallback)
"""

import logging
from typing import Optional, Dict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and inject API keys from request headers."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """Extract API keys from headers and attach to request state.

        Note: FastAPI/Starlette converts all headers to lowercase, so we must
        use lowercase header names when accessing request.headers.
        """

        # Extract API keys from headers (lowercase as per HTTP/2 spec)
        raw_api_keys = {
            'alpha_vantage': request.headers.get('x-api-key-alphavantage'),
            'rapidapi': request.headers.get('x-api-key-rapidapi'),
            'fmp': request.headers.get('x-api-key-fmp'),
            'fred': request.headers.get('x-api-key-fred'),
            'sec_edgar': request.headers.get('x-api-key-secedgar'),
            'openrouter': request.headers.get('x-api-key-openrouter'),
            'groq': request.headers.get('x-api-key-groq'),
            'gemini': request.headers.get('x-api-key-gemini'),
            'qwen': request.headers.get('x-api-key-qwen'),
        }

        # Parse comma-separated keys and register them in ApiKeyManager
        from app.core.api_key_manager import api_key_manager
        api_keys = {}
        for service, raw_value in raw_api_keys.items():
            if raw_value:
                # Support comma-separated multiple keys
                keys = [k.strip() for k in raw_value.split(',') if k.strip()]
                if keys:
                    # Store the first key for backward compatibility
                    api_keys[service] = keys[0]
                    # Register all keys in the manager for rotation
                    for key in keys:
                        api_key_manager.add_key(service, key, source='header')

        # Attach to request state for downstream access
        request.state.api_keys = api_keys

        # Log if any custom API keys provided (without logging the actual keys)
        if api_keys:
            logger.debug(f"Request includes custom API keys for: {list(api_keys.keys())}")

        # Continue processing
        response = await call_next(request)
        return response


def get_api_key_from_request(request: Request, service_name: str) -> Optional[str]:
    """
    Helper function to retrieve API key from request state.

    Args:
        request: FastAPI request object
        service_name: Name of the service ('alpha_vantage', 'fmp', 'fred', 'sec_edgar')

    Returns:
        API key from header if provided, None otherwise
    """
    api_keys = getattr(request.state, 'api_keys', {})
    return api_keys.get(service_name)


def get_all_api_keys(request: Request) -> Dict[str, str]:
    """
    Get all API keys from request state.

    Args:
        request: FastAPI request object

    Returns:
        Dictionary of API keys (empty dict if none provided)
    """
    return getattr(request.state, 'api_keys', {})