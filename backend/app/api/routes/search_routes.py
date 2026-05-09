"""
Search and Ticker Routes - Refactored to use SessionService and International Services

Handles ticker search and selection functionality using Step1-3 processors.
"""

import logging
from typing import List, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.logging_config import get_logger
from app.core.session_service import session_service
from app.api.schemas import SearchRequest, TickerSelectRequest, SearchResponse, SessionCreateResponse, SearchResult
from app.services.international.step1_ticker_processor import Step1TickerProcessor
from app.services.international.step2_market_data_processor import Step2MarketDataProcessor
from app.services.international.step3_historical_processor import Step3HistoricalProcessor

logger = get_logger(__name__)

router = APIRouter(tags=["Search & Ticker"])

# Initialize processors
step1_processor = Step1TickerProcessor()
step2_processor = Step2MarketDataProcessor()
step3_processor = Step3HistoricalProcessor()


@router.post("/step-1-search", response_model=SearchResponse)
async def search_tickers(request: SearchRequest):
    """
    Step 1: Search for tickers by symbol or company name.
    Uses Step1TickerProcessor for consistent search logic.

    Args:
        request: Search request with query and market parameters

    Returns:
        List of matching tickers
    """
    logger.info(f"Searching for tickers with query='{request.query}', market='{request.market}'")

    try:
        results = await step1_processor.search_tickers(query=request.query, market=request.market)

        if not results:
            logger.warning(f"No tickers found for query='{request.query}'")
            return SearchResponse(results=[], message="No tickers found. Try exact symbol.")

        logger.info(f"Found {len(results)} ticker(s) for query='{request.query}'")
        return SearchResponse(results=[SearchResult(**r) for r in results])

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
        result = await step2_processor.select_company(
            ticker=request.ticker,
            market=request.market,
            session_id=session_id
        )

        # Update session status from processor result
        session_service.update_session_data(session_id, "status", result["status"])

        # Extract company data from the result if available
        company_data = None
        if result.get("data"):
            data = result["data"]
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
            if "market_data" in data:
                for md in data["market_data"]:
                    if md.get("metric") == "current_price":
                        company_data["current_price"] = md.get("value")
                    elif md.get("metric") == "market_cap":
                        company_data["market_cap"] = md.get("value")
                    elif md.get("metric") == "beta":
                        company_data["beta"] = md.get("value")
                    elif md.get("metric") == "risk_free_rate":
                        company_data["risk_free_rate"] = md.get("value")
                    elif md.get("metric") == "market_risk_premium":
                        company_data["market_risk_premium"] = md.get("value")
            
            # Extract from risk_metrics
            if "risk_metrics" in data:
                risk_metrics = data["risk_metrics"]
                if not company_data["beta"] and risk_metrics.get("beta"):
                    company_data["beta"] = risk_metrics.get("beta")
                if not company_data["risk_free_rate"] and risk_metrics.get("risk_free_rate"):
                    company_data["risk_free_rate"] = risk_metrics.get("risk_free_rate")
                if not company_data["market_risk_premium"] and risk_metrics.get("market_risk_premium"):
                    company_data["market_risk_premium"] = risk_metrics.get("market_risk_premium")
            
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
    Step 3: Validate ticker has sufficient historical data.
    Uses Step3HistoricalProcessor for robust data verification.
    """
    try:
        is_valid, message = await step3_processor.validate_ticker(
            ticker=ticker,
            market=market
        )

        return {
            "valid": is_valid,
            "message": message
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
        ticker: Target ticker symbol
        max_peers: Maximum number of peers to suggest (default: 10)
        market: Market type (default: international)
    
    Returns:
        List of peer candidates with similarity scores
    """
    ticker = request.get("ticker")
    max_peers = request.get("max_peers", 10)
    market = request.get("market", "international")
    
    logger.info(f"Suggesting peers for ticker='{ticker}', max_peers={max_peers}, market={market}")
    
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


@router.post("/suggest-peers")
async def suggest_peers_legacy(ticker: str, max_peers: int = 10, market: str = "international"):
    """
    Legacy endpoint for suggesting peers (kept for backward compatibility).
    """
    logger.info(f"Suggesting peers for ticker='{ticker}', max_peers={max_peers}")
    
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
