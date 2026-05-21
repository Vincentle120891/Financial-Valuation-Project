"""
Peer Routes - Step 4 and Step 5

Handles peer suggestion and validation functionality using Step4 Peer Management Service with PeerDiscoveryService.
Uses unified schemas for consistent API contracts.

Single Responsibility:
- Step 4: Suggest peers for a given ticker
- Step 5: Validate manually selected peers
"""

import logging
from fastapi import APIRouter, HTTPException

from app.core.logging_config import get_logger
from app.services.international.step4_peer_management_service import Step4PeerManagementService

logger = get_logger(__name__)

router = APIRouter(tags=["Step 4-5 - Peer Selection"])

# Initialize processor
step4_processor = Step4PeerManagementService()


@router.post("/step-4-suggest-peers")
async def suggest_peers_endpoint(request: dict):
    """
    Step 4: Suggest peer companies for a given ticker.
    Uses Step2MarketDataProcessor with PeerDiscoveryService.

    Args:
        ticker: Target ticker symbol (required)
        max_peers: Maximum number of peers to suggest (default: 10)
        market: Market type (default: international)
        method: Valuation method (DCF, COMPS, DuPont) - affects peer criteria
        session_id: Optional session ID for session tracking

    Returns:
        List of peer candidates with similarity scores
    """
    ticker = request.get("ticker")
    max_peers = request.get("max_peers", 10)
    market = request.get("market", "international")
    method = request.get("method")  # NEW: valuation method
    session_id = request.get("session_id")

    # Validate required parameters
    if not ticker:
        raise HTTPException(status_code=400, detail="Missing required parameter: ticker")

    # Log session info if provided
    if session_id:
        logger.info(f"Suggesting peers for ticker='{ticker}', method='{method}', session_id='{session_id}', market={market}")
    else:
        logger.warning(f"Suggesting peers for ticker='{ticker}' without session_id. Consider adding session tracking.")

    try:
        result = await step4_processor.suggest_peers(
            ticker=ticker,
            max_peers=max_peers,
            market=market,
            method=method  # NEW: pass method
        )

        # Add session validation warning if no session_id provided
        if not session_id and result.get("status") == "success":
            result["warnings"] = result.get("warnings", [])
            result["warnings"].append("No session_id provided. For better tracking, include session_id in requests.")

        return result

    except Exception as e:
        logger.error(f"Failed to suggest peers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Peer suggestion failed: {str(e)}")


@router.post("/step-5-validate-manual-peers")
async def validate_manual_peers(request: dict):
    """
    Step 5: Validate manually entered peer tickers.

    Args:
        session_id: Session identifier (required)
        tickers: List of ticker symbols to validate (required)
        market: Market type (default: international)

    Returns:
        Dictionary with validated peers and any errors
    """
    from fastapi import HTTPException

    session_id = request.get("session_id")
    tickers = request.get("tickers", [])
    market = request.get("market", "international")

    # Validate required parameters
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing required parameter: session_id")
    if not tickers:
        raise HTTPException(status_code=400, detail="Missing required parameter: tickers")

    logger.info(f"Validating {len(tickers)} manual peers for session='{session_id}', market={market}")

    try:
        result = step4_processor.validate_peer_tickers(
            session_id=session_id,
            tickers=tickers
        )

        return result

    except Exception as e:
        logger.error(f"Failed to validate manual peers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Manual peer validation failed: {str(e)}")