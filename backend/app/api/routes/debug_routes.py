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
    
    # AI provider headers
    openrouter_header = raw_headers.get('x-api-key-openrouter')
    openai_header = raw_headers.get('x-api-key-openai')
    groq_header = raw_headers.get('x-api-key-groq')
    gemini_header = raw_headers.get('x-api-key-gemini')
    qwen_header = raw_headers.get('x-api-key-qwen')
    
    logger.info(f"Debug API keys endpoint accessed - FMP source: {fmp_key_source}")
    
    return {
        "success": True,
        "data": {
            
            "received_headers": {
                "x-api-key-fmp": mask_api_key(fmp_header_key) if fmp_header_key else None,
                "x-api-key-alphavantage": mask_api_key(av_header_key) if av_header_key else None,
                "x-api-key-fred": mask_api_key(fred_header_key) if fred_header_key else None,
                "x-api-key-secedgar": mask_api_key(sec_header_key) if sec_header_key else None,
                "x-api-key-openrouter": mask_api_key(openrouter_header) if openrouter_header else None,
                "x-api-key-openai": mask_api_key(openai_header) if openai_header else None,
                "x-api-key-groq": mask_api_key(groq_header) if groq_header else None,
                "x-api-key-gemini": mask_api_key(gemini_header) if gemini_header else None,
                "x-api-key-qwen": mask_api_key(qwen_header) if qwen_header else None,
            },
            "extracted_to_state": {
                "fmp": mask_api_key(extracted_keys.get('fmp')) if extracted_keys.get('fmp') else None,
                "alpha_vantage": mask_api_key(extracted_keys.get('alpha_vantage')) if extracted_keys.get('alpha_vantage') else None,
                "fred": mask_api_key(extracted_keys.get('fred')) if extracted_keys.get('fred') else None,
                "sec_edgar": mask_api_key(extracted_keys.get('sec_edgar')) if extracted_keys.get('sec_edgar') else None,
                "openrouter": mask_api_key(extracted_keys.get('openrouter')) if extracted_keys.get('openrouter') else None,
                "openai": mask_api_key(extracted_keys.get('openai')) if extracted_keys.get('openai') else None,
                "groq": mask_api_key(extracted_keys.get('groq')) if extracted_keys.get('groq') else None,
                "gemini": mask_api_key(extracted_keys.get('gemini')) if extracted_keys.get('gemini') else None,
                "qwen": mask_api_key(extracted_keys.get('qwen')) if extracted_keys.get('qwen') else None,
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
                "openrouter": {
                    "source": "header" if openrouter_header else ("environment" if os.getenv("OPENROUTER_API_KEY") else "none"),
                    "masked_value": mask_api_key(openrouter_header or os.getenv("OPENROUTER_API_KEY")) if (openrouter_header or os.getenv("OPENROUTER_API_KEY")) else None,
                    "header_present": openrouter_header is not None,
                    "env_present": os.getenv("OPENROUTER_API_KEY") is not None,
                },
                "openai": {
                    "source": "header" if openai_header else ("environment" if os.getenv("OPENAI_API_KEY") else "none"),
                    "masked_value": mask_api_key(openai_header or os.getenv("OPENAI_API_KEY")) if (openai_header or os.getenv("OPENAI_API_KEY")) else None,
                    "header_present": openai_header is not None,
                    "env_present": os.getenv("OPENAI_API_KEY") is not None,
                },
                "groq": {
                    "source": "header" if groq_header else ("environment" if os.getenv("GROQ_API_KEY") else "none"),
                    "masked_value": mask_api_key(groq_header or os.getenv("GROQ_API_KEY")) if (groq_header or os.getenv("GROQ_API_KEY")) else None,
                    "header_present": groq_header is not None,
                    "env_present": os.getenv("GROQ_API_KEY") is not None,
                },
                "gemini": {
                    "source": "header" if gemini_header else ("environment" if os.getenv("GOOGLE_GEMINI_API_KEY") else "none"),
                    "masked_value": mask_api_key(gemini_header or os.getenv("GOOGLE_GEMINI_API_KEY")) if (gemini_header or os.getenv("GOOGLE_GEMINI_API_KEY")) else None,
                    "header_present": gemini_header is not None,
                    "env_present": os.getenv("GOOGLE_GEMINI_API_KEY") is not None,
                },
                "qwen": {
                    "source": "header" if qwen_header else ("environment" if os.getenv("DASHSCOPE_API_KEY") else "none"),
                    "masked_value": mask_api_key(qwen_header or os.getenv("DASHSCOPE_API_KEY")) if (qwen_header or os.getenv("DASHSCOPE_API_KEY")) else None,
                    "header_present": qwen_header is not None,
                    "env_present": os.getenv("DASHSCOPE_API_KEY") is not None,
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


@router.get("/api-key-manager")
async def debug_api_key_manager(request: Request, session_id: Optional[str] = None):
    """
    Debug endpoint showing full API key manager status.
    
    Shows:
    - All registered keys per service (masked)
    - Key rotation status
    - Usage statistics (requests, successes, failures, rate limits)
    - Which key is currently active
    - Error history per key
    """
    from app.core.api_key_manager import api_key_manager
    
    # Load session keys if session_id provided
    if session_id:
        api_key_manager.load_from_session(session_id)
    
    # Also load from request headers
    extracted_keys = getattr(request.state, 'api_keys', {})
    for service_name, key_value in extracted_keys.items():
        if key_value:
            api_key_manager.add_key(service_name, key_value, source='header')
    
    all_status = api_key_manager.get_all_status()
    
    # Build summary
    total_keys = sum(s['total_keys'] for s in all_status.values())
    total_requests = sum(
        sum(k['total_requests'] for k in s['all_keys'])
        for s in all_status.values()
    )
    total_rate_limits = sum(
        sum(k['rate_limit_hits'] for k in s['all_keys'])
        for s in all_status.values()
    )
    
    return {
        "success": True,
        "summary": {
            "total_services": len(all_status),
            "total_keys_registered": total_keys,
            "total_requests_made": total_requests,
            "total_rate_limit_hits": total_rate_limits,
        },
        "services": all_status,
        "diagnostic": _build_key_diagnostic(all_status)
    }


def _build_key_diagnostic(all_status: dict) -> str:
    """Build human-readable diagnostic message."""
    messages = []
    for service, status in all_status.items():
        total = status['total_keys']
        current = status.get('current_key', {})
        if total == 0:
            messages.append(f"⚠️ {service}: No keys registered")
        elif current and current.get('rate_limit_hits', 0) > 0:
            messages.append(f"🔄 {service}: Key #{status['current_key_index']} active, {current['rate_limit_hits']} rate limit hit(s)")
        elif current and current.get('failed_requests', 0) > 0:
            messages.append(f"❌ {service}: Key #{status['current_key_index']} has {current['failed_requests']} failure(s)")
        else:
            messages.append(f"✅ {service}: {total} key(s) registered, Key #{status['current_key_index']} active")
    return " | ".join(messages) if messages else "No services registered"
