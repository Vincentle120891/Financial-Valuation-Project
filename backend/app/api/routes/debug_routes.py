"""
Debug Routes - API Key Visibility & Troubleshooting

These endpoints help diagnose API key flow issues between frontend and backend.
"""

import logging
from fastapi import APIRouter, Request, Depends
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["debug"])


def mask_api_key(key: str) -> str:
    """Mask API key for secure display (show first 4 and last 4 chars)."""
    if not key or len(key) < 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


@router.get("/api-keys")
async def debug_api_keys(request: Request):
    """
    Debug endpoint to visualize API key flow.
    
    Shows:
    - What headers were received from the client
    - What API keys were extracted to request.state
    - Which key source is being used (header/env/default)
    - Masked key preview for security
    
    This helps identify if:
    - API key isn't saved in localStorage
    - Header name doesn't match
    - Middleware isn't extracting the key
    - Key is falling back to environment variable or default
    """
    import os
    
    # Get all raw headers (lowercase keys as per HTTP/2 spec)
    raw_headers = dict(request.headers)
    
    # Filter to only API key related headers
    api_key_headers = {
        k: v for k, v in raw_headers.items() 
        if 'api' in k.lower() and 'key' in k.lower()
    }
    
    # Get extracted API keys from request.state
    extracted_keys = getattr(request.state, 'api_keys', {})
    
    # Determine FMP key source and value
    fmp_header_key = raw_headers.get('x-api-key-fmp')
    fmp_env_key = os.getenv('FMP_API_KEY')
    fmp_default_key = "meq65Y3F8YP1LRdtqHQHLu6s0RmHSISL"
    
    fmp_key_source = "none"
    fmp_key_value = None
    
    if fmp_header_key:
        fmp_key_source = "header"
        fmp_key_value = fmp_header_key
    elif fmp_env_key:
        fmp_key_source = "environment"
        fmp_key_value = fmp_env_key
    else:
        fmp_key_source = "default"
        fmp_key_value = fmp_default_key
    
    # Determine AlphaVantage key source
    av_header_key = raw_headers.get('x-api-key-alphavantage')
    av_env_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    
    av_key_source = "none"
    av_key_value = None
    
    if av_header_key:
        av_key_source = "header"
        av_key_value = av_header_key
    elif av_env_key:
        av_key_source = "environment"
        av_key_value = av_env_key
    
    # Determine FRED key source
    fred_header_key = raw_headers.get('x-api-key-fred')
    fred_env_key = os.getenv('FRED_API_KEY')
    
    fred_key_source = "none"
    fred_key_value = None
    
    if fred_header_key:
        fred_key_source = "header"
        fred_key_value = fred_header_key
    elif fred_env_key:
        fred_key_source = "environment"
        fred_key_value = fred_env_key
    
    # Determine SEC EDGAR key source
    sec_header_key = raw_headers.get('x-api-key-secedgar')
    sec_env_key = os.getenv('SEC_EDGAR_EMAIL')
    
    sec_key_source = "none"
    sec_key_value = None
    
    if sec_header_key:
        sec_key_source = "header"
        sec_key_value = sec_header_key
    elif sec_env_key:
        sec_key_source = "environment"
        sec_key_value = sec_env_key
    
    logger.info(f"Debug API keys endpoint accessed - FMP source: {fmp_key_source}")
    
    return {
        "success": True,
        "data": {
            "received_headers": {
                "x-api-key-fmp": mask_api_key(fmp_header_key) if fmp_header_key else None,
                "x-api-key-alphavantage": mask_api_key(av_header_key) if av_header_key else None,
                "x-api-key-fred": mask_api_key(fred_header_key) if fred_header_key else None,
                "x-api-key-secedgar": mask_api_key(sec_header_key) if sec_header_key else None,
            },
            "extracted_to_state": {
                "fmp": mask_api_key(extracted_keys.get('fmp')) if extracted_keys.get('fmp') else None,
                "alpha_vantage": mask_api_key(extracted_keys.get('alpha_vantage')) if extracted_keys.get('alpha_vantage') else None,
                "fred": mask_api_key(extracted_keys.get('fred')) if extracted_keys.get('fred') else None,
                "sec_edgar": mask_api_key(extracted_keys.get('sec_edgar')) if extracted_keys.get('sec_edgar') else None,
            },
            "key_sources": {
                "fmp": {
                    "source": fmp_key_source,
                    "masked_value": mask_api_key(fmp_key_value) if fmp_key_value else None,
                    "header_present": fmp_header_key is not None,
                    "env_present": fmp_env_key is not None,
                },
                "alpha_vantage": {
                    "source": av_key_source,
                    "masked_value": mask_api_key(av_key_value) if av_key_value else None,
                    "header_present": av_header_key is not None,
                    "env_present": av_env_key is not None,
                },
                "fred": {
                    "source": fred_key_source,
                    "masked_value": mask_api_key(fred_key_value) if fred_key_value else None,
                    "header_present": fred_header_key is not None,
                    "env_present": fred_env_key is not None,
                },
                "sec_edgar": {
                    "source": sec_key_source,
                    "masked_value": mask_api_key(sec_key_value) if sec_key_value else None,
                    "header_present": sec_header_key is not None,
                    "env_present": sec_env_key is not None,
                },
            },
            "diagnostic": {
                "fmp_flow_ok": fmp_header_key is not None or fmp_env_key is not None,
                "message": get_diagnostic_message(
                    fmp_header_key, fmp_env_key, 
                    av_header_key, av_env_key,
                    fred_header_key, fred_env_key
                )
            }
        }
    }


def get_diagnostic_message(fmp_header, fmp_env, av_header, av_env, fred_header, fred_env):
    """Generate diagnostic message based on key availability."""
    messages = []
    
    if not fmp_header and not fmp_env:
        messages.append("⚠️ FMP API key not found in headers or environment. Peer discovery will use default key or fail.")
    elif fmp_header:
        messages.append("✅ FMP API key successfully received from frontend header.")
    elif fmp_env:
        messages.append("ℹ️ FMP API key using environment variable fallback.")
    
    if not av_header and not av_env:
        messages.append("⚠️ Alpha Vantage API key not configured.")
    
    if not fred_header and not fred_env:
        messages.append("ℹ️ FRED API key not configured (optional for risk-free rate).")
    
    return " ".join(messages) if messages else "✅ All required API keys configured."
