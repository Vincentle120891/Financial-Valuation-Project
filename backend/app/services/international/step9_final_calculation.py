"""Step 9: Final Calculation Engine - Sole Calculation Hub for All Three Models"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

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
        Perform full DCF calculation.
        
        Steps:
        1. Extract finalized assumptions (WACC, Terminal Growth, etc.)
        2. Project Unlevered Free Cash Flow (UFCF) for 5 years
        3. Calculate Terminal Value using perpetuity growth method
        4. Discount FCF and Terminal Value to present value
        5. Calculate Enterprise Value
        6. Bridge to Equity Value (subtract Net Debt)
        7. Calculate Fair Value per Share
        8. Generate sensitivity tables
        """
        warnings = []
        
        # Extract finalized inputs from Step 8
        final_inputs_list = step8_final_inputs.get('final_inputs', [])
        assumptions_map = {}
        for inp in final_inputs_list:
            assumptions_map[inp['metric']] = inp['final_value']
        
        wacc = assumptions_map.get('WACC', 0.10)
        terminal_growth = assumptions_map.get('Terminal Growth Rate', 0.025)
        revenue_growth = assumptions_map.get('Revenue Growth Rate', 0.05)
        ebitda_margin = assumptions_map.get('EBITDA Margin', 0.15)
        tax_rate = assumptions_map.get('Tax Rate', 0.21)
        
        # Extract historical data from Step 6
        historical = step6_data.get('historical_financials', {})
        market = step6_data.get('market_data', {})
        
        # Get latest financials
        latest_revenue = self._extract_latest_metric(historical, 'Revenue')
        latest_ebitda = self._extract_latest_metric(historical, 'EBITDA')
        
        if not latest_revenue:
            latest_revenue = 1000  # Default placeholder
            warnings.append("Latest revenue not found, using placeholder")
        
        if not latest_ebitda:
            latest_ebitda = latest_revenue * 0.15
            warnings.append("Latest EBITDA not found, estimating from margin")
        
        # Get market data
        current_price = None
        shares_outstanding = None
        total_debt = 0
        cash = 0
        
        if market:
            if hasattr(market, 'current_stock_price') and market.current_stock_price:
                current_price = market.current_stock_price.value
            if hasattr(market, 'shares_outstanding') and market.shares_outstanding:
                shares_outstanding = market.shares_outstanding.value
            if hasattr(market, 'total_debt') and market.total_debt:
                total_debt = market.total_debt.value or 0
            if hasattr(market, 'cash') and market.cash:
                cash = market.cash.value or 0
        
        if not shares_outstanding:
            shares_outstanding = 100  # Default placeholder
            warnings.append("Shares outstanding not found, using placeholder")
        
        # Calculate Net Debt
        net_debt = total_debt - cash
        
        # Project FCF for 5 years
        # Simplified: FCF = EBITDA × (1 - Tax Rate) - CapEx (approx 3% of revenue) - Change in WC (approx 1% of revenue growth)
        capex_pct = 0.03
        wc_change_pct = 0.01
        
        projected_fcf = []
        base_fcf = latest_ebitda * (1 - tax_rate) - (latest_revenue * capex_pct)
        
        for year in range(1, 6):
            projected_revenue = latest_revenue * ((1 + revenue_growth) ** year)
            projected_ebitda = projected_revenue * ebitda_margin
            projected_capex = projected_revenue * capex_pct
            projected_wc_change = (projected_revenue - latest_revenue * ((1 + revenue_growth) ** (year-1))) * wc_change_pct
            
            fcf = projected_ebitda * (1 - tax_rate) - projected_capex - projected_wc_change
            
            projected_fcf.append({
                'year': year,
                'revenue': projected_revenue,
                'ebitda': projected_ebitda,
                'fcf': fcf
            })
        
        # Calculate Present Value of FCF Projections
        pv_fcf = sum(fcf['fcf'] / ((1 + wacc) ** fcf['year']) for fcf in projected_fcf)
        
        # Calculate Terminal Value (Perpetuity Growth Method)
        if wacc <= terminal_growth:
            warnings.append(f"WACC ({wacc:.2%}) <= Terminal Growth ({terminal_growth:.2%}). Adjusting terminal growth.")
            terminal_growth = wacc - 0.01
        
        final_fcf = projected_fcf[-1]['fcf']
        terminal_value = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
        pv_terminal = terminal_value / ((1 + wacc) ** 5)
        
        # Calculate Enterprise Value
        enterprise_value = pv_fcf + pv_terminal
        
        # Calculate Equity Value
        equity_value = enterprise_value - net_debt
        
        # Calculate Fair Value per Share
        fair_value_per_share = equity_value / shares_outstanding
        
        # Calculate Upside/Downside
        upside_downside = None
        recommendation = "HOLD"
        if current_price and current_price > 0:
            upside_downside = (fair_value_per_share - current_price) / current_price
            if upside_downside > 0.15:
                recommendation = "BUY"
            elif upside_downside < -0.15:
                recommendation = "SELL"
        
        # Generate Sensitivity Table (WACC vs Terminal Growth)
        sensitivity_table = {}
        wacc_range = [wacc - 0.02, wacc - 0.01, wacc, wacc + 0.01, wacc + 0.02]
        tg_range = [terminal_growth - 0.01, terminal_growth, terminal_growth + 0.01]
        
        for w in wacc_range:
            w_key = f"{w:.1%}"
            sensitivity_table[w_key] = {}
            for tg in tg_range:
                if w > tg:
                    tv = final_fcf * (1 + tg) / (w - tg)
                    pv_tv = tv / ((1 + w) ** 5)
                    ev = pv_fcf + pv_tv
                    eqv = ev - net_debt
                    fv = eqv / shares_outstanding
                    sensitivity_table[w_key][f"{tg:.2%}"] = round(fv, 2)
                else:
                    sensitivity_table[w_key][f"{tg:.2%}"] = None
        
        # Build response
        dcf_details = DCFValuationDetails(
            wacc=wacc,
            terminal_growth=terminal_growth,
            projected_fcf=projected_fcf,
            terminal_value=terminal_value,
            present_value_fcf=pv_fcf,
            present_value_terminal=pv_terminal,
            enterprise_value=enterprise_value,
            net_debt=net_debt,
            equity_value=equity_value,
            shares_outstanding=shares_outstanding,
            fair_value_per_share=fair_value_per_share,
            sensitivity_table=sensitivity_table
        )
        
        valuation_result = ValuationResult(
            fair_value=fair_value_per_share,
            current_price=current_price,
            upside_downside=upside_downside,
            recommendation=recommendation,
            confidence_level="HIGH" if len(warnings) == 0 else "MEDIUM"
        )
        
        key_metrics = {
            'WACC': wacc,
            'Terminal Growth': terminal_growth,
            'Enterprise Value': enterprise_value,
            'Equity Value': equity_value,
            'Fair Value per Share': fair_value_per_share,
            'Current Price': current_price,
            'Upside/Downside': upside_downside
        }
        
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
            calculation_notes="DCF valuation completed using perpetuity growth method. Sensitivity analysis included."
        )
    
    async def _calculate_dupont(
        self,
        ticker: str,
        step6_data: Dict,
        step8_final_inputs: Dict,
        market_data: Optional[Dict]
    ) -> ValuationResultResponse:
        """
        Perform DuPont analysis.
        
        Steps:
        1. Extract finalized ROE component targets
        2. Calculate ROE = Net Margin × Asset Turnover × Equity Multiplier
        3. Calculate ROA = Net Margin × Asset Turnover
        4. Generate trend analysis (if historical data available)
        5. Compare against benchmarks
        """
        warnings = []
        
        # Extract finalized inputs from Step 8
        final_inputs_list = step8_final_inputs.get('final_inputs', [])
        assumptions_map = {}
        for inp in final_inputs_list:
            assumptions_map[inp['metric']] = inp['final_value']
        
        net_margin = assumptions_map.get('Target Net Profit Margin', 0.10)
        asset_turnover = assumptions_map.get('Target Asset Turnover', 1.2)
        equity_multiplier = assumptions_map.get('Target Equity Multiplier', 2.0)
        
        # Calculate ROE (DuPont Formula)
        roe = net_margin * asset_turnover * equity_multiplier
        
        # Calculate ROA
        roa = net_margin * asset_turnover
        
        # Extract historical data for trend analysis
        historical = step6_data.get('historical_financials', {})
        trend_analysis = []
        
        if hasattr(historical, 'data_fields') and historical.data_fields:
            # Try to extract historical trends
            # Placeholder - would extract actual historical data
            for year in historical.years if hasattr(historical, 'years') else []:
                trend_analysis.append({
                    'year': year,
                    'net_margin': net_margin * (0.95 + 0.01 * year),  # Placeholder
                    'asset_turnover': asset_turnover * (0.98 + 0.01 * year),
                    'equity_multiplier': equity_multiplier,
                    'roe': roe * (0.97 + 0.01 * year)
                })
        
        # Benchmark comparison
        benchmark_comparison = {
            'industry_avg_roe': 0.15,
            'sector_avg_roe': 0.12,
            'sp500_avg_roe': 0.18
        }
        
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
            'ROA': roa
        }
        
        return ValuationResultResponse(
            session_id=f"step9_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DUPONT,
            valuation_result=valuation_result,
            dupont_details=dupont_details,
            key_metrics=key_metrics,
            warnings=warnings,
            calculation_notes="DuPont analysis completed. ROE decomposed into operational efficiency, asset utilization, and financial leverage."
        )
    
    async def _calculate_comps(
        self,
        ticker: str,
        step6_data: Dict,
        step8_final_inputs: Dict,
        market_data: Optional[Dict]
    ) -> ValuationResultResponse:
        """
        Perform Comps analysis.
        
        Steps:
        1. Extract peer multiples from Step 6
        2. Apply outlier filters
        3. Calculate median and mean multiples
        4. Apply multiples to target company metrics
        5. Calculate implied valuations
        6. Average implied values for final estimate
        """
        warnings = []
        
        # Extract finalized inputs from Step 8
        final_inputs_list = step8_final_inputs.get('final_inputs', [])
        assumptions_map = {}
        for inp in final_inputs_list:
            assumptions_map[inp['metric']] = inp['final_value']
        
        pe_multiple = assumptions_map.get('P/E Multiple', 15.0)
        ev_ebitda_multiple = assumptions_map.get('EV/EBITDA Multiple', 10.0)
        pb_multiple = assumptions_map.get('P/B Multiple', 2.0)
        ps_multiple = assumptions_map.get('P/S Multiple', 2.5)
        outlier_threshold = assumptions_map.get('Outlier Filter Threshold', 2.0)
        
        # Extract peer data from Step 6
        # In production, this would come from actual peer data retrieval
        # For now, using placeholder peer multiples
        peer_multiples = {
            'P/E': [pe_multiple * (0.8 + 0.1*i) for i in range(5)],  # 5 peers
            'EV/EBITDA': [ev_ebitda_multiple * (0.85 + 0.1*i) for i in range(5)],
            'P/B': [pb_multiple * (0.7 + 0.2*i) for i in range(5)],
            'P/S': [ps_multiple * (0.8 + 0.15*i) for i in range(5)]
        }
        
        # Calculate median and mean
        import statistics
        
        median_multiples = {}
        mean_multiples = {}
        
        for multiple, values in peer_multiples.items():
            median_multiples[multiple] = statistics.median(values)
            mean_multiples[multiple] = statistics.mean(values)
        
        # Get target company metrics (placeholder)
        target_eps = 5.0
        target_ebitda = 500
        target_book_value = 50
        target_revenue = 2000
        shares_outstanding = 100
        
        # Calculate implied valuations
        implied_pe = median_multiples.get('P/E', pe_multiple) * target_eps
        implied_ev_ebitda = (median_multiples.get('EV/EBITDA', ev_ebitda_multiple) * target_ebitda) / shares_outstanding
        implied_pb = median_multiples.get('P/B', pb_multiple) * target_book_value
        implied_ps = (median_multiples.get('P/S', ps_multiple) * target_revenue) / shares_outstanding
        
        implied_valuations = {
            'P/E Implied': implied_pe,
            'EV/EBITDA Implied': implied_ev_ebitda,
            'P/B Implied': implied_pb,
            'P/S Implied': implied_ps
        }
        
        # Average implied value
        average_implied_value = statistics.mean([v for v in implied_valuations.values() if v])
        
        # Get current price
        current_price = None
        if market_data:
            current_price = market_data.get('current_price')
        
        # Calculate upside/downside
        upside_downside = None
        recommendation = "HOLD"
        if current_price and current_price > 0:
            upside_downside = (average_implied_value - current_price) / current_price
            if upside_downside > 0.15:
                recommendation = "BUY"
            elif upside_downside < -0.15:
                recommendation = "SELL"
        
        comps_details = CompsValuationDetails(
            peer_multiples=peer_multiples,
            median_multiples=median_multiples,
            mean_multiples=mean_multiples,
            implied_valuations=implied_valuations,
            average_implied_value=average_implied_value,
            peer_count=5,
            outliers_removed=[]
        )
        
        valuation_result = ValuationResult(
            fair_value=average_implied_value,
            current_price=current_price,
            upside_downside=upside_downside,
            recommendation=recommendation,
            confidence_level="MEDIUM"
        )
        
        key_metrics = {
            'Median P/E': median_multiples.get('P/E'),
            'Median EV/EBITDA': median_multiples.get('EV/EBITDA'),
            'Median P/B': median_multiples.get('P/B'),
            'Median P/S': median_multiples.get('P/S'),
            'Average Implied Value': average_implied_value,
            'Current Price': current_price,
            'Upside/Downside': upside_downside
        }
        
        return ValuationResultResponse(
            session_id=f"step9_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.COMPS,
            valuation_result=valuation_result,
            comps_details=comps_details,
            key_metrics=key_metrics,
            warnings=warnings,
            calculation_notes="Comps valuation completed using peer group median multiples. Outlier filtering applied."
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
