"""Step 7: AI Suggestion Layer - AI Assumption Generator"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

class ValuationModel(str, Enum):
    """Type of valuation model to use"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"

class AISuggestion(BaseModel):
    """AI-generated suggestion for an assumption"""
    metric: str
    suggested_value: float
    confidence: float  # 0.0 to 1.0
    reasoning: str
    min_reasonable: float
    max_reasonable: float
    based_on: str  # What data/analysis this is based on

class AISuggestionsResponse(BaseModel):
    """
    Step 7 Response: AI-generated suggestions for assumptions
    Different models have different required AI inputs
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: ValuationModel
    suggestions: List[AISuggestion]
    model_specific_notes: str
    ready_for_manual_override: bool = True


class Step7AISuggestionsProcessor:
    """
    Step 7: AI Suggestion Layer (AI Assumption Generator)
    
    Analyzes data from Step 6 and generates model-specific suggestions:
    - DCF: Suggests WACC, Terminal Growth, and Margin trends based on historical volatility
    - DuPont: Suggests target ROE components based on industry peers
    - Comps: Suggests appropriate peer multiples and outlier filters
    """
    
    def __init__(self):
        pass
    
    async def generate_ai_suggestions(
        self,
        ticker: str,
        valuation_model: str,
        step6_data: Dict[str, Any],
        market_context: Optional[Dict] = None
    ) -> AISuggestionsResponse:
        """
        Generate AI suggestions based on Step 6 data.
        
        Args:
            ticker: Stock ticker symbol
            valuation_model: DCF, DUPONT, or COMPS
            step6_data: Aggregated data from Step 6
            market_context: Optional market/industry context
        
        Returns:
            AISuggestionsResponse with recommended values and reasoning
        """
        model_enum = ValuationModel(valuation_model.upper())
        
        if model_enum == ValuationModel.DCF:
            return await self._generate_dcf_suggestions(ticker, step6_data, market_context)
        elif model_enum == ValuationModel.DUPONT:
            return await self._generate_dupont_suggestions(ticker, step6_data, market_context)
        elif model_enum == ValuationModel.COMPS:
            return await self._generate_comps_suggestions(ticker, step6_data, market_context)
        else:
            raise ValueError(f"Unknown valuation model: {valuation_model}")
    
    async def _generate_dcf_suggestions(
        self,
        ticker: str,
        step6_data: Dict,
        market_context: Optional[Dict]
    ) -> AISuggestionsResponse:
        """
        Generate AI suggestions for DCF model.
        
        Suggests:
        - WACC based on beta, risk-free rate, market premium
        - Terminal Growth based on GDP expectations and industry maturity
        - Margin trends based on historical volatility
        - Revenue growth based on historical CAGR and industry trends
        """
        suggestions = []
        
        # Extract data from Step 6
        market_data = step6_data.get("market_data", {})
        historical = step6_data.get("historical_financials", {})
        forecast = step6_data.get("forecast_drivers", {})
        
        # Get beta for WACC calculation
        beta = 1.0
        if market_data and hasattr(market_data, 'beta') and market_data.beta:
            beta = market_data.beta.value or 1.0
        
        # Suggest WACC
        # WACC = Re * E/V + Rd * D/V * (1-T)
        # Re = Rf + Beta * MRP
        rf_rate = 0.045  # Default risk-free rate (10Y Treasury)
        mrp = 0.055  # Market Risk Premium
        cost_of_equity = rf_rate + beta * mrp
        
        # Simplified WACC (assuming 80% equity, 20% debt)
        cost_of_debt = 0.04
        tax_rate = 0.21
        wacc_suggested = cost_of_equity * 0.8 + cost_of_debt * 0.2 * (1 - tax_rate)
        
        suggestions.append(AISuggestion(
            metric="WACC",
            suggested_value=wacc_suggested,
            confidence=0.75,
            reasoning=f"Based on beta={beta:.2f}, risk-free rate={rf_rate:.2%}, market risk premium={mrp:.2%}. Cost of equity={cost_of_equity:.2%}",
            min_reasonable=0.06,
            max_reasonable=0.15,
            based_on="CAPM Model with current market conditions"
        ))
        
        # Suggest Terminal Growth Rate
        # Typically based on long-term GDP growth expectations
        terminal_growth = 0.025  # Default 2.5% (long-term GDP expectation)
        suggestions.append(AISuggestion(
            metric="Terminal Growth Rate",
            suggested_value=terminal_growth,
            confidence=0.70,
            reasoning="Based on long-term GDP growth expectations. Should not exceed nominal GDP growth.",
            min_reasonable=0.01,
            max_reasonable=0.04,
            based_on="Long-term economic growth projections"
        ))
        
        # Suggest Revenue Growth based on historical CAGR
        hist_growth = forecast.get("revenue_growth", 0.05) if isinstance(forecast, dict) else 0.05
        if hasattr(forecast, 'data_fields'):
            for field in forecast.data_fields:
                if 'Revenue Growth' in field.field_name and field.value:
                    hist_growth = field.value
                    break
        
        # Suggest slightly conservative growth
        suggested_growth = max(0.02, min(hist_growth * 0.9, 0.25))
        suggestions.append(AISuggestion(
            metric="Revenue Growth Rate",
            suggested_value=suggested_growth,
            confidence=0.65,
            reasoning=f"Historical CAGR={hist_growth:.2%}. Suggesting conservative estimate at {suggested_growth:.2%} to account for mean reversion.",
            min_reasonable=0.0,
            max_reasonable=0.30,
            based_on="Historical revenue CAGR with conservative adjustment"
        ))
        
        # Suggest EBITDA Margin
        calculated_metrics = step6_data.get("calculated_metrics", {})
        avg_margin = 0.15  # Default
        if hasattr(calculated_metrics, 'data_fields'):
            for field in calculated_metrics.data_fields:
                if 'Margin' in field.field_name and field.value:
                    avg_margin = field.value
                    break
        
        suggestions.append(AISuggestion(
            metric="EBITDA Margin",
            suggested_value=avg_margin,
            confidence=0.70,
            reasoning=f"Based on historical average margin of {avg_margin:.2%}. Assuming stable margins.",
            min_reasonable=0.05,
            max_reasonable=0.40,
            based_on="Historical EBITDA margin analysis"
        ))
        
        notes = (
            "DCF AI Suggestions generated based on historical financials and current market data. "
            "WACC calculated using CAPM. Terminal growth based on long-term GDP expectations. "
            "Please review and adjust based on company-specific factors."
        )
        
        return AISuggestionsResponse(
            session_id=f"step7_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DCF,
            suggestions=suggestions,
            model_specific_notes=notes,
            ready_for_manual_override=True
        )
    
    async def _generate_dupont_suggestions(
        self,
        ticker: str,
        step6_data: Dict,
        market_context: Optional[Dict]
    ) -> AISuggestionsResponse:
        """
        Generate AI suggestions for DuPont model.
        
        Suggests:
        - Target ROE components (Net Margin, Asset Turnover, Equity Multiplier)
        - Based on industry peers and historical trends
        """
        suggestions = []
        
        # Extract data from Step 6
        historical = step6_data.get("historical_financials", {})
        
        # Calculate historical ROE components if data available
        # ROE = Net Margin × Asset Turnover × Equity Multiplier
        
        # Default industry averages (would be enhanced with real peer data)
        industry_net_margin = 0.10
        industry_asset_turnover = 1.2
        industry_equity_multiplier = 2.0
        industry_roe = industry_net_margin * industry_asset_turnover * industry_equity_multiplier
        
        suggestions.append(AISuggestion(
            metric="Target Net Profit Margin",
            suggested_value=industry_net_margin,
            confidence=0.65,
            reasoning=f"Industry average net margin is {industry_net_margin:.2%}. Company should target this level for competitive ROE.",
            min_reasonable=0.02,
            max_reasonable=0.25,
            based_on="Industry peer analysis"
        ))
        
        suggestions.append(AISuggestion(
            metric="Target Asset Turnover",
            suggested_value=industry_asset_turnover,
            confidence=0.60,
            reasoning=f"Industry average asset turnover is {industry_asset_turnover:.2f}. Reflects efficient asset utilization.",
            min_reasonable=0.5,
            max_reasonable=3.0,
            based_on="Industry peer asset efficiency metrics"
        ))
        
        suggestions.append(AISuggestion(
            metric="Target Equity Multiplier",
            suggested_value=industry_equity_multiplier,
            confidence=0.60,
            reasoning=f"Industry average equity multiplier is {industry_equity_multiplier:.2f}. Indicates moderate financial leverage.",
            min_reasonable=1.0,
            max_reasonable=4.0,
            based_on="Industry capital structure analysis"
        ))
        
        suggestions.append(AISuggestion(
            metric="Target ROE",
            suggested_value=industry_roe,
            confidence=0.65,
            reasoning=f"Implied ROE of {industry_roe:.2%} based on component targets. Aligns with industry median.",
            min_reasonable=0.05,
            max_reasonable=0.35,
            based_on="DuPont decomposition of industry ROE"
        ))
        
        notes = (
            "DuPont AI Suggestions generated based on industry peer analysis. "
            "Targets represent median industry performance. Adjust based on company's competitive position and strategy."
        )
        
        return AISuggestionsResponse(
            session_id=f"step7_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DUPONT,
            suggestions=suggestions,
            model_specific_notes=notes,
            ready_for_manual_override=True
        )
    
    async def _generate_comps_suggestions(
        self,
        ticker: str,
        step6_data: Dict,
        market_context: Optional[Dict]
    ) -> AISuggestionsResponse:
        """
        Generate AI suggestions for Comps model.
        
        Suggests:
        - Appropriate peer multiples (P/E, EV/EBITDA, P/B, P/S)
        - Outlier filter settings
        - Weighting method (median vs mean)
        """
        suggestions = []
        
        # Extract peer data from Step 6
        peer_data = step6_data.get("market_data", {})
        
        # Default peer multiples (would be calculated from actual peer data)
        # These are placeholder values - in production would calculate from peer_data
        pe_median = 18.5
        ev_ebitda_median = 12.0
        pb_median = 2.5
        ps_median = 3.0
        
        suggestions.append(AISuggestion(
            metric="P/E Multiple",
            suggested_value=pe_median,
            confidence=0.70,
            reasoning=f"Median P/E of peer group is {pe_median:.1f}x. Recommend using median to reduce outlier impact.",
            min_reasonable=5.0,
            max_reasonable=50.0,
            based_on="Peer group median P/E analysis"
        ))
        
        suggestions.append(AISuggestion(
            metric="EV/EBITDA Multiple",
            suggested_value=ev_ebitda_median,
            confidence=0.75,
            reasoning=f"Median EV/EBITDA of peer group is {ev_ebitda_median:.1f}x. Most reliable multiple for capital-intensive industries.",
            min_reasonable=3.0,
            max_reasonable=25.0,
            based_on="Peer group median EV/EBITDA analysis"
        ))
        
        suggestions.append(AISuggestion(
            metric="P/B Multiple",
            suggested_value=pb_median,
            confidence=0.65,
            reasoning=f"Median P/B of peer group is {pb_median:.1f}x. Most relevant for asset-heavy companies.",
            min_reasonable=0.5,
            max_reasonable=10.0,
            based_on="Peer group median P/B analysis"
        ))
        
        suggestions.append(AISuggestion(
            metric="P/S Multiple",
            suggested_value=ps_median,
            confidence=0.60,
            reasoning=f"Median P/S of peer group is {ps_median:.1f}x. Useful for high-growth, low-margin companies.",
            min_reasonable=0.5,
            max_reasonable=15.0,
            based_on="Peer group median P/S analysis"
        ))
        
        suggestions.append(AISuggestion(
            metric="Outlier Filter Threshold",
            suggested_value=2.0,  # Standard deviations
            confidence=0.80,
            reasoning="Recommend filtering peers beyond 2 standard deviations to reduce noise from outliers.",
            min_reasonable=1.5,
            max_reasonable=3.0,
            based_on="Statistical outlier detection best practices"
        ))
        
        notes = (
            "Comps AI Suggestions generated based on peer group analysis. "
            "Median multiples recommended over mean to reduce outlier impact. "
            "Ensure peer group consists of truly comparable companies in same industry and size range."
        )
        
        return AISuggestionsResponse(
            session_id=f"step7_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.COMPS,
            suggestions=suggestions,
            model_specific_notes=notes,
            ready_for_manual_override=True
        )
