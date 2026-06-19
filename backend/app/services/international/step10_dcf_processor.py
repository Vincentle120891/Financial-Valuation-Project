"""Step 10: DCF Valuation Processor

Handles DCF (Discounted Cash Flow) valuation for the international market.
Extracted from step10_valuation_processor.py for single-responsibility clarity.

Flow: Step 9 confirmed outputs → DCFInputs → DCFEngine → Results dict
"""
import logging
from typing import Dict, List, Optional, Any

from app.services.international.dcf_engine import (
    DCFEngine,
    DCFInputs,
    create_default_inputs,
    ScenarioDrivers,
)
from app.services.international.step10_utils import build_fallback_result

logger = logging.getLogger(__name__)


def _extract_numeric(data: Dict, key: str, default: float) -> float:
    """Extract a numeric value from raw confirmed_assumptions.

    Handles both raw values and {value, source} wrapper dicts.
    """
    val = data.get(key)
    if val is None:
        return default
    if isinstance(val, dict):
        val = val.get('value', default)
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _normalize_pct(val: float, field_name: str) -> float:
    """Normalize percentage values to decimal (0-1) format.

    Some upstream data stores percentages as whole numbers (e.g., 4.56 for 4.56%)
    instead of decimals (0.0456). This function detects and fixes that.
    """
    if val is None:
        return val
    pct_fields = {
        'risk_free_rate', 'market_risk_premium', 'country_risk_premium',
        'statutory_tax_rate', 'pre_tax_cost_of_debt', 'terminal_growth',
    }
    if field_name in pct_fields:
        if val > 1.0 and val <= 100.0:
            return val / 100.0
        if val > 100.0:
            return val / 10000.0  # Handle basis-point-like values
    return val


