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
        New session ID and status
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

        return SessionCreateResponse(
            session_id=session_id,
            status=result["status"],
            message=result.get("message", "Session created successfully")
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
