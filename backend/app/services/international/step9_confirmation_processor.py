"""Step 9: Confirmation Processor - International Market

This module consolidates all inputs from Steps 6-8 and processes user confirmations/overrides
before passing to Step 10 for final valuation.

Workflow:
- Step 6: Aggregated historical financials and market data
- Step 7: Gap-filled historical data and AI web search results  
- Step 8: Manual overrides and AI suggestions for assumptions
- Step 9 (this): Confirmation processing - consolidates all inputs, validates, prepares for Step 10
- Step 10: Final valuation using ONLY Step 9 outputs (no direct access to earlier steps)

Input: Step 6 data + Step 7 data + Step 8 final inputs (including manual overrides)
Output: Confirmed and validated inputs ready for Step 10 valuation engines
"""
import logging
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ValuationModel(str, Enum):
    """Type of valuation model"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"


class ParameterSource(str, Enum):
    """Source of a confirmed parameter"""
    AI_SUGGESTION = "ai_suggestion"
    MANUAL_OVERRIDE = "manual_override"
    HISTORICAL_DATA = "historical_data"
    MARKET_DEFAULT = "market_default"


class ConfirmedParameter(BaseModel):
    """Single confirmed parameter with source tracking"""
    parameter_name: str
    final_value: Any
    unit: str
    source: ParameterSource
    original_ai_value: Optional[Any] = None
    override_reason: Optional[str] = None
    confidence_score: Optional[float] = None
    validation_status: str = "valid"  # valid, warning, error
    validation_message: Optional[str] = None


class ConfirmationCategory(BaseModel):
    """Category of confirmed parameters"""
    category_name: str
    parameters: List[ConfirmedParameter]
    category_status: str = "complete"  # complete, incomplete, warning


class ModelSpecificInputs(BaseModel):
    """Model-specific consolidated inputs for Step 10"""
    # Common fields
    ticker: str
    valuation_model: str
    
    # DCF-specific
    revenue_projections: Optional[List[Dict[str, Any]]] = None
    operating_margin_projections: Optional[List[Dict[str, Any]]] = None
    tax_rate: Optional[float] = None
    capex_percent_revenue: Optional[float] = None
    nwc_percent_revenue: Optional[float] = None
    terminal_growth_rate: Optional[float] = None
    wacc: Optional[float] = None
    risk_free_rate: Optional[float] = None
    market_risk_premium: Optional[float] = None
    beta: Optional[float] = None
    cost_of_debt: Optional[float] = None
    debt_to_equity: Optional[float] = None
    
    # DuPont-specific
    target_net_margin: Optional[float] = None
    target_asset_turnover: Optional[float] = None
    target_equity_multiplier: Optional[float] = None
    
    # Comps-specific
    peer_multiples: Optional[Dict[str, float]] = None
    outlier_threshold: Optional[float] = None
    selected_peers: Optional[List[str]] = None
    
    # Market data
    current_price: Optional[float] = None
    shares_outstanding: Optional[float] = None
    net_debt: Optional[float] = None


class MarketContext(BaseModel):
    """Market context for valuation"""
    market: str = "international"
    currency: str = "USD"
    sector: Optional[str] = None
    industry: Optional[str] = None
    risk_free_rate: Optional[float] = None
    country_risk_premium: Optional[float] = None
    market_risk_premium: Optional[float] = None
    corporate_tax_rate: Optional[float] = None


class Step9ConfirmationOutput(BaseModel):
    """
    Step 9 Output: Consolidated and confirmed inputs for Step 10
    
    This is the SOLE output that Step 10 can access. Step 10 cannot
    directly access Step 6, 7, or 8 data - only what's provided here.
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: ValuationModel
    market: str = "international"
    
    # All confirmed parameters organized by category
    confirmed_parameters: List[ConfirmedParameter]
    categories: List[ConfirmationCategory]
    
    # Model-specific consolidated inputs (ready for Step 10 engines)
    model_specific_inputs: ModelSpecificInputs
    
    # Market context
    market_context: MarketContext
    
    # Historical data summary (from Step 6/7, consolidated for Step 10)
    historical_financials_summary: Dict[str, Any]
    
    # Validation
    validation_status: str = "passed"  # passed, warning, failed
    warnings: List[str] = []
    errors: List[str] = []
    
    # Status flags
    ready_for_valuation: bool = True
    next_step: str = "step10_valuation"
    
    # Metadata
    step8_manual_overrides_applied: bool = False
    total_parameters_confirmed: int = 0
    parameters_from_ai: int = 0
    parameters_manually_overridden: int = 0


