"""Vietnamese Step 8: Comps Assumption & AI Suggestion Studio

This is the critical "Brain" of the Vietnamese Comps workflow, bridging historical reality with future valuation.

Purpose: Comps-specific assumption generation and AI suggestions for Vietnamese market
- Comps Multiples & Filters (P/E, EV/EBITDA, P/B, P/S, Outlier Filter Threshold)

AI Usage in Step 8 Vietnamese Comps:
- AI provides minimal suggestions (mostly calculated from peer data)
- Users can accept AI suggestions or manually override them
- All AI suggestions include rationale and confidence scores with Vietnam-specific context
- Focus on trading multiples and peer comparison filters calibrated for TT99 standards

Vietnam-Specific Features:
- Sector-specific multiple benchmarks for Vietnamese industries
- Liquidity filters appropriate for HOSE/HNX/UPCOM exchanges
- TT99 accounting standard compliance
- Exchange-specific considerations (HOSE, HNX, UPCOM)
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ValuationModel(str, Enum):
    """Type of valuation model to use"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"


class OverrideStatus(str, Enum):
    """Status of manual override"""
    ACCEPTED_AI = "ACCEPTED_AI"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"
    DEFAULT = "DEFAULT"


class AssumptionCategory(str, Enum):
    """Categories for Comps assumptions"""
    COMPS_MULTIPLES = "COMPS_MULTIPLES"


class HistoricalTrendPoint(BaseModel):
    """A single point in a historical trend"""
    year: int
    value: float
    label: str = ""


class HistoricalTrendline(BaseModel):
    """Historical trend data for an assumption"""
    metric: str
    trend_points: List[HistoricalTrendPoint]
    average: float
    cagr: Optional[float] = None
    trend_direction: str = "stable"  # increasing, decreasing, stable
    volatility: str = "low"  # low, medium, high


class AISuggestion(BaseModel):
    """AI suggestion for an assumption"""
    metric: str
    suggested_value: float
    reasoning: str
    confidence_level: str = "medium"  # low, medium, high
    min_range: float
    max_range: float
    category: AssumptionCategory


class AssumptionInput(BaseModel):
    """A single assumption input with full context"""
    metric: str
    category: AssumptionCategory
    description: str
    unit: str = "%"

    # Historical context
    historical_trendline: Optional[HistoricalTrendline] = None

    # Current state
    ai_suggestion: Optional[AISuggestion] = None
    user_value: Optional[float] = None
    final_value: Optional[float] = None
    status: OverrideStatus = OverrideStatus.DEFAULT

    # Validation
    is_valid: bool = True
    validation_message: Optional[str] = None
    warning_message: Optional[str] = None

    # Multi-year support (for forecast years 1-5)
    is_multi_year: bool = False
    year_values: Dict[int, float] = {}  # year -> value


class AssumptionCategoryResponse(BaseModel):
    """Response for a single assumption category"""
    category: AssumptionCategory
    category_name: str
    assumptions: List[AssumptionInput]
    ai_generated_at: datetime = Field(default_factory=datetime.utcnow)
    is_complete: bool = False


class VNCompsAssumptionsOutput(BaseModel):
    """Complete output for Vietnamese Comps Step 8"""
    session_id: str
    ticker: str
    company_name: str
    exchange: str  # HOSE, HNX, UPCOM
    sector: str
    industry: str

    # Comps assumption categories
    comps_multiples: AssumptionCategoryResponse

    # Vietnam-specific context
    sector_analysis: Dict[str, Any]

    # Metadata
    warnings: List[str]
    ai_confidence_score: float
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    next_step: str = "step9_confirmation"
    status: str = "success"


