"""
Vietnamese Step 9: Confirmation Processor
Final validation and consolidation before running valuation
"""
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class vn_ConfirmationInput(BaseModel):
    """Input for Vietnamese confirmation step"""
    session_id: str
    company_name: str
    ticker: str
    exchange: Literal["HOSE", "HNX", "UPCOM"]
    selected_model: Literal["dcf", "dupont", "comps"]

    # Historical data (from Step 7)
    historical_financials: Dict[str, Any]

    # AI Assumptions (from Step 8)
    ai_assumptions: Optional[List[Dict[str, Any]]] = None

    # User-confirmed/overridden parameters
    confirmed_parameters: Dict[str, Any]

    # Manual overrides (if any)
    manual_overrides: Optional[Dict[str, Any]] = None

    # Market context
    sector: str
    industry: str

    # Metadata
    user_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class vn_ConfirmedParameter(BaseModel):
    """Single confirmed parameter with source tracking"""
    parameter_name: str
    final_value: Any
    unit: str
    source: Literal["ai_suggestion", "manual_override", "historical_data", "market_default"]
    original_ai_value: Optional[Any] = None
    override_reason: Optional[str] = None
    confidence_score: Optional[float] = None
    vietnam_context: Optional[str] = None


class vn_ConfirmationOutput(BaseModel):
    """Output with all confirmed parameters ready for valuation"""
    session_id: str
    company_name: str
    ticker: str
    exchange: str
    selected_model: str
    confirmed_parameters: List[vn_ConfirmedParameter]
    model_specific_inputs: Dict[str, Any]
    market_context: Dict[str, Any]
    validation_status: str
    warnings: List[str]
    ready_for_valuation: bool
    next_step: str = "step10_valuation"
    status: str = "success"

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "vn-session-123",
                "company_name": "VinGroup Joint Stock Company",
                "ticker": "VIC",
                "exchange": "HOSE",
                "selected_model": "dcf",
                "confirmed_parameters": [
                    {
                        "parameter_name": "revenue_growth_year_1",
                        "final_value": 0.12,
                        "unit": "percentage",
                        "source": "ai_suggestion",
                        "original_ai_value": 0.12,
                        "confidence_score": 0.75,
                        "vietnam_context": "Vietnam real estate sector outlook positive"
                    }
                ],
                "model_specific_inputs": {
                    "revenue_projections": [...],
                    "operating_margin_projections": [...],
                    "tax_rate": 0.20,
                    "terminal_growth_rate": 0.055,
                    "wacc": 0.12
                },
                "market_context": {
                    "currency": "VND",
                    "risk_free_rate": 0.068,
                    "country_risk_premium": 0.035,
                    "corporate_tax_rate": 0.20
                },
                "validation_status": "passed",
                "warnings": [],
                "ready_for_valuation": True,
                "status": "success"
            }
        }


