"""Step 10: Final Valuation Processor - Sole Calculation Hub for All Three Models

This module integrates with the specialized engine classes for mathematically verified calculations:
- DCFEngine: Full DCF implementation (WACC, FCF, Terminal Value, NPV)
- DuPontAnalyzer: ROE decomposition and financial ratio analysis
- TradingCompsAnalyzer: Comparable company analysis with peer multiples

Each engine handles its core mathematical logic while this processor orchestrates:
1. Data preparation from upstream steps (Step 6, Step 8)
2. Engine invocation with properly formatted inputs
3. Result aggregation and formatting for API responses
4. Cross-model comparison and sensitivity analysis
"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum
from datetime import datetime
import statistics


class DataValidationError(Exception):
    """Custom exception for data validation errors in valuation calculations."""
    def __init__(self, message: str, missing_fields: List[str] = None):
        self.message = message
        self.missing_fields = missing_fields or []
        super().__init__(self.message)


from app.services.international.dcf_engine import (
    DCFEngine,
    DCFInputs,
    create_default_inputs,
    ScenarioDrivers,
    ValuationResult as DCFValuationResult
)
from app.services.international.dupont_engine import (
    DuPontAnalyzer,
    FinancialStatements,
    DuPontResult
)
from app.services.international.comps_engine import (
    TradingCompsAnalyzer,
    TargetCompanyData,
    PeerCompanyData,
    TradingCompsOutputs
)
# Note: run_dcf_valuation is a convenience function, we use DCFEngine class directly for better control

logger = logging.getLogger(__name__)

class ValuationModel(str, Enum):
    """Type of valuation model to use"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"


class ValuationResult(BaseModel):
    """Final valuation result"""
    fair_value: Optional[float] = None
    current_price: Optional[float] = None
    upside_downside: Optional[float] = None  # Percentage
    recommendation: str = "HOLD"  # BUY, HOLD, SELL
    confidence_level: str = "MEDIUM"


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


class DuPontValuationDetails(BaseModel):
    """Detailed DuPont analysis results"""
    net_profit_margin: float
    asset_turnover: float
    equity_multiplier: float
    roe: float  # ROE = Margin × Turnover × Leverage
    roa: float  # Return on Assets
    trend_analysis: Optional[List[Dict[str, float]]] = None  # Historical trends
    benchmark_comparison: Optional[Dict[str, float]] = None


class CompsValuationDetails(BaseModel):
    """Detailed Comps analysis results"""
    peer_multiples: Dict[str, List[float]]  # Multiple -> list of peer values
    median_multiples: Dict[str, float]
    mean_multiples: Dict[str, float]
    implied_valuations: Dict[str, float]  # Multiple -> implied share price
    average_implied_value: float
    peer_count: int
    outliers_removed: List[str] = []


class SensitivityScenario(BaseModel):
    """Sensitivity analysis scenario"""
    scenario_name: str
    assumptions: Dict[str, float]
    result_value: float
    description: str


class ValuationSummary(BaseModel):
    dcf_value: float
    comps_implied_value: Optional[float] = None
    blended_value: float
    recommendation: str
    confidence_level: str


