"""
Session Routes - Step 2 Only

Handles session creation functionality using SessionService and Step2 processor.
Uses unified schemas for consistent API contracts.

Single Responsibility: Only handles Step 2 - Create session when user selects a ticker.
"""

import logging
from fastapi import APIRouter, HTTPException, Request

from app.core.logging_config import get_logger
from app.core.session_service import session_service
from app.api.schemas import (
    UnifiedStep2Response,
    TickerSelectRequest,
)
from app.services.international.step2_market_data_processor import Step2MarketDataProcessor

logger = get_logger(__name__)

router = APIRouter(tags=["Step 2 - Create Session"])


@router.post("/step-2-create-session", response_model=UnifiedStep2Response)
async def create_session(request: Request, payload: TickerSelectRequest):
    """
    Step 2: User chooses ticker and creates a session.
    Uses SessionService for session management and Step2MarketDataProcessor for validation.
    Returns UnifiedStep2Response with complete market data, risk metrics, and data quality scoring.

    Args:
        request: FastAPI request object (for API key access)
        payload: Ticker selection request

    Returns:
        UnifiedStep2Response with session_id, ticker, market, company_name, confirmed status,
        market_data array, risk_metrics, missing_data, warnings, and data_quality_score
    """
    logger.info(f"Creating session for ticker='{payload.ticker}', market='{payload.market}'")

    try:
        # Initialize processor with request to enable API key propagation
        step2_processor = Step2MarketDataProcessor(request=request)
        
        # Create session using SessionService
        session_id = session_service.create_session(
            ticker=payload.ticker,
            market=payload.market
        )
        
        # Validate and enrich session data using Step2 processor
        # This returns UnifiedStep2Response directly
        unified_response = step2_processor.process_market_data(
            ticker=payload.ticker,
            market=payload.market,
            session_id=session_id,
            company_name=None
        )
        
        # Get ticker_info for sector/industry/country data
        ticker_info = step2_processor.yfinance_service.get_ticker_info(payload.ticker)
        
        # Update session status from processor result
        session_service.update_session_data(session_id, "status", unified_response.status)
        
        # Update session with company_name and data_quality_score from Step 2 response
        session_service.update_session_data(session_id, "company_name", unified_response.company_name)
        session_service.update_session_data(session_id, "data_quality_score", unified_response.data_quality_score)
        session_service.update_session_data(session_id, "confirmed", unified_response.confirmed)
        session_service.update_session_data(session_id, "market", unified_response.market)
        
        # Add ticker_info to response for frontend display
        if ticker_info:
            unified_response_dict = unified_response.model_dump()
            unified_response_dict['ticker_info'] = {
                'sector': ticker_info.get('sector'),
                'industry': ticker_info.get('industry'),
                'country': ticker_info.get('country', ticker_info.get('exchange'))
            }
            return unified_response_dict

        # Return the unified response directly (with updated session_id)
        return unified_response

    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Session creation failed: {str(e)}")
