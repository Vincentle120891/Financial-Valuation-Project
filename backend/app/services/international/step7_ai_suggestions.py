"""
Step 7: AI Suggestions Processor

Integrates with AI Engine for generating forward-looking assumptions.
The AI engine handles prompt generation and LLM communication.
This processor orchestrates the AI assumption generation for DCF models.

Note: For DuPont and Comps models, AI is bypassed (all inputs are calculated/fetched).
For DCF models, AI generates only forward-looking macro assumptions.
"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

from app.services.international.ai_engine import (
    AIFallbackEngine,
    get_strategy,
    DCFStrategy,
    VietnamDCFStrategy,
    DuPontStrategy,
    CompsStrategy
)

logger = logging.getLogger(__name__)


class ValuationModel(str, Enum):
    """Type of valuation model to use"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"


class AISuggestionResponse(BaseModel):
    """
    Step 7 Response: AI-generated forward-looking assumptions
    These are suggestions from the AI engine, subject to user review/override
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: ValuationModel
    ai_assumptions: Optional[Dict[str, Any]]
    rationale: Optional[str]
    provider_used: Optional[str]
    confidence_score: float
    ready_for_review: bool = True


class Step7AISuggestionsProcessor:
    """
    Step 7: AI Suggestions Processor
    
    Generates forward-looking assumptions using the AI Engine:
    - DCF: ERP, CRP, Terminal Growth, Terminal Multiple, Forecast Drivers
    - DuPont: No AI (bypassed)
    - Comps: No AI (bypassed)
    
    The AI engine handles prompt construction and LLM communication.
    This processor orchestrates the flow and formats responses.
    """
    
    def __init__(self):
        self.ai_engine = AIFallbackEngine()
    
    async def generate_ai_suggestions(
        self,
        ticker: str,
        company_name: str,
        valuation_model: str,
        market: str,
        financial_data: Dict[str, Any],
        sector: str = "General",
        industry: str = "General"
    ) -> AISuggestionResponse:
        """
        Generate AI suggestions for forward-looking assumptions.
        
        Args:
            ticker: Stock ticker symbol
            company_name: Company name
            valuation_model: DCF, DUPONT, or COMPS
            market: Market/country (e.g., "US", "Vietnam")
            financial_data: Historical financial data and market metrics
            sector: Company sector
            industry: Company industry
            
        Returns:
            AISuggestionResponse with AI-generated assumptions
        """
        model_enum = ValuationModel(valuation_model.upper())
        
        # Prepare company data for AI engine
        company_data = {
            "ticker": ticker,
            "company_name": company_name,
            "sector": sector,
            "industry": industry,
            "country": market,
            **financial_data
        }
        
        # Use AI engine to generate assumptions
        result = self.ai_engine.generate_assumptions(
            company_data=company_data,
            model_type=model_enum.value,
            market=market
        )
        
        # Extract AI status information
        ai_status = result.get("_ai_status", {})
        success = ai_status.get("success", False)
        provider = ai_status.get("provider_used")
        
        # Determine confidence score based on provider success
        if success and provider:
            confidence = 0.9 if provider in ["groq", "gemini"] else 0.7
        elif success and not provider:
            # DuPont or Comps - no AI needed
            confidence = 1.0
        else:
            # Fallback used
            confidence = 0.5
        
        return AISuggestionResponse(
            session_id=f"step7_ai_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=model_enum,
            ai_assumptions=result.get("ai_assumptions"),
            rationale=result.get("rationale") if result.get("ai_assumptions") else None,
            provider_used=provider,
            confidence_score=confidence,
            ready_for_review=True
        )
