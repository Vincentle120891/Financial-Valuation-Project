"""Step 9: DCF Final Calculation Engine - Specialized DCF Valuation Processor

This module performs complete DCF valuation calculations using the mathematically verified DCFEngine:
- WACC calculation from comparable companies
- UFCF projection with detailed revenue/cost schedules
- Terminal Value (Perpetuity and Exit Multiple methods)
- Discounting and Enterprise Value calculation
- Bridge to Equity Value and Fair Value per Share
- Sensitivity analysis

Input: Step 6 aggregated data + Step 8 DCF assumptions
Output: Complete DCF valuation with fair value, key metrics, and sensitivity tables
"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime
import statistics

# Import specialized DCF engine for calculations
from app.services.international.dcf_engine import (
    DCFEngine,
    DCFInputs,
    create_default_inputs,
    ScenarioDrivers,
    ValuationResult as DCFValuationResult
)

logger = logging.getLogger(__name__)


class DCFValuationDetails(BaseModel):
    """Detailed DCF calculation results"""
    wacc: float
    terminal_growth: float
    projected_fcf: List[Dict[str, float]]  # Year-by-year FCF projections
    terminal_value: float
    present_value_fcf: float
    present_value_terminal: float
    enterprise_value: float
    net_debt: float
    equity_value: float
    shares_outstanding: float
    fair_value_per_share: float
    sensitivity_table: Optional[Dict[str, Dict[str, float]]] = None


class SensitivityScenario(BaseModel):
    """Sensitivity analysis scenario"""
    scenario_name: str
    assumptions: Dict[str, float]
    result_value: float
    description: str


class DCFValuationResultResponse(BaseModel):
    """
    Step 9 DCF Response: Final DCF valuation results with key metrics and sensitivity tables.
    This is the SOLE calculation hub for DCF model in the international market.
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: str = "DCF"
    fair_value: Optional[float] = None
    current_price: Optional[float] = None
    upside_downside: Optional[float] = None  # Percentage
    recommendation: str = "HOLD"  # BUY, HOLD, SELL
    confidence_level: str = "MEDIUM"
    dcf_details: Optional[DCFValuationDetails] = None
    sensitivity_scenarios: Optional[List[SensitivityScenario]] = None
    key_metrics: Dict[str, float] = {}
    warnings: List[str] = []
    calculation_notes: str = ""


