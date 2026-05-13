"""
Session Routes - Step 2 Only

Handles session creation functionality using SessionService and Step2 processor.
Uses unified schemas for consistent API contracts.

Single Responsibility: Only handles Step 2 - Create session when user selects a ticker.
"""

import logging
from fastapi import APIRouter, HTTPException

from app.core.logging_config import get_logger
from app.core.session_service import session_service
from app.api.schemas import (
    SessionCreateResponse,
    TickerSelectRequest,
)
from app.services.international.step2_market_data_processor import Step2MarketDataProcessor

logger = get_logger(__name__)

router = APIRouter(tags=["Step 2 - Create Session"])

# Initialize processor
step2_processor = Step2MarketDataProcessor()


@router.post("/step-2-create-session", response_model=SessionCreateResponse)
async def create_session(request: TickerSelectRequest):
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