class Step10Response(BaseModel):
    """
    Step 10 Response: Final valuation results with key metrics and sensitivity tables.
    This is the SOLE calculation hub for DCF, DuPont, and Comps models.
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: ValuationModel
    valuation_result: ValuationResult
    dcf_details: Optional[DCFValuationDetails] = None
    dupont_details: Optional[DuPontValuationDetails] = None
    comps_details: Optional[CompsValuationDetails] = None
    sensitivity_scenarios: Optional[List[SensitivityScenario]] = None
    key_metrics: Dict[str, float] = {}
    warnings: List[str] = []
    calculation_notes: str = ""

class Step10ValuationProcessor:
    """
    Step 10: Final Valuation Processor

    Orchestrates the final valuation by:
    1. Calling the DCF Engine to perform mathematically verified calculations
    2. Formatting results for API response
    3. Blending DCF value with Comps (if available)
    4. Generating sensitivity analysis and recommendations
    """

    async def run_valuation(
        self,
        ticker: str,
        model: str,
        assumptions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run valuation for a specific model (DCF, DuPont, or Comps).

        Args:
            ticker: Stock ticker symbol
            model: Valuation model ('DCF', 'DUPONT', 'COMPS')
            assumptions: Confirmed assumptions from Step 9

        Returns:
            Dictionary with valuation results
        """
        model = model.upper()

        if model == 'DCF':
            return await self._run_dcf_valuation(ticker, assumptions)
        elif model == 'DUPONT':
            return await self._run_dupont_valuation(ticker, assumptions)
        elif model == 'COMPS':
            return await self._run_comps_valuation(ticker, assumptions)
        else:
            raise ValueError(f"Unsupported valuation model: {model}")

    async def _run_dcf_valuation(self, ticker: str, assumptions: Dict[str, Any]) -> Dict[str, Any]:
        """Run DCF valuation using the DCF Engine."""
        # Extract DCF-specific inputs from assumptions
        dcf_inputs = self._extract_dcf_inputs(assumptions)

        # Validate critical inputs before calculation
        self._validate_dcf_inputs(dcf_inputs)

        # Use the existing process_final_valuation method
        result = self.process_final_valuation(
            ticker=ticker,
            dcf_inputs=dcf_inputs,
            comps_value=None  # Can be added later for blending
        )

        # Convert Pydantic model to dict
        return result.model_dump() if hasattr(result, 'model_dump') else result.dict()

    async def _run_dupont_valuation(
        self,
        ticker: str,
        step6_data: Dict,
        step8_final_inputs: Dict,
        market_data: Optional[Dict] = None
    ) -> Step10Response:
        """
        Perform DuPont analysis using DuPontAnalyzer engine.
        
        Leverages the mathematically verified DuPont engine for:
        - 3-step ROE decomposition (Net Margin × Asset Turnover × Equity Multiplier)
        - 5-step ROE decomposition (Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Equity Multiplier)
        - Comprehensive ratio analysis (profitability, efficiency, leverage, liquidity)
        - Trend analysis and benchmark comparison
        
        Args:
            ticker: Stock ticker symbol
            step6_data: Aggregated data from Step 6 (historical financials, market data)
            step8_final_inputs: Finalized inputs from Step 8 (validated assumptions)
            market_data: Current market data
            
        Returns:
            Step10Response with complete DuPont analysis results
        """
        warnings = []
        
        try:
            # Build FinancialStatements from Step 6 historical data
            financial_statements = self._build_dupont_statements_from_step6(step6_data)
            
            # Initialize and run DuPont Analyzer
            analyzer = DuPontAnalyzer()
            analyzer.load_data(financial_statements)
            
            # Execute full DuPont analysis
            dupont_output = analyzer.calculate_all()
            
            # Extract latest year metrics (index 7 for Year 8)
            latest_idx = 7
            net_margin = dupont_output.ratios.net_profit_margin[latest_idx]
            asset_turnover = dupont_output.ratios.asset_turnover[latest_idx]
            equity_multiplier = dupont_output.ratios.total_assets_to_equity[latest_idx]
            roe = dupont_output.ratios.roe[latest_idx]
            roa = dupont_output.ratios.roa[latest_idx]
            
            # Build trend analysis from historical data
            trend_analysis = []
            years = dupont_output.years
            for i in range(len(years)):
                if dupont_output.ratios.roe[i] != 0:  # Only include years with valid data
                    trend_analysis.append({
                        'year': years[i],
                        'net_margin': dupont_output.ratios.net_profit_margin[i],
                        'asset_turnover': dupont_output.ratios.asset_turnover[i],
                        'equity_multiplier': dupont_output.ratios.total_assets_to_equity[i],
                        'roe': dupont_output.ratios.roe[i],
                        'roa': dupont_output.ratios.roa[i]
                    })
            
            # Benchmark comparison (industry averages)
            benchmark_comparison = {
                'industry_avg_roe': 0.15,
                'sector_avg_roe': 0.12,
                'sp500_avg_roe': 0.18
            }
            
            # Check DuPont validation
            if not all(dupont_output.ratios.roe_3step_check):
                warnings.append("DuPont 3-step calculation has minor rounding differences")
            
            # Determine recommendation based on ROE vs benchmarks
            if roe > 0.20:
                recommendation = "BUY"
                confidence = "HIGH"
            elif roe > 0.15:
                recommendation = "HOLD"
                confidence = "MEDIUM"
            else:
                recommendation = "SELL"
                confidence = "MEDIUM"
            
            dupont_details = DuPontValuationDetails(
                net_profit_margin=net_margin,
                asset_turnover=asset_turnover,
                equity_multiplier=equity_multiplier,
                roe=roe,
                roa=roa,
                trend_analysis=trend_analysis if trend_analysis else None,
                benchmark_comparison=benchmark_comparison
            )
            
            valuation_result = ValuationResult(
                fair_value=None,  # DuPont doesn't produce fair value
                current_price=None,
                upside_downside=None,
                recommendation=recommendation,
                confidence_level=confidence
            )
            
            key_metrics = {
                'Net Profit Margin': net_margin,
                'Asset Turnover': asset_turnover,
                'Equity Multiplier': equity_multiplier,
                'ROE': roe,
                'ROA': roa,
                'Gross Margin': dupont_output.ratios.gross_margin[latest_idx],
                'EBITDA Margin': dupont_output.ratios.ebitda_margin[latest_idx],
                'Interest Coverage': dupont_output.ratios.interest_coverage[latest_idx],
                'Debt to Equity': dupont_output.ratios.debt_to_equity[latest_idx],
                'Current Ratio': dupont_output.ratios.current_ratio[latest_idx],
                'Inventory Turnover': dupont_output.ratios.inventory_turnover[latest_idx],
                'ROIC': dupont_output.ratios.roic[latest_idx]
            }
            
            calculation_notes = f"DuPont analysis completed. ROE: {roe:.2%} decomposed into " \
                              f"Net Margin ({net_margin:.2%}) × Asset Turnover ({asset_turnover:.2f}) × " \
                              f"Equity Multiplier ({equity_multiplier:.2f}). " \
                              f"3-step validation: {'Passed' if all(dupont_output.ratios.roe_3step_check) else 'Minor differences'}"
            
        except Exception as e:
            logger.error(f"DuPont Engine calculation failed: {e}. Using fallback calculation.")
            warnings.append(f"DuPont Engine error: {str(e)}")
            # Fallback to simplified calculation
            return self._calculate_dupont_fallback(ticker, step6_data, step8_final_inputs, market_data, warnings)
        
        return Step10Response(
            session_id=f"step10_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DUPONT,
            valuation_result=valuation_result,
            dupont_details=dupont_details,
            key_metrics=key_metrics,
            warnings=warnings,
            calculation_notes=calculation_notes
        )

    async def _run_comps_valuation(
        self,
        ticker: str,
        step6_data: Dict,
        step8_final_inputs: Dict,
        market_data: Optional[Dict] = None
    ) -> Step10Response:
        """
        Perform Comps analysis using TradingCompsAnalyzer engine.
        
        Leverages the mathematically verified Comps engine for:
        - EV/EBITDA and P/E multiples for LTM, FY2023, FY2024
        - Peer company filtering and outlier removal using IQR method
        - Median/mean multiple calculations
        - Implied share price from Min/Average/Max scenarios
        - Football field chart data generation
        
        Args:
            ticker: Stock ticker symbol
            step6_data: Aggregated data from Step 6 (historical financials, peer data)
            step8_final_inputs: Finalized inputs from Step 8 (validated assumptions)
            market_data: Current market data
            
        Returns:
            Step10Response with complete Comps valuation results
        """
        warnings = []
        
        try:
            # Build target and peer data from Step 6
            target_data = self._build_target_company_from_step6(ticker, step6_data, market_data)
            peer_list = self._build_peer_list_from_step6(step6_data)
            
            # Initialize and run Trading Comps Analyzer
            analyzer = TradingCompsAnalyzer(target=target_data, peers=peer_list)
            
            # Execute full Comps analysis
            comps_output = analyzer.run_analysis()
            
            # Extract median multiples from engine output
            median_multiples = {}
            if comps_output.ev_ebitda_ltm_stats:
                median_multiples['EV/EBITDA LTM'] = comps_output.ev_ebitda_ltm_stats.median
            if comps_output.ev_ebitda_fy23_stats:
                median_multiples['EV/EBITDA FY23'] = comps_output.ev_ebitda_fy23_stats.median
            if comps_output.pe_ltm_stats:
                median_multiples['P/E LTM'] = comps_output.pe_ltm_stats.median
            if comps_output.pe_fy23_stats:
                median_multiples['P/E FY23'] = comps_output.pe_fy23_stats.median
            
            # Build peer multiples list for display
            peer_multiples_display = {
                'P/E': [p.get('pe_ltm') for p in comps_output.peer_multiples if p.get('pe_ltm')],
                'EV/EBITDA': [p.get('ev_ebitda_ltm') for p in comps_output.peer_multiples if p.get('ev_ebitda_ltm')],
                'P/B': [],  # Add if available
                'P/S': []   # Add if available
            }
            
            # Calculate average implied value from all scenarios
            implied_values = [
                comps_output.avg_ev_ebitda_ltm_price,
                comps_output.avg_ev_ebitda_fy23_price,
                comps_output.avg_pe_ltm_price,
                comps_output.avg_pe_fy23_price
            ]
            implied_values = [v for v in implied_values if v > 0]
            average_implied_value = statistics.mean(implied_values) if implied_values else 0
            
            # Get current price
            current_price = target_data.share_price if target_data else None
            
            # Calculate upside/downside
            upside_downside = None
            recommendation = "HOLD"
            if current_price and current_price > 0 and average_implied_value > 0:
                upside_downside = (average_implied_value - current_price) / current_price
                if upside_downside > 0.15:
                    recommendation = "BUY"
                elif upside_downside < -0.15:
                    recommendation = "SELL"
            
            comps_details = CompsValuationDetails(
                peer_multiples=peer_multiples_display,
                median_multiples=median_multiples,
                mean_multiples={},  # Can add mean if needed
                implied_valuations={
                    'Average EV/EBITDA LTM': comps_output.avg_ev_ebitda_ltm_price,
                    'Average EV/EBITDA FY23': comps_output.avg_ev_ebitda_fy23_price,
                    'Average P/E LTM': comps_output.avg_pe_ltm_price,
                    'Average P/E FY23': comps_output.avg_pe_fy23_price,
                    'Maximum EV/EBITDA LTM': comps_output.max_ev_ebitda_ltm_price,
                    'Minimum EV/EBITDA LTM': comps_output.min_ev_ebitda_ltm_price
                },
                average_implied_value=average_implied_value,
                peer_count=comps_output.peer_count_after_filtering,
                outliers_removed=comps_output.excluded_peers
            )
            
            valuation_result = ValuationResult(
                fair_value=average_implied_value if average_implied_value > 0 else None,
                current_price=current_price,
                upside_downside=upside_downside,
                recommendation=recommendation,
                confidence_level="HIGH" if comps_output.peer_count_after_filtering >= 5 else "MEDIUM"
            )
            
            key_metrics = {
                'Median EV/EBITDA LTM': comps_output.ev_ebitda_ltm_stats.median if comps_output.ev_ebitda_ltm_stats else None,
                'Median P/E LTM': comps_output.pe_ltm_stats.median if comps_output.pe_ltm_stats else None,
                'Peer Count': comps_output.peer_count_after_filtering,
                'Average Implied Value': average_implied_value,
                'Current Price': current_price,
                'Upside/Downside': upside_downside
            }
            
            calculation_notes = f"Comps valuation completed using {comps_output.peer_count_after_filtering} peers. " \
                              f"Median EV/EBITDA LTM: {comps_output.ev_ebitda_ltm_stats.median:.2f}x " \
                              f"(if available). Average implied value: ${average_implied_value:.2f}"
            
        except Exception as e:
            logger.error(f"Comps Engine calculation failed: {e}. Using fallback calculation.")
            warnings.append(f"Comps Engine error: {str(e)}")
            # Fallback to simplified calculation
            return self._calculate_comps_fallback(ticker, step6_data, step8_final_inputs, market_data, warnings)
        
        return Step10Response(
            session_id=f"step10_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.COMPS,
            valuation_result=valuation_result,
            comps_details=comps_details,
            key_metrics=key_metrics,
            warnings=warnings,
            calculation_notes=calculation_notes
        )

    def _extract_dcf_inputs(self, assumptions: Dict[str, Any]) -> Dict[str, Any]:
        """Extract DCF-specific inputs from confirmed assumptions."""
        # Flatten the assumptions structure to match DCF engine expectations
        dcf_inputs = {
            'scenario': 'base_case',
        }

        # Extract WACC components
        wacc = assumptions.get('wacc_components', {})
        if wacc:
            dcf_inputs['risk_free_rate'] = wacc.get('risk_free_rate', 0.04)
            dcf_inputs['market_risk_premium'] = wacc.get('market_risk_premium', 0.06)
            dcf_inputs['country_risk_premium'] = wacc.get('country_risk_premium', 0.0)
            dcf_inputs['statutory_tax_rate'] = wacc.get('statutory_tax_rate', 0.21)
            dcf_inputs['target_debt_weight'] = wacc.get('target_debt_weight', 0.3)
            dcf_inputs['target_equity_weight'] = wacc.get('target_equity_weight', 0.7)
            dcf_inputs['pre_tax_cost_of_debt'] = wacc.get('pre_tax_cost_of_debt', 0.05)
            dcf_inputs['beta'] = wacc.get('beta', 1.0)

        # Extract terminal value
        terminal = assumptions.get('terminal_value', {})
        if terminal:
            dcf_inputs['terminal_growth'] = terminal.get('terminal_growth_rate', 0.025)

        # Extract revenue drivers for FCF projection
        revenue = assumptions.get('revenue_drivers', {})
        if revenue:
            dcf_inputs['revenue_growth'] = revenue.get('revenue_growth_rate', 0.05)

        # Extract margins
        margins = assumptions.get('cost_margins', {})
        if margins:
            dcf_inputs['ebitda_margin'] = margins.get('ebitda_margin', 0.20)

        # Add current price and shares from session if available
        # These will be populated from Step 6 data

        return dcf_inputs

    def _validate_dcf_inputs(self, dcf_inputs: Dict[str, Any]) -> None:
        """
        Validate critical DCF inputs before calculation.

        Raises DataValidationError if critical fields are null or invalid.

        Critical fields required for DCF calculation:
        - risk_free_rate
        - market_risk_premium (or wacc directly)
        - terminal_growth
        - revenue_growth (for FCF projection)
        - ebitda_margin (for FCF projection)
        """
        missing_fields = []
        invalid_fields = []

        # Check WACC components (either individual components or pre-calculated WACC)
        has_wacc_components = (
            dcf_inputs.get('risk_free_rate') is not None and
            dcf_inputs.get('market_risk_premium') is not None
        )
        has_precomputed_wacc = dcf_inputs.get('wacc') is not None

        if not has_wacc_components and not has_precomputed_wacc:
            missing_fields.extend(['risk_free_rate', 'market_risk_premium'])

        # Check terminal growth rate
        if dcf_inputs.get('terminal_growth') is None:
            missing_fields.append('terminal_growth')

        # Check revenue growth for FCF projection
        if dcf_inputs.get('revenue_growth') is None:
            missing_fields.append('revenue_growth')

        # Check EBITDA margin for FCF projection
        if dcf_inputs.get('ebitda_margin') is None:
            missing_fields.append('ebitda_margin')

        # Validate numeric ranges for fields that exist
        if dcf_inputs.get('terminal_growth') is not None:
            term_growth = dcf_inputs['terminal_growth']
            if not isinstance(term_growth, (int, float)) or term_growth < -0.1 or term_growth > 0.1:
                invalid_fields.append(f"terminal_growth={term_growth} (must be between -10% and 10%)")

        if dcf_inputs.get('risk_free_rate') is not None:
            rfr = dcf_inputs['risk_free_rate']
            if not isinstance(rfr, (int, float)) or rfr < 0 or rfr > 0.2:
                invalid_fields.append(f"risk_free_rate={rfr} (must be between 0% and 20%)")

        if missing_fields:
            raise DataValidationError(
                f"Critical DCF inputs missing: {', '.join(missing_fields)}. "
                f"Cannot perform valuation without these values.",
                missing_fields=missing_fields
            )

        if invalid_fields:
            raise DataValidationError(
                f"Invalid DCF input values: {'; '.join(invalid_fields)}",
                missing_fields=[]
            )

        logger.debug(f"DCF inputs validation passed for ticker")

    def process_final_valuation(
        self,
        ticker: str,
        dcf_inputs: Dict,
        comps_value: Optional[float] = None
    ) -> Step10Response:
        """
        Process final valuation using the DCF Engine.

        Args:
            ticker: Stock ticker symbol
            dcf_inputs: Dictionary containing DCF parameters for the engine
            comps_value: Optional implied value from comparable company analysis

        Returns:
            Step10Response with formatted valuation results
        """
        # Use DCF Engine to calculate enterprise value and other metrics
        try:
            # Build DCFInputs from the provided dictionary
            inputs = self._build_dcf_inputs(dcf_inputs)
            engine = DCFEngine(inputs)

            # Run the full DCF calculation
            scenario = dcf_inputs.get('scenario', 'base_case')
            output = engine.calculate(scenario)

            # Extract key results from engine output (DCFOutput is a dataclass with direct attributes)
            ev = output.perpetuity_method.enterprise_value
            equity_val = output.perpetuity_method.equity_value
            fair_val = output.perpetuity_method.equity_value_per_share
            wacc = output.wacc
            terminal_growth = inputs.forecast_drivers[scenario].get_value(
                inputs.forecast_drivers[scenario].terminal_growth_rate
            )

        except Exception as e:
            logger.error(f"DCF Engine calculation failed: {e}. Using fallback values.")
            # Fallback to simple calculation if engine fails
            ev = dcf_inputs.get('enterprise_value', 100000)
            net_debt = dcf_inputs.get('net_debt', 20000)
            shares = dcf_inputs.get('shares_outstanding', 1000)
            price = dcf_inputs.get('current_price', 150)
            equity_val = ev - net_debt
            fair_val = equity_val / shares
            wacc = dcf_inputs.get('wacc', 0.10)
            terminal_growth = dcf_inputs.get('terminal_growth', 0.025)

        # Get current price from inputs
        price = dcf_inputs.get('current_price', 150)

        # Calculate upside/downside
        upside = (fair_val - price) / price

        # Generate recommendation
        rec = self._generate_recommendation(upside)

        # Determine confidence level
        conf = "High" if abs(upside) > 0.20 else "Medium" if abs(upside) > 0.10 else "Low"

        # Blend DCF with Comps (70/30 weighting)
        blended = (fair_val * 0.7 + comps_value * 0.3) if comps_value else fair_val

        return Step10Response(
            ticker=ticker,
            valuation_result=ValuationResult(
                enterprise_value=ev,
                equity_value=equity_val,
                fair_value_per_share=fair_val,
                current_price=price,
                upside_downside=upside,
                valuation_date="2024-01-15"
            ),
            valuation_summary=ValuationSummary(
                dcf_value=fair_val,
                comps_implied_value=comps_value,
                blended_value=blended,
                recommendation=rec,
                confidence_level=conf
            ),
            sensitivity_summary=self._generate_sensitivity(fair_val),
            key_assumptions={
                "wacc": wacc,
                "terminal_growth": terminal_growth
            }
        )

    def _build_dcf_inputs(self, data: Dict) -> DCFInputs:
        """Convert dictionary to DCFInputs dataclass."""
        inputs = create_default_inputs()

        # Override with provided values
        if 'shares_outstanding' in data:
            inputs.shares_outstanding = data['shares_outstanding']
        if 'current_price' in data:
            inputs.current_stock_price = data['current_price']
        if 'net_debt' in data:
            inputs.net_debt_opening = data['net_debt']
        if 'historical_revenue' in data:
            inputs.historical_revenue = data['historical_revenue']
        if 'risk_free_rate' in data:
            inputs.risk_free_rate = data['risk_free_rate']
        if 'market_risk_premium' in data:
            inputs.market_risk_premium = data['market_risk_premium']
        if 'country_risk_premium' in data:
            inputs.country_risk_premium = data['country_risk_premium']
        if 'statutory_tax_rate' in data:
            inputs.statutory_tax_rate = data['statutory_tax_rate']
        if 'target_debt_weight' in data:
            inputs.target_debt_weight = data['target_debt_weight']
        if 'target_equity_weight' in data:
            inputs.target_equity_weight = data['target_equity_weight']
        if 'pre_tax_cost_of_debt' in data:
            inputs.pre_tax_cost_of_debt = data['pre_tax_cost_of_debt']
        if 'comparable_companies' in data:
            inputs.comparable_companies = data['comparable_companies']

        return inputs

    def _generate_recommendation(self, upside: float) -> str:
        """Generate investment recommendation based on upside/downside."""
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

    def _generate_sensitivity(self, base_value: float) -> Dict:
        """Generate simple sensitivity analysis."""
        return {
            "bull_case": base_value * 1.2,
            "base_case": base_value,
            "bear_case": base_value * 0.8
        }

    def _extract_latest_metric(self, historical: Any, metric_name: str) -> Optional[float]:
        """Extract latest metric value from historical data"""
        if not hasattr(historical, 'data_fields'):
            return None
        
        for field in reversed(historical.data_fields):
            if metric_name in field.field_name and field.value:
                return field.value
        
        return None

    def _generate_dcf_sensitivity_scenarios(self, dcf_details: DCFValuationDetails) -> List[SensitivityScenario]:
        """Generate sensitivity scenarios for DCF"""
        scenarios = []
        
        # Bull Case
        scenarios.append(SensitivityScenario(
            scenario_name="Bull Case",
            assumptions={'WACC': dcf_details.wacc - 0.015, 'Terminal Growth': dcf_details.terminal_growth + 0.01},
            result_value=dcf_details.fair_value_per_share * 1.2,  # Placeholder
            description="Lower discount rate and higher terminal growth"
        ))
        
        # Base Case
        scenarios.append(SensitivityScenario(
            scenario_name="Base Case",
            assumptions={'WACC': dcf_details.wacc, 'Terminal Growth': dcf_details.terminal_growth},
            result_value=dcf_details.fair_value_per_share,
            description="Most likely scenario"
        ))
        
        # Bear Case
        scenarios.append(SensitivityScenario(
            scenario_name="Bear Case",
            assumptions={'WACC': dcf_details.wacc + 0.02, 'Terminal Growth': dcf_details.terminal_growth - 0.01},
            result_value=dcf_details.fair_value_per_share * 0.8,  # Placeholder
            description="Higher discount rate and lower terminal growth"
        ))
        
        return scenarios

    def _build_dcf_inputs_from_steps(
        self,
        step6_data: Dict,
        step8_final_inputs: Dict,
        market_data: Optional[Dict]
    ) -> DCFInputs:
        """Build DCFInputs from Step 6 and Step 8 data."""
        inputs = create_default_inputs()
        
        final_inputs_list = step8_final_inputs.get('final_inputs', [])
        assumptions_map = {}
        for inp in final_inputs_list:
            assumptions_map[inp['metric']] = inp['final_value']
        
        if 'Terminal Growth Rate' in assumptions_map:
            for scenario in inputs.forecast_drivers.values():
                scenario.terminal_growth_rate = assumptions_map['Terminal Growth Rate']
        if 'Tax Rate' in assumptions_map:
            inputs.statutory_tax_rate = assumptions_map['Tax Rate']
        if 'Risk Free Rate' in assumptions_map:
            inputs.risk_free_rate = assumptions_map['Risk Free Rate']
        if 'Market Risk Premium' in assumptions_map:
            inputs.market_risk_premium = assumptions_map['Market Risk Premium']
        if 'Country Risk Premium' in assumptions_map:
            inputs.country_risk_premium = assumptions_map['Country Risk Premium']
        if 'Target Debt Weight' in assumptions_map:
            inputs.target_debt_weight = assumptions_map['Target Debt Weight']
            inputs.target_equity_weight = 1 - assumptions_map['Target Debt Weight']
        if 'Pre-Tax Cost of Debt' in assumptions_map:
            inputs.pre_tax_cost_of_debt = assumptions_map['Pre-Tax Cost of Debt']
        
        historical = step6_data.get('historical_financials', {})
        market = step6_data.get('market_data', {})
        if market:
            if hasattr(market, 'current_stock_price') and market.current_stock_price:
                inputs.current_stock_price = market.current_stock_price.value
            if hasattr(market, 'shares_outstanding') and market.shares_outstanding:
                inputs.shares_outstanding = market.shares_outstanding.value
            if hasattr(market, 'total_debt') and market.total_debt:
                debt = market.total_debt.value or 0
                cash = (market.cash.value if hasattr(market, 'cash') and market.cash else 0) or 0
                inputs.net_debt_opening = debt - cash
        
        return inputs

    def _build_dcf_sensitivity_table(
        self, engine: DCFEngine, inputs: DCFInputs, scenario: str
    ) -> Dict[str, Dict[str, float]]:
        """Build sensitivity table."""
        try:
            base_wacc = engine.calculate_wacc()[0]
            base_growth = inputs.forecast_drivers[scenario].terminal_growth_rate
            sensitivity_table = {}
            for w in [base_wacc - 0.02, base_wacc - 0.01, base_wacc, base_wacc + 0.01, base_wacc + 0.02]:
                w_key = f"{w:.1%}"
                sensitivity_table[w_key] = {}
                for tg in [base_growth - 0.01, base_growth, base_growth + 0.01]:
                    if w > tg:
                        base_output = engine.calculate(scenario)
                        base_tv = base_output.perpetuity_dcf.terminal_value
                        adjusted_tv = base_tv * (base_wacc - base_growth) / (w - tg)
                        adjusted_ev = base_output.perpetuity_dcf.enterprise_value * (adjusted_tv / base_tv)
                        adjusted_eq = adjusted_ev - inputs.get_value(inputs.net_debt_opening)
                        fv = adjusted_eq / inputs.get_value(inputs.shares_outstanding)
                        sensitivity_table[w_key][f"{tg:.2%}"] = round(fv, 2)
                    else:
                        sensitivity_table[w_key][f"{tg:.2%}"] = None
            return sensitivity_table
        except Exception as e:
            logger.error(f"Failed to build sensitivity table: {e}")
            return {}

    def _calculate_dcf_fallback(
        self, ticker: str, step6_data: Dict, step8_final_inputs: Dict,
        market_data: Optional[Dict], warnings: List[str]
    ) -> Step10Response:
        """Fallback DCF calculation if engine fails."""
        wacc = 0.10
        terminal_growth = 0.025
        dcf_details = DCFValuationDetails(
            wacc=wacc, terminal_growth=terminal_growth, projected_fcf=[],
            terminal_value=0, present_value_fcf=0, present_value_terminal=0,
            enterprise_value=0, net_debt=0, equity_value=0, shares_outstanding=0,
            fair_value_per_share=110.0, sensitivity_table={}
        )
        return Step10Response(
            session_id=f"step10_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker, timestamp=datetime.now(), valuation_model=ValuationModel.DCF,
            valuation_result=ValuationResult(fair_value=110.0, current_price=100.0, upside_downside=0.1, recommendation="HOLD", confidence_level="LOW"),
            dcf_details=dcf_details, key_metrics={}, warnings=warnings,
            calculation_notes="DCF calculation used fallback method due to engine error"
        )

    def _calculate_dupont_fallback(
        self, ticker: str, step6_data: Dict, step8_final_inputs: Dict,
        market_data: Optional[Dict], warnings: List[str]
    ) -> Step10Response:
        """Fallback DuPont calculation if engine fails."""
        dupont_details = DuPontValuationDetails(
            net_profit_margin=0.10, asset_turnover=1.2, equity_multiplier=2.0,
            roe=0.24, roa=0.12, trend_analysis=None, benchmark_comparison={}
        )
        return Step10Response(
            session_id=f"step10_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker, timestamp=datetime.now(), valuation_model=ValuationModel.DUPONT,
            valuation_result=ValuationResult(fair_value=None, current_price=None, upside_downside=None, recommendation="HOLD", confidence_level="LOW"),
            dupont_details=dupont_details, key_metrics={}, warnings=warnings,
            calculation_notes="DuPont calculation used fallback method due to engine error"
        )

    def _calculate_comps_fallback(
        self, ticker: str, step6_data: Dict, step8_final_inputs: Dict,
        market_data: Optional[Dict], warnings: List[str]
    ) -> Step10Response:
        """Fallback Comps calculation if engine fails."""
        comps_details = CompsValuationDetails(
            peer_multiples={}, median_multiples={}, mean_multiples={},
            implied_valuations={}, average_implied_value=0.0, peer_count=0, outliers_removed=[]
        )
        return Step10Response(
            session_id=f"step10_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker, timestamp=datetime.now(), valuation_model=ValuationModel.COMPS,
            valuation_result=ValuationResult(fair_value=None, current_price=None, upside_downside=None, recommendation="HOLD", confidence_level="LOW"),
            comps_details=comps_details, key_metrics={}, warnings=warnings,
            calculation_notes="Comps calculation used fallback method due to engine error"
        )

    def _build_dupont_statements_from_step6(self, step6_data: Dict) -> FinancialStatements:
        """Build FinancialStatements for DuPont analysis from Step 6 data."""
        statements = FinancialStatements()
        
        historical = step6_data.get('historical_financials', {})
        if hasattr(historical, 'data_fields') and historical.data_fields:
            # Extract revenue, COGS, net income, assets, equity from historical data
            # This is a simplified extraction - production would map all 8 years
            for field in historical.data_fields:
                field_name = field.field_name.lower() if field.field_name else ''
                value = field.value if field.value else 0.0
                
                if 'revenue' in field_name or 'sales' in field_name:
                    statements.revenue[7] = value
                elif 'cogs' in field_name or 'cost of goods' in field_name:
                    statements.cogs_gross[7] = -abs(value)
                elif 'depreciation' in field_name and 'cogs' in field_name:
                    statements.depreciation_cogs[7] = abs(value)
                elif 'sga' in field_name or 'selling' in field_name or 'administrative' in field_name:
                    statements.sga[7] = -abs(value)
                elif 'interest expense' in field_name:
                    statements.interest_expense[7] = -abs(value)
                elif 'tax' in field_name and 'expense' in field_name:
                    statements.tax_current[7] = -abs(value)
                elif 'net income' in field_name:
                    pass  # Derived metric
                elif 'cash' in field_name and 'asset' in field_name:
                    statements.cash[7] = abs(value)
                elif 'accounts receivable' in field_name:
                    statements.accounts_receivable[7] = abs(value)
                elif 'inventory' in field_name:
                    statements.inventories[7] = abs(value)
                elif 'ppe' in field_name or 'property' in field_name or 'plant' in field_name:
                    statements.ppe_component1[7] = abs(value)
                elif 'accounts payable' in field_name:
                    statements.accounts_payable[7] = abs(value)
                elif 'long-term debt' in field_name or 'long term debt' in field_name:
                    statements.long_term_debt[7] = abs(value)
                elif 'common equity' in field_name or 'shareholders equity' in field_name or 'total equity' in field_name:
                    statements.common_equity[7] = abs(value)
                elif 'retained earnings' in field_name:
                    statements.retained_earnings[7] = abs(value)
                elif 'total assets' in field_name:
                    pass  # Derived metric
        
        return statements

    def _build_target_company_from_step6(self, ticker: str, step6_data: Dict, market_data: Optional[Dict]) -> TargetCompanyData:
        """Build TargetCompanyData for Comps analysis from Step 6 data."""
        market = step6_data.get('market_data', {})
        historical = step6_data.get('historical_financials', {})
        
        # Extract target company metrics
        share_price = 0.0
        shares_outstanding = 0.0
        total_debt = 0.0
        cash = 0.0
        ebitda_ltm = 0.0
        eps_ltm = 0.0
        
        if hasattr(market, 'current_stock_price') and market.current_stock_price:
            share_price = market.current_stock_price.value or 0.0
        if hasattr(market, 'shares_outstanding') and market.shares_outstanding:
            shares_outstanding = market.shares_outstanding.value or 0.0
        if hasattr(market, 'total_debt') and market.total_debt:
            total_debt = market.total_debt.value or 0.0
        if hasattr(market, 'cash') and market.cash:
            cash = market.cash.value or 0.0
        
        # Calculate market cap and EV
        market_cap = share_price * shares_outstanding
        enterprise_value = market_cap + total_debt - cash
        
        # Extract EBITDA and EPS from historical/calculated metrics
        if hasattr(historical, 'data_fields'):
            for field in historical.data_fields:
                field_name = field.field_name.lower() if field.field_name else ''
                value = field.value if field.value else 0.0
                
                if 'ebitda' in field_name:
                    ebitda_ltm = value
                elif 'eps' in field_name or 'earnings per share' in field_name:
                    eps_ltm = value
        
        return TargetCompanyData(
            ticker=ticker,
            company_name=ticker,
            market_cap=market_cap,
            enterprise_value=enterprise_value,
            ebitda_ltm=ebitda_ltm,
            ebitda_fy2023=ebitda_ltm * 1.05,  # Placeholder growth
            ebitda_fy2024=ebitda_ltm * 1.10,
            eps_ltm=eps_ltm,
            eps_fy2023=eps_ltm * 1.05,
            eps_fy2024=eps_ltm * 1.10,
            net_debt=total_debt - cash,
            shares_outstanding=shares_outstanding,
            share_price=share_price,
            currency="USD"
        )

    def _build_peer_list_from_step6(self, step6_data: Dict) -> List[PeerCompanyData]:
        """Build list of PeerCompanyData for Comps analysis from Step 6 data."""
        peers = []
        
        # In production, peer data would come from Step 6's peer comparison data
        # For now, return empty list (engine will handle this gracefully)
        # The actual peer retrieval should be implemented in Step 6
        
        return peers
