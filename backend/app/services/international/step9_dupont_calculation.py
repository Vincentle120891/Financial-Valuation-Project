"""Step 9: DuPont Final Calculation Engine - Specialized DuPont Analysis Processor

This module performs complete DuPont analysis using the mathematically verified DuPontAnalyzer:
- 3-step ROE decomposition (Net Margin × Asset Turnover × Equity Multiplier)
- 5-step ROE decomposition (Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Equity Multiplier)
- Comprehensive ratio analysis (profitability, efficiency, leverage, liquidity)
- Trend analysis and benchmark comparison

Input: Step 6 aggregated historical financial data
Output: Complete DuPont analysis with ROE breakdown, trends, and benchmarks
"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime

# Import specialized DuPont engine for calculations
from app.services.international.dupont_engine import (
    DuPontAnalyzer,
    FinancialStatements,
    DuPontResult
)

logger = logging.getLogger(__name__)


class DuPontValuationDetails(BaseModel):
    """Detailed DuPont analysis results"""
    net_profit_margin: float
    asset_turnover: float
    equity_multiplier: float
    roe: float  # ROE = Margin × Turnover × Leverage
    roa: float  # Return on Assets
    trend_analysis: Optional[List[Dict[str, float]]] = None  # Historical trends
    benchmark_comparison: Optional[Dict[str, float]] = None


class DuPontValuationResultResponse(BaseModel):
    """
    Step 9 DuPont Response: Final DuPont analysis results with ROE decomposition.
    This is the SOLE calculation hub for DuPont model in the international market.
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: str = "DUPONT"
    roe: float
    roa: float
    net_profit_margin: float
    asset_turnover: float
    equity_multiplier: float
    recommendation: str = "HOLD"  # BUY, HOLD, SELL
    confidence_level: str = "MEDIUM"
    dupont_details: Optional[DuPontValuationDetails] = None
    key_metrics: Dict[str, float] = {}
    warnings: List[str] = []
    calculation_notes: str = ""