class vn_Step9ConfirmationProcessor:
    """
    Processor for final confirmation before Vietnamese valuation

    Consolidates:
    - Historical data from Step 7
    - AI assumptions from Step 8
    - User overrides
    - Market defaults

    Validates completeness and prepares inputs for valuation engine
    """

    # Vietnam market defaults
    VN_MARKET_DEFAULTS = {
        "risk_free_rate": 0.068,  # 10Y government bond
        "country_risk_premium": 0.035,  # 3.5% CRP
        "market_risk_premium": 0.075,  # 7.5% emerging market
        "corporate_tax_rate": 0.20,  # Standard CIT
        "inflation_target": 0.04,  # SBV target
        "gdp_growth": 0.055,  # Vietnam GDP growth estimate
        "currency": "VND",
        "currency_symbol": "₫"
    }

    # Model-specific required parameters
    MODEL_REQUIRED_PARAMS = {
        "dcf": [
            "revenue_growth_year_1",
            "revenue_growth_year_2",
            "revenue_growth_year_3",
            "revenue_growth_year_4",
            "revenue_growth_year_5",
            "target_operating_margin",
            "tax_rate",
            "capex_as_percent_revenue",
            "nwc_as_percent_revenue",
            "terminal_growth_rate",
            "risk_free_rate",
            "beta",
            "equity_risk_premium"
        ],
        "dupont": [
            "net_income",
            "shareholders_equity",
            "revenue",
            "total_assets",
            "financial_leverage"
        ],
        "comps": [
            "num_peers_final",
            "liquidity_filter_days",
            "target_multiples",
            "peer_selection_criteria"
        ]
    }

    async def process(self, input_data: VNConfirmationInput) -> VNConfirmationOutput:
        """
        Process confirmation for Vietnamese valuation

        Args:
            input_data: Input with all parameters to confirm

        Returns:
            VNConfirmationOutput with validated parameters

        Raises:
            ValueError: If required parameters are missing
        """
        warnings = []
        confirmed_parameters = []

        # Process AI assumptions vs manual overrides
        if input_data.ai_assumptions:
            for assumption in input_data.ai_assumptions:
                param_name = assumption.get("parameter_name")
                ai_value = assumption.get("suggested_value")

                # Check if user provided override
                override_value = None
                if input_data.manual_overrides and param_name in input_data.manual_overrides:
                    override_value = input_data.manual_overrides[param_name]

                # Determine final value and source
                if override_value is not None:
                    final_value = override_value
                    source = "manual_override"
                    override_reason = f"User overridden from {ai_value} to {override_value}"
                else:
                    final_value = ai_value
                    source = "ai_suggestion"
                    override_reason = None

                confirmed_parameters.append(VNConfirmedParameter(
                    parameter_name=param_name,
                    final_value=final_value,
                    unit=assumption.get("unit", "value"),
                    source=source,
                    original_ai_value=ai_value,
                    override_reason=override_reason,
                    confidence_score=assumption.get("confidence_score"),
                    vietnam_context=assumption.get("vietnam_context")
                ))

        # Add confirmed parameters from user input
        for param_name, param_value in input_data.confirmed_parameters.items():
            # Skip if already processed from AI assumptions
            if any(cp.parameter_name == param_name for cp in confirmed_parameters):
                continue

            confirmed_parameters.append(VNConfirmedParameter(
                parameter_name=param_name,
                final_value=param_value,
                unit="value",
                source="manual_override",
                original_ai_value=None,
                override_reason=None,
                confidence_score=None,
                vietnam_context=None
            ))

        # Add Vietnam market defaults where applicable
        vn_defaults_to_add = {
            "tax_rate": self.VN_MARKET_DEFAULTS["corporate_tax_rate"],
            "risk_free_rate": self.VN_MARKET_DEFAULTS["risk_free_rate"],
            "country_risk_premium": self.VN_MARKET_DEFAULTS["country_risk_premium"]
        }

        for param_name, default_value in vn_defaults_to_add.items():
            if not any(cp.parameter_name == param_name for cp in confirmed_parameters):
                confirmed_parameters.append(VNConfirmedParameter(
                    parameter_name=param_name,
                    final_value=default_value,
                    unit="percentage",
                    source="market_default",
                    original_ai_value=None,
                    override_reason=None,
                    confidence_score=0.95,
                    vietnam_context=f"Vietnam market default: {param_name.replace('_', ' ').title()}"
                ))

        # Validate required parameters for selected model
        required_params = self.MODEL_REQUIRED_PARAMS.get(input_data.selected_model, [])
        missing_params = []

        confirmed_param_names = {cp.parameter_name for cp in confirmed_parameters}
        for req_param in required_params:
            if req_param not in confirmed_param_names:
                # Check if it's in confirmed_parameters dict
                if req_param not in input_data.confirmed_parameters:
                    missing_params.append(req_param)

        if missing_params:
            warnings.append(f"Missing recommended parameters for {input_data.selected_model.upper()}: {', '.join(missing_params)}")

        # Build model-specific inputs
        model_specific_inputs = self._build_model_specific_inputs(
            input_data.selected_model,
            confirmed_parameters,
            input_data.historical_financials
        )

        # Build market context
        market_context = {
            "currency": self.VN_MARKET_DEFAULTS["currency"],
            "currency_symbol": self.VN_MARKET_DEFAULTS["currency_symbol"],
            "exchange": input_data.exchange,
            "sector": input_data.sector,
            "industry": input_data.industry,
            "risk_free_rate": self.VN_MARKET_DEFAULTS["risk_free_rate"],
            "country_risk_premium": self.VN_MARKET_DEFAULTS["country_risk_premium"],
            "market_risk_premium": self.VN_MARKET_DEFAULTS["market_risk_premium"],
            "corporate_tax_rate": self.VN_MARKET_DEFAULTS["corporate_tax_rate"],
            "gdp_growth": self.VN_MARKET_DEFAULTS["gdp_growth"],
            "inflation_target": self.VN_MARKET_DEFAULTS["inflation_target"]
        }

        # Determine validation status
        critical_missing = [p for p in missing_params if self._is_critical_parameter(p, input_data.selected_model)]
        if critical_missing:
            validation_status = "failed"
            ready_for_valuation = False
            warnings.insert(0, f"Critical parameters missing: {', '.join(critical_missing)}")
        elif missing_params:
            validation_status = "warning"
            ready_for_valuation = True
        else:
            validation_status = "passed"
            ready_for_valuation = True

        return VNConfirmationOutput(
            session_id=input_data.session_id,
            company_name=input_data.company_name,
            ticker=input_data.ticker,
            exchange=input_data.exchange,
            selected_model=input_data.selected_model,
            confirmed_parameters=confirmed_parameters,
            model_specific_inputs=model_specific_inputs,
            market_context=market_context,
            validation_status=validation_status,
            warnings=warnings,
            ready_for_valuation=ready_for_valuation,
            next_step="step10_valuation" if ready_for_valuation else "step8_assumptions",
            status="success" if validation_status != "failed" else "failed"
        )

    def _build_model_specific_inputs(
        self,
        model_type: str,
        confirmed_parameters: List[VNConfirmedParameter],
        historical_financials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build model-specific input dictionary for valuation engine"""

        # Convert confirmed parameters to dict
        params_dict = {cp.parameter_name: cp.final_value for cp in confirmed_parameters}

        if model_type == "dcf":
            return self._build_dcf_inputs(params_dict, historical_financials)
        elif model_type == "dupont":
            return self._build_dupont_inputs(params_dict, historical_financials)
        elif model_type == "comps":
            return self._build_comps_inputs(params_dict, historical_financials)

        return {}

    def _build_dcf_inputs(self, params: Dict[str, Any], historical: Dict[str, Any]) -> Dict[str, Any]:
        """Build DCF-specific inputs"""
        # Get latest revenue from historical data
        latest_revenue = historical.get("revenue", {}).get("latest", 0)

        # Build revenue projections
        revenue_projections = []
        for year in range(1, 6):
            growth_rate = params.get(f"revenue_growth_year_{year}", 0.05)
            if year == 1:
                projected_revenue = latest_revenue * (1 + growth_rate)
            else:
                prev_revenue = revenue_projections[-1]["projected_revenue"]
                projected_revenue = prev_revenue * (1 + growth_rate)

            revenue_projections.append({
                "year": year,
                "growth_rate": growth_rate,
                "projected_revenue": projected_revenue
            })

        # Calculate WACC components
        risk_free_rate = params.get("risk_free_rate", self.VN_MARKET_DEFAULTS["risk_free_rate"])
        beta = params.get("beta", 1.0)
        market_premium = params.get("market_risk_premium", self.VN_MARKET_DEFAULTS["market_risk_premium"])
        crp = params.get("country_risk_premium", self.VN_MARKET_DEFAULTS["country_risk_premium"])

        cost_of_equity = risk_free_rate + (beta * (market_premium + crp))

        return {
            "revenue_projections": revenue_projections,
            "operating_margin": params.get("target_operating_margin", 0.10),
            "tax_rate": params.get("tax_rate", self.VN_MARKET_DEFAULTS["corporate_tax_rate"]),
            "capex_percent_revenue": params.get("capex_as_percent_revenue", 0.05),
            "nwc_percent_revenue": params.get("nwc_as_percent_revenue", 0.10),
            "terminal_growth_rate": params.get("terminal_growth_rate", self.VN_MARKET_DEFAULTS["gdp_growth"]),
            "wacc": {
                "risk_free_rate": risk_free_rate,
                "beta": beta,
                "market_risk_premium": market_premium,
                "country_risk_premium": crp,
                "cost_of_equity": cost_of_equity,
                "cost_of_debt": params.get("cost_of_debt", 0.08),
                "debt_to_equity": params.get("debt_to_equity", 0.5),
                "wacc": cost_of_equity  # Simplified: assuming all equity for now
            },
            "latest_revenue": latest_revenue
        }

    def _build_dupont_inputs(self, params: Dict[str, Any], historical: Dict[str, Any]) -> Dict[str, Any]:
        """Build DuPont-specific inputs"""
        return {
            "net_income": historical.get("net_income", {}).get("latest", 0),
            "shareholders_equity": historical.get("shareholders_equity", {}).get("latest", 0),
            "revenue": historical.get("revenue", {}).get("latest", 0),
            "total_assets": historical.get("total_assets", {}).get("latest", 0),
            "financial_leverage": params.get("financial_leverage", historical.get("financial_leverage", 2.0))
        }

    def _build_comps_inputs(self, params: Dict[str, Any], historical: Dict[str, Any]) -> Dict[str, Any]:
        """Build Comps-specific inputs"""
        return {
            "num_peers_final": params.get("num_peers_final", 5),
            "liquidity_filter_days": params.get("liquidity_filter_days", 60),
            "target_multiples": params.get("target_multiples", ["P/E", "EV/EBITDA", "P/B"]),
            "peer_selection_criteria": {
                "sector": params.get("sector"),
                "market_cap_range": params.get("market_cap_range"),
                "geography": "Vietnam"
            },
            "target_metrics": {
                "revenue": historical.get("revenue", {}).get("latest", 0),
                "ebitda": historical.get("ebitda", {}).get("latest", 0),
                "net_income": historical.get("net_income", {}).get("latest", 0),
                "book_value": historical.get("shareholders_equity", {}).get("latest", 0)
            }
        }

    def _is_critical_parameter(self, param_name: str, model_type: str) -> bool:
        """Determine if a parameter is critical for valuation"""
        critical_params = {
            "dcf": ["terminal_growth_rate", "wacc", "tax_rate"],
            "dupont": ["net_income", "shareholders_equity", "revenue"],
            "comps": ["num_peers_final", "target_multiples"]
        }

        return param_name in critical_params.get(model_type, [])