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

# Lazy import to avoid circular dependencies
_dcf_engine = None
_dcf_inputs_cls = None

def _get_dcf_engine():
    global _dcf_engine, _dcf_inputs_cls
    if _dcf_engine is None:
        from app.services.international.dcf_engine import DCFEngine, DCFInputs
        _dcf_engine = DCFEngine
        _dcf_inputs_cls = DCFInputs
    return _dcf_engine, _dcf_inputs_cls
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
    
    # Financing assumptions (Step 8 → Step 9 → Step 10)
    change_in_lt_debt: Optional[Any] = None       # list[float] (multi-year) or single value
    change_in_common_equity: Optional[Any] = None  # list[float] (multi-year) or single value
    dividend_payout_ratio: Optional[float] = None
    
    # DCF Model Parameters (Step 8 → Step 9 → Step 10)
    cash_interest_rate: Optional[float] = None
    revolving_credit_rate: Optional[float] = None
    lt_debt_interest_rate: Optional[float] = None
    useful_life_existing: Optional[float] = None
    useful_life_new: Optional[float] = None
    first_year_tax_dep_rate: Optional[float] = None
    blended_tax_dep_rate: Optional[float] = None
    first_year_acctg_dep_rate: Optional[float] = None
    
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
    Step 9 Output: Consolidated and confirmed inputs for Step 10,
    plus building block schedules from the DCF Engine.

    Step 9 runs the DCF Engine to compute the "building block" schedules
    (IS, BS, CFS, WC, Depreciation, Asset, Debt 1&2, Equity, Tax).
    These are projected financial statements the user reviews before Step 10.

    UFCF / DCF / Valuation schedules are deferred to Step 10.

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
    
    # Building block schedules from DCF Engine (Step 9)
    # These are the projected financial statements that feed into UFCF.
    # Shown in Step 9 for user review before proceeding to Step 10.
    calculated_schedules: Optional[Dict[str, Any]] = None
    
    # Full DCF Engine output (stored for Step 10 reuse to avoid double calculation)
    # Step 10 reads this to extract UFCF/DCF/valuation schedules.
    dcf_engine_output: Optional[Dict[str, Any]] = None
    
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
        "risk_free_rate": None,  # No default - must be provided by user
        "market_risk_premium": None,  # No default - must be provided by user
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
        market: str = "international",
        complete_statements: Optional[Dict[str, Any]] = None,
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
                ticker, step6_data, step7_data, step8_confirmed, step8_overrides, step8_ai_suggestions,
                complete_statements=complete_statements
            )
        elif model_enum == ValuationModel.DUPONT:
            confirmed_parameters, categories = await self._process_dupont_confirmation(
                ticker, step6_data, step7_data, step8_confirmed, step8_overrides, step8_ai_suggestions,
                complete_statements=complete_statements
            )
        elif model_enum == ValuationModel.COMPS:
            confirmed_parameters, categories = await self._process_comps_confirmation(
                ticker, step6_data, step7_data, step8_confirmed, step8_overrides, step8_ai_suggestions,
                complete_statements=complete_statements
            )
        
        # Build model-specific inputs for Step 10
        model_specific_inputs = self._build_model_specific_inputs(
            model_enum.value,
            confirmed_parameters,
            step6_data
        )
        
        # Build market context
        market_context = self._build_market_context(market, step6_data)
        
        # Extract historical financials summary
        # complete_statements is already the merged Step 6+7 output (from FinancialStatementsMerger)
        # Use it directly as the primary source — no re-merging needed
        historical_summary = self._extract_historical_summary_from_complete_statements(
            complete_statements, step6_data, step7_data
        )
        
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
        
        # ── Run DCF Engine to produce building block schedules (Step 9) ──
        # Step 9 runs the DCF Engine so the user can review the projected
        # financial statements (IS, BS, CFS, WC, Dep, Asset, Debt, Equity, Tax)
        # before proceeding to Step 10 for UFCF/DCF/valuation.
        calculated_schedules = None
        dcf_engine_output = None
        
        if ready_for_valuation and model_enum == ValuationModel.DCF:
            try:
                dcf_engine_output = self._run_dcf_calculation(
                    model_specific_inputs, historical_summary, market_context, step8_final_inputs
                )
                if dcf_engine_output:
                    calculated_schedules = self._extract_building_block_schedules(dcf_engine_output)
                    # Store full engine output for Step 10 reuse (avoids double calculation)
                    warnings.append("Building block schedules calculated from DCF Engine")
                else:
                    warnings.append("DCF Engine calculation returned no output — building block schedules unavailable")
            except Exception as e:
                logger.warning(f"DCF Engine calculation failed in Step 9: {e}")
                warnings.append(f"DCF Engine calculation failed: {str(e)} — building block schedules unavailable")
        
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
            calculated_schedules=calculated_schedules,
            dcf_engine_output=dcf_engine_output,
            step8_manual_overrides_applied=len(step8_overrides) > 0,
            total_parameters_confirmed=len(confirmed_parameters),
            parameters_from_ai=params_from_ai,
            parameters_manually_overridden=params_overridden,
        )
    
    async def _process_dcf_confirmation(
        self,
        ticker: str,
        step6_data: Dict,
        step7_data: Optional[Dict],
        step8_confirmed: Dict,
        step8_overrides: Dict,
        step8_ai_suggestions: Dict,
        complete_statements: Optional[Dict] = None,
    ) -> tuple[List[ConfirmedParameter], List[ConfirmationCategory]]:
        """Process DCF-specific confirmation parameters"""
        confirmed_parameters = []
        categories = []
        
        # Revenue Growth Parameters (Years 1-5)
        revenue_params = []
        for year in range(1, 6):
            param_name = f"revenue_growth_year_{year}"
            final_value, source, original_ai, override_reason = self._resolve_parameter_value(
                param_name, step8_confirmed, step8_overrides, step8_ai_suggestions,
                step6_data, step7_data, complete_statements
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
                param_name, step8_confirmed, step8_overrides, step8_ai_suggestions,
                step6_data, step7_data, complete_statements
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
                param_name, step8_confirmed, step8_overrides, step8_ai_suggestions,
                step6_data, step7_data, complete_statements
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
        
        # Financing Parameters
        financing_params = []
        for param_name in ["change_in_lt_debt", "change_in_common_equity", "dividend_payout_ratio"]:
            final_value, source, original_ai, override_reason = self._resolve_parameter_value(
                param_name, step8_confirmed, step8_overrides, step8_ai_suggestions,
                step6_data, step7_data, complete_statements
            )
            if final_value is not None:
                financing_params.append(ConfirmedParameter(
                    parameter_name=param_name,
                    final_value=final_value,
                    unit="usd" if param_name != "dividend_payout_ratio" else "percentage",
                    source=source,
                    original_ai_value=original_ai,
                    override_reason=override_reason
                ))
        
        if financing_params:
            categories.append(ConfirmationCategory(
                category_name="Financing",
                parameters=financing_params,
                category_status="complete"
            ))
            confirmed_parameters.extend(financing_params)
        
        # DCF Model Parameters (interest rates, depreciation params)
        model_params = []
        for param_name in ["cash_interest_rate", "revolving_credit_rate", "lt_debt_interest_rate",
                           "useful_life_existing", "useful_life_new",
                           "first_year_tax_dep_rate", "blended_tax_dep_rate", "first_year_acctg_dep_rate"]:
            final_value, source, original_ai, override_reason = self._resolve_parameter_value(
                param_name, step8_confirmed, step8_overrides, step8_ai_suggestions,
                step6_data, step7_data, complete_statements
            )
            if final_value is not None:
                model_params.append(ConfirmedParameter(
                    parameter_name=param_name,
                    final_value=final_value,
                    unit="percentage" if "rate" in param_name or "dep_rate" in param_name else "years",
                    source=source,
                    original_ai_value=original_ai,
                    override_reason=override_reason
                ))
        
        if model_params:
            categories.append(ConfirmationCategory(
                category_name="DCF Model Parameters",
                parameters=model_params,
                category_status="complete"
            ))
            confirmed_parameters.extend(model_params)
        
        # WACC Components
        wacc_params = []
        for param_name in ["wacc", "risk_free_rate", "market_risk_premium", "beta", "cost_of_debt", "debt_to_equity"]:
            final_value, source, original_ai, override_reason = self._resolve_parameter_value(
                param_name, step8_confirmed, step8_overrides, step8_ai_suggestions,
                step6_data, step7_data, complete_statements
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
        step8_ai_suggestions: Dict,
        complete_statements: Optional[Dict] = None,
    ) -> tuple[List[ConfirmedParameter], List[ConfirmationCategory]]:
        """Process DuPont-specific confirmation parameters"""
        confirmed_parameters = []
        categories = []
        
        # DuPont ROE Components
        dupont_params = []
        for param_name in ["target_net_margin", "target_asset_turnover", "target_equity_multiplier"]:
            final_value, source, original_ai, override_reason = self._resolve_parameter_value(
                param_name, step8_confirmed, step8_overrides, step8_ai_suggestions,
                step6_data, step7_data, complete_statements
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
        step8_ai_suggestions: Dict,
        complete_statements: Optional[Dict] = None,
    ) -> tuple[List[ConfirmedParameter], List[ConfirmationCategory]]:
        """Process Comps-specific confirmation parameters"""
        confirmed_parameters = []
        categories = []
        
        # Peer Multiples
        multiples_params = []
        for param_name in ["peer_ev_ebitda", "peer_pe", "peer_pb", "peer_ps"]:
            final_value, source, original_ai, override_reason = self._resolve_parameter_value(
                param_name, step8_confirmed, step8_overrides, step8_ai_suggestions,
                step6_data, step7_data, complete_statements
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
        step8_ai_suggestions: Dict,
        step6_data: Optional[Dict] = None,
        step7_data: Optional[Dict] = None,
        complete_statements: Optional[Dict] = None,
    ) -> tuple[Any, ParameterSource, Optional[Any], Optional[str]]:
        """
        Resolve the final value for a parameter based on source priority:
        1. Manual override (highest priority) — user typed in Step 8
        2. SEC EDGAR data — official filing data from Step 7
        3. Market-derived data — real market prices/yields from Step 6
        4. AI suggestion — LLM-generated estimate from Step 8
        5. Default — hardcoded fallback
        
        Returns:
            Tuple of (final_value, source, original_ai_value, override_reason)
        """
        original_ai = step8_ai_suggestions.get(param_name)
        override_value = step8_overrides.get(param_name)
        confirmed_value = step8_confirmed.get(param_name)
        
        # Priority 1: Manual override (user typed in Step 8)
        if override_value is not None:
            return override_value, ParameterSource.MANUAL_OVERRIDE, original_ai, f"User overridden from {original_ai} to {override_value}"
        
        # Priority 2: SEC EDGAR data (official filing from Step 7)
        sec_edgar_value = self._get_sec_edgar_value(param_name, complete_statements, step7_data)
        if sec_edgar_value is not None:
            return sec_edgar_value, ParameterSource.HISTORICAL_DATA, original_ai, None
        
        # Priority 3: Market-derived data (real market prices/yields from Step 6)
        market_value = self._get_market_data_value(param_name, step6_data)
        if market_value is not None:
            return market_value, ParameterSource.HISTORICAL_DATA, original_ai, None
        
        # Priority 4: Confirmed value from Step 8 (could be AI suggestion that was auto-confirmed)
        if confirmed_value is not None:
            return confirmed_value, ParameterSource.AI_SUGGESTION, original_ai, None
        
        # Priority 5: AI suggestion (raw AI output)
        if original_ai is not None:
            return original_ai, ParameterSource.AI_SUGGESTION, original_ai, None
        
        # Priority 6: Default
        return None, ParameterSource.MARKET_DEFAULT, None, None
    
    def _get_sec_edgar_value(
        self,
        param_name: str,
        complete_statements: Optional[Dict],
        step7_data: Optional[Dict],
    ) -> Optional[Any]:
        """Extract a parameter value from SEC EDGAR data (Step 7 / complete_statements)."""
        if not complete_statements and not step7_data:
            return None
        
        # Map parameter names to complete_statements section + field
        sec_edgar_map = {
            # Income Statement
            'revenue_growth_year_1': ('income_statement', 'revenue'),
            'tax_rate': ('income_statement', 'income_tax_expense'),
            # Balance Sheet
            'debt_to_equity': ('balance_sheet', 'total_debt'),
            # Cash Flow
            'capex_percent_revenue': ('cash_flow_statement', 'capital_expenditure'),
        }
        
        if param_name in sec_edgar_map and complete_statements:
            section_key, field_name = sec_edgar_map[param_name]
            section = complete_statements.get(section_key, {})
            if isinstance(section, dict):
                # Get the latest period's value
                periods = sorted(section.keys())
                if periods:
                    latest = section[periods[-1]]
                    if isinstance(latest, dict) and field_name in latest:
                        return latest[field_name]
        
        return None
    
    def _get_market_data_value(
        self,
        param_name: str,
        step6_data: Optional[Dict],
    ) -> Optional[Any]:
        """Extract a parameter value from market data (Step 6)."""
        if not step6_data:
            return None
        
        market_data = step6_data.get('market_data', {})
        if not isinstance(market_data, dict):
            return None
        
        # Map parameter names to market_data fields
        market_map = {
            'risk_free_rate': 'risk_free_rate',
            'market_risk_premium': 'market_risk_premium',
            'country_risk_premium': 'country_risk_premium',
            'beta': 'beta',
            'cost_of_debt': 'cost_of_debt',
            'terminal_growth_rate': 'terminal_growth_rate',
        }
        
        if param_name in market_map:
            return market_data.get(market_map[param_name])
        
        # Check peer medians for WACC-related params
        peer_medians = step6_data.get('peer_medians', {})
        if isinstance(peer_medians, dict):
            peer_map = {
                'wacc': 'wacc',
                'debt_to_equity': 'debt_to_equity',
            }
            if param_name in peer_map:
                return peer_medians.get(peer_map[param_name])
        
        return None
    
    @staticmethod
    def _normalize_pct(val, field_name):
        """Normalize percentage values to decimal (0-1) format."""
        if val is None or not isinstance(val, (int, float)):
            return val
        pct_fields = {
            'risk_free_rate', 'market_risk_premium', 'country_risk_premium',
            'tax_rate', 'wacc', 'terminal_growth_rate', 'cost_of_debt',
            'first_year_acctg_dep_rate', 'first_year_tax_dep_rate', 'blended_tax_dep_rate',
            'cash_interest_rate', 'revolving_credit_rate', 'lt_debt_interest_rate',
        }
        if field_name in pct_fields:
            if val > 1.0 and val <= 100.0:
                return val / 100.0
            if val > 100.0:
                return val / 10000.0
        return val

    def _build_model_specific_inputs(
        self,
        model_type: str,
        confirmed_parameters: List[ConfirmedParameter],
        step6_data: Dict
    ) -> ModelSpecificInputs:
        """Build model-specific inputs dictionary for Step 10 engines"""
        
        # Convert confirmed parameters to dict, unwrapping any {value, source} wrappers
        params_dict = {}
        for cp in confirmed_parameters:
            name = cp.parameter_name
            val = cp.final_value
            if isinstance(val, dict) and 'value' in val:
                val = val['value']
            params_dict[name] = val
        
        # Get market data from Step 6
        market_data = step6_data.get('market_data', {})
        
        def _unwrap(val):
            """Unwrap {value, source} wrapper dicts to plain values."""
            if isinstance(val, dict) and 'value' in val:
                return val['value']
            return val

        base_inputs = ModelSpecificInputs(
            ticker=step6_data.get('ticker', ''),
            valuation_model=model_type,
            current_price=_unwrap(market_data.get('current_price')),
            shares_outstanding=_unwrap(market_data.get('shares_outstanding')),
            net_debt=_unwrap(market_data.get('net_debt'))
        )
        
        if model_type == "DCF":
            # Build revenue projections
            raw_revenue = step6_data.get('historical_financials', {}).get('revenue', [])
            # Handle multiple data formats:
            # 1. {value: [{period, value}, ...], status} — Step 6 DataField format
            # 2. {period: value, ...} — dict from complete_statements merger
            # 3. [number, ...] — flat list
            latest_revenue = []
            if isinstance(raw_revenue, dict):
                if 'value' in raw_revenue:
                    # Step 6 DataField format: {value: [{period, value}, ...], status: "..."}
                    field_value = raw_revenue['value']
                    if isinstance(field_value, list):
                        for item in field_value:
                            if isinstance(item, dict) and item.get('value') is not None:
                                try:
                                    latest_revenue.append(float(item['value']))
                                except (TypeError, ValueError):
                                    pass
                            elif isinstance(item, (int, float)):
                                latest_revenue.append(float(item))
                    elif isinstance(field_value, (int, float)):
                        latest_revenue = [float(field_value)]
                else:
                    # Dict format from merger: {period_key: value, ...}
                    for k, v in sorted(raw_revenue.items()):
                        if v is not None:
                            try:
                                latest_revenue.append(float(v))
                            except (TypeError, ValueError):
                                pass
            elif isinstance(raw_revenue, list):
                for item in raw_revenue:
                    if isinstance(item, (int, float)):
                        latest_revenue.append(float(item))
                    elif isinstance(item, dict) and item.get('value') is not None:
                        try:
                            latest_revenue.append(float(item['value']))
                        except (TypeError, ValueError):
                            pass
            revenue_projections = []
            if latest_revenue:
                base_revenue = latest_revenue[-1] if latest_revenue[-1] != 0 else latest_revenue[0]
                for year in range(1, 6):
                    growth_rate = params_dict.get(f"revenue_growth_year_{year}", 0.05)
                    if not isinstance(growth_rate, (int, float)):
                        growth_rate = float(growth_rate) if growth_rate else 0.05
                    if year == 1:
                        projected = base_revenue * (1 + growth_rate)
                    else:
                        projected = float(revenue_projections[-1]["projected_revenue"]) * (1 + growth_rate)
                    revenue_projections.append({
                        "year": year,
                        "growth_rate": growth_rate,
                        "projected_revenue": projected
                    })
            
            base_inputs.revenue_projections = revenue_projections
            base_inputs.tax_rate = self._normalize_pct(params_dict.get("tax_rate", self.INTERNATIONAL_DEFAULTS["corporate_tax_rate"]), "tax_rate")
            base_inputs.capex_percent_revenue = params_dict.get("capex_percent_revenue", 0.05)
            base_inputs.nwc_percent_revenue = params_dict.get("nwc_percent_revenue", 0.10)
            base_inputs.terminal_growth_rate = self._normalize_pct(params_dict.get("terminal_growth_rate", 0.025), "terminal_growth_rate")
            base_inputs.wacc = self._normalize_pct(params_dict.get("wacc", 0.08), "wacc")
            base_inputs.risk_free_rate = self._normalize_pct(params_dict.get("risk_free_rate", self.INTERNATIONAL_DEFAULTS["risk_free_rate"]), "risk_free_rate")
            base_inputs.market_risk_premium = self._normalize_pct(params_dict.get("market_risk_premium", self.INTERNATIONAL_DEFAULTS["market_risk_premium"]), "market_risk_premium")
            base_inputs.beta = params_dict.get("beta", 1.0)
            base_inputs.cost_of_debt = self._normalize_pct(params_dict.get("cost_of_debt", 0.05), "cost_of_debt")
            base_inputs.debt_to_equity = params_dict.get("debt_to_equity", 0.5)
            
            # Financing assumptions — pass through for Step 10
            if params_dict.get("change_in_lt_debt") is not None:
                base_inputs.change_in_lt_debt = params_dict["change_in_lt_debt"]
            if params_dict.get("change_in_common_equity") is not None:
                base_inputs.change_in_common_equity = params_dict["change_in_common_equity"]
            if params_dict.get("dividend_payout_ratio") is not None:
                base_inputs.dividend_payout_ratio = params_dict["dividend_payout_ratio"]
            
            # DCF Model Parameters — pass through for Step 10
            if params_dict.get("cash_interest_rate") is not None:
                base_inputs.cash_interest_rate = params_dict["cash_interest_rate"]
            if params_dict.get("revolving_credit_rate") is not None:
                base_inputs.revolving_credit_rate = params_dict["revolving_credit_rate"]
            if params_dict.get("lt_debt_interest_rate") is not None:
                base_inputs.lt_debt_interest_rate = params_dict["lt_debt_interest_rate"]
            if params_dict.get("useful_life_existing") is not None:
                base_inputs.useful_life_existing = params_dict["useful_life_existing"]
            if params_dict.get("useful_life_new") is not None:
                base_inputs.useful_life_new = params_dict["useful_life_new"]
            if params_dict.get("first_year_tax_dep_rate") is not None:
                base_inputs.first_year_tax_dep_rate = params_dict["first_year_tax_dep_rate"]
            if params_dict.get("blended_tax_dep_rate") is not None:
                base_inputs.blended_tax_dep_rate = params_dict["blended_tax_dep_rate"]
            if params_dict.get("first_year_acctg_dep_rate") is not None:
                base_inputs.first_year_acctg_dep_rate = params_dict["first_year_acctg_dep_rate"]
            
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
            risk_free_rate=self._normalize_pct(market_data.get('risk_free_rate', self.INTERNATIONAL_DEFAULTS["risk_free_rate"]), "risk_free_rate"),
            country_risk_premium=self._normalize_pct(market_data.get('country_risk_premium', self.INTERNATIONAL_DEFAULTS["country_risk_premium"]), "country_risk_premium"),
            market_risk_premium=self._normalize_pct(market_data.get('market_risk_premium', self.INTERNATIONAL_DEFAULTS["market_risk_premium"]), "market_risk_premium"),
            corporate_tax_rate=self._normalize_pct(market_data.get('corporate_tax_rate', self.INTERNATIONAL_DEFAULTS["corporate_tax_rate"]), "tax_rate")
        )
    
    def _extract_historical_summary(self, step6_data: Dict, step7_data: Optional[Dict]) -> Dict[str, Any]:
        """
        Extract key historical financials summary from Step 6/7 data.
        
        Handles TWO data formats:
        1. Step 6 format: {field_name: [val1, val2, val3]} (list arrays)
        2. Complete Statements format: {field_name: {period: val}} (dict keyed by period)
           — from FinancialStatementsMerger (Step 8 merged Step 6+7)
        
        Returns BOTH latest values AND full multi-year arrays so Step 10
        can populate DCFInputs with real company data instead of Excel defaults.
        """
        historical = step6_data.get('historical_financials', {})
        
        def to_list(val):
            """Convert any format to a list of values sorted chronologically."""
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                # {period: value} format from FinancialStatementsMerger
                # Sort by period key (date strings sort chronologically)
                sorted_items = sorted(val.items(), key=lambda x: x[0])
                return [v for _, v in sorted_items if v is not None]
            return []
        
        def get_series(*keys, default=None):
            """Get full multi-year array from historical data, trying multiple key names.
            
            The FinancialStatementsMerger uses different key names than Step 6:
            - merger: sg_and_a, depreciation, ebit, capex
            - step6: selling_general_administrative, depreciation_amortization, operating_income, capital_expenditure
            """
            for key in keys:
                val = historical.get(key)
                if val is not None:
                    result = to_list(val)
                    if result:
                        return result
            return default or []
        
        def get_latest(key):
            """Get latest non-zero value from a series."""
            series = get_series(key)
            if not series:
                return 0
            for v in reversed(series):
                if v and v != 0:
                    return v
            return series[0] if series else 0
        
        # Also extract from market_data and balance_sheet sections
        market_data = step6_data.get('market_data', {})
        
        def get_market_val(key, default=0):
            if isinstance(market_data, dict):
                return market_data.get(key, default)
            return default
        
        return {
            # ── Latest values (backward compatible) ──
            "latest_revenue": get_latest('revenue'),
            "latest_ebitda": get_latest('ebitda'),
            "latest_operating_income": get_latest('operating_income'),
            "latest_net_income": get_latest('net_income'),
            "latest_total_assets": get_latest('total_assets'),
            "latest_shareholders_equity": get_latest('shareholders_equity'),
            "latest_operating_cash_flow": get_latest('operating_cash_flow'),
            "latest_capex": get_latest('capital_expenditure'),
            
            # ── Full multi-year arrays (for DCFInputs mapping) ──
            # Keys tried in order: Step 6 name → Merger name → Step 10 DCFInputs name
            # Income Statement
            "revenue": get_series('revenue'),
            "cost_of_revenue": get_series('cost_of_revenue', 'cogs'),
            "cogs": get_series('cogs', 'cost_of_revenue'),
            "operating_expenses": get_series('operating_expenses'),
            "selling_general_administrative": get_series('selling_general_administrative', 'sg_and_a'),
            "research_development": get_series('research_development'),
            "depreciation_amortization": get_series('depreciation_amortization', 'depreciation'),
            "depreciation": get_series('depreciation', 'depreciation_amortization'),
            "interest_expense": get_series('interest_expense'),
            "pretax_income": get_series('pretax_income'),
            "tax_provision": get_series('tax_provision'),
            # Defensive tax decomposition: if deferred_tax unavailable, all provision = current tax
            "deferred_tax": (lambda _tp, _dt: _dt if _dt and any(v != 0 for v in _dt) else [0.0] * len(_tp))(
                get_series('tax_provision'), get_series('deferred_tax')
            ),
            "current_tax": (lambda _tp, _dt: [_t - _d if _t and _d else _t for _t, _d in zip(_tp, _dt)] if _dt and any(v != 0 for v in _dt) else _tp)(
                get_series('tax_provision'), get_series('deferred_tax')
            ),
            "net_income": get_series('net_income'),
            "ebitda": get_series('ebitda'),
            "operating_income": get_series('operating_income', 'ebit'),
            "ebit": get_series('ebit', 'operating_income'),
            
            # Balance Sheet (opening balances)
            "total_assets": get_series('total_assets'),
            "total_debt": get_series('total_debt'),
            "long_term_debt": get_series('long_term_debt'),
            "current_debt": get_series('current_debt'),
            "cash_and_equivalents": get_series('cash_and_equivalents'),
            "accounts_receivable": get_series('accounts_receivable'),
            "inventory": get_series('inventory'),
            "accounts_payable": get_series('accounts_payable'),
            "shareholders_equity": get_series('shareholders_equity'),
            "retained_earnings": get_series('retained_earnings'),
            "ppe_gross": get_series('ppe_gross'),
            "net_ppe": get_series('net_ppe'),
            "accumulated_depreciation": get_series('accumulated_depreciation'),
            "shares_outstanding": get_series('shares_outstanding'),
            # Institution-grade balance sheet items
            "non_current_marketable_securities": get_series('non_current_marketable_securities'),
            "other_current_liabilities": get_series('other_current_liabilities'),
            "deferred_tax_liabilities": get_series('deferred_tax_liabilities'),
            "interest_income": get_series('interest_income'),
            "total_liabilities": get_series('total_liabilities'),
            # New granularity balance sheet items (Steps 5-6-7 additions)
            "current_accrued_expenses": get_series('current_accrued_expenses'),
            "current_deferred_liabilities": get_series('current_deferred_liabilities'),
            "trade_and_other_payables_non_current": get_series('trade_and_other_payables_non_current'),
            "other_non_current_liabilities": get_series('other_non_current_liabilities'),
            "other_short_term_investments": get_series('other_short_term_investments'),
            "other_current_assets": get_series('other_current_assets'),
            "other_non_current_assets": get_series('other_non_current_assets'),
            "common_stock": get_series('common_stock'),
            "other_equity_adjustments": get_series('other_equity_adjustments'),
            # Common Equity = Total Equity - Retained Earnings (contributed capital)
            # Not a raw XBRL field; computed so frontend has correct historical values
            "common_equity": [
                (se or 0) - (re or 0)
                for se, re in zip(
                    get_series('shareholders_equity') or [],
                    get_series('retained_earnings') or []
                )
            ] if get_series('shareholders_equity') and get_series('retained_earnings') else [],
            
            # Cash Flow
            "capital_expenditure": get_series('capital_expenditure', 'capex'),
            "capex": get_series('capex', 'capital_expenditure'),
            "operating_cash_flow": get_series('operating_cash_flow'),
            "dividends_paid": get_series('dividends_paid'),
            "debt_repayments": get_series('debt_repayments'),
            "debt_issuance": get_series('debt_issuance'),
            "share_buybacks": get_series('share_buybacks'),
            "interest_paid": get_series('interest_paid'),
            "tax_paid": get_series('tax_paid'),
            
            # Market data
            "current_price": get_market_val('current_price', 0),
            "market_cap": get_market_val('market_cap', 0),
            "beta": get_market_val('beta', 1.0),
        }
    
    def _extract_historical_summary_from_complete_statements(
        self,
        complete_statements: Optional[Dict[str, Any]],
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract historical financials summary using complete_statements as primary source.
        
        complete_statements is already the merged Step 6+7 output from FinancialStatementsMerger.
        Use it directly — no re-merging needed.
        
        Falls back to step6_data for market_data, sector, industry.
        Falls back to _extract_historical_summary() if complete_statements is unavailable.
        """
        if not complete_statements or not isinstance(complete_statements, dict):
            # Fallback: use the legacy re-merging approach
            return self._extract_historical_summary(step6_data, step7_data)
        
        # Helper to convert {period: value} dict to list
        def to_list(val):
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                sorted_items = sorted(val.items(), key=lambda x: x[0])
                return [v for _, v in sorted_items if v is not None]
            return []
        
        def get_from_section(section_key, field_name, default=None):
            """Get a field from a specific section of complete_statements.
            
            complete_statements format: {section: {period: {field: value}}}
            Example: income_statement -> {"2022-12-31": {"revenue": 55749, "cogs": 29200}}
            
            Returns list of values sorted chronologically by period key.
            """
            section = complete_statements.get(section_key, {})
            if isinstance(section, dict):
                # Collect field values across all periods (sorted chronologically)
                values = []
                for period_key in sorted(section.keys()):
                    period_data = section[period_key]
                    if isinstance(period_data, dict) and field_name in period_data:
                        val = period_data[field_name]
                        if val is not None:
                            values.append(val)
                if values:
                    return values
            return default or []
        
        def get_latest(series):
            """Get latest non-zero value from a series."""
            if not series:
                return 0
            for v in reversed(series):
                if v and v != 0:
                    return v
            return series[0] if series else 0
        
        # Extract from complete_statements sections
        revenue = get_from_section('income_statement', 'revenue')
        cogs = get_from_section('income_statement', 'cogs')
        sga = get_from_section('income_statement', 'sg_and_a')
        depreciation = get_from_section('income_statement', 'depreciation')
        interest = get_from_section('income_statement', 'interest_expense')
        ebitda = get_from_section('income_statement', 'ebitda')
        operating_income = get_from_section('income_statement', 'operating_income')
        net_income = get_from_section('income_statement', 'net_income')
        # Defensive tax decomposition: Tax Provision = Current Tax + Deferred Tax
        # If deferred_tax is missing, treat entire tax_provision as current tax
        tax_provision = get_from_section('income_statement', 'tax_provision')
        deferred_tax = get_from_section('income_statement', 'deferred_tax')
        if not deferred_tax or all(v == 0 for v in deferred_tax):
            # deferred_tax unavailable or all zeros — tax_provision is the current tax proxy
            current_tax = tax_provision
            deferred_tax = [0.0] * len(tax_provision) if tax_provision else []
        else:
            current_tax = [t - d if t and d else t for t, d in zip(tax_provision, deferred_tax)]
        
        ar = get_from_section('balance_sheet', 'accounts_receivable')
        inventory = get_from_section('balance_sheet', 'inventory')
        ap = get_from_section('balance_sheet', 'accounts_payable')
        total_assets = get_from_section('balance_sheet', 'total_assets')
        equity = get_from_section('balance_sheet', 'shareholders_equity')
        ppe_gross = get_from_section('balance_sheet', 'ppe_gross')
        net_ppe = get_from_section('balance_sheet', 'net_ppe')
        accum_dep = get_from_section('balance_sheet', 'accumulated_depreciation')
        lt_debt = get_from_section('balance_sheet', 'long_term_debt')
        total_debt = get_from_section('balance_sheet', 'total_debt')
        cash = get_from_section('balance_sheet', 'cash_and_equivalents')
        retained_earnings = get_from_section('balance_sheet', 'retained_earnings')
        # Institution-grade balance sheet items
        non_current_mkt_sec = get_from_section('balance_sheet', 'non_current_marketable_securities')
        other_cl = get_from_section('balance_sheet', 'other_current_liabilities')
        deferred_tax_liab = get_from_section('balance_sheet', 'deferred_tax_liabilities')
        # New granularity balance sheet items (Steps 5-6-7 additions)
        current_accrued_exp = get_from_section('balance_sheet', 'current_accrued_expenses')
        current_deferred_liab = get_from_section('balance_sheet', 'current_deferred_liabilities')
        trade_payables_nc = get_from_section('balance_sheet', 'trade_and_other_payables_non_current')
        other_nc_liab = get_from_section('balance_sheet', 'other_non_current_liabilities')
        other_sti = get_from_section('balance_sheet', 'other_short_term_investments')
        other_ca = get_from_section('balance_sheet', 'other_current_assets')
        other_nca = get_from_section('balance_sheet', 'other_non_current_assets')
        common_stock = get_from_section('balance_sheet', 'common_stock')
        other_eq_adj = get_from_section('balance_sheet', 'other_equity_adjustments')
        total_liab = get_from_section('balance_sheet', 'total_liabilities')
        
        # Compute common_equity = Total Equity - Retained Earnings (contributed capital)
        # This is the equity portion that is NOT retained earnings (par value + APIC + other paid-in capital)
        if equity and retained_earnings:
            min_len = min(len(equity), len(retained_earnings))
            common_equity = [
                (equity[i] or 0) - (retained_earnings[i] or 0)
                for i in range(min_len)
            ]
        else:
            common_equity = []
        
        capex = get_from_section('cash_flow', 'capital_expenditure')
        ocf = get_from_section('cash_flow', 'operating_cash_flow')
        dividends = get_from_section('cash_flow', 'dividends_paid')
        
        # Market data from step6_data (not in complete_statements)
        market_data = step6_data.get('market_data', {}) if step6_data else {}
        
        return {
            # Latest values
            "latest_revenue": get_latest(revenue),
            "latest_ebitda": get_latest(ebitda),
            "latest_operating_income": get_latest(operating_income),
            "latest_net_income": get_latest(net_income),
            "latest_total_assets": get_latest(total_assets),
            "latest_shareholders_equity": get_latest(equity),
            "latest_operating_cash_flow": get_latest(ocf),
            "latest_capex": get_latest(capex),
            
            # Full multi-year arrays (from complete_statements)
            "revenue": revenue,
            "cogs": cogs,
            "cost_of_revenue": cogs,
            "selling_general_administrative": sga,
            "sg_and_a": sga,
            "depreciation_amortization": depreciation,
            "depreciation": depreciation,
            "interest_expense": interest,
            "ebitda": ebitda,
            "operating_income": operating_income,
            "ebit": operating_income,
            "net_income": net_income,
            "tax_provision": tax_provision,
            "current_tax": current_tax,
            "deferred_tax": deferred_tax,
            "accounts_receivable": ar,
            "inventory": inventory,
            "accounts_payable": ap,
            "total_assets": total_assets,
            "shareholders_equity": equity,
            "ppe_gross": ppe_gross,
            "net_ppe": net_ppe,
            "accumulated_depreciation": accum_dep,
            "long_term_debt": lt_debt,
            "total_debt": total_debt,
            "cash_and_equivalents": cash,
            "retained_earnings": retained_earnings,
            "common_equity": common_equity,
            # Institution-grade balance sheet items
            "non_current_marketable_securities": non_current_mkt_sec,
            "other_current_liabilities": other_cl,
            "deferred_tax_liabilities": deferred_tax_liab,
            # New granularity balance sheet items (Steps 5-6-7 additions)
            "current_accrued_expenses": current_accrued_exp,
            "current_deferred_liabilities": current_deferred_liab,
            "trade_and_other_payables_non_current": trade_payables_nc,
            "other_non_current_liabilities": other_nc_liab,
            "other_short_term_investments": other_sti,
            "other_current_assets": other_ca,
            "other_non_current_assets": other_nca,
            "common_stock": common_stock,
            "other_equity_adjustments": other_eq_adj,
            "total_liabilities": total_liab,
            "capital_expenditure": capex,
            "capex": capex,
            "operating_cash_flow": ocf,
            "dividends_paid": dividends,
            
            # Market data (from step6_data, not complete_statements)
            "current_price": market_data.get('current_price', 0) if isinstance(market_data, dict) else 0,
            "market_cap": market_data.get('market_cap', 0) if isinstance(market_data, dict) else 0,
            "beta": market_data.get('beta', 1.0) if isinstance(market_data, dict) else 1.0,
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

    def _extract_building_block_schedules(
        self,
        dcf_engine_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract building block schedules from BuildingBlockOutput.to_dict().

        Input is always the serialized output of DCFEngine.calculate_building_blocks(),
        which contains all building block schedules directly — no extraction or
        reconstruction needed.

        Building block schedules (Excel Model sheet):
        - Income Statement (rows 96-111)
        - Cash Flow Statement (rows 115-134)
        - Balance Sheet (rows 138-156)
        - Working Capital Schedule (rows 160-175)
        - Depreciation Schedule (rows 180-206)
        - Debt Schedule Part 1 (Cash + LT Debt)
        - Debt Schedule Part 2 (Revolving Credit + Net Interest)
        - Equity Schedule (Common Equity + Retained Earnings)
        - Income Tax Schedule — Levered
        - Income Tax Schedule — Unlevered
        """
        schedules = dcf_engine_output.get('supporting_schedules', {})

        return {
            # ── Income Statement (rows 96-111) ──
            'income_statement': schedules.get('income_statement', {}),

            # ── Cash Flow Statement (rows 115-134) ──
            'cash_flow_statement': dcf_engine_output.get('cash_flow_statement', {}),

            # ── Balance Sheet (rows 138-156) ──
            'balance_sheet': dcf_engine_output.get('balance_sheet', {}),

            # ── Working Capital Schedule (rows 160-175) ──
            'working_capital': schedules.get('working_capital', {}),

            # ── Depreciation + Asset Schedule (rows 180-224) ──
            'depreciation': schedules.get('depreciation', {}),

            # ── Debt Schedule Part 1 (rows 331-345) ──
            'debt_schedule_part1': dcf_engine_output.get('debt_schedule_part1', {}),

            # ── Debt Schedule Part 2 (rows 347-368) ──
            'debt_schedule_part2': dcf_engine_output.get('debt_schedule_part2', {}),

            # ── Equity Schedule (rows 370-385) ──
            'equity_schedule': dcf_engine_output.get('equity_schedule', {}),

            # ── Income Tax Schedule — Levered (rows 387-413) ──
            'tax_levered': schedules.get('tax_levered', {}),

            # ── Income Tax Schedule — Unlevered (rows 415-418) ──
            'tax_unlevered': schedules.get('tax_unlevered', {}),

            # ── WACC Calculation (Inputs sheet, rows 26-59) ──
            'wacc_calculation': dcf_engine_output.get('wacc_calculation', schedules.get('wacc_calculation', {})),

            # ── Full-period schedules (historical + forecast) ──
            'interest_schedule': dcf_engine_output.get('interest_schedule', {}),
            'historical_references': dcf_engine_output.get('historical_references', {}),
            'full_working_capital': dcf_engine_output.get('full_working_capital', {}),

            # ── Period labels ──
            'historical_years': dcf_engine_output.get('historical_years', []),
            'forecast_years': dcf_engine_output.get('forecast_years', []),
            'all_years': dcf_engine_output.get('all_years', []),
        }

    def _run_dcf_calculation(
        self,
        model_specific_inputs: ModelSpecificInputs,
        historical_summary: Dict[str, Any],
        market_context: MarketContext,
        step8_final_inputs: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Run the DCF calculation engine after all inputs are confirmed.

        Uses the shared dcf_input_builder module for input construction,
        then runs DCFEngine.calculate_building_blocks() to produce building block
        schedules only (no UFCF/DCF/valuation — those are deferred to Step 10).

        Returns:
            Dict with BuildingBlockOutput (building block schedules only), or None if calculation fails.
        """
        from app.services.international.dcf_input_builder import extract_dcf_inputs, build_dcf_inputs
        from app.services.international.dcf_engine import DCFEngine

        # Build the assumptions dict
        raw_confirmed = step8_final_inputs.get('raw_frontend_confirmed', {})
        assumptions = {
            'model_specific_inputs': model_specific_inputs.model_dump() if hasattr(model_specific_inputs, 'model_dump') else model_specific_inputs,
            'historical_financials_summary': historical_summary,
            'market_context': market_context.model_dump() if hasattr(market_context, 'model_dump') else market_context,
            'scenario': 'base_case',
            'raw_confirmed_assumptions': raw_confirmed,
        }

        # Use shared input builder
        dcf_inputs_dict = extract_dcf_inputs(assumptions)
        dcf_inputs = build_dcf_inputs(dcf_inputs_dict)

        # Run only building blocks (Phase 1 of DCF calculation)
        engine = DCFEngine(dcf_inputs)
        building_blocks = engine.calculate_building_blocks('base_case')

        # Convert building blocks to serializable dict
        return building_blocks.to_dict()
