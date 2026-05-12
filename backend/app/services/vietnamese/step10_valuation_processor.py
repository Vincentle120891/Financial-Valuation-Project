"""
Vietnamese Step 10: Valuation Processor
Orchestrates execution of Vietnamese valuation engines
"""
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import importlib


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

    async def process(self, input_data: VNValuationInput) -> VNValuationOutput:
        """
        Execute Vietnamese valuation

        Args:
            input_data: Validated inputs from Step 9

        Returns:
            VNValuationOutput with valuation results

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

            return VNValuationOutput(
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

            return VNValuationOutput(
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

            return VNValuationOutput(
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

    async def _execute_dcf_valuation(self, engine, input_data: VNValuationInput) -> VNValuationResult:
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
        return VNValuationResult(
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

    async def _execute_dupont_valuation(self, engine, input_data: VNValuationInput) -> VNValuationResult:
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
        return VNValuationResult(
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

    async def _execute_comps_valuation(self, engine, input_data: VNValuationInput) -> VNValuationResult:
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
        return VNValuationResult(
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

    def _create_empty_result(self, model_type: str) -> VNValuationResult:
        """Create empty result for error cases"""
        return VNValuationResult(
            model_type=model_type,
            valuation_value=0,
            currency="VND",
            valuation_date=datetime.utcnow(),
            key_metrics={},
            assumptions_summary={},
            warnings=["Valuation failed - check errors"],
            calculation_details=None
        )