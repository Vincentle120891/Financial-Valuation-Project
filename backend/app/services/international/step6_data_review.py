"""Step 6: Data Review Layer - Routing Wrapper (Backward Compatibility)

This module provides backward compatibility by routing requests to the new
specialized step 6 processors for each valuation method.

Architecture:
- Legacy API maintained for existing routes
- Delegates to dedicated processors: DCFStep6Processor, DuPontStep6Processor, CompsStep6Processor
- No internal conditional branching logic - pure delegation pattern
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .step6_dcf_data_review import DCFStep6Processor
from .step6_dupont_data_review import DuPontStep6Processor
from .step6_comps_data_review import CompsStep6Processor
from .step6_data_review_models import (
    Step6DataReviewResponse,
    ValuationModel,
    HistoricalFinancialsDisplay,
    ForecastDriversDisplay,
    MarketDataDisplay,
    PeerComparablesDisplay,
    CalculatedMetricsDisplay,
    MissingDataSummary
)

logger = logging.getLogger(__name__)


class Step6DataReviewProcessor:
    """
    Step 6: Data Review Layer - Routing Wrapper
    
    Maintains backward compatibility by delegating to specialized processors.
    This is a thin wrapper that routes based on valuation model type.
    
    For new implementations, consider using the specialized processors directly:
    - DCFStep6Processor for DCF valuations
    - DuPontStep6Processor for DuPont analysis
    - CompsStep6Processor for Trading Comps
    """

    def __init__(self):
        """Initialize specialized processors"""
        self.dcf_processor = DCFStep6Processor()
        self.dupont_processor = DuPontStep6Processor()
        self.comps_processor = CompsStep6Processor()

    async def process_data_review(
        self,
        ticker: str,
        market: str = "international",
        historical_data: Optional[Dict] = None,
        market_data: Optional[Dict] = None,
        forecast_data: Optional[Dict] = None,
        retrieved_assumptions: Optional[Dict] = None,
        user_overrides: Optional[Dict[str, Any]] = None,
        valuation_model: Optional[str] = None,
        session_cache: Optional[Dict] = None  # NEW: Session cache for "Fetch Once, Use Many"
    ) -> Step6DataReviewResponse:
        """
        Main entry point for Step 6 data review.
        Routes to appropriate specialized processor based on valuation model.
        
        Args:
            ticker: Stock ticker symbol
            market: Market region (international/vietnam)
            historical_data: Historical financial data
            market_data: Current market data
            forecast_data: Analyst forecast data
            retrieved_assumptions: Peer and assumption data from previous steps
            user_overrides: Manual overrides applied by user
            valuation_model: Type of valuation (DCF/DUPONT/COMPS)
            session_cache: Session cache dict to check before fetching (implements "Fetch Once, Use Many")
            
        Returns:
            Step6DataReviewResponse with aggregated data
            
        Raises:
            ValueError: If unknown valuation model is specified
        """
        # Default to DCF if not specified
        valuation_model = valuation_model or "DCF"
        model_upper = valuation_model.upper()
        
        logger.info(f"Step 6: Routing {valuation_model} request for {ticker}")
        
        # Route to specialized processor - no internal logic, pure delegation
        if model_upper == "DCF":
            return await self.dcf_processor.process_dcf_data_review(
                ticker=ticker,
                market=market,
                historical_data=historical_data,
                market_data=market_data,
                forecast_data=forecast_data,
                retrieved_assumptions=retrieved_assumptions,
                user_overrides=user_overrides,
                session_cache=session_cache  # PASS cache to DCF processor
            )
        elif model_upper == "DUPONT":
            return await self.dupont_processor.process_dupont_data_review(
                ticker=ticker,
                market=market,
                historical_data=historical_data,
                market_data=market_data,
                retrieved_assumptions=retrieved_assumptions,
                user_overrides=user_overrides,
                session_cache=session_cache  # PASS cache to DuPont processor
            )
        elif model_upper == "COMPS":
            return await self.comps_processor.process_comps_data_review(
                ticker=ticker,
                market=market,
                historical_data=historical_data,
                market_data=market_data,
                retrieved_assumptions=retrieved_assumptions,
                user_overrides=user_overrides,
                session_cache=session_cache  # PASS cache to Comps processor
            )
        else:
            raise ValueError(f"Unknown valuation model: {valuation_model}. "
                           f"Supported models: DCF, DUPONT, COMPS")

