"""
Vietnamese Step 8: AI Assumptions Processor
Generates forward-looking assumptions calibrated for Vietnamese market conditions
"""
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime


class vn_AIAssumptionsInput(BaseModel):
    """Input for Vietnamese AI assumptions generation"""
    session_id: str
    company_name: str
    ticker: str
    exchange: Literal["HOSE", "HNX", "UPCOM"]
    selected_model: Literal["dcf", "dupont", "comps"]
    sector: str
    industry: str

    # Historical data context
    historical_financials: Dict[str, Any]
    historical_ratios: Optional[Dict[str, float]] = None

    # Market context
    peer_data: Optional[List[Dict[str, Any]]] = None
    market_conditions: Optional[Dict[str, Any]] = None

    # Vietnam-specific macro inputs
    vietnam_macro: Dict[str, Any] = Field(
        default_factory=lambda: {
            "gdp_growth": 0.055,
            "inflation_target": 0.04,
            "risk_free_rate": 0.068,
            "country_risk_premium": 0.035
        }
    )

    # User constraints (optional overrides)
    user_constraints: Optional[Dict[str, Any]] = None

    # Metadata
    user_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class vn_AIAssumptionItem(BaseModel):
    """Single assumption with confidence and rationale"""
    parameter_name: str
    suggested_value: Any
    unit: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    rationale: str
    source: str
    vietnam_context: str
    min_reasonable: Optional[Any] = None
    max_reasonable: Optional[Any] = None


class vn_AIAssumptionsOutput(BaseModel):
    """Output with AI-generated assumptions for Vietnamese market"""
    session_id: str
    model_type: str
    assumptions: List[vn_AIAssumptionItem]
    sector_analysis: Dict[str, Any]
    macro_integration: Dict[str, Any]
    warnings: List[str]
    next_step: str = "step9_confirmation"
    status: str = "success"

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "vn-session-123",
                "model_type": "dcf",
                "assumptions": [
                    {
                        "parameter_name": "revenue_growth_year_1",
                        "suggested_value": 0.12,
                        "unit": "percentage",
                        "confidence_score": 0.75,
                        "rationale": "Based on 3-year CAGR and sector outlook",
                        "source": "historical_trend_analysis",
                        "vietnam_context": "Vietnam GDP growth ~5.5%, sector outperforming",
                        "min_reasonable": 0.05,
                        "max_reasonable": 0.20
                    }
                ],
                "sector_analysis": {
                    "sector": "Banking",
                    "vietnam_outlook": "Positive on credit growth",
                    "key_drivers": ["NIM expansion", "Fee income growth"]
                },
                "macro_integration": {
                    "gdp_growth_used": 0.055,
                    "inflation_adjustment": True,
                    "crp_applied": 0.035
                },
                "warnings": ["Limited peer data for UPCOM companies"],
                "status": "success"
            }
        }