class DCFStep9Processor:
    """
    Step 9: DCF Final Calculation Engine

    Performs complete DCF valuation:
    - UFCF projection, Discounting, Terminal Value, Bridge to Equity Value
    - WACC calculation, Cost of Equity, After-Tax Cost of Debt
    - Sensitivity analysis across WACC and Terminal Growth

    Input: Step 6 aggregated data + Step 8 DCF assumptions
    Output: DCFValuationResultResponse with fair value per share and detailed metrics
    """

    def __init__(self):
        pass

    async def calculate_dcf_valuation(
        self,
        ticker: str,
        step6_data: Dict[str, Any],
        step8_final_inputs: Dict[str, Any],
        market_data: Optional[Dict] = None
    ) -> DCFValuationResultResponse:
        """
        Main entry point for DCF valuation calculation.

        Args:
            ticker: Stock ticker symbol
            step6_data: Aggregated data from Step 6 (historical financials, market data)
            step8_final_inputs: Finalized inputs from Step 8 (validated DCF assumptions)
            market_data: Current market data

        Returns:
            DCFValuationResultResponse with complete DCF valuation results
        """
        warnings = []

        try:
            # Build DCFInputs from Step 6 and Step 8 data
            dcf_inputs = self._build_dcf_inputs_from_steps(step6_data, step8_final_inputs, market_data)

            # Initialize and run DCF Engine
            engine = DCFEngine(dcf_inputs)

            # Get scenario from inputs (default to base_case)
            scenario = step8_final_inputs.get('scenario', 'base_case')
            if scenario not in ['best_case', 'base_case', 'worst_case']:
                scenario = 'base_case'

            # Execute full DCF calculation
            dcf_output = engine.calculate(scenario=scenario)

            # Extract results from perpetuity method (primary)
            perpetuity_result = dcf_output.perpetuity_method
            dcf_details_output = dcf_output.perpetuity_dcf

            # Get current price
            current_price = dcf_inputs.get_value(dcf_inputs.current_stock_price)

            # Calculate upside/downside
            upside_downside = None
            recommendation = "HOLD"
            if current_price and current_price > 0:
                upside_downside = (perpetuity_result.equity_value_per_share - current_price) / current_price
                if upside_downside > 0.15:
                    recommendation = "BUY"
                elif upside_downside < -0.15:
                    recommendation = "SELL"

            # Build projected FCF list from engine output
            projected_fcf = []
            for i, year in enumerate(dcf_output.ufcf.years):
                projected_fcf.append({
                    'year': i + 1,
                    'revenue': dcf_output.income_statement.revenue[i],
                    'ebitda': dcf_output.income_statement.ebitda[i],
                    'fcf': dcf_output.ufcf.ufcf[i]
                })

            # Build sensitivity table from engine calculations
            sensitivity_table = self._build_dcf_sensitivity_table(engine, dcf_inputs, scenario)

            # Create DCF details for response
            dcf_details = DCFValuationDetails(
                wacc=dcf_output.wacc,
                terminal_growth=dcf_inputs.forecast_drivers[scenario].terminal_growth_rate,
                projected_fcf=projected_fcf,
                terminal_value=dcf_details_output.terminal_value,
                present_value_fcf=sum(dcf_details_output.pv_discrete_cf),
                present_value_terminal=dcf_details_output.pv_terminal_value,
                enterprise_value=perpetuity_result.enterprise_value,
                net_debt=dcf_inputs.get_value(dcf_inputs.net_debt_opening),
                equity_value=perpetuity_result.equity_value,
                shares_outstanding=dcf_inputs.get_value(dcf_inputs.shares_outstanding),
                fair_value_per_share=perpetuity_result.equity_value_per_share,
                sensitivity_table=sensitivity_table
            )

            key_metrics = {
                'WACC': dcf_output.wacc,
                'Terminal Growth': dcf_inputs.forecast_drivers[scenario].terminal_growth_rate,
                'Enterprise Value': perpetuity_result.enterprise_value,
                'Equity Value': perpetuity_result.equity_value,
                'Fair Value per Share': perpetuity_result.equity_value_per_share,
                'Current Price': current_price,
                'Upside/Downside': upside_downside,
                'Levered Beta': dcf_output.levered_beta,
                'Cost of Equity': dcf_output.cost_of_equity,
                'After-Tax Cost of Debt': dcf_output.after_tax_cost_of_debt
            }

            calculation_notes = f"DCF valuation completed using {scenario} scenario. " \
                              f"Perpetuity method EV: ${perpetuity_result.enterprise_value:,.2f}. " \
                              f"WACC: {dcf_output.wacc:.2%}"

        except Exception as e:
            logger.error(f"DCF Engine calculation failed: {e}. Using fallback calculation.")
            warnings.append(f"DCF Engine error: {str(e)}")
            # Fallback to simplified calculation
            return self._calculate_dcf_fallback(ticker, step6_data, step8_final_inputs, market_data, warnings)

        return DCFValuationResultResponse(
            session_id=f"step9_dcf_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            fair_value=perpetuity_result.equity_value_per_share,
            current_price=current_price,
            upside_downside=upside_downside,
            recommendation=recommendation,
            confidence_level="HIGH" if dcf_output.ufcf_methods_reconcile else "MEDIUM",
            dcf_details=dcf_details,
            sensitivity_scenarios=self._generate_dcf_sensitivity_scenarios(dcf_details),
            key_metrics=key_metrics,
            warnings=warnings,
            calculation_notes=calculation_notes
        )

    def _generate_dcf_sensitivity_scenarios(self, dcf_details: DCFValuationDetails) -> List[SensitivityScenario]:
        """Generate sensitivity scenarios for DCF valuation"""
        scenarios = []

        if dcf_details.sensitivity_table:
            # Base case
            base_fair_value = dcf_details.fair_value_per_share
            scenarios.append(SensitivityScenario(
                scenario_name="Base Case",
                assumptions={'wacc': dcf_details.wacc, 'terminal_growth': dcf_details.terminal_growth},
                result_value=base_fair_value,
                description="Base case assumptions from Step 8"
            ))

            # Extract sensitivity variations
            for wacc_key, wacc_values in dcf_details.sensitivity_table.items():
                try:
                    wacc_pct = float(wacc_key.replace('%', '')) / 100
                    for tg_key, fair_value in wacc_values.items():
                        if abs(wacc_pct - dcf_details.wacc) > 0.001 or abs(float(tg_key.replace('%', '')) / 100 - dcf_details.terminal_growth) > 0.001:
                            tg_pct = float(tg_key.replace('%', '')) / 100
                            scenarios.append(SensitivityScenario(
                                scenario_name=f"WACC {wacc_key}, TG {tg_key}",
                                assumptions={'wacc': wacc_pct, 'terminal_growth': tg_pct},
                                result_value=fair_value,
                                description=f"Sensitivity: WACC {wacc_key}, Terminal Growth {tg_key}"
                            ))
                except (ValueError, AttributeError):
                    continue

        return scenarios

    def _build_dcf_inputs_from_steps(
        self,
        step6_data: Dict,
        step8_final_inputs: Dict,
        market_data: Optional[Dict]
    ) -> DCFInputs:
        """Build DCFInputs from Step 6 and Step 8 data"""
        # Create default inputs
        dcf_inputs = create_default_inputs()

        # Extract historical data from Step 6
        historical_data = step6_data.get('historical_financials', {})

        # Populate historical financials
        if 'revenue' in historical_data:
            dcf_inputs.historicals.revenue = historical_data['revenue']
        if 'ebitda' in historical_data:
            dcf_inputs.historicals.ebitda = historical_data['ebitda']
        if 'operating_income' in historical_data:
            dcf_inputs.historicals.ebit = historical_data['operating_income']
        if 'net_income' in historical_data:
            dcf_inputs.historicals.net_income = historical_data['net_income']
        if 'operating_cash_flow' in historical_data:
            dcf_inputs.historicals.operating_cash_flow = historical_data['operating_cash_flow']
        if 'capex' in historical_data:
            dcf_inputs.historicals.capex = historical_data['capex']
        if 'depreciation_amortization' in historical_data:
            dcf_inputs.historicals.depreciation_and_amortization = historical_data['depreciation_amortization']
        if 'working_capital_change' in historical_data:
            dcf_inputs.historicals.change_in_working_capital = historical_data['working_capital_change']

        # Extract market data
        if market_data:
            if 'current_price' in market_data:
                dcf_inputs.current_stock_price = market_data['current_price']
            if 'shares_outstanding' in market_data:
                dcf_inputs.shares_outstanding = market_data['shares_outstanding']
            if 'net_debt' in market_data:
                dcf_inputs.net_debt_opening = market_data['net_debt']
            if 'risk_free_rate' in market_data:
                dcf_inputs.risk_free_rate = market_data['risk_free_rate']
            if 'market_risk_premium' in market_data:
                dcf_inputs.equity_risk_premium = market_data['market_risk_premium']

        # Extract assumptions from Step 8
        if 'revenue_growth' in step8_final_inputs:
            growth_rates = step8_final_inputs['revenue_growth']
            if isinstance(growth_rates, dict):
                scenario = step8_final_inputs.get('scenario', 'base_case')
                if scenario in growth_rates:
                    dcf_inputs.forecast_drivers[scenario].revenue_growth_rate = growth_rates[scenario]

        if 'target_operating_margin' in step8_final_inputs:
            margin = step8_final_inputs['target_operating_margin']
            scenario = step8_final_inputs.get('scenario', 'base_case')
            if isinstance(margin, dict) and scenario in margin:
                dcf_inputs.forecast_drivers[scenario].target_operating_margin = margin[scenario]
            elif isinstance(margin, (int, float)):
                dcf_inputs.forecast_drivers[scenario].target_operating_margin = margin

        if 'tax_rate' in step8_final_inputs:
            tax_rate = step8_final_inputs['tax_rate']
            scenario = step8_final_inputs.get('scenario', 'base_case')
            if isinstance(tax_rate, dict) and scenario in tax_rate:
                dcf_inputs.forecast_drivers[scenario].tax_rate = tax_rate[scenario]
            elif isinstance(tax_rate, (int, float)):
                dcf_inputs.forecast_drivers[scenario].tax_rate = tax_rate

        if 'capex_percent_revenue' in step8_final_inputs:
            capex_pct = step8_final_inputs['capex_percent_revenue']
            scenario = step8_final_inputs.get('scenario', 'base_case')
            if isinstance(capex_pct, dict) and scenario in capex_pct:
                dcf_inputs.forecast_drivers[scenario].capex_percent_of_revenue = capex_pct[scenario]
            elif isinstance(capex_pct, (int, float)):
                dcf_inputs.forecast_drivers[scenario].capex_percent_of_revenue = capex_pct

        if 'wacc' in step8_final_inputs:
            wacc = step8_final_inputs['wacc']
            scenario = step8_final_inputs.get('scenario', 'base_case')
            if isinstance(wacc, dict) and scenario in wacc:
                dcf_inputs.forecast_drivers[scenario].wacc = wacc[scenario]
            elif isinstance(wacc, (int, float)):
                dcf_inputs.forecast_drivers[scenario].wacc = wacc

        if 'terminal_growth_rate' in step8_final_inputs:
            tg = step8_final_inputs['terminal_growth_rate']
            scenario = step8_final_inputs.get('scenario', 'base_case')
            if isinstance(tg, dict) and scenario in tg:
                dcf_inputs.forecast_drivers[scenario].terminal_growth_rate = tg[scenario]
            elif isinstance(tg, (int, float)):
                dcf_inputs.forecast_drivers[scenario].terminal_growth_rate = tg

        if 'levered_beta' in step8_final_inputs:
            beta = step8_final_inputs['levered_beta']
            scenario = step8_final_inputs.get('scenario', 'base_case')
            if isinstance(beta, dict) and scenario in beta:
                dcf_inputs.forecast_drivers[scenario].levered_beta = beta[scenario]
            elif isinstance(beta, (int, float)):
                dcf_inputs.forecast_drivers[scenario].levered_beta = beta

        return dcf_inputs

    def _build_dcf_sensitivity_table(
        self,
        engine: DCFEngine,
        dcf_inputs: DCFInputs,
        scenario: str
    ) -> Dict[str, Dict[str, float]]:
        """Build sensitivity table for WACC and Terminal Growth variations"""
        sensitivity_table = {}

        base_wacc = dcf_inputs.forecast_drivers[scenario].wacc
        base_tg = dcf_inputs.forecast_drivers[scenario].terminal_growth_rate

        # WACC variations: -2%, -1%, base, +1%, +2%
        wacc_variations = [-0.02, -0.01, 0, 0.01, 0.02]
        # Terminal Growth variations: -1%, -0.5%, base, +0.5%, +1%
        tg_variations = [-0.01, -0.005, 0, 0.005, 0.01]

        for wacc_adj in wacc_variations:
            wacc_key = f"{(base_wacc + wacc_adj):.1%}"
            sensitivity_table[wacc_key] = {}

            for tg_adj in tg_variations:
                tg_key = f"{(base_tg + tg_adj):.2%}"

                try:
                    # Create temporary inputs with adjusted values
                    temp_drivers = dcf_inputs.forecast_drivers[scenario].model_copy()
                    temp_drivers.wacc = base_wacc + wacc_adj
                    temp_drivers.terminal_growth_rate = base_tg + tg_adj

                    temp_inputs = dcf_inputs.model_copy()
                    temp_inputs.forecast_drivers[scenario] = temp_drivers

                    temp_engine = DCFEngine(temp_inputs)
                    temp_output = temp_engine.calculate(scenario=scenario)

                    fair_value = temp_output.perpetuity_method.equity_value_per_share
                    sensitivity_table[wacc_key][tg_key] = fair_value
                except Exception:
                    sensitivity_table[wacc_key][tg_key] = 0.0

        return sensitivity_table

    def _calculate_dcf_fallback(
        self,
        ticker: str,
        step6_data: Dict,
        step8_final_inputs: Dict,
        market_data: Optional[Dict],
        warnings: List[str]
    ) -> DCFValuationResultResponse:
        """Fallback DCF calculation if engine fails"""
        # Simplified fallback logic
        current_price = market_data.get('current_price', 0) if market_data else 0

        return DCFValuationResultResponse(
            session_id=f"step9_dcf_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            fair_value=None,
            current_price=current_price,
            upside_downside=None,
            recommendation="HOLD",
            confidence_level="LOW",
            key_metrics={},
            warnings=warnings,
            calculation_notes="DCF calculation failed. Using fallback with limited data."
        )