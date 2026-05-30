"""
API Key Resolver - Centralized fallback chain for API key resolution

Provides a single source of truth for resolving API keys across all services
with consistent priority: headers → session storage → environment variables.

This prevents the architectural discrepancy where some routes check headers
while others check session storage, ensuring unified key resolution logic.
"""

import logging
import os
from typing import Optional, Dict, Any
from fastapi import Request

from app.core.session_service import session_service

logger = logging.getLogger(__name__)


# Mapping of internal service names to header keys and environment variables
API_KEY_CONFIG = {
    'fmp': {
        'header_key': 'x-api-key-fmp',
        'env_vars': ['FMP_API_KEY', 'FINANCIAL_MODELING_PREP_API_KEY'],
        'session_key': 'fmp_key'
    },
    'alpha_vantage': {
        'header_key': 'x-api-key-alphavantage',
        'env_vars': ['ALPHAVANTAGE_API_KEY', 'ALPHA_VANTAGE_API_KEY'],
        'session_key': 'alpha_vantage_key'
    },
    'fred': {
        'header_key': 'x-api-key-fred',
        'env_vars': ['FRED_API_KEY'],
        'session_key': 'fred_key'
    },
    'sec_edgar': {
        'header_key': 'x-api-key-secedgar',
        'env_vars': ['SEC_EDGAR_EMAIL', 'SEC_EDGAR_IDENTIFIER'],
        'session_key': 'sec_edgar_email'
    },
    'openrouter': {
        'header_key': 'x-api-key-openrouter',
        'env_vars': ['OPENROUTER_API_KEY'],
        'session_key': 'openrouter_api_key'
    },
    'groq': {
        'header_key': 'x-api-key-groq',
        'env_vars': ['GROQ_API_KEY'],
        'session_key': 'groq_api_key'
    },
    'gemini': {
        'header_key': 'x-api-key-gemini',
        'env_vars': ['GEMINI_API_KEY', 'GOOGLE_GEMINI_API_KEY'],
        'session_key': 'gemini_api_key'
    },
    'qwen': {
        'header_key': 'x-api-key-qwen',
        'env_vars': ['QWEN_API_KEY', 'DASHSCOPE_API_KEY'],
        'session_key': 'qwen_api_key'
    }
}


def get_api_key(
    service_name: str,
    request: Optional[Request] = None,
    session_id: Optional[str] = None
) -> Optional[str]:
    """
    Resolve API key using standardized fallback chain.
    
    Priority Order:
        1. Request header (highest priority - allows per-request override)
        2. Session storage (user-provided keys saved during session)
        3. Environment variable (server-side default configuration)
    
    Args:
        service_name: Name of the service ('fmp', 'alpha_vantage', 'fred', etc.)
        request: FastAPI request object (for header extraction)
        session_id: Session identifier (for session storage lookup)
    
    Returns:
        API key if found, None otherwise
    
    Example:
        >>> fmp_key = get_api_key('fmp', request=request, session_id=session_id)
        >>> if fmp_key:
        ...     # Use the key for API calls
        ...     pass
    """
    if service_name not in API_KEY_CONFIG:
        logger.warning(f"Unknown service name: {service_name}")
        return None
    
    config = API_KEY_CONFIG[service_name]
    
    # PRIORITY 1: Check request headers (via request.state populated by middleware)
    if request:
        api_keys = getattr(request.state, 'api_keys', {})
        header_key = api_keys.get(service_name)
        if header_key:
            logger.debug(f"Using {service_name} API key from request header")
            return header_key
    
    # PRIORITY 2: Check session storage
    if session_id:
        try:
            stored_keys = session_service.get_session_value(
                session_id,
                "api_keys",
                {}
            )
            session_key = stored_keys.get(config['session_key'])
            if session_key:
                logger.debug(f"Using {service_name} API key from session storage")
                return session_key
        except Exception as e:
            logger.warning(f"Failed to retrieve API keys from session: {e}")
    
    # PRIORITY 3: Check environment variables
    for env_var in config['env_vars']:
        env_key = os.getenv(env_var)
        if env_key:
            logger.debug(f"Using {service_name} API key from environment variable ({env_var})")
            return env_key
    
    # No key found
    logger.warning(f"{service_name} API key not configured (checked: header, session, env)")
    return None


def get_all_api_keys(
    request: Optional[Request] = None,
    session_id: Optional[str] = None
) -> Dict[str, Optional[str]]:
    """
    Resolve all API keys using the fallback chain.
    
    Args:
        request: FastAPI request object (for header extraction)
        session_id: Session identifier (for session storage lookup)
    
    Returns:
        Dictionary mapping service names to their resolved API keys (or None)
    
    Example:
        >>> keys = get_all_api_keys(request=request, session_id=session_id)
        >>> if keys['fmp']:
        ...     # FMP key is available
        ...     pass
    """
    result = {}
    for service_name in API_KEY_CONFIG.keys():
        result[service_name] = get_api_key(
            service_name=service_name,
            request=request,
            session_id=session_id
        )
    return result


def check_api_keys_status(
    request: Optional[Request] = None,
    session_id: Optional[str] = None
) -> Dict[str, bool]:
    """
    Check which API keys are currently configured/available.
    
    Args:
        request: FastAPI request object (for header extraction)
        session_id: Session identifier (for session storage lookup)
    
    Returns:
        Dictionary mapping service names to boolean availability status
    
    Example:
        >>> status = check_api_keys_status(request=request, session_id=session_id)
        >>> if status['fmp']:
        ...     # FMP key is available
        ...     pass
    """
    result = {}
    for service_name in API_KEY_CONFIG.keys():
        key = get_api_key(
            service_name=service_name,
            request=request,
            session_id=session_id
        )
        result[service_name] = key is not None and len(key.strip()) > 0
    return result


def validate_api_key(key: Optional[str], service_name: str) -> bool:
    """
    Validate that an API key is present and properly formatted.
    
    Args:
        key: The API key to validate
        service_name: Name of the service (for logging purposes)
    
    Returns:
        True if key is valid, False otherwise
    """
    if not key:
        logger.warning(f"{service_name} API key is missing")
        return False
    
    if not isinstance(key, str):
        logger.warning(f"{service_name} API key is not a string")
        return False
    
    if len(key.strip()) == 0:
        logger.warning(f"{service_name} API key is empty")
        return False
    
    return True