class Step9ConfirmationProcessor:
    """
    Step 9: Confirmation Processor
    
    Consolidates all inputs from Steps 6-8:
    1. Historical financials from Step 6
    2. Gap-filled data from Step 7
    3. AI suggestions and manual overrides from Step 8
    
    Validates completeness and prepares inputs exclusively for Step 10.
    Step 10 will ONLY receive data from this processor's output.
    """
    
    # International market defaults
    INTERNATIONAL_DEFAULTS = {
        "risk_free_rate": 0.045,  # 10Y US Treasury
        "market_risk_premium": 0.055,  # 5.5% equity risk premium
        "country_risk_premium": 0.0,  # No additional CRP for developed markets
        "corporate_tax_rate": 0.21,  # US federal rate
        "currency": "USD"
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
            "capex_percent_revenue",
            "nwc_percent_revenue",
            "terminal_growth_rate",
            "wacc"
        ],
        "dupont": [
            "target_net_margin",
            "target_asset_turnover",
            "target_equity_multiplier"
        ],
        "comps": [
            "peer_multiples",
            "outlier_threshold",
            "selected_peers"
        ]
    }
    
    def __init__(self):
        pass
    
    async def process_confirmation(
        self,
        session_id: str,
        ticker: str,
        valuation_model: str,
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]],
        step8_final_inputs: Dict[str, Any],
        market: str = "international"
    ) -> Step9ConfirmationOutput:
        """
        Main entry point for Step 9 confirmation processing.
        
        Args:
            session_id: User session identifier
            ticker: Stock ticker symbol
            valuation_model: DCF, DUPONT, or COMPS
            step6_data: Aggregated data from Step 6 (historical financials, market data)
            step7_data: Gap-filled data from Step 7 (optional, may be merged with step6)
            step8_final_inputs: Final inputs from Step 8 including manual overrides and AI suggestions
            market: Market type (international or vietnam)
            
        Returns:
            Step9ConfirmationOutput with all confirmed and validated inputs for Step 10
            
        Raises:
            ValueError: If critical parameters are missing
        """
        warnings = []
        errors = []
        confirmed_parameters = []
        categories = []
        
        # Parse Step 8 final inputs to extract confirmed values and overrides
        step8_overrides = step8_final_inputs.get('manual_overrides', {})
        step8_ai_suggestions = step8_final_inputs.get('ai_suggestions', {})
        step8_confirmed = step8_final_inputs.get('confirmed_values', {})
        
        # Process each model type
        model_enum = ValuationModel(valuation_model.upper())
        
        if model_enum == ValuationModel.DCF:
            confirmed_parameters, categories = await self._process_dcf_confirmation(
                ticker, step6_data, step7_data, step8_confirmed, step8_overrides, step8_ai_suggestions
            )
        elif model_enum == ValuationModel.DUPONT:
            confirmed_parameters, categories = await self._process_dupont_confirmation(
                ticker, step6_data, step7_data, step8_confirmed, step8_overrides, step8_ai_suggestions
            )
        elif model_enum == ValuationModel.COMPS:
            confirmed_parameters, categories = await self._process_comps_confirmation(
                ticker, step6_data, step7_data, step8_confirmed, step8_overrides, step8_ai_suggestions
            )
        
        # Build model-specific inputs for Step 10
        model_specific_inputs = self._build_model_specific_inputs(
            model_enum.value,
            confirmed_parameters,
            step6_data
        )
        
        # Build market context
        market_context = self._build_market_context(market, step6_data)
        
        # Extract historical financials summary from Step 6/7
        historical_summary = self._extract_historical_summary(step6_data, step7_data)
        
        # Validate required parameters
        validation_status, val_warnings, val_errors = self._validate_confirmation(
            model_enum.value,
            confirmed_parameters,
            model_specific_inputs
        )
        warnings.extend(val_warnings)
        errors.extend(val_errors)
        
        # Count parameter sources
        params_from_ai = sum(1 for p in confirmed_parameters if p.source == ParameterSource.AI_SUGGESTION)
        params_overridden = sum(1 for p in confirmed_parameters if p.source == ParameterSource.MANUAL_OVERRIDE)
        
        # Determine if ready for valuation
        ready_for_valuation = validation_status != "failed"
        next_step = "step10_valuation" if ready_for_valuation else "step8_assumptions"
        
        return Step9ConfirmationOutput(
            session_id=session_id,
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=model_enum,
            market=market,
            confirmed_parameters=confirmed_parameters,
            categories=categories,
            model_specific_inputs=model_specific_inputs,
            market_context=market_context,
            historical_financials_summary=historical_summary,
            validation_status=validation_status,
            warnings=warnings,
            errors=errors,
            ready_for_valuation=ready_for_valuation,
            next_step=next_step,
            step8_manual_overrides_applied=len(step8_overrides) > 0,
            total_parameters_confirmed=len(confirmed_parameters),
            parameters_from_ai=params_from_ai,
            parameters_manually_overridden=params_overridden
        )
    
    async def _process_dcf_confirmation(
        self,
        ticker: str,
        step6_data: Dict,
        step7_data: Optional[Dict],
        step8_confirmed: Dict,
        step8_overrides: Dict,
        step8_ai_suggestions: Dict
    ) -> tuple[List[ConfirmedParameter], List[ConfirmationCategory]]:
        """Process DCF-specific confirmation parameters"""
        confirmed_parameters = []
        categories = []
        
        # Revenue Growth Parameters (Years 1-5)
        revenue_params = []
        for year in range(1, 6):
            param_name = f"revenue_growth_year_{year}"
            final_value, source, original_ai, override_reason = self._resolve_parameter_value(
                param_name, step8_confirmed, step8_overrides, step8_ai_suggestions
            )
            
            if final_value is not None:
                revenue_params.append(ConfirmedParameter(
                    parameter_name=param_name,
                    final_value=final_value,
                    unit="percentage",
                    source=source,
                    original_ai_value=original_ai,
                    override_reason=override_reason
                ))
        
        if revenue_params:
            categories.append(ConfirmationCategory(
                category_name="Revenue Growth Projections",
                parameters=revenue_params,
                category_status="complete"
            ))
            confirmed_parameters.extend(revenue_params)
        
        # Margin Parameters
        margin_params = []
        for param_name in ["target_operating_margin", "tax_rate"]:
            final_value, source, original_ai, override_reason = self._resolve_parameter_value(
                param_name, step8_confirmed, step8_overrides, step8_ai_suggestions
            )
            if final_value is not None:
                margin_params.append(ConfirmedParameter(
                    parameter_name=param_name,
                    final_value=final_value,
                    unit="percentage",
                    source=source,
                    original_ai_value=original_ai,
                    override_reason=override_reason
                ))
        
        if margin_params:
            categories.append(ConfirmationCategory(
                category_name="Margins & Tax",
                parameters=margin_params,
                category_status="complete"
            ))
            confirmed_parameters.extend(margin_params)
        
        # Working Capital Parameters
        wc_params = []
        for param_name in ["capex_percent_revenue", "nwc_percent_revenue"]:
            final_value, source, original_ai, override_reason = self._resolve_parameter_value(
                param_name, step8_confirmed, step8_overrides, step8_ai_suggestions
            )
            if final_value is not None:
                wc_params.append(ConfirmedParameter(
                    parameter_name=param_name,
                    final_value=final_value,
                    unit="percentage",
                    source=source,
                    original_ai_value=original_ai,
                    override_reason=override_reason
                ))
        
        if wc_params:
            categories.append(ConfirmationCategory(
                category_name="Working Capital & CapEx",
                parameters=wc_params,
                category_status="complete"
            ))
            confirmed_parameters.extend(wc_params)
        
        # Terminal Value Parameters
        tv_params = []
        final_value, source, original_ai, override_reason = self._resolve_parameter_value(
            "terminal_growth_rate", step8_confirmed, step8_overrides, step8_ai_suggestions
        )
        if final_value is not None:
            tv_params.append(ConfirmedParameter(
                parameter_name="terminal_growth_rate",
                final_value=final_value,
                unit="percentage",
                source=source,
                original_ai_value=original_ai,
                override_reason=override_reason
            ))
        
        if tv_params:
            categories.append(ConfirmationCategory(
                category_name="Terminal Value",
                parameters=tv_params,
                category_status="complete"
            ))
            confirmed_parameters.extend(tv_params)
        
        # WACC Components
        wacc_params = []
        for param_name in ["wacc", "risk_free_rate", "market_risk_premium", "beta", "cost_of_debt", "debt_to_equity"]:
            final_value, source, original_ai, override_reason = self._resolve_parameter_value(
                param_name, step8_confirmed, step8_overrides, step8_ai_suggestions
            )
            if final_value is not None:
                wacc_params.append(ConfirmedParameter(
                    parameter_name=param_name,
                    final_value=final_value,
                    unit="percentage" if param_name != "beta" and param_name != "debt_to_equity" else "ratio",
                    source=source,
                    original_ai_value=original_ai,
                    override_reason=override_reason
                ))
        
        if wacc_params:
            categories.append(ConfirmationCategory(
                category_name="WACC Components",
                parameters=wacc_params,
                category_status="complete"
            ))
            confirmed_parameters.extend(wacc_params)
        
        return confirmed_parameters, categories
    
    async def _process_dupont_confirmation(
        self,
        ticker: str,
        step6_data: Dict,
        step7_data: Optional[Dict],
        step8_confirmed: Dict,
        step8_overrides: Dict,
        step8_ai_suggestions: Dict
    ) -> tuple[List[ConfirmedParameter], List[ConfirmationCategory]]:
        """Process DuPont-specific confirmation parameters"""
        confirmed_parameters = []
        categories = []
        
        # DuPont ROE Components
        dupont_params = []
        for param_name in ["target_net_margin", "target_asset_turnover", "target_equity_multiplier"]:
            final_value, source, original_ai, override_reason = self._resolve_parameter_value(
                param_name, step8_confirmed, step8_overrides, step8_ai_suggestions
            )
            if final_value is not None:
                dupont_params.append(ConfirmedParameter(
                    parameter_name=param_name,
                    final_value=final_value,
                    unit="percentage" if param_name == "target_net_margin" else "ratio",
                    source=source,
                    original_ai_value=original_ai,
                    override_reason=override_reason
                ))
        
        if dupont_params:
            categories.append(ConfirmationCategory(
                category_name="DuPont ROE Components",
                parameters=dupont_params,
                category_status="complete"
            ))
            confirmed_parameters.extend(dupont_params)
        
        return confirmed_parameters, categories
    
    async def _process_comps_confirmation(
        self,
        ticker: str,
        step6_data: Dict,
        step7_data: Optional[Dict],
        step8_confirmed: Dict,
        step8_overrides: Dict,
        step8_ai_suggestions: Dict
    ) -> tuple[List[ConfirmedParameter], List[ConfirmationCategory]]:
        """Process Comps-specific confirmation parameters"""
        confirmed_parameters = []
        categories = []
        
        # Peer Multiples
        multiples_params = []
        for param_name in ["peer_ev_ebitda", "peer_pe", "peer_pb", "peer_ps"]:
            final_value, source, original_ai, override_reason = self._resolve_parameter_value(
                param_name, step8_confirmed, step8_overrides, step8_ai_suggestions
            )
            if final_value is not None:
                multiples_params.append(ConfirmedParameter(
                    parameter_name=param_name,
                    final_value=final_value,
                    unit="multiple",
                    source=source,
                    original_ai_value=original_ai,
                    override_reason=override_reason
                ))
        
        if multiples_params:
            categories.append(ConfirmationCategory(
                category_name="Peer Multiples",
                parameters=multiples_params,
                category_status="complete"
            ))
            confirmed_parameters.extend(multiples_params)
        
        # Selection Criteria
        selection_params = []
        final_value, source, original_ai, override_reason = self._resolve_parameter_value(
            "outlier_threshold", step8_confirmed, step8_overrides, step8_ai_suggestions
        )
        if final_value is not None:
            selection_params.append(ConfirmedParameter(
                parameter_name="outlier_threshold",
                final_value=final_value,
                unit="standard_deviations",
                source=source,
                original_ai_value=original_ai,
                override_reason=override_reason
            ))
        
        selected_peers = step8_confirmed.get("selected_peers")
        if selected_peers:
            selection_params.append(ConfirmedParameter(
                parameter_name="selected_peers",
                final_value=selected_peers,
                unit="list",
                source=ParameterSource.MANUAL_OVERRIDE if step8_overrides.get("selected_peers") else ParameterSource.AI_SUGGESTION,
                original_ai_value=step8_ai_suggestions.get("selected_peers"),
                override_reason="User modified peer selection" if step8_overrides.get("selected_peers") else None
            ))
        
        if selection_params:
            categories.append(ConfirmationCategory(
                category_name="Peer Selection Criteria",
                parameters=selection_params,
                category_status="complete"
            ))
            confirmed_parameters.extend(selection_params)
        
        return confirmed_parameters, categories
    
    def _resolve_parameter_value(
        self,
        param_name: str,
        step8_confirmed: Dict,
        step8_overrides: Dict,
        step8_ai_suggestions: Dict
    ) -> tuple[Any, ParameterSource, Optional[Any], Optional[str]]:
        """
        Resolve the final value for a parameter based on source priority:
        1. Manual override (highest priority)
        2. Confirmed value from Step 8
        3. AI suggestion
        4. Default (if applicable)
        
        Returns:
            Tuple of (final_value, source, original_ai_value, override_reason)
        """
        original_ai = step8_ai_suggestions.get(param_name)
        override_value = step8_overrides.get(param_name)
        confirmed_value = step8_confirmed.get(param_name)
        
        if override_value is not None:
            return override_value, ParameterSource.MANUAL_OVERRIDE, original_ai, f"User overridden from {original_ai} to {override_value}"
        elif confirmed_value is not None:
            return confirmed_value, ParameterSource.AI_SUGGESTION, original_ai, None
        elif original_ai is not None:
            return original_ai, ParameterSource.AI_SUGGESTION, original_ai, None
        else:
            return None, ParameterSource.MARKET_DEFAULT, None, None
    
    def _build_model_specific_inputs(
        self,
        model_type: str,
        confirmed_parameters: List[ConfirmedParameter],
        step6_data: Dict
    ) -> ModelSpecificInputs:
        """Build model-specific inputs dictionary for Step 10 engines"""
        
        # Convert confirmed parameters to dict
        params_dict = {cp.parameter_name: cp.final_value for cp in confirmed_parameters}
        
        # Get market data from Step 6
        market_data = step6_data.get('market_data', {})
        
        base_inputs = ModelSpecificInputs(
            ticker=step6_data.get('ticker', ''),
            valuation_model=model_type,
            current_price=market_data.get('current_price'),
            shares_outstanding=market_data.get('shares_outstanding'),
            net_debt=market_data.get('net_debt')
        )
        
        if model_type == "DCF":
            # Build revenue projections
            latest_revenue = step6_data.get('historical_financials', {}).get('revenue', [])
            revenue_projections = []
            if latest_revenue:
                base_revenue = latest_revenue[-1] if latest_revenue[-1] != 0 else latest_revenue[0]
                for year in range(1, 6):
                    growth_rate = params_dict.get(f"revenue_growth_year_{year}", 0.05)
                    if year == 1:
                        projected = base_revenue * (1 + growth_rate)
                    else:
                        projected = revenue_projections[-1]["projected_revenue"] * (1 + growth_rate)
                    revenue_projections.append({
                        "year": year,
                        "growth_rate": growth_rate,
                        "projected_revenue": projected
                    })
            
            base_inputs.revenue_projections = revenue_projections
            base_inputs.tax_rate = params_dict.get("tax_rate", self.INTERNATIONAL_DEFAULTS["corporate_tax_rate"])
            base_inputs.capex_percent_revenue = params_dict.get("capex_percent_revenue", 0.05)
            base_inputs.nwc_percent_revenue = params_dict.get("nwc_percent_revenue", 0.10)
            base_inputs.terminal_growth_rate = params_dict.get("terminal_growth_rate", 0.025)
            base_inputs.wacc = params_dict.get("wacc", 0.08)
            base_inputs.risk_free_rate = params_dict.get("risk_free_rate", self.INTERNATIONAL_DEFAULTS["risk_free_rate"])
            base_inputs.market_risk_premium = params_dict.get("market_risk_premium", self.INTERNATIONAL_DEFAULTS["market_risk_premium"])
            base_inputs.beta = params_dict.get("beta", 1.0)
            base_inputs.cost_of_debt = params_dict.get("cost_of_debt", 0.05)
            base_inputs.debt_to_equity = params_dict.get("debt_to_equity", 0.5)
            
        elif model_type == "DUPONT":
            base_inputs.target_net_margin = params_dict.get("target_net_margin", 0.10)
            base_inputs.target_asset_turnover = params_dict.get("target_asset_turnover", 1.0)
            base_inputs.target_equity_multiplier = params_dict.get("target_equity_multiplier", 2.0)
            
        elif model_type == "COMPS":
            base_inputs.peer_multiples = {
                "EV/EBITDA": params_dict.get("peer_ev_ebitda", 10.0),
                "P/E": params_dict.get("peer_pe", 15.0),
                "P/B": params_dict.get("peer_pb", 2.0),
                "P/S": params_dict.get("peer_ps", 3.0)
            }
            base_inputs.outlier_threshold = params_dict.get("outlier_threshold", 2.0)
            base_inputs.selected_peers = params_dict.get("selected_peers", [])
        
        return base_inputs
    
    def _build_market_context(self, market: str, step6_data: Dict) -> MarketContext:
        """Build market context from Step 6 data and defaults"""
        market_data = step6_data.get('market_data', {})
        
        return MarketContext(
            market=market,
            currency=self.INTERNATIONAL_DEFAULTS["currency"],
            sector=step6_data.get('sector'),
            industry=step6_data.get('industry'),
            risk_free_rate=market_data.get('risk_free_rate', self.INTERNATIONAL_DEFAULTS["risk_free_rate"]),
            country_risk_premium=market_data.get('country_risk_premium', self.INTERNATIONAL_DEFAULTS["country_risk_premium"]),
            market_risk_premium=market_data.get('market_risk_premium', self.INTERNATIONAL_DEFAULTS["market_risk_premium"]),
            corporate_tax_rate=market_data.get('corporate_tax_rate', self.INTERNATIONAL_DEFAULTS["corporate_tax_rate"])
        )
    
    def _extract_historical_summary(self, step6_data: Dict, step7_data: Optional[Dict]) -> Dict[str, Any]:
        """Extract key historical financials summary from Step 6/7 data"""
        historical = step6_data.get('historical_financials', {})
        
        # Get latest year data (last non-zero value)
        def get_latest(series):
            if not series:
                return 0
            for val in reversed(series):
                if val != 0:
                    return val
            return series[0] if series else 0
        
        return {
            "latest_revenue": get_latest(historical.get('revenue', [])),
            "latest_ebitda": get_latest(historical.get('ebitda', [])),
            "latest_operating_income": get_latest(historical.get('operating_income', [])),
            "latest_net_income": get_latest(historical.get('net_income', [])),
            "latest_total_assets": get_latest(historical.get('total_assets', [])),
            "latest_shareholders_equity": get_latest(historical.get('shareholders_equity', [])),
            "latest_operating_cash_flow": get_latest(historical.get('operating_cash_flow', [])),
            "latest_capex": get_latest(historical.get('capex', []))
        }
    
    def _validate_confirmation(
        self,
        model_type: str,
        confirmed_parameters: List[ConfirmedParameter],
        model_specific_inputs: ModelSpecificInputs
    ) -> tuple[str, List[str], List[str]]:
        """
        Validate confirmed parameters for completeness.
        
        Returns:
            Tuple of (validation_status, warnings, errors)
        """
        warnings = []
        errors = []
        
        # Get confirmed parameter names
        confirmed_names = {p.parameter_name for p in confirmed_parameters}
        
        # Check required parameters for model type
        required_params = self.MODEL_REQUIRED_PARAMS.get(model_type, [])
        missing_required = [p for p in required_params if p not in confirmed_names]
        
        if missing_required:
            errors.append(f"Missing required parameters for {model_type}: {', '.join(missing_required)}")
            return "failed", warnings, errors
        
        # Add warnings for potentially problematic values
        for param in confirmed_parameters:
            if param.parameter_name == "terminal_growth_rate" and param.final_value > 0.05:
                warnings.append(f"Terminal growth rate ({param.final_value:.2%}) exceeds typical long-term GDP growth")
            if param.parameter_name == "wacc" and param.final_value < 0.04:
                warnings.append(f"WACC ({param.final_value:.2%}) seems low for most companies")
            if param.parameter_name == "tax_rate" and param.final_value < 0.15:
                warnings.append(f"Tax rate ({param.final_value:.2%}) is below standard corporate rates")
        
        validation_status = "warning" if warnings else "passed"
        return validation_status, warnings, errors
