"""
Vietnamese Step 10: Valuation Processor
Orchestrates execution of Vietnamese valuation engines

Bridge method: run_valuation() matches the INT Step10ValuationProcessor signature
so valuation_routes.py can delegate to this processor when market='vietnam'.
"""
import logging
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import importlib

logger = logging.getLogger(__name__)


class vn_ValuationInput(BaseModel):
    """Input for Vietnamese valuation execution"""
    session_id: str
    company_name: str
    ticker: str
    exchange: Literal["HOSE", "HNX", "UPCOM"]
    selected_model: Literal["dcf", "dupont", "comps"]

    # Model-specific inputs (from Step 9)
    model_specific_inputs: Dict[str, Any]

    # Market context (from Step 9)
    market_context: Dict[str, Any]

    # Historical data reference
    historical_financials: Optional[Dict[str, Any]] = None

    # Peer data (for Comps)
    peer_data: Optional[list] = None

    # Metadata
    user_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class vn_ValuationResult(BaseModel):
    """Standardized valuation result structure"""
    model_type: str
    valuation_value: float
    currency: str
    valuation_date: datetime
    key_metrics: Dict[str, Any]
    sensitivity_analysis: Optional[Dict[str, Any]] = None
    assumptions_summary: Dict[str, Any]
    warnings: list
    calculation_details: Optional[Dict[str, Any]] = None


class vn_ValuationOutput(BaseModel):
    """Output from Vietnamese valuation execution"""
    session_id: str
    company_name: str
    ticker: str
    exchange: str
    selected_model: str
    result: vn_ValuationResult
    market_context: Dict[str, Any]
    execution_time_ms: float
    status: str = "success"
    errors: list = []
    next_step: str = "step11_results"

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "vn-session-123",
                "company_name": "VinGroup Joint Stock Company",
                "ticker": "VIC",
                "exchange": "HOSE",
                "selected_model": "dcf",
                "result": {
                    "model_type": "dcf",
                    "valuation_value": 125000000000000,
                    "currency": "VND",
                    "valuation_date": "2024-01-15T10:30:00",
                    "key_metrics": {
                        "enterprise_value": 150000000000000,
                        "equity_value": 125000000000000,
                        "value_per_share": 25000,
                        "wacc": 0.12,
                        "terminal_growth_rate": 0.055
                    },
                    "sensitivity_analysis": {
                        "wacc_range": [0.10, 0.14],
                        "terminal_growth_range": [0.04, 0.07],
                        "valuation_matrix": [[...]]
                    },
                    "assumptions_summary": {
                        "revenue_cagr": 0.12,
                        "target_margin": 0.15,
                        "tax_rate": 0.20
                    },
                    "warnings": []
                },
                "market_context": {
                    "currency": "VND",
                    "risk_free_rate": 0.068,
                    "country_risk_premium": 0.035
                },
                "execution_time_ms": 245.5,
                "status": "success"
            }
        }


