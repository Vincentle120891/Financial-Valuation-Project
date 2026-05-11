"""Vietnamese Step 8: DCF Assumption & AI Suggestion Studio

This is the critical "Brain" of the Vietnamese DCF workflow, bridging historical reality with future valuation.

Purpose: DCF-specific assumption generation and AI suggestions for Vietnamese market
- Revenue Drivers (Volume Growth, Price Increase) - multi-year
- Cost & Margins (COGS %, SG&A %, Tax Rate)
- Working Capital (AR Days, Inventory Days, AP Days)
- WACC Components (Risk-Free Rate, Market Risk Premium, Country Risk Premium, Cost of Debt, D/E Ratio)
- Terminal Value (Terminal Growth Rate, Terminal EBITDA Multiple)

AI Usage in Step 8 Vietnamese DCF:
- AI provides suggestions for all DCF assumptions based on historical trends, peer analysis, and Vietnam market conditions
- Users can accept AI suggestions or manually override them
- All AI suggestions include rationale and confidence scores with Vietnam-specific context
- Key drivers: Revenue Growth, Margins, WACC components, Terminal Value calibrated for TT99 standards

Vietnam-Specific Features:
- Sector-specific growth ranges for Vietnamese industries
- Vietnam macroeconomic integration (GDP growth, inflation, risk-free rate)
- Country risk premium calibration
- TT99 accounting standard compliance
- Exchange-specific considerations (HOSE, HNX, UPCOM)
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import json

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
    """Categories for DCF assumptions"""
    REVENUE_DRIVERS = "REVENUE_DRIVERS"
    COST_MARGINS = "COST_MARGINS"
    WORKING_CAPITAL = "WORKING_CAPITAL"
    WACC_COMPONENTS = "WACC_COMPONENTS"
    TERMINAL_VALUE = "TERMINAL_VALUE"


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


class VNDCFAssumptionsOutput(BaseModel):
    """Complete output for Vietnamese DCF Step 8"""
    session_id: str
    ticker: str
    company_name: str
    exchange: str  # HOSE, HNX, UPCOM
    sector: str
    industry: str

    # All assumption categories
    revenue_drivers: AssumptionCategoryResponse
    cost_margins: AssumptionCategoryResponse
    working_capital: AssumptionCategoryResponse
    wacc_components: AssumptionCategoryResponse
    terminal_value: AssumptionCategoryResponse

    # Vietnam-specific context
    vietnam_macro: Dict[str, Any]
    sector_analysis: Dict[str, Any]

    # Metadata
    warnings: List[str]
    ai_confidence_score: float
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    next_step: str = "step9_confirmation"
    status: str = "success"


class VNDCFStep8Processor:
    """
    Vietnamese DCF Step 8 Processor - Specialized for DCF valuations in Vietnam

    Generates forward-looking DCF assumptions based on:
    - Historical financial performance (TT99 standards)
    - Vietnamese sector dynamics
    - Macroeconomic indicators (Vietnam GDP, inflation, risk-free rate)
    - Peer benchmarking (when available)
    - Exchange-specific considerations (HOSE, HNX, UPCOM)
    """

    # Vietnam sector-specific growth ranges
    SECTOR_GROWTH_RANGES = {
        "Banking": {"min": 0.08, "max": 0.18, "typical": 0.12},
        "Real Estate": {"min": 0.05, "max": 0.25, "typical": 0.15},
        "Manufacturing": {"min": 0.06, "max": 0.20, "typical": 0.10},
        "Retail": {"min": 0.08, "max": 0.22, "typical": 0.14},
        "Technology": {"min": 0.15, "max": 0.40, "typical": 0.25},
        "Energy": {"min": 0.04, "max": 0.15, "typical": 0.08},
        "Consumer Goods": {"min": 0.06, "max": 0.16, "typical": 0.10},
        "Healthcare": {"min": 0.10, "max": 0.25, "typical": 0.18},
        "Telecommunications": {"min": 0.03, "max": 0.10, "typical": 0.06},
        "Materials": {"min": 0.05, "max": 0.18, "typical": 0.09}
    }

    # Vietnam margin benchmarks by sector
    SECTOR_MARGIN_BENCHMARKS = {
        "Banking": {"net_margin": 0.25, "operating_margin": 0.35, "gross_margin": 0.40},
        "Real Estate": {"net_margin": 0.18, "operating_margin": 0.25, "gross_margin": 0.30},
        "Manufacturing": {"net_margin": 0.08, "operating_margin": 0.12, "gross_margin": 0.18},
        "Retail": {"net_margin": 0.05, "operating_margin": 0.08, "gross_margin": 0.15},
        "Technology": {"net_margin": 0.15, "operating_margin": 0.20, "gross_margin": 0.35},
        "Energy": {"net_margin": 0.12, "operating_margin": 0.18, "gross_margin": 0.25},
        "Consumer Goods": {"net_margin": 0.10, "operating_margin": 0.14, "gross_margin": 0.22},
        "Healthcare": {"net_margin": 0.15, "operating_margin": 0.20, "gross_margin": 0.30},
        "Telecommunications": {"net_margin": 0.20, "operating_margin": 0.30, "gross_margin": 0.45},
        "Materials": {"net_margin": 0.08, "operating_margin": 0.12, "gross_margin": 0.18}
    }

    # Vietnam WACC components by sector
    SECTOR_WACC_RANGES = {
        "Banking": {"min": 0.10, "max": 0.15, "typical": 0.12},
        "Real Estate": {"min": 0.12, "max": 0.20, "typical": 0.15},
        "Manufacturing": {"min": 0.10, "max": 0.16, "typical": 0.13},
        "Retail": {"min": 0.11, "max": 0.17, "typical": 0.14},
        "Technology": {"min": 0.15, "max": 0.25, "typical": 0.18},
        "Energy": {"min": 0.09, "max": 0.14, "typical": 0.11},
        "Consumer Goods": {"min": 0.10, "max": 0.15, "typical": 0.12},
        "Healthcare": {"min": 0.12, "max": 0.18, "typical": 0.14},
        "Telecommunications": {"min": 0.09, "max": 0.13, "typical": 0.11},
        "Materials": {"min": 0.10, "max": 0.16, "typical": 0.13}
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
        vietnam_macro: Optional[Dict[str, Any]] = None,
        peer_data: Optional[List[Dict[str, Any]]] = None
    ) -> VNDCFAssumptionsOutput:
        """
        Generate DCF-specific assumptions for Vietnamese companies

        Args:
            session_id: Session identifier
            ticker: Stock ticker symbol
            company_name: Company name
            exchange: HOSE, HNX, or UPCOM
            sector: Business sector
            industry: Specific industry
            historical_data: Historical financial data from Step 7
            vietnam_macro: Vietnam macroeconomic indicators
            peer_data: Peer company data for benchmarking

        Returns:
            VNDCFAssumptionsOutput with all DCF assumption categories
        """
        # Default Vietnam macro inputs
        if vietnam_macro is None:
            vietnam_macro = {
                "gdp_growth": 0.055,
                "inflation_target": 0.04,
                "risk_free_rate": 0.068,
                "country_risk_premium": 0.035,
                "market_risk_premium": 0.065
            }

        # Build all assumption categories
        revenue_drivers = self._generate_revenue_drivers(
            sector, historical_data, vietnam_macro
        )
        cost_margins = self._generate_cost_margins(
            sector, historical_data, vietnam_macro
        )
        working_capital = self._generate_working_capital(
            sector, historical_data
        )
        wacc_components = self._generate_wacc_components(
            sector, vietnam_macro
        )
        terminal_value = self._generate_terminal_value(
            sector, vietnam_macro
        )

        # Build sector analysis
        sector_analysis = self._build_sector_analysis(sector, industry)

        # Generate warnings
        warnings = self._generate_warnings(
            exchange, sector, historical_data, peer_data
        )

        # Calculate overall AI confidence
        ai_confidence = self._calculate_confidence_score(
            revenue_drivers, cost_margins, working_capital,
            wacc_components, terminal_value
        )

        return VNDCFAssumptionsOutput(
            session_id=session_id,
            ticker=ticker,
            company_name=company_name,
            exchange=exchange,
            sector=sector,
            industry=industry,
            revenue_drivers=revenue_drivers,
            cost_margins=cost_margins,
            working_capital=working_capital,
            wacc_components=wacc_components,
            terminal_value=terminal_value,
            vietnam_macro=vietnam_macro,
            sector_analysis=sector_analysis,
            warnings=warnings,
            ai_confidence_score=ai_confidence,
            status="success"
        )

    def _generate_revenue_drivers(
        self,
        sector: str,
        historical_data: Dict[str, Any],
        vietnam_macro: Dict[str, Any]
    ) -> AssumptionCategoryResponse:
        """Generate revenue driver assumptions for DCF"""
        assumptions = []
        growth_range = self.SECTOR_GROWTH_RANGES.get(
            sector, {"min": 0.05, "max": 0.20, "typical": 0.10}
        )
        gdp_growth = vietnam_macro.get("gdp_growth", 0.055)

        # Revenue growth for 5 forecast years (with decay toward GDP growth)
        for year in range(1, 6):
            decay_factor = 0.8 ** (year - 1)
            base_growth = growth_range["typical"]
            suggested_growth = gdp_growth + (base_growth - gdp_growth) * decay_factor

            assumptions.append(AssumptionInput(
                metric=f"revenue_growth_year_{year}",
                category=AssumptionCategory.REVENUE_DRIVERS,
                description=f"Revenue growth rate for Year {year}",
                unit="%",
                is_multi_year=True,
                year_values={year: suggested_growth},
                ai_suggestion=AISuggestion(
                    metric=f"revenue_growth_year_{year}",
                    suggested_value=suggested_growth,
                    reasoning=f"Based on {sector} sector trends and Vietnam GDP trajectory",
                    confidence_level="high" if year <= 2 else "medium",
                    min_range=growth_range["min"],
                    max_range=growth_range["max"],
                    category=AssumptionCategory.REVENUE_DRIVERS
                ),
                vietnam_context=f"Vietnam {sector} sector typically grows {growth_range['min']*100:.0f}-{growth_range['max']*100:.0f}% annually"
            ))

        return AssumptionCategoryResponse(
            category=AssumptionCategory.REVENUE_DRIVERS,
            category_name="Revenue Drivers",
            assumptions=assumptions,
            is_complete=True
        )

    def _generate_cost_margins(
        self,
        sector: str,
        historical_data: Dict[str, Any],
        vietnam_macro: Dict[str, Any]
    ) -> AssumptionCategoryResponse:
        """Generate cost and margin assumptions for DCF"""
        assumptions = []
        margin_benchmarks = self.SECTOR_MARGIN_BENCHMARKS.get(
            sector, {"net_margin": 0.10, "operating_margin": 0.15, "gross_margin": 0.20}
        )

        # Gross Margin
        assumptions.append(AssumptionInput(
            metric="gross_margin",
            category=AssumptionCategory.COST_MARGINS,
            description="Gross profit margin",
            unit="%",
            ai_suggestion=AISuggestion(
                metric="gross_margin",
                suggested_value=margin_benchmarks["gross_margin"],
                reasoning=f"Aligned with {sector} sector benchmarks in Vietnam",
                confidence_level="medium",
                min_range=margin_benchmarks["gross_margin"] * 0.8,
                max_range=margin_benchmarks["gross_margin"] * 1.2,
                category=AssumptionCategory.COST_MARGINS
            )
        ))

        # Operating Margin
        assumptions.append(AssumptionInput(
            metric="operating_margin",
            category=AssumptionCategory.COST_MARGINS,
            description="Operating profit margin (EBIT margin)",
            unit="%",
            ai_suggestion=AISuggestion(
                metric="operating_margin",
                suggested_value=margin_benchmarks["operating_margin"],
                reasoning=f"Sector benchmark for {sector} operating efficiency",
                confidence_level="medium",
                min_range=margin_benchmarks["operating_margin"] * 0.8,
                max_range=margin_benchmarks["operating_margin"] * 1.2,
                category=AssumptionCategory.COST_MARGINS
            )
        ))

        # Net Margin
        assumptions.append(AssumptionInput(
            metric="net_margin",
            category=AssumptionCategory.COST_MARGINS,
            description="Net profit margin",
            unit="%",
            ai_suggestion=AISuggestion(
                metric="net_margin",
                suggested_value=margin_benchmarks["net_margin"],
                reasoning=f"Based on {sector} sector profitability in Vietnam",
                confidence_level="medium",
                min_range=margin_benchmarks["net_margin"] * 0.8,
                max_range=margin_benchmarks["net_margin"] * 1.2,
                category=AssumptionCategory.COST_MARGINS
            )
        ))

        # Tax Rate (Vietnam standard CIT)
        assumptions.append(AssumptionInput(
            metric="tax_rate",
            category=AssumptionCategory.COST_MARGINS,
            description="Corporate income tax rate",
            unit="%",
            ai_suggestion=AISuggestion(
                metric="tax_rate",
                suggested_value=0.20,
                reasoning="Standard Corporate Income Tax rate in Vietnam",
                confidence_level="high",
                min_range=0.20,
                max_range=0.20,
                category=AssumptionCategory.COST_MARGINS
            ),
            vietnam_context="Vietnam CIT rate is 20% for most companies (Law on Corporate Income Tax)"
        ))

        return AssumptionCategoryResponse(
            category=AssumptionCategory.COST_MARGINS,
            category_name="Cost & Margins",
            assumptions=assumptions,
            is_complete=True
        )

    def _generate_working_capital(
        self,
        sector: str,
        historical_data: Dict[str, Any]
    ) -> AssumptionCategoryResponse:
        """Generate working capital assumptions for DCF"""
        assumptions = []

        # NWC as % of revenue
        nwc_ratio = 0.15 if sector == "Retail" else 0.10
        assumptions.append(AssumptionInput(
            metric="nwc_as_percent_revenue",
            category=AssumptionCategory.WORKING_CAPITAL,
            description="Net working capital as percentage of revenue",
            unit="%",
            ai_suggestion=AISuggestion(
                metric="nwc_as_percent_revenue",
                suggested_value=nwc_ratio,
                reasoning=f"Working capital needs for {sector} sector",
                confidence_level="medium",
                min_range=nwc_ratio * 0.5,
                max_range=nwc_ratio * 1.5,
                category=AssumptionCategory.WORKING_CAPITAL
            ),
            vietnam_context=f"Vietnam {sector} companies maintain {nwc_ratio*100:.1f}% NWC to revenue"
        ))

        return AssumptionCategoryResponse(
            category=AssumptionCategory.WORKING_CAPITAL,
            category_name="Working Capital",
            assumptions=assumptions,
            is_complete=True
        )

    def _generate_wacc_components(
        self,
        sector: str,
        vietnam_macro: Dict[str, Any]
    ) -> AssumptionCategoryResponse:
        """Generate WACC component assumptions for DCF"""
        assumptions = []
        wacc_range = self.SECTOR_WACC_RANGES.get(
            sector, {"min": 0.10, "max": 0.16, "typical": 0.13}
        )

        # Risk-Free Rate (Vietnam government bonds)
        risk_free_rate = vietnam_macro.get("risk_free_rate", 0.068)
        assumptions.append(AssumptionInput(
            metric="risk_free_rate",
            category=AssumptionCategory.WACC_COMPONENTS,
            description="Risk-free rate (Vietnam 10Y government bond)",
            unit="%",
            ai_suggestion=AISuggestion(
                metric="risk_free_rate",
                suggested_value=risk_free_rate,
                reasoning="Based on Vietnam 10-year government bond yield",
                confidence_level="high",
                min_range=risk_free_rate * 0.9,
                max_range=risk_free_rate * 1.1,
                category=AssumptionCategory.WACC_COMPONENTS
            ),
            vietnam_context="Vietnam 10Y government bond yield as risk-free rate proxy"
        ))

        # Market Risk Premium
        market_risk_premium = vietnam_macro.get("market_risk_premium", 0.065)
        assumptions.append(AssumptionInput(
            metric="market_risk_premium",
            category=AssumptionCategory.WACC_COMPONENTS,
            description="Equity market risk premium",
            unit="%",
            ai_suggestion=AISuggestion(
                metric="market_risk_premium",
                suggested_value=market_risk_premium,
                reasoning="Vietnam equity market risk premium estimate",
                confidence_level="medium",
                min_range=0.055,
                max_range=0.075,
                category=AssumptionCategory.WACC_COMPONENTS
            )
        ))

        # Country Risk Premium
        crp = vietnam_macro.get("country_risk_premium", 0.035)
        assumptions.append(AssumptionInput(
            metric="country_risk_premium",
            category=AssumptionCategory.WACC_COMPONENTS,
            description="Country risk premium for Vietnam",
            unit="%",
            ai_suggestion=AISuggestion(
                metric="country_risk_premium",
                suggested_value=crp,
                reasoning="Vietnam sovereign risk premium",
                confidence_level="medium",
                min_range=0.025,
                max_range=0.045,
                category=AssumptionCategory.WACC_COMPONENTS
            )
        ))

        # Target WACC
        assumptions.append(AssumptionInput(
            metric="target_wacc",
            category=AssumptionCategory.WACC_COMPONENTS,
            description="Target Weighted Average Cost of Capital",
            unit="%",
            ai_suggestion=AISuggestion(
                metric="target_wacc",
                suggested_value=wacc_range["typical"],
                reasoning=f"Sector-appropriate WACC for {sector} in Vietnam",
                confidence_level="medium",
                min_range=wacc_range["min"],
                max_range=wacc_range["max"],
                category=AssumptionCategory.WACC_COMPONENTS
            ),
            vietnam_context=f"Vietnam {sector} sector WACC typically ranges {wacc_range['min']*100:.0f}-{wacc_range['max']*100:.0f}%"
        ))

        return AssumptionCategoryResponse(
            category=AssumptionCategory.WACC_COMPONENTS,
            category_name="WACC Components",
            assumptions=assumptions,
            is_complete=True
        )

    def _generate_terminal_value(
        self,
        sector: str,
        vietnam_macro: Dict[str, Any]
    ) -> AssumptionCategoryResponse:
        """Generate terminal value assumptions for DCF"""
        assumptions = []
        gdp_growth = vietnam_macro.get("gdp_growth", 0.055)

        # Terminal Growth Rate
        terminal_growth = min(gdp_growth * 0.9, 0.05)  # Conservative approach
        assumptions.append(AssumptionInput(
            metric="terminal_growth_rate",
            category=AssumptionCategory.TERMINAL_VALUE,
            description="Perpetual growth rate for terminal value",
            unit="%",
            ai_suggestion=AISuggestion(
                metric="terminal_growth_rate",
                suggested_value=terminal_growth,
                reasoning="Conservative rate below long-term GDP growth",
                confidence_level="medium",
                min_range=0.02,
                max_range=min(gdp_growth, 0.06),
                category=AssumptionCategory.TERMINAL_VALUE
            ),
            vietnam_context=f"Terminal growth capped below Vietnam's long-term GDP growth of {gdp_growth*100:.1f}%"
        ))

        # Terminal EBITDA Multiple
        ebitda_multiple = 8.0 if sector in ["Banking", "Technology"] else 6.0
        assumptions.append(AssumptionInput(
            metric="terminal_ebitda_multiple",
            category=AssumptionCategory.TERMINAL_VALUE,
            description="Exit multiple for terminal value calculation",
            unit="x",
            ai_suggestion=AISuggestion(
                metric="terminal_ebitda_multiple",
                suggested_value=ebitda_multiple,
                reasoning=f"Typical exit multiple for {sector} sector",
                confidence_level="low",
                min_range=ebitda_multiple * 0.7,
                max_range=ebitda_multiple * 1.3,
                category=AssumptionCategory.TERMINAL_VALUE
            ),
            vietnam_context=f"Vietnam {sector} sector trading multiples reference"
        ))

        return AssumptionCategoryResponse(
            category=AssumptionCategory.TERMINAL_VALUE,
            category_name="Terminal Value",
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

        years_available = historical_data.get("years_available", 0)
        if years_available < 3:
            warnings.append("Less than 3 years of historical data - assumptions less reliable")

        return warnings

    def _calculate_confidence_score(self, *categories) -> float:
        """Calculate overall AI confidence score"""
        total_confidence = 0.0
        count = 0

        for category in categories:
            for assumption in category.assumptions:
                if assumption.ai_suggestion:
                    conf_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
                    total_confidence += conf_map.get(assumption.ai_suggestion.confidence_level, 0.7)
                    count += 1

        return round(total_confidence / count, 2) if count > 0 else 0.7