class vn_Step8AssumptionsProcessor:
    """
    Processor for generating Vietnam-calibrated AI assumptions

    Generates forward-looking assumptions based on:
    - Historical financial performance
    - Vietnamese sector dynamics
    - Macroeconomic indicators
    - Peer benchmarking (when available)
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
        "Banking": {"net_margin": 0.25, "operating_margin": 0.35},
        "Real Estate": {"net_margin": 0.18, "operating_margin": 0.25},
        "Manufacturing": {"net_margin": 0.08, "operating_margin": 0.12},
        "Retail": {"net_margin": 0.05, "operating_margin": 0.08},
        "Technology": {"net_margin": 0.15, "operating_margin": 0.20},
        "Energy": {"net_margin": 0.12, "operating_margin": 0.18},
        "Consumer Goods": {"net_margin": 0.10, "operating_margin": 0.14},
        "Healthcare": {"net_margin": 0.15, "operating_margin": 0.20},
        "Telecommunications": {"net_margin": 0.20, "operating_margin": 0.30},
        "Materials": {"net_margin": 0.08, "operating_margin": 0.12}
    }

    async def process(self, input_data: VNAIAssumptionsInput) -> VNAIAssumptionsOutput:
        """
        Generate AI assumptions calibrated for Vietnamese market

        Args:
            input_data: Input with historical data and context

        Returns:
            VNAIAssumptionsOutput with suggested assumptions

        Note:
            In production, this would call actual AI/ML models.
            This implementation provides rule-based suggestions
            calibrated to Vietnamese market conditions.
        """
        assumptions = []
        warnings = []

        # Generate assumptions based on selected model
        if input_data.selected_model == "dcf":
            assumptions = self._generate_dcf_assumptions(input_data)
        elif input_data.selected_model == "dupont":
            assumptions = self._generate_dupont_assumptions(input_data)
        elif input_data.selected_model == "comps":
            assumptions = self._generate_comps_assumptions(input_data)

        # Build sector analysis
        sector_analysis = self._build_sector_analysis(
            input_data.sector,
            input_data.industry
        )

        # Integrate macro inputs
        macro_integration = {
            "gdp_growth_used": input_data.vietnam_macro.get("gdp_growth", 0.055),
            "inflation_target": input_data.vietnam_macro.get("inflation_target", 0.04),
            "risk_free_rate": input_data.vietnam_macro.get("risk_free_rate", 0.068),
            "country_risk_premium": input_data.vietnam_macro.get("country_risk_premium", 0.035),
            "inflation_adjustment": True,
            "crp_applied": input_data.vietnam_macro.get("country_risk_premium", 0.035)
        }

        # Add warnings for Vietnamese market specifics
        if input_data.exchange == "UPCOM":
            warnings.append("UPCOM companies may have limited disclosure and liquidity")
        if not input_data.peer_data or len(input_data.peer_data) < 3:
            warnings.append(f"Limited peer set for {input_data.sector} sector in Vietnam")
        if input_data.historical_financials.get("years_available", 0) < 3:
            warnings.append("Less than 3 years of historical data - assumptions less reliable")

        return VNAIAssumptionsOutput(
            session_id=input_data.session_id,
            model_type=input_data.selected_model,
            assumptions=assumptions,
            sector_analysis=sector_analysis,
            macro_integration=macro_integration,
            warnings=warnings,
            next_step="step9_confirmation",
            status="success"
        )

    def _generate_dcf_assumptions(self, input_data: VNAIAssumptionsInput) -> List[VNAIAssumptionItem]:
        """Generate DCF-specific assumptions for Vietnamese companies"""
        assumptions = []
        sector = input_data.sector
        hist = input_data.historical_financials

        # Get sector benchmarks
        growth_range = self.SECTOR_GROWTH_RANGES.get(sector, {"min": 0.05, "max": 0.20, "typical": 0.10})
        margin_benchmarks = self.SECTOR_MARGIN_BENCHMARKS.get(sector, {"net_margin": 0.10, "operating_margin": 0.15})

        # Revenue growth assumptions (5-year projection)
        for year in range(1, 6):
            # Decay growth rate toward GDP growth over time
            base_growth = growth_range["typical"]
            decay_factor = 0.8 ** (year - 1)
            terminal_growth = input_data.vietnam_macro.get("gdp_growth", 0.055)
            suggested_growth = terminal_growth + (base_growth - terminal_growth) * decay_factor

            assumptions.append(VNAIAssumptionItem(
                parameter_name=f"revenue_growth_year_{year}",
                suggested_value=round(suggested_growth, 3),
                unit="percentage",
                confidence_score=0.75 * decay_factor + 0.20,
                rationale=f"Based on {sector} sector trends and Vietnam GDP growth trajectory",
                source="sector_benchmark_analysis",
                vietnam_context=f"Vietnam {sector} sector typically grows {growth_range['min']*100:.0f}-{growth_range['max']*100:.0f}% annually",
                min_reasonable=growth_range["min"],
                max_reasonable=growth_range["max"]
            ))

        # Operating margin assumptions
        assumptions.append(VNAIAssumptionItem(
            parameter_name="target_operating_margin",
            suggested_value=margin_benchmarks["operating_margin"],
            unit="percentage",
            confidence_score=0.70,
            rationale=f"Aligned with {sector} sector benchmarks in Vietnam",
            source="sector_margin_analysis",
            vietnam_context=f"Vietnam {sector} companies average {margin_benchmarks['operating_margin']*100:.1f}% operating margin",
            min_reasonable=margin_benchmarks["operating_margin"] * 0.7,
            max_reasonable=margin_benchmarks["operating_margin"] * 1.3
        ))

        # Tax rate (Vietnam standard CIT)
        assumptions.append(VNAIAssumptionItem(
            parameter_name="tax_rate",
            suggested_value=0.20,
            unit="percentage",
            confidence_score=0.95,
            rationale="Standard Corporate Income Tax rate in Vietnam",
            source="vietnam_tax_code",
            vietnam_context="Vietnam CIT rate is 20% for most companies (Law on Corporate Income Tax)",
            min_reasonable=0.20,
            max_reasonable=0.20
        ))

        # Terminal growth rate
        gdp_growth = input_data.vietnam_macro.get("gdp_growth", 0.055)
        assumptions.append(VNAIAssumptionItem(
            parameter_name="terminal_growth_rate",
            suggested_value=gdp_growth,
            unit="percentage",
            confidence_score=0.80,
            rationale="Terminal growth aligned with long-term Vietnam GDP growth",
            source="macroeconomic_projection",
            vietnam_context=f"Vietnam long-term GDP growth estimated at {gdp_growth*100:.1f}%",
            min_reasonable=0.03,
            max_reasonable=min(gdp_growth * 1.2, 0.07)
        ))

        # Capex as % of revenue
        capex_ratio = 0.05 if sector in ["Technology", "Services"] else 0.08
        assumptions.append(VNAIAssumptionItem(
            parameter_name="capex_as_percent_revenue",
            suggested_value=capex_ratio,
            unit="percentage",
            confidence_score=0.65,
            rationale=f"Typical capex intensity for {sector} in Vietnam",
            source="sector_capex_analysis",
            vietnam_context=f"Vietnam {sector} companies typically invest {capex_ratio*100:.1f}% of revenue in capex",
            min_reasonable=capex_ratio * 0.5,
            max_reasonable=capex_ratio * 1.5
        ))

        # NWC as % of revenue
        nwc_ratio = 0.15 if sector == "Retail" else 0.10
        assumptions.append(VNAIAssumptionItem(
            parameter_name="nwc_as_percent_revenue",
            suggested_value=nwc_ratio,
            unit="percentage",
            confidence_score=0.60,
            rationale=f"Working capital needs for {sector} sector",
            source="sector_working_capital_analysis",
            vietnam_context=f"Vietnam {sector} companies maintain {nwc_ratio*100:.1f}% NWC to revenue",
            min_reasonable=nwc_ratio * 0.5,
            max_reasonable=nwc_ratio * 1.5
        ))

        return assumptions

    def _generate_dupont_assumptions(self, input_data: VNAIAssumptionsInput) -> List[VNAIAssumptionItem]:
        """Generate DuPont-specific assumptions"""
        assumptions = []
        sector = input_data.sector

        # For DuPont, we focus on current period analysis rather than projections
        margin_benchmarks = self.SECTOR_MARGIN_BENCHMARKS.get(sector, {"net_margin": 0.10})

        assumptions.append(VNAIAssumptionItem(
            parameter_name="target_net_margin",
            suggested_value=margin_benchmarks["net_margin"],
            unit="percentage",
            confidence_score=0.75,
            rationale=f"Sector benchmark for {sector} in Vietnam",
            source="sector_analysis",
            vietnam_context=f"Vietnam {sector} sector averages {margin_benchmarks['net_margin']*100:.1f}% net margin",
            min_reasonable=margin_benchmarks["net_margin"] * 0.7,
            max_reasonable=margin_benchmarks["net_margin"] * 1.3
        ))

        return assumptions

    def _generate_comps_assumptions(self, input_data: VNAIAssumptionsInput) -> List[VNAIAssumptionItem]:
        """Generate Comps-specific assumptions"""
        assumptions = []

        # Suggest number of peers
        assumptions.append(VNAIAssumptionItem(
            parameter_name="num_peers_final",
            suggested_value=5,
            unit="count",
            confidence_score=0.70,
            rationale="Optimal balance between representativeness and comparability",
            source="valuation_best_practices",
            vietnam_context="Vietnam market often has limited pure-play peers; 3-5 peers recommended",
            min_reasonable=3,
            max_reasonable=10
        ))

        # Liquidity filter
        assumptions.append(VNAIAssumptionItem(
            parameter_name="liquidity_filter_days",
            suggested_value=60,
            unit="trading_days",
            confidence_score=0.85,
            rationale="60-day average volume filter appropriate for Vietnam market",
            source="vietnam_market_standards",
            vietnam_context="60-day liquidity filter ensures adequate trading activity on HOSE/HNX/UPCOM",
            min_reasonable=30,
            max_reasonable=120
        ))

        return assumptions

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