class vn_Step10ValuationProcessor:
    """
    Processor for executing Vietnamese valuation models

    Routes to appropriate Vietnamese engine based on selected model:
    - vietnamese_dcf_engine
    - vietnamese_dupont_engine
    - vietnamese_comps_engine
    """

    # Engine module paths for Vietnamese models
    ENGINE_MODULES = {
        "dcf": "app.services.vietnamese.vietnamese_dcf_engine",
        "dupont": "app.services.vietnamese.vietnamese_dupont_engine",
        "comps": "app.services.vietnamese.vietnamese_comps_engine"
    }

    # Engine class names
    ENGINE_CLASSES = {
        "dcf": "VietnameseDCFEngine",
        "dupont": "VietnameseDuPontEngine",
        "comps": "VietnameseCompsEngine"
    }

    async def process(self, input_data: vn_ValuationInput) -> vn_ValuationOutput:
        """
        Execute Vietnamese valuation

        Args:
            input_data: Validated inputs from Step 9

        Returns:
            vn_ValuationOutput with valuation results

        Raises:
            ValueError: If model type is invalid
            ImportError: If engine module cannot be loaded
            Exception: If valuation calculation fails
        """
        import time
        start_time = time.time()

        errors = []
        warnings = []

        try:
            # Get engine module and class
            module_path = self.ENGINE_MODULES.get(input_data.selected_model)
            class_name = self.ENGINE_CLASSES.get(input_data.selected_model)

            if not module_path or not class_name:
                raise ValueError(f"Invalid model type: {input_data.selected_model}")

            # Import engine module
            engine_module = importlib.import_module(module_path)
            engine_class = getattr(engine_module, class_name)

            # Instantiate engine
            engine = engine_class()

            # Execute valuation based on model type
            if input_data.selected_model == "dcf":
                result = await self._execute_dcf_valuation(engine, input_data)
            elif input_data.selected_model == "dupont":
                result = await self._execute_dupont_valuation(engine, input_data)
            elif input_data.selected_model == "comps":
                result = await self._execute_comps_valuation(engine, input_data)
            else:
                raise ValueError(f"Unsupported model: {input_data.selected_model}")

            execution_time_ms = (time.time() - start_time) * 1000

            return vn_ValuationOutput(
                session_id=input_data.session_id,
                company_name=input_data.company_name,
                ticker=input_data.ticker,
                exchange=input_data.exchange,
                selected_model=input_data.selected_model,
                result=result,
                market_context=input_data.market_context,
                execution_time_ms=execution_time_ms,
                status="success",
                errors=errors,
                next_step="step11_results"
            )

        except ImportError as e:
            errors.append(f"Engine import error: {str(e)}")
            execution_time_ms = (time.time() - start_time) * 1000

            return vn_ValuationOutput(
                session_id=input_data.session_id,
                company_name=input_data.company_name,
                ticker=input_data.ticker,
                exchange=input_data.exchange,
                selected_model=input_data.selected_model,
                result=self._create_empty_result(input_data.selected_model),
                market_context=input_data.market_context,
                execution_time_ms=execution_time_ms,
                status="failed",
                errors=errors,
                next_step="step9_confirmation"
            )

        except Exception as e:
            errors.append(f"Valuation calculation error: {str(e)}")
            execution_time_ms = (time.time() - start_time) * 1000

            return vn_ValuationOutput(
                session_id=input_data.session_id,
                company_name=input_data.company_name,
                ticker=input_data.ticker,
                exchange=input_data.exchange,
                selected_model=input_data.selected_model,
                result=self._create_empty_result(input_data.selected_model),
                market_context=input_data.market_context,
                execution_time_ms=execution_time_ms,
                status="failed",
                errors=errors,
                next_step="step9_confirmation"
            )

    async def _execute_dcf_valuation(self, engine, input_data: vn_ValuationInput) -> vn_ValuationResult:
        """Execute DCF valuation using Vietnamese engine"""
        # Prepare DCF inputs
        dcf_inputs = {
            **input_data.model_specific_inputs,
            "company_name": input_data.company_name,
            "ticker": input_data.ticker,
            "currency": input_data.market_context.get("currency", "VND"),
            "historical_financials": input_data.historical_financials
        }

        # Call engine (assuming async method)
        if hasattr(engine, 'calculate_async'):
            raw_result = await engine.calculate_async(dcf_inputs)
        else:
            raw_result = engine.calculate(dcf_inputs)

        # Parse result into standardized format
        return vn_ValuationResult(
            model_type="dcf",
            valuation_value=raw_result.get("equity_value", 0),
            currency=input_data.market_context.get("currency", "VND"),
            valuation_date=datetime.utcnow(),
            key_metrics={
                "enterprise_value": raw_result.get("enterprise_value", 0),
                "equity_value": raw_result.get("equity_value", 0),
                "value_per_share": raw_result.get("value_per_share", 0),
                "wacc": raw_result.get("wacc", 0),
                "terminal_growth_rate": raw_result.get("terminal_growth_rate", 0),
                "npv_of_fcf": raw_result.get("npv_of_fcf", 0),
                "terminal_value": raw_result.get("terminal_value", 0)
            },
            sensitivity_analysis=raw_result.get("sensitivity_analysis"),
            assumptions_summary={
                "revenue_cagr": raw_result.get("revenue_cagr", 0),
                "target_margin": raw_result.get("target_margin", 0),
                "tax_rate": raw_result.get("tax_rate", 0.20),
                "capex_percent": raw_result.get("capex_percent", 0),
                "nwc_percent": raw_result.get("nwc_percent", 0)
            },
            warnings=raw_result.get("warnings", []),
            calculation_details=raw_result.get("calculation_details")
        )

    async def _execute_dupont_valuation(self, engine, input_data: vn_ValuationInput) -> vn_ValuationResult:
        """Execute DuPont analysis using Vietnamese engine"""
        # Prepare DuPont inputs
        dupont_inputs = {
            **input_data.model_specific_inputs,
            "company_name": input_data.company_name,
            "ticker": input_data.ticker,
            "currency": input_data.market_context.get("currency", "VND")
        }

        # Call engine
        if hasattr(engine, 'calculate_async'):
            raw_result = await engine.calculate_async(dupont_inputs)
        else:
            raw_result = engine.calculate(dupont_inputs)

        # Parse result
        return vn_ValuationResult(
            model_type="dupont",
            valuation_value=raw_result.get("roe", 0),
            currency=input_data.market_context.get("currency", "VND"),
            valuation_date=datetime.utcnow(),
            key_metrics={
                "roe": raw_result.get("roe", 0),
                "net_profit_margin": raw_result.get("net_profit_margin", 0),
                "asset_turnover": raw_result.get("asset_turnover", 0),
                "financial_leverage": raw_result.get("financial_leverage", 0),
                "roa": raw_result.get("roa", 0)
            },
            sensitivity_analysis=None,  # DuPont typically doesn't have sensitivity
            assumptions_summary={
                "analysis_period": raw_result.get("analysis_period", "Latest FY"),
                "sector_comparison": raw_result.get("sector_comparison", {})
            },
            warnings=raw_result.get("warnings", []),
            calculation_details=raw_result.get("calculation_details")
        )

    async def _execute_comps_valuation(self, engine, input_data: vn_ValuationInput) -> vn_ValuationResult:
        """Execute Trading Comps valuation using Vietnamese engine"""
        # Prepare Comps inputs
        comps_inputs = {
            **input_data.model_specific_inputs,
            "company_name": input_data.company_name,
            "ticker": input_data.ticker,
            "currency": input_data.market_context.get("currency", "VND"),
            "peer_data": input_data.peer_data
        }

        # Call engine
        if hasattr(engine, 'calculate_async'):
            raw_result = await engine.calculate_async(comps_inputs)
        else:
            raw_result = engine.calculate(comps_inputs)

        # Parse result
        return vn_ValuationResult(
            model_type="comps",
            valuation_value=raw_result.get("implied_equity_value", 0),
            currency=input_data.market_context.get("currency", "VND"),
            valuation_date=datetime.utcnow(),
            key_metrics={
                "implied_equity_value": raw_result.get("implied_equity_value", 0),
                "implied_enterprise_value": raw_result.get("implied_enterprise_value", 0),
                "value_per_share": raw_result.get("value_per_share", 0),
                "peers_used_count": raw_result.get("peers_used_count", 0),
                "median_pe": raw_result.get("median_pe", 0),
                "median_ev_ebitda": raw_result.get("median_ev_ebitda", 0),
                "median_pb": raw_result.get("median_pb", 0)
            },
            sensitivity_analysis=raw_result.get("sensitivity_analysis"),
            assumptions_summary={
                "num_peers": raw_result.get("num_peers", 0),
                "multiples_used": raw_result.get("multiples_used", []),
                "liquidity_filter_days": raw_result.get("liquidity_filter_days", 60),
                "peer_selection_method": raw_result.get("peer_selection_method", "sector_match")
            },
            warnings=raw_result.get("warnings", []),
            calculation_details=raw_result.get("calculation_details")
        )

    def _create_empty_result(self, model_type: str) -> vn_ValuationResult:
        """Create empty result for error cases"""
        return vn_ValuationResult(
            model_type=model_type,
            valuation_value=0,
            currency="VND",
            valuation_date=datetime.utcnow(),
            key_metrics={},
            assumptions_summary={},
            warnings=["Valuation failed - check errors"],
            calculation_details=None
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Bridge method — matches INT Step10ValuationProcessor.run_valuation()
    # ──────────────────────────────────────────────────────────────────────────

    async def run_valuation(
        self,
        ticker: str,
        model: str,
        assumptions: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Bridge method matching INT Step10ValuationProcessor.run_valuation() signature.

        Routes to the appropriate Vietnamese engine based on the model parameter,
        translates Step 9 confirmed outputs into engine-specific inputs, and returns
        a result dict whose keys match what valuation_routes.py expects.

        Args:
            ticker: Stock ticker symbol
            model: Valuation model ('DCF', 'DUPONT', 'COMPS')
            assumptions: Confirmed assumptions dict from Step 9 outputs.
                         Keys: model_specific_inputs, historical_financials_summary,
                         market_context, scenario, raw_confirmed_assumptions, etc.

        Returns:
            Dict with valuation_summary, detailed_outputs, sensitivity_analysis,
            scenario_analysis, confidence_level, key_assumptions_summary, warnings.
        """
        model_upper = model.upper()
        warnings: list = []

        model_inputs = assumptions.get("model_specific_inputs", {})
        hist_summary = assumptions.get("historical_financials_summary", {})
        market_ctx = assumptions.get("market_context", {})
        scenario = assumptions.get("scenario", "base_case")
        raw_confirmed = assumptions.get("raw_confirmed_assumptions", {})

        try:
            if model_upper == "DCF":
                result = await self._run_vn_dcf(ticker, model_inputs, hist_summary, market_ctx, raw_confirmed)
            elif model_upper == "DUPONT":
                result = await self._run_vn_dupont(ticker, model_inputs, hist_summary, market_ctx)
            elif model_upper == "COMPS":
                result = await self._run_vn_comps(ticker, model_inputs, hist_summary, market_ctx)
            else:
                raise ValueError(f"Unsupported model: {model}")

            result["warnings"] = warnings + result.get("warnings", [])
            return result

        except Exception as e:
            logger.error(f"VN Step 10 run_valuation error ({model_upper}): {e}", exc_info=True)
            return {
                "valuation_summary": {},
                "detailed_outputs": {},
                "sensitivity_analysis": None,
                "scenario_analysis": None,
                "confidence_level": "low",
                "key_assumptions_summary": {},
                "warnings": [f"VN valuation failed: {str(e)}"],
            }

    # ──────────────────────────────────────────────────────────────────────────
    # Model-specific runners
    # ──────────────────────────────────────────────────────────────────────────

    async def _run_vn_dcf(
        self,
        ticker: str,
        model_inputs: Dict[str, Any],
        hist_summary: Dict[str, Any],
        market_ctx: Dict[str, Any],
        raw_confirmed: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run Vietnamese DCF engine using confirmed Step 9 inputs."""
        from app.services.vietnamese.vietnamese_dcf_engine import VietnameseDCFEngine
        from app.models.vietnamese.vietnamese_inputs import VietnameseDCFRequest, VNSector

        # Extract WACC components from model_inputs
        wacc_data = model_inputs.get("wacc", {}) if isinstance(model_inputs.get("wacc"), dict) else {}
        revenue_projections = model_inputs.get("revenue_projections", [])

        # Build latest revenue from projections or historical summary
        latest_revenue = hist_summary.get("latest_revenue", 0)
        if revenue_projections:
            latest_revenue = revenue_projections[0].get("projected_revenue", latest_revenue)

        # Revenue growth rates from projections
        rev_growth_rates = [p.get("growth_rate", 0.05) for p in revenue_projections] if revenue_projections else [0.05] * 5

        # Extract current price & shares from raw_confirmed or market_ctx
        current_price = raw_confirmed.get("current_price", 0) or market_ctx.get("current_price", 0)
        shares_outstanding = raw_confirmed.get("shares_outstanding", 0) or market_ctx.get("shares_outstanding", 0)

        # Build VietnameseDCFRequest
        vn_request = VietnameseDCFRequest(
            ticker=ticker,
            company_name=market_ctx.get("company_name", ticker),
            exchange=market_ctx.get("exchange", "HOSE"),
            sector=VNSector(market_ctx.get("sector", "Other")) if market_ctx.get("sector") in [s.value for s in VNSector] else VNSector.OTHER,
            current_price_vnd=max(current_price, 1),
            shares_outstanding=max(shares_outstanding, 1),
            risk_free_rate_vn=wacc_data.get("risk_free_rate", market_ctx.get("risk_free_rate", 0.068)),
            market_risk_premium_vn=market_ctx.get("market_risk_premium", 0.075),
            beta=wacc_data.get("beta", 1.0),
            terminal_growth_rate=model_inputs.get("terminal_growth_rate", 0.03),
            forecast_years=len(rev_growth_rates) if rev_growth_rates else 5,
            corporate_tax_rate=model_inputs.get("tax_rate", market_ctx.get("corporate_tax_rate", 0.20)),
            wacc_override=wacc_data.get("wacc"),
        )

        # Build financial data dict for the engine
        financial_data = {
            "revenue": latest_revenue,
            "ebit_margin": model_inputs.get("operating_margin", 0.15),
            "depreciation": hist_summary.get("latest_capex", 0) * 0.5,  # rough proxy
            "capex": latest_revenue * model_inputs.get("capex_percent_revenue", 0.05),
            "change_in_nwc": latest_revenue * model_inputs.get("nwc_percent_revenue", 0.05),
            "revenue_growth_rates": rev_growth_rates,
            "cost_of_debt": wacc_data.get("cost_of_debt", 0.08),
            "debt_to_equity": wacc_data.get("debt_to_equity", 0.5),
            "total_debt": raw_confirmed.get("total_debt", 0),
            "cash": raw_confirmed.get("cash", 0),
        }

        engine = VietnameseDCFEngine(
            corporate_tax_rate=vn_request.corporate_tax_rate,
            risk_free_rate=vn_request.risk_free_rate_vn,
            market_risk_premium=vn_request.market_risk_premium_vn,
        )
        raw_result = engine.valuate_vn_dcf(vn_request, financial_data)

        # Build sensitivity analysis (WACC vs terminal growth)
        wacc_val = raw_result.get("wacc_analysis", {}).get("wacc", 0.10)
        tg_val = vn_request.terminal_growth_rate
        sensitivity = self._build_vn_sensitivity(engine, vn_request, financial_data, wacc_val, tg_val)

        valuation_summary = raw_result.get("valuation_summary", {})
        dcf_components = raw_result.get("dcf_components", {})

        return {
            "valuation_summary": {
                "intrinsic_value_per_share": valuation_summary.get("intrinsic_value_per_share", 0),
                "current_price": valuation_summary.get("current_price", 0),
                "upside_downside_pct": valuation_summary.get("upside_downside_pct", 0),
                "recommendation": valuation_summary.get("recommendation", "HOLD"),
                "currency": "VND",
            },
            "detailed_outputs": {
                "enterprise_value": dcf_components.get("enterprise_value", 0),
                "equity_value": dcf_components.get("equity_value", 0),
                "value_per_share": valuation_summary.get("intrinsic_value_per_share", 0),
                "wacc": wacc_val,
                "terminal_growth_rate": tg_val,
                "npv_of_fcf": raw_result.get("wacc_analysis", {}),
                "terminal_value": raw_result.get("terminal_value", {}),
                "projections": raw_result.get("projections", []),
            },
            "sensitivity_analysis": sensitivity,
            "scenario_analysis": None,
            "confidence_level": "medium",
            "key_assumptions_summary": {
                "revenue_growth": rev_growth_rates[0] if rev_growth_rates else 0,
                "ebitda_margin": model_inputs.get("operating_margin", 0),
                "wacc": wacc_val,
                "terminal_growth": tg_val,
                "tax_rate": vn_request.corporate_tax_rate,
            },
            "warnings": [],
        }

    def _build_vn_sensitivity(
        self,
        engine: "VietnameseDCFEngine",
        vn_request: "VietnameseDCFRequest",
        financial_data: Dict[str, Any],
        base_wacc: float,
        base_tg: float,
    ) -> Dict[str, Any]:
        """Build WACC vs terminal growth sensitivity matrix for Vietnamese DCF."""
        import numpy as np

        wacc_range = [base_wacc - 0.02, base_wacc - 0.01, base_wacc, base_wacc + 0.01, base_wacc + 0.02]
        tg_range = [base_tg - 0.01, base_tg - 0.005, base_tg, base_tg + 0.005, base_tg + 0.01]
        wacc_range = [w for w in wacc_range if 0.04 <= w <= 0.25]
        tg_range = [g for g in tg_range if 0.01 <= g <= 0.08]

        matrix = []
        for w in wacc_range:
            row = []
            for g in tg_range:
                try:
                    fcf_projections = engine.project_free_cash_flows(
                        revenue_base=financial_data.get("revenue", 0),
                        ebit_margin=financial_data.get("ebit_margin", 0.15),
                        tax_rate=vn_request.corporate_tax_rate,
                        depreciation=financial_data.get("depreciation", 0),
                        capex=financial_data.get("capex", 0),
                        change_in_nwc=financial_data.get("change_in_nwc", 0),
                        revenue_growth_rates=financial_data.get("revenue_growth_rates", [0.05] * 5),
                        forecast_years=vn_request.forecast_years,
                    )
                    tv = engine.calculate_terminal_value(fcf_projections[-1]["fcff"] if fcf_projections else 0, g, w)
                    ev_result = engine.calculate_enterprise_value(fcf_projections, tv, w)
                    eq = engine.calculate_equity_value(
                        ev_result["enterprise_value"],
                        financial_data.get("total_debt", 0),
                        financial_data.get("cash", 0),
                    )
                    per_share = eq / vn_request.shares_outstanding if vn_request.shares_outstanding > 0 else 0
                    row.append(round(per_share, 0))
                except Exception:
                    row.append(0)
            matrix.append(row)

        return {
            "variable_1": "WACC",
            "variable_2": "Terminal Growth Rate",
            "ranges": {"wacc": wacc_range, "terminal_growth": tg_range},
            "results_matrix": matrix,
        }

    async def _run_vn_dupont(
        self,
        ticker: str,
        model_inputs: Dict[str, Any],
        hist_summary: Dict[str, Any],
        market_ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run Vietnamese DuPont engine."""
        from app.services.vietnamese.vietnamese_dupont_engine import VietnameseDuPontEngine
        from app.models.vietnamese.vietnamese_inputs import VNFinancialStatements

        # Build minimal VNFinancialStatements from available data
        statements = VNFinancialStatements(
            ticker=ticker,
            periods=[],
            revenue=[hist_summary.get("latest_revenue", 0)],
            cogs_gross=[0],
            depreciation_cogs=[0],
            sga=[0],
            other_operating_expenses=[0],
            interest_expense=[0],
            other_income=[0],
            tax_expense=[0],
            total_assets=[hist_summary.get("latest_total_assets", 0)],
            total_liabilities=[0],
            shareholders_equity=[hist_summary.get("latest_shareholders_equity", 0)],
            cash=[0],
            short_term_debt=[0],
            long_term_debt=[0],
        )

        engine = VietnameseDuPontEngine()
        engine.load_data(statements)
        result = await engine.analyze()

        # Convert to dict
        result_dict = result.model_dump() if hasattr(result, "model_dump") else result.dict()

        # Build top-level keys the route expects
        ratios = result_dict.get("ratios", {})
        return {
            "valuation_summary": {
                "roe": ratios.get("roe", 0),
                "currency": "VND",
            },
            "detailed_outputs": result_dict,
            "sensitivity_analysis": None,
            "scenario_analysis": None,
            "confidence_level": "medium",
            "key_assumptions_summary": {
                "net_profit_margin": ratios.get("net_profit_margin", 0),
                "asset_turnover": ratios.get("asset_turnover", 0),
                "equity_multiplier": ratios.get("equity_multiplier", 0),
            },
            "warnings": result_dict.get("warnings", []),
        }

    async def _run_vn_comps(
        self,
        ticker: str,
        model_inputs: Dict[str, Any],
        hist_summary: Dict[str, Any],
        market_ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run Vietnamese Comps engine (stub — requires peer data from Step 4)."""
        logger.warning(f"VN Comps engine called for {ticker} — returning placeholder (peer data required)")

        return {
            "valuation_summary": {
                "message": "Comps valuation requires peer data from Step 4",
                "currency": "VND",
            },
            "detailed_outputs": {},
            "sensitivity_analysis": None,
            "scenario_analysis": None,
            "confidence_level": "low",
            "key_assumptions_summary": {},
            "warnings": ["Vietnamese Comps engine requires peer data not yet available in Step 9 outputs"],
        }