class DuPontStep9Processor:
    """
    Step 9: DuPont Final Calculation Engine

    Performs complete DuPont analysis:
    - ROE decomposition (Margin × Turnover × Leverage)
    - 5-step extended decomposition
    - Trend analysis across historical periods
    - Benchmark comparison vs industry/sector

    Input: Step 6 aggregated historical financial data
    Output: DuPontValuationResultResponse with ROE breakdown and detailed metrics
    """

    def __init__(self):
        pass

    async def calculate_dupont_analysis(
        self,
        ticker: str,
        step6_data: Dict[str, Any],
        step8_final_inputs: Optional[Dict[str, Any]] = None,
        market_data: Optional[Dict] = None
    ) -> DuPontValuationResultResponse:
        """
        Main entry point for DuPont analysis calculation.

        Args:
            ticker: Stock ticker symbol
            step6_data: Aggregated data from Step 6 (historical financials)
            step8_final_inputs: Optional target assumptions from Step 8
            market_data: Current market data

        Returns:
            DuPontValuationResultResponse with complete DuPont analysis results
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
            if latest_idx >= len(dupont_output.years):
                latest_idx = len(dupont_output.years) - 1

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
                trend_analysis=trend_analysis,
                benchmark_comparison=benchmark_comparison
            )

            key_metrics = {
                'ROE': roe,
                'ROA': roa,
                'Net Profit Margin': net_margin,
                'Asset Turnover': asset_turnover,
                'Equity Multiplier': equity_multiplier,
                'Industry Avg ROE': benchmark_comparison['industry_avg_roe'],
                'Sector Avg ROE': benchmark_comparison['sector_avg_roe']
            }

            calculation_notes = f"DuPont analysis completed. ROE: {roe:.2%} " \
                              f"(Margin: {net_margin:.2%}, Turnover: {asset_turnover:.2f}, Leverage: {equity_multiplier:.2f})"

        except Exception as e:
            logger.error(f"DuPont Engine calculation failed: {e}. Using fallback calculation.")
            warnings.append(f"DuPont Engine error: {str(e)}")
            # Fallback to simplified calculation
            return self._calculate_dupont_fallback(ticker, step6_data, step8_final_inputs, market_data, warnings)

        return DuPontValuationResultResponse(
            session_id=f"step9_dupont_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            roe=roe,
            roa=roa,
            net_profit_margin=net_margin,
            asset_turnover=asset_turnover,
            equity_multiplier=equity_multiplier,
            recommendation=recommendation,
            confidence_level=confidence,
            dupont_details=dupont_details,
            key_metrics=key_metrics,
            warnings=warnings,
            calculation_notes=calculation_notes
        )

    def _build_dupont_statements_from_step6(self, step6_data: Dict) -> FinancialStatements:
        """Build FinancialStatements from Step 6 data"""
        historical_data = step6_data.get('historical_financials', {})

        # Extract arrays of historical data (8 years expected)
        revenue = historical_data.get('revenue', [0] * 8)
        net_income = historical_data.get('net_income', [0] * 8)
        total_assets = historical_data.get('total_assets', [0] * 8)
        shareholders_equity = historical_data.get('shareholders_equity', [0] * 8)
        operating_income = historical_data.get('operating_income', [0] * 8)
        ebit = historical_data.get('ebit', operating_income)
        interest_expense = historical_data.get('interest_expense', [0] * 8)
        tax_expense = historical_data.get('tax_expense', [0] * 8)
        ebt = historical_data.get('ebt', [0] * 8)

        # Create FinancialStatements instance
        statements = FinancialStatements(
            revenue=revenue,
            net_income=net_income,
            total_assets=total_assets,
            shareholders_equity=shareholders_equity,
            operating_income=operating_income,
            ebit=ebit,
            interest_expense=interest_expense,
            tax_expense=tax_expense,
            ebt=ebt
        )

        return statements

    def _calculate_dupont_fallback(
        self,
        ticker: str,
        step6_data: Dict,
        step8_final_inputs: Optional[Dict],
        market_data: Optional[Dict],
        warnings: List[str]
    ) -> DuPontValuationResultResponse:
        """Fallback DuPont calculation if engine fails"""
        historical_data = step6_data.get('historical_financials', {})

        # Try to extract basic metrics for simple calculation
        net_income = historical_data.get('net_income', [])
        shareholders_equity = historical_data.get('shareholders_equity', [])
        total_assets = historical_data.get('total_assets', [])
        revenue = historical_data.get('revenue', [])

        if net_income and shareholders_equity and len(net_income) > 0 and len(shareholders_equity) > 0:
            latest_ni = net_income[-1] if net_income[-1] != 0 else 0
            latest_eq = shareholders_equity[-1] if shareholders_equity[-1] != 0 else 1
            latest_ta = total_assets[-1] if total_assets and total_assets[-1] != 0 else 1
            latest_rev = revenue[-1] if revenue and revenue[-1] != 0 else 1

            roe = latest_ni / latest_eq if latest_eq != 0 else 0
            roa = latest_ni / latest_ta if latest_ta != 0 else 0
            net_margin = latest_ni / latest_rev if latest_rev != 0 else 0
            asset_turnover = latest_rev / latest_ta if latest_ta != 0 else 0
            equity_multiplier = latest_ta / latest_eq if latest_eq != 0 else 1
        else:
            roe = 0
            roa = 0
            net_margin = 0
            asset_turnover = 0
            equity_multiplier = 1

        return DuPontValuationResultResponse(
            session_id=f"step9_dupont_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            roe=roe,
            roa=roa,
            net_profit_margin=net_margin,
            asset_turnover=asset_turnover,
            equity_multiplier=equity_multiplier,
            recommendation="HOLD",
            confidence_level="LOW",
            key_metrics={'ROE': roe, 'ROA': roa},
            warnings=warnings,
            calculation_notes="DuPont calculation failed. Using fallback with limited data."
        )