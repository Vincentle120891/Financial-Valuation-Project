"""
Search and Ticker Routes - Refactored to use Unified Schemas and SessionService

Handles ticker search and selection functionality using Step1-3 processors.
Uses unified schemas for consistent API contracts across all steps.
"""

import logging
from typing import List, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.logging_config import get_logger
from app.core.session_service import session_service
from app.api.schemas import (
    SearchResponse, 
    SessionCreateResponse, 
    SearchResult,
    UnifiedStep1Request,
    UnifiedStep1Response,
    CompanySearchResult,
    UnifiedStep2Request,
    UnifiedStep2Response,
    MarketType,
    TickerSelectRequest
)
from app.services.international.step1_ticker_processor import Step1TickerProcessor
from app.services.international.step2_market_data_processor import Step2MarketDataProcessor
# NOTE: step3_historical_processor.py renamed to mismatch_historical_processor.py
# Historical data validation now handled differently in the new workflow

logger = get_logger(__name__)

router = APIRouter(tags=["Search & Ticker"])

# Initialize processors
step1_processor = Step1TickerProcessor()
step2_processor = Step2MarketDataProcessor()
# NOTE: step3_processor removed - historical data validation now handled differently


@router.post("/step-1-search", response_model=UnifiedStep1Response)
async def search_tickers(request: UnifiedStep1Request):
    """
    Step 1: Search for tickers by symbol or company name.
    Uses Step1TickerProcessor for consistent search logic.
    Returns unified schema response with proper status tracking.

    Args:
        request: UnifiedStep1Request with query, market, and limit parameters

    Returns:
        UnifiedStep1Response with search results and metadata
    """
    logger.info(f"Searching for tickers with query='{request.query}', market='{request.market.value if isinstance(request.market, MarketType) else request.market}'")

    try:
        # Convert market enum to string if needed
        market_str = request.market.value if isinstance(request.market, MarketType) else request.market
        
        results = await step1_processor.search_tickers(query=request.query, market=market_str)

        if not results:
            logger.warning(f"No tickers found for query='{request.query}'")
            return UnifiedStep1Response(
                status="no_results",
                query=request.query,
                market=market_str,
                results=[],
                total_results=0,
                message="No tickers found. Try exact symbol or company name."
            )

        # Convert raw results to CompanySearchResult format
        # FIX Issue #2: Ensure field names match CompanySearchResult schema (ticker, company_name)
        company_results = []
        for r in results:
            company_results.append(CompanySearchResult(
                ticker=r.get('ticker', r.get('symbol', '')),  # Prefer 'ticker', fallback to 'symbol'
                company_name=r.get('company_name', r.get('name', '')),  # Prefer 'company_name', fallback to 'name'
                exchange=r.get('exchange', ''),
                market=r.get('market', market_str),
                sector=r.get('sector'),
                industry=r.get('industry'),
                currency=r.get('currency'),
                country=r.get('country')
            ))

        logger.info(f"Found {len(company_results)} ticker(s) for query='{request.query}'")
        return UnifiedStep1Response(
            status="success",
            query=request.query,
            market=market_str,
            results=company_results,
            total_results=len(company_results),
            message=f"Found {len(company_results)} matching companies"
        )

    except Exception as e:
        logger.error(f"Failed to search tickers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/step-3-select-ticker", response_model=SessionCreateResponse)
async def select_ticker(request: TickerSelectRequest):
    """
    Step 2: User chooses ticker and creates a session.
    Uses SessionService for session management and Step2MarketDataProcessor for validation.

    Args:
        request: Ticker selection request

    Returns:
        New session ID and status with company data including current price, beta, risk-free rate, and market risk premium
    """
    logger.info(f"Creating session for ticker='{request.ticker}', market='{request.market}'")

    try:
        # Create session using SessionService
        session_id = session_service.create_session(
            ticker=request.ticker,
            market=request.market
        )
        
        # Validate and enrich session data using Step2 processor
        unified_response = step2_processor.process_market_data(
            ticker=request.ticker,
            market=request.market,
            session_id=session_id,
            company_name=None
        )
        
        # Build result dict from unified response
        result = {
            "status": unified_response.status,
            "message": unified_response.message,
            "data": unified_response.model_dump()
        }

        # Update session status from processor result
        session_service.update_session_data(session_id, "status", result["status"])

        # Extract company data from the unified response
        company_data = None
        if unified_response:
            # Build company_data dict with key metrics
            company_data = {
                "current_price": None,
                "market_cap": None,
                "beta": None,
                "risk_free_rate": None,
                "market_risk_premium": None,
                "sector": None,
                "industry": None,
                "country": None
            }
            
            # Extract from market_data array
            for md in unified_response.market_data:
                if md.metric == "current_price":
                    company_data["current_price"] = md.value
                elif md.metric == "market_cap":
                    company_data["market_cap"] = md.value
                elif md.metric == "beta":
                    company_data["beta"] = md.value
                elif md.metric == "risk_free_rate":
                    company_data["risk_free_rate"] = md.value
                elif md.metric == "market_risk_premium":
                    company_data["market_risk_premium"] = md.value
            
            # Extract from risk_metrics
            if unified_response.risk_metrics:
                risk_metrics = unified_response.risk_metrics
                if not company_data["beta"] and risk_metrics.beta and risk_metrics.beta.value:
                    company_data["beta"] = risk_metrics.beta.value
                if not company_data["risk_free_rate"] and risk_metrics.risk_free_rate and risk_metrics.risk_free_rate.value:
                    company_data["risk_free_rate"] = risk_metrics.risk_free_rate.value
                if not company_data["market_risk_premium"] and risk_metrics.market_risk_premium and risk_metrics.market_risk_premium.value:
                    company_data["market_risk_premium"] = risk_metrics.market_risk_premium.value
            
            # Get sector/industry/country from yfinance ticker info
            ticker_info = step2_processor.yfinance_service.get_ticker_info(request.ticker)
            if ticker_info:
                if not company_data["sector"]:
                    company_data["sector"] = ticker_info.get("sector")
                if not company_data["industry"]:
                    company_data["industry"] = ticker_info.get("industry")
                if not company_data["country"]:
                    company_data["country"] = ticker_info.get("country") or ticker_info.get("state") or "N/A"

        return SessionCreateResponse(
            session_id=session_id,
            status=result["status"],
            message=result.get("message", "Session created successfully"),
            company_data=company_data
        )

    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Session creation failed: {str(e)}")


