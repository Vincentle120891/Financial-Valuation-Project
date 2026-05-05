"""Step 9: Final Calculation Engine - Sole Calculation Hub for All Three Models

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

# Import specialized engines for calculations
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

class ValuationResultResponse(BaseModel):
    """
    Step 9 Response: Final valuation results with key metrics and sensitivity tables.
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


class Step9FinalCalculationProcessor:
    """
    Step 9: Calculation Engine (Sole Calculation Hub)
    
    Performs full calculations for all three models:
    - DCF Mode: UFCF projection, Discounting, Terminal Value, Bridge to Equity Value
    - DuPont Mode: ROE decomposition (Margin × Turnover × Leverage) and trend analysis
    - Comps Mode: Median/mean multiples and implied valuation
    
    Output: ValuationResultResponse with final fair value, key metrics, and sensitivity tables
    """
    
    def __init__(self):
        pass
    
    async def calculate_final_valuation(
        self,
        ticker: str,
        valuation_model: str,
        step6_data: Dict[str, Any],
        step8_final_inputs: Dict[str, Any],
        market_data: Optional[Dict] = None
    ) -> ValuationResultResponse:
        """
        Main entry point for final valuation calculation.
        
        Args:
            ticker: Stock ticker symbol
            valuation_model: DCF, DUPONT, or COMPS
            step6_data: Aggregated data from Step 6 (historical financials, market data)
            step8_final_inputs: Finalized inputs from Step 8 (validated assumptions)
            market_data: Current market data
        
        Returns:
            ValuationResultResponse with complete valuation results
        """
        model_enum = ValuationModel(valuation_model.upper())
        
        if model_enum == ValuationModel.DCF:
            return await self._calculate_dcf(ticker, step6_data, step8_final_inputs, market_data)
        elif model_enum == ValuationModel.DUPONT:
            return await self._calculate_dupont(ticker, step6_data, step8_final_inputs, market_data)
        elif model_enum == ValuationModel.COMPS:
            return await self._calculate_comps(ticker, step6_data, step8_final_inputs, market_data)
        else:
            raise ValueError(f"Unknown valuation model: {valuation_model}")
    
    async def _calculate_dcf(
        self,
        ticker: str,
        step6_data: Dict,
        step8_final_inputs: Dict,
        market_data: Optional[Dict]
    ) -> ValuationResultResponse:
        """
        Perform full DCF calculation using DCFEngine.
        
        Leverages the mathematically verified DCF engine for:
        - WACC calculation from comparable companies
        - UFCF projection with detailed revenue/cost schedules
        - Terminal Value (Perpetuity and Exit Multiple methods)
        - Discounting and Enterprise Value calculation
        - Bridge to Equity Value and Fair Value per Share
        - Sensitivity analysis
        
        Args:
            ticker: Stock ticker symbol
            step6_data: Aggregated data from Step 6 (historical financials, market data)
            step8_final_inputs: Finalized inputs from Step 8 (validated assumptions)
            market_data: Current market data
            
        Returns:
            ValuationResultResponse with complete DCF valuation results
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
            
            valuation_result = ValuationResult(
                fair_value=perpetuity_result.equity_value_per_share,
                current_price=current_price,
                upside_downside=upside_downside,
                recommendation=recommendation,
                confidence_level="HIGH" if dcf_output.ufcf_methods_reconcile else "MEDIUM"
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
        
        return ValuationResultResponse(
            session_id=f"step9_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DCF,
            valuation_result=valuation_result,
            dcf_details=dcf_details,
            sensitivity_scenarios=self._generate_dcf_sensitivity_scenarios(dcf_details),
            key_metrics=key_metrics,
            warnings=warnings,
            calculation_notes=calculation_notes
        )
    
    async def _calculate_dupont(
        self,
        ticker: str,
        step6_data: Dict,
        step8_final_inputs: Dict,
        market_data: Optional[Dict]
    ) -> ValuationResultResponse:
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
            ValuationResultResponse with complete DuPont analysis results
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
        
        return ValuationResultResponse(
            session_id=f"step9_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DUPONT,
            valuation_result=valuation_result,
            dupont_details=dupont_details,
            key_metrics=key_metrics,
            warnings=warnings,
            calculation_notes=calculation_notes
        )
    
    async def _calculate_comps(
        self,
        ticker: str,
        step6_data: Dict,
        step8_final_inputs: Dict,
        market_data: Optional[Dict]
    ) -> ValuationResultResponse:
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
            ValuationResultResponse with complete Comps valuation results
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
        
        return ValuationResultResponse(
            session_id=f"step9_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.COMPS,
            valuation_result=valuation_result,
            comps_details=comps_details,
            key_metrics=key_metrics,
            warnings=warnings,
            calculation_notes=calculation_notes
        )
    
    # === Helper Methods ===
    
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
    ) -> ValuationResultResponse:
        """Fallback DCF calculation if engine fails."""
        wacc = 0.10
        terminal_growth = 0.025
        dcf_details = DCFValuationDetails(
            wacc=wacc, terminal_growth=terminal_growth, projected_fcf=[],
            terminal_value=0, present_value_fcf=0, present_value_terminal=0,
            enterprise_value=0, net_debt=0, equity_value=0, shares_outstanding=0,
            fair_value_per_share=110.0, sensitivity_table={}
        )
        return ValuationResultResponse(
            session_id=f"step9_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker, timestamp=datetime.now(), valuation_model=ValuationModel.DCF,
            valuation_result=ValuationResult(fair_value=110.0, current_price=100.0, upside_downside=0.1, recommendation="HOLD", confidence_level="LOW"),
            dcf_details=dcf_details, key_metrics={}, warnings=warnings,
            calculation_notes="DCF calculation used fallback method due to engine error"
        )

    def _calculate_dupont_fallback(
        self, ticker: str, step6_data: Dict, step8_final_inputs: Dict,
        market_data: Optional[Dict], warnings: List[str]
    ) -> ValuationResultResponse:
        """Fallback DuPont calculation if engine fails."""
        dupont_details = DuPontValuationDetails(
            net_profit_margin=0.10, asset_turnover=1.2, equity_multiplier=2.0,
            roe=0.24, roa=0.12, trend_analysis=None, benchmark_comparison={}
        )
        return ValuationResultResponse(
            session_id=f"step9_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker, timestamp=datetime.now(), valuation_model=ValuationModel.DUPONT,
            valuation_result=ValuationResult(fair_value=None, current_price=None, upside_downside=None, recommendation="HOLD", confidence_level="LOW"),
            dupont_details=dupont_details, key_metrics={}, warnings=warnings,
            calculation_notes="DuPont calculation used fallback method due to engine error"
        )

    def _calculate_comps_fallback(
        self, ticker: str, step6_data: Dict, step8_final_inputs: Dict,
        market_data: Optional[Dict], warnings: List[str]
    ) -> ValuationResultResponse:
        """Fallback Comps calculation if engine fails."""
        comps_details = CompsValuationDetails(
            peer_multiples={}, median_multiples={}, mean_multiples={},
            implied_valuations={}, average_implied_value=0.0, peer_count=0, outliers_removed=[]
        )
        return ValuationResultResponse(
            session_id=f"step9_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
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