class Step10DCFProcessor:
    """DCF valuation processor — builds ScenarioDrivers, runs DCFEngine, returns results.

    Input building is delegated to shared dcf_input_builder module.
    """

    # Delegate to shared module
    _extract_dcf_inputs = staticmethod(
        lambda assumptions: __import__(
            'app.services.international.dcf_input_builder', fromlist=['extract_dcf_inputs']
        ).extract_dcf_inputs(assumptions)
    )
    _build_dcf_inputs = staticmethod(
        lambda data: __import__(
            'app.services.international.dcf_input_builder', fromlist=['build_dcf_inputs']
        ).build_dcf_inputs(data)
    )

    # NOTE: Legacy run_dcf_valuation() removed.
    # DCF valuation is now exclusively run via run_valuation_with_building_blocks(),
    # which reads pre-computed building blocks from Step 9 (calculate_building_blocks).
    # Step 9 runs Phase 1 (building blocks), Step 10 runs Phase 2 (valuation only).

    # ─── Validation ────────────────────────────────────────────────────────

    def _validate_dcf_inputs(self, dcf_inputs: Dict[str, Any]) -> None:
        """Validate critical DCF inputs before calculation."""
        from app.services.international.step10_valuation_processor import DataValidationError

        missing_fields = []
        invalid_fields = []

        has_wacc_components = (
            dcf_inputs.get('risk_free_rate') is not None and
            dcf_inputs.get('market_risk_premium') is not None
        )
        has_precomputed_wacc = (
            dcf_inputs.get('wacc') is not None or
            dcf_inputs.get('precomputed_wacc') is not None
        )

        if not has_wacc_components and not has_precomputed_wacc:
            missing_fields.extend(['risk_free_rate', 'market_risk_premium'])

        if dcf_inputs.get('terminal_growth') is None:
            missing_fields.append('terminal_growth')
        if dcf_inputs.get('revenue_growth') is None:
            missing_fields.append('revenue_growth')
        if dcf_inputs.get('ebitda_margin') is None:
            missing_fields.append('ebitda_margin')

        if dcf_inputs.get('terminal_growth') is not None:
            tg = dcf_inputs['terminal_growth']
            if not isinstance(tg, (int, float)) or tg < -0.1 or tg > 0.1:
                invalid_fields.append(f"terminal_growth={tg} (must be between -10% and 10%)")

        if dcf_inputs.get('risk_free_rate') is not None:
            rfr = dcf_inputs['risk_free_rate']
            if not isinstance(rfr, (int, float)) or rfr < 0 or rfr > 0.2:
                invalid_fields.append(f"risk_free_rate={rfr} (must be between 0% and 20%)")

        if missing_fields:
            raise DataValidationError(
                f"Critical DCF inputs missing: {', '.join(missing_fields)}",
                missing_fields=missing_fields,
            )
        if invalid_fields:
            raise DataValidationError(
                f"Invalid DCF input values: {'; '.join(invalid_fields)}",
                missing_fields=[],
            )

        logger.debug("DCF inputs validation passed")

    # ─── DCFInputs Builder ─────────────────────────────────────────────────

    # ─── ScenarioDrivers Builder ───────────────────────────────────────────

    def _build_sensitivity(self, engine, valuation_output, dcf_inputs, warnings) -> Optional[Dict]:
        """Build WACC × Terminal Growth sensitivity table.
        
        Uses pre-computed sensitivity from ValuationOutput if available,
        otherwise recomputes from WACC components.
        """
        try:
            # Use pre-computed sensitivity from calculate_valuation()
            raw_sens = valuation_output.sensitivity_perpetuity
            if raw_sens and isinstance(raw_sens, dict):
                # Check if already in frontend format (has 'ranges' and 'results_matrix')
                if 'ranges' in raw_sens and 'results_matrix' in raw_sens:
                    return raw_sens
                # Convert from nested dict format {wacc_str: {growth_str: ev}} to frontend format
                wacc_keys = sorted(raw_sens.keys())
                growth_keys = sorted(raw_sens[wacc_keys[0]].keys()) if wacc_keys else []
                matrix = []
                for w in wacc_keys:
                    row = []
                    for g in growth_keys:
                        row.append(raw_sens[w].get(g, 0))
                    matrix.append(row)
                return {
                    'variable_1': 'WACC',
                    'variable_2': 'Terminal Growth Rate',
                    'ranges': {
                        'wacc': [float(w) for w in wacc_keys],
                        'growth': [float(g) for g in growth_keys],
                    },
                    'results_matrix': matrix,
                }
            
            # Fallback: recompute using WACC components
            wacc_base = dcf_inputs.get('wacc', 0.10)
            if not wacc_base or wacc_base <= 0:
                wacc_base = 0.10
            tg = dcf_inputs.get('terminal_growth', 0.025)
            wacc_range = [round(wacc_base + delta, 4) for delta in [-0.02, -0.01, -0.005, 0, 0.005, 0.01, 0.02]]
            growth_range = [round(tg + delta, 4) for delta in [-0.01, -0.005, 0, 0.005, 0.01]]
            sensitivity_table = engine.calculate_sensitivity_perpetuity(
                valuation_output.ufcf, valuation_output.perpetuity_dcf, wacc_base, wacc_range, growth_range
            )
            matrix = []
            for w in wacc_range:
                row = []
                for g in growth_range:
                    w_key = str(round(w, 4))
                    g_key = str(round(g, 4))
                    row.append(sensitivity_table.get(w_key, {}).get(g_key, 0))
                matrix.append(row)
            return {
                'variable_1': 'WACC',
                'variable_2': 'Terminal Growth Rate',
                'ranges': {
                    'wacc': [round(w, 4) for w in wacc_range],
                    'growth': [round(g, 4) for g in growth_range],
                },
                'results_matrix': matrix,
            }
        except Exception as e:
            logger.warning(f"Sensitivity analysis failed: {e}")
            warnings.append(f"Sensitivity analysis failed: {str(e)}")
            return None

    def _build_scenario_analysis(self, engine) -> Dict:
        """Run Bull/Bear scenarios using engine's two-phase API."""
        scenario_analysis = {}
        for s_name, s_label in [('best_case', 'Bull Case'), ('worst_case', 'Bear Case')]:
            try:
                blocks = engine.calculate_building_blocks(s_name)
                s_output = engine.calculate_valuation(blocks, s_name)
                scenario_analysis[s_label] = {
                    'enterprise_value': {'value': s_output.perpetuity_method.enterprise_value, 'status': 'CALCULATED', 'unit': 'USD'},
                    'equity_value': {'value': s_output.perpetuity_method.equity_value, 'status': 'CALCULATED', 'unit': 'USD'},
                    'fair_value_per_share': {'value': s_output.perpetuity_method.equity_value_per_share, 'status': 'CALCULATED', 'unit': 'USD'},
                }
            except Exception:
                pass
        return scenario_analysis

    # ─── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _generate_recommendation(upside: float) -> str:
        if upside > 0.20:
            return "STRONG BUY"
        elif upside > 0.10:
            return "BUY"
        elif upside > -0.10:
            return "HOLD"
        elif upside > -0.20:
            return "SELL"
        else:
            return "STRONG SELL"

    async def run_valuation_with_building_blocks(
        self,
        ticker: str,
        building_blocks: Dict[str, Any],
        dcf_inputs_dict: Dict[str, Any],
        scenario: str = "base_case"
    ) -> Dict[str, Any]:
        """
        Run valuation phases using pre-computed building blocks.

        This is the new Step 10 path: instead of running the full DCFEngine.calculate(),
        it reads the stored building blocks from session and runs only the valuation
        phases (UFCF, DCF, terminal value, equity values, sensitivity).

        Args:
            ticker: Stock ticker symbol
            building_blocks: Serialized BuildingBlockOutput dict from session storage
            dcf_inputs_dict: DCF input dictionary (for building DCFInputs)
            scenario: Scenario name (default: base_case)

        Returns:
            Dictionary with valuation_summary, detailed_outputs, sensitivity_analysis,
            scenario_analysis, confidence_level, key_assumptions_summary, warnings
        """
        warnings = []

        try:
            inputs = self._build_dcf_inputs(dcf_inputs_dict)
            engine = DCFEngine(inputs)

            # Deserialize building blocks
            building_block_output = DCFEngine._deserialize_building_blocks(building_blocks)

            # Run only valuation phases
            valuation_output = engine.calculate_valuation(building_block_output, scenario)

            ev = valuation_output.perpetuity_method.enterprise_value
            equity_val = valuation_output.perpetuity_method.equity_value
            fair_val = valuation_output.perpetuity_method.equity_value_per_share
            current_price = dcf_inputs_dict.get('current_price', 0) or 0

            upside = ((fair_val - current_price) / current_price) if current_price and current_price > 0 else 0
            recommendation = self._generate_recommendation(upside)
            confidence = "high" if abs(upside) > 0.20 else "medium" if abs(upside) > 0.10 else "low"
            warnings.extend(valuation_output.warnings)

            # Sensitivity table — pass valuation_output directly (has .wacc)
            sensitivity_analysis = self._build_sensitivity(engine, valuation_output, dcf_inputs_dict, warnings)

            # Build detailed_outputs by merging BuildingBlockOutput + ValuationOutput dicts
            # This produces the same structure the frontend expects from to_dict(DCFOutput)
            bb_dict = building_block_output.to_dict()
            vo_dict = valuation_output.to_dict()
            detailed_outputs = {
                'main_outputs': vo_dict['main_outputs'],
                'dcf_details': vo_dict.get('dcf_details'),
                'wacc_calculation': bb_dict['wacc_calculation'],
                'supporting_schedules': {
                    **bb_dict.get('supporting_schedules', {}),
                    'ufcf': vo_dict.get('supporting_schedules', {}).get('ufcf'),
                },
                # Valuation analysis schedules
                'ufcf_3_methods': vo_dict.get('ufcf_3_methods'),
                'intrinsic_extracts': vo_dict.get('intrinsic_extracts'),
                'npv_xnpv': vo_dict.get('npv_xnpv'),
                'sensitivity_perpetuity': vo_dict.get('sensitivity_perpetuity'),
                'sensitivity_multiple': vo_dict.get('sensitivity_multiple'),
                'dcf_analysis': {'method': 'perpetuity'},
                'validation': bb_dict.get('validation'),
                'metadata': bb_dict.get('metadata'),
            }

            # Scenario analysis
            scenario_analysis = self._build_scenario_analysis(engine)

            return {
                'valuation_summary': {
                    'enterprise_value': {'value': ev, 'status': 'CALCULATED', 'unit': 'USD'},
                    'equity_value': {'value': equity_val, 'status': 'CALCULATED', 'unit': 'USD'},
                    'fair_value_per_share': {'value': fair_val, 'status': 'CALCULATED', 'unit': 'USD'},
                    'current_price': {'value': current_price, 'status': 'RETRIEVED', 'unit': 'USD'},
                    'implied_upside_downside': {'value': upside, 'status': 'CALCULATED', 'unit': 'percentage'},
                    'valuation_range_low': {'value': fair_val * 0.85, 'status': 'CALCULATED', 'unit': 'USD'},
                    'valuation_range_high': {'value': fair_val * 1.15, 'status': 'CALCULATED', 'unit': 'USD'},
                },
                'detailed_outputs': detailed_outputs,
                'sensitivity_analysis': sensitivity_analysis,
                'scenario_analysis': scenario_analysis if scenario_analysis else None,
                'confidence_level': confidence,
                'key_assumptions_summary': {
                    'wacc': building_block_output.wacc,
                    'terminal_growth_rate': dcf_inputs_dict.get('terminal_growth'),
                    'risk_free_rate': dcf_inputs_dict.get('risk_free_rate'),
                    'market_risk_premium': dcf_inputs_dict.get('market_risk_premium'),
                    'revenue_growth': dcf_inputs_dict.get('revenue_growth'),
                    'ebitda_margin': dcf_inputs_dict.get('ebitda_margin'),
                    'tax_rate': dcf_inputs_dict.get('statutory_tax_rate'),
                    'cost_of_debt': dcf_inputs_dict.get('pre_tax_cost_of_debt'),
                },
                'warnings': warnings,
            }

        except Exception as e:
            logger.error(f"DCF valuation with building blocks failed: {e}", exc_info=True)
            warnings.append(f"DCF Engine error: {str(e)}")
            return self._build_fallback_result(ticker, warnings)

    @staticmethod
    def _build_fallback_result(ticker: str, warnings: List[str]) -> Dict[str, Any]:
        return build_fallback_result(ticker, 'DCF', warnings)