@router.post("/validate-ticker")
async def validate_ticker(ticker: str, market: str = "US"):
    """
    Validate ticker has sufficient historical data.
    NOTE: This endpoint is deprecated in the new workflow.
    Historical data validation is now handled during data retrieval steps.
    """
    try:
        # Simple validation - just check if ticker exists
        from app.services.international.yfinance_service import YFinanceService
        yf_service = YFinanceService()
        ticker_info = yf_service.get_ticker_info(ticker)
        
        if ticker_info and ticker_info.get('currentPrice'):
            return {
                "valid": True,
                "message": f"Ticker {ticker} is valid"
            }
        else:
            return {
                "valid": False,
                "message": f"Ticker {ticker} not found or no price data available"
            }
    except Exception as e:
        logger.error(f"Validate ticker error: {e}")
        return {
            "valid": False,
            "message": str(e)
        }


@router.post("/step-2-suggest-peers")
async def suggest_peers_endpoint(request: dict):
    """
    Suggest peer companies for a given ticker.
    Uses Step2MarketDataProcessor with PeerDiscoveryService.
    
    Args:
        ticker: Target ticker symbol (required)
        max_peers: Maximum number of peers to suggest (default: 10)
        market: Market type (default: international)
        session_id: Optional session ID for session tracking
    
    Returns:
        List of peer candidates with similarity scores
    """
    ticker = request.get("ticker")
    max_peers = request.get("max_peers", 10)
    market = request.get("market", "international")
    session_id = request.get("session_id")
    
    # Validate required parameters
    if not ticker:
        raise HTTPException(status_code=400, detail="Missing required parameter: ticker")
    
    # Log session info if provided
    if session_id:
        logger.info(f"Suggesting peers for ticker='{ticker}', session_id='{session_id}', market={market}")
    else:
        logger.warning(f"Suggesting peers for ticker='{ticker}' without session_id. Consider adding session tracking.")
    
    try:
        result = await step2_processor.suggest_peers(
            ticker=ticker,
            max_peers=max_peers,
            market=market
        )
        
        # Add session validation warning if no session_id provided
        if not session_id and result.get("status") == "success":
            result["warnings"] = result.get("warnings", [])
            result["warnings"].append("No session_id provided. For better tracking, include session_id in requests.")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to suggest peers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Peer suggestion failed: {str(e)}")


@router.post("/suggest-peers")
async def suggest_peers_legacy(ticker: str, max_peers: int = 10, market: str = "international"):
    """
    DEPRECATED: Use /step-2-suggest-peers instead.
    
    Legacy endpoint for suggesting peers (kept for backward compatibility).
    This endpoint will be removed in a future version.
    """
    import warnings
    warnings.warn(
        "The /suggest-peers endpoint is deprecated. Use /step-2-suggest-peers instead.",
        DeprecationWarning,
        stacklevel=2
    )
    logger.warning("DEPRECATED: Using legacy /suggest-peers endpoint. Migrate to /step-2-suggest-peers.")
    
    try:
        result = await step2_processor.suggest_peers(
            ticker=ticker,
            max_peers=max_peers,
            market=market
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to suggest peers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Peer suggestion failed: {str(e)}")


@router.post("/validate-manual-peers")
async def validate_manual_peers(request: dict):
    """
    Validate manually entered peer tickers.
    
    Args:
        session_id: Session identifier (required)
        tickers: List of ticker symbols to validate (required)
        market: Market type (default: international)
    
    Returns:
        Dictionary with validated peers and any errors
    """
    from app.api.schemas import ManualPeerRequest
    
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
        result = await step2_processor.validate_manual_peers(
            tickers=tickers,
            market=market
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to validate manual peers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Manual peer validation failed: {str(e)}")