class VNCompsStep8Processor:
    """
    Vietnamese Comps Step 8 Processor - Specialized for Trading Comps valuations in Vietnam

    Generates forward-looking Comps assumptions based on:
    - Historical financial performance (TT99 standards)
    - Vietnamese sector dynamics
    - Peer benchmarking (when available)
    - Exchange-specific considerations (HOSE, HNX, UPCOM)
    """

    # Vietnam sector-specific P/E ranges
    SECTOR_PE_RANGES = {
        "Banking": {"min": 6.0, "max": 12.0, "typical": 9.0},
        "Real Estate": {"min": 8.0, "max": 15.0, "typical": 11.0},
        "Manufacturing": {"min": 10.0, "max": 18.0, "typical": 14.0},
        "Retail": {"min": 12.0, "max": 20.0, "typical": 16.0},
        "Technology": {"min": 15.0, "max": 30.0, "typical": 22.0},
        "Energy": {"min": 8.0, "max": 14.0, "typical": 11.0},
        "Consumer Goods": {"min": 12.0, "max": 20.0, "typical": 16.0},
        "Healthcare": {"min": 14.0, "max": 25.0, "typical": 19.0},
        "Telecommunications": {"min": 10.0, "max": 16.0, "typical": 13.0},
        "Materials": {"min": 8.0, "max": 15.0, "typical": 11.0}
    }

    # Vietnam sector-specific EV/EBITDA ranges
    SECTOR_EV_EBITDA_RANGES = {
        "Banking": {"min": 4.0, "max": 8.0, "typical": 6.0},
        "Real Estate": {"min": 6.0, "max": 12.0, "typical": 9.0},
        "Manufacturing": {"min": 7.0, "max": 13.0, "typical": 10.0},
        "Retail": {"min": 8.0, "max": 14.0, "typical": 11.0},
        "Technology": {"min": 10.0, "max": 20.0, "typical": 15.0},
        "Energy": {"min": 5.0, "max": 10.0, "typical": 7.5},
        "Consumer Goods": {"min": 8.0, "max": 14.0, "typical": 11.0},
        "Healthcare": {"min": 10.0, "max": 18.0, "typical": 14.0},
        "Telecommunications": {"min": 6.0, "max": 11.0, "typical": 8.5},
        "Materials": {"min": 6.0, "max": 12.0, "typical": 9.0}
    }

    # Vietnam sector-specific P/B ranges
    SECTOR_PB_RANGES = {
        "Banking": {"min": 0.8, "max": 2.0, "typical": 1.3},
        "Real Estate": {"min": 0.6, "max": 1.5, "typical": 1.0},
        "Manufacturing": {"min": 1.0, "max": 2.5, "typical": 1.7},
        "Retail": {"min": 1.5, "max": 3.5, "typical": 2.5},
        "Technology": {"min": 2.0, "max": 5.0, "typical": 3.5},
        "Energy": {"min": 0.8, "max": 1.8, "typical": 1.2},
        "Consumer Goods": {"min": 1.5, "max": 3.0, "typical": 2.2},
        "Healthcare": {"min": 2.0, "max": 4.0, "typical": 3.0},
        "Telecommunications": {"min": 1.0, "max": 2.0, "typical": 1.5},
        "Materials": {"min": 0.8, "max": 2.0, "typical": 1.3}
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def process(
        self,
        session_id: str,
        ticker: str,
        company_name: str,
        exchange: str,
        sector: str,
        industry: str,
        historical_data: Dict[str, Any],
        peer_data: Optional[List[Dict[str, Any]]] = None
    ) -> VNCompsAssumptionsOutput:
        """
        Generate Comps-specific assumptions for Vietnamese companies

        Args:
            session_id: Session identifier
            ticker: Stock ticker symbol
            company_name: Company name
            exchange: HOSE, HNX, or UPCOM
            sector: Business sector
            industry: Specific industry
            historical_data: Historical financial data from Step 7
            peer_data: Peer company data for benchmarking

        Returns:
            VNCompsAssumptionsOutput with Comps assumption categories
        """
        # Build Comps multiples
        comps_multiples = self._generate_comps_multiples(
            sector, historical_data, peer_data
        )

        # Build sector analysis
        sector_analysis = self._build_sector_analysis(sector, industry)

        # Generate warnings
        warnings = self._generate_warnings(
            exchange, sector, historical_data, peer_data
        )

        # Calculate overall AI confidence
        ai_confidence = self._calculate_confidence_score(comps_multiples)

        return VNCompsAssumptionsOutput(
            session_id=session_id,
            ticker=ticker,
            company_name=company_name,
            exchange=exchange,
            sector=sector,
            industry=industry,
            comps_multiples=comps_multiples,
            sector_analysis=sector_analysis,
            warnings=warnings,
            ai_confidence_score=ai_confidence,
            status="success"
        )

    def _generate_comps_multiples(
        self,
        sector: str,
        historical_data: Dict[str, Any],
        peer_data: Optional[List[Dict[str, Any]]]
    ) -> AssumptionCategoryResponse:
        """Generate Comps multiples and filter assumptions"""
        assumptions = []

        pe_range = self.SECTOR_PE_RANGES.get(
            sector, {"min": 8.0, "max": 16.0, "typical": 12.0}
        )
        ev_ebitda_range = self.SECTOR_EV_EBITDA_RANGES.get(
            sector, {"min": 6.0, "max": 12.0, "typical": 9.0}
        )
        pb_range = self.SECTOR_PB_RANGES.get(
            sector, {"min": 1.0, "max": 2.5, "typical": 1.7}
        )

        # Target P/E Multiple
        assumptions.append(AssumptionInput(
            metric="target_pe_multiple",
            category=AssumptionCategory.COMPS_MULTIPLES,
            description="Target P/E multiple for valuation",
            unit="x",
            ai_suggestion=AISuggestion(
                metric="target_pe_multiple",
                suggested_value=pe_range["typical"],
                reasoning=f"Sector benchmark for {sector} in Vietnam",
                confidence_level="medium",
                min_range=pe_range["min"],
                max_range=pe_range["max"],
                category=AssumptionCategory.COMPS_MULTIPLES
            ),
            vietnam_context=f"Vietnam {sector} sector typically trades at {pe_range['typical']:.1f}x P/E"
        ))

        # Target EV/EBITDA Multiple
        assumptions.append(AssumptionInput(
            metric="target_ev_ebitda_multiple",
            category=AssumptionCategory.COMPS_MULTIPLES,
            description="Target EV/EBITDA multiple for valuation",
            unit="x",
            ai_suggestion=AISuggestion(
                metric="target_ev_ebitda_multiple",
                suggested_value=ev_ebitda_range["typical"],
                reasoning=f"Enterprise value multiple for {sector} sector",
                confidence_level="medium",
                min_range=ev_ebitda_range["min"],
                max_range=ev_ebitda_range["max"],
                category=AssumptionCategory.COMPS_MULTIPLES
            ),
            vietnam_context=f"Vietnam {sector} sector EV/EBITDA typically {ev_ebitda_range['typical']:.1f}x"
        ))

        # Target P/B Multiple
        assumptions.append(AssumptionInput(
            metric="target_pb_multiple",
            category=AssumptionCategory.COMPS_MULTIPLES,
            description="Target P/B multiple for valuation",
            unit="x",
            ai_suggestion=AISuggestion(
                metric="target_pb_multiple",
                suggested_value=pb_range["typical"],
                reasoning=f"Price-to-book benchmark for {sector} sector",
                confidence_level="medium",
                min_range=pb_range["min"],
                max_range=pb_range["max"],
                category=AssumptionCategory.COMPS_MULTIPLES
            ),
            vietnam_context=f"Vietnam {sector} sector P/B ratio averages {pb_range['typical']:.1f}x"
        ))

        # Number of Peers
        num_peers = min(len(peer_data) if peer_data else 5, 10)
        assumptions.append(AssumptionInput(
            metric="num_peers_final",
            category=AssumptionCategory.COMPS_MULTIPLES,
            description="Number of peer companies to include",
            unit="count",
            ai_suggestion=AISuggestion(
                metric="num_peers_final",
                suggested_value=num_peers,
                reasoning="Optimal balance between representativeness and comparability",
                confidence_level="high" if num_peers >= 3 else "low",
                min_range=3,
                max_range=10,
                category=AssumptionCategory.COMPS_MULTIPLES
            ),
            vietnam_context="Vietnam market often has limited pure-play peers; 3-5 peers recommended"
        ))

        # Liquidity Filter (trading days)
        assumptions.append(AssumptionInput(
            metric="liquidity_filter_days",
            category=AssumptionCategory.COMPS_MULTIPLES,
            description="Minimum trading days for liquidity filter",
            unit="days",
            ai_suggestion=AISuggestion(
                metric="liquidity_filter_days",
                suggested_value=60,
                reasoning="60-day average volume filter appropriate for Vietnam market",
                confidence_level="high",
                min_range=30,
                max_range=120,
                category=AssumptionCategory.COMPS_MULTIPLES
            ),
            vietnam_context="60-day liquidity filter ensures adequate trading activity on HOSE/HNX/UPCOM"
        ))

        # Outlier Filter Threshold (standard deviations)
        assumptions.append(AssumptionInput(
            metric="outlier_filter_std_dev",
            category=AssumptionCategory.COMPS_MULTIPLES,
            description="Standard deviation threshold for outlier exclusion",
            unit="std dev",
            ai_suggestion=AISuggestion(
                metric="outlier_filter_std_dev",
                suggested_value=2.0,
                reasoning="2 standard deviations captures 95% of normal distribution",
                confidence_level="medium",
                min_range=1.5,
                max_range=2.5,
                category=AssumptionCategory.COMPS_MULTIPLES
            ),
            vietnam_context="Standard statistical approach for Vietnam peer analysis"
        ))

        return AssumptionCategoryResponse(
            category=AssumptionCategory.COMPS_MULTIPLES,
            category_name="Comps Multiples & Filters",
            assumptions=assumptions,
            is_complete=True
        )

    def _build_sector_analysis(self, sector: str, industry: str) -> Dict[str, Any]:
        """Build sector-specific analysis for Vietnam"""
        sector_outlooks = {
            "Banking": {
                "vietnam_outlook": "Positive on credit growth and digital transformation",
                "key_drivers": ["NIM expansion", "Fee income growth", "Digital banking adoption"],
                "risks": ["NPL concerns", "Regulatory changes", "Competition from fintech"]
            },
            "Real Estate": {
                "vietnam_outlook": "Recovering with infrastructure investments",
                "key_drivers": ["Urbanization", "FDI inflows", "Infrastructure development"],
                "risks": ["Legal framework complexity", "Liquidity constraints", "Oversupply in some segments"]
            },
            "Manufacturing": {
                "vietnam_outlook": "Strong on FDI and export competitiveness",
                "key_drivers": ["Supply chain diversification", "FTA benefits", "Labor cost advantage"],
                "risks": ["Global demand slowdown", "Raw material costs", "Currency fluctuations"]
            },
            "Retail": {
                "vietnam_outlook": "Robust growth from rising middle class",
                "key_drivers": ["Disposable income growth", "E-commerce expansion", "Modern trade penetration"],
                "risks": ["Intense competition", "Changing consumer preferences", "Real estate costs"]
            },
            "Technology": {
                "vietnam_outlook": "High growth potential with government support",
                "key_drivers": ["Digital transformation", "Startup ecosystem", "Tech talent pool"],
                "risks": ["Talent shortage", "Regulatory uncertainty", "Funding challenges"]
            }
        }

        default_outlook = {
            "vietnam_outlook": "Stable with Vietnam economic growth",
            "key_drivers": ["GDP growth", "Domestic consumption", "Export opportunities"],
            "risks": ["Market volatility", "Regulatory changes", "Competition"]
        }

        return {
            "sector": sector,
            "industry": industry,
            **sector_outlooks.get(sector, default_outlook)
        }

    def _generate_warnings(
        self,
        exchange: str,
        sector: str,
        historical_data: Dict[str, Any],
        peer_data: Optional[List[Dict[str, Any]]]
    ) -> List[str]:
        """Generate Vietnam-specific warnings"""
        warnings = []

        if exchange == "UPCOM":
            warnings.append("UPCOM companies may have limited disclosure and liquidity")

        if not peer_data or len(peer_data) < 3:
            warnings.append(f"Limited peer set for {sector} sector in Vietnam")
        elif len(peer_data) < 5:
            warnings.append(f"Only {len(peer_data)} peers identified; consider expanding peer criteria")

        years_available = historical_data.get("years_available", 0)
        if years_available < 3:
            warnings.append("Less than 3 years of historical data - Comps analysis less reliable")

        return warnings

    def _calculate_confidence_score(self, comps_multiples: AssumptionCategoryResponse) -> float:
        """Calculate overall AI confidence score"""
        total_confidence = 0.0
        count = 0

        for assumption in comps_multiples.assumptions:
            if assumption.ai_suggestion:
                conf_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
                total_confidence += conf_map.get(assumption.ai_suggestion.confidence_level, 0.7)
                count += 1

        return round(total_confidence / count, 2) if count > 0 else 0.7
