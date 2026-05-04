"""
Step 3: Historical Financial Data Processor
Handles historical financials retrieval, currency conversion, and gap filling.
"""

import logging
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.services.international.yfinance_service import YFinanceService

logger = logging.getLogger(__name__)


class HistoricalYearData(BaseModel):
    """Financial data for a single year."""
    year: str
    revenue: Optional[float] = None
    cogs: Optional[float] = None
    gross_profit: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    net_income: Optional[float] = None
    total_assets: Optional[float] = None
    total_debt: Optional[float] = None
    shareholders_equity: Optional[float] = None
    free_cash_flow: Optional[float] = None
    capex: Optional[float] = None
    depreciation: Optional[float] = None
    status: str = "RETRIEVED"
    source: str = "yfinance"


class CalculatedMetrics(BaseModel):
    """Calculated historical metrics."""
    revenue_cagr_3y: Optional[float] = None
    revenue_cagr_5y: Optional[float] = None
    avg_ebitda_margin: Optional[float] = None
    avg_net_margin: Optional[float] = None
    avg_roe: Optional[float] = None
    avg_roa: Optional[float] = None
    debt_to_equity_avg: Optional[float] = None


class Step3Response(BaseModel):
    """Step 3 response model."""
    ticker: str
    historical_data: List[HistoricalYearData]
    calculated_metrics: CalculatedMetrics
    missing_years: List[str] = []
    missing_fields: Dict[str, List[str]] = {}
    warnings: List[str] = []
    data_quality_score: float = 0.0


class Step3HistoricalProcessor:
    """
    Processor for Step 3: Historical Financial Data.
    
    Responsibilities:
    - Fetch historical financials (3-5 years)
    - Handle currency conversion
    - Fill missing years with estimates
    - Calculate growth rates and margins
    - Flag data gaps
    """
    
    MIN_YEARS_REQUIRED = 3
    IDEAL_YEARS = 5
    
    def __init__(self, yfinance_service: Optional[YFinanceService] = None):
        self.yfinance_service = yfinance_service or YFinanceService()
    
    def process_historical_data(
        self,
        ticker: str,
        market: str = "international",
        years_requested: int = 5
    ) -> Step3Response:
        """
        Process historical financial data.
        
        Args:
            ticker: Ticker symbol
            market: Market type
            years_requested: Number of years to fetch
            
        Returns:
            Step3Response with historical data and metrics
        """
        logger.info(f"Processing historical data for ticker='{ticker}', years={years_requested}")
        
        # Fetch financial statements
        financials = self.yfinance_service.get_financial_statements(ticker)
        
        if not financials:
            return Step3Response(
                ticker=ticker,
                historical_data=[],
                calculated_metrics=CalculatedMetrics(),
                missing_years=[f"All {years_requested} years"],
                warnings=["Could not fetch any financial statements"],
                data_quality_score=0.0
            )
        
        income_stmt = financials.get('income_stmt', {})
        balance_sheet = financials.get('balance_sheet', {})
        cashflow = financials.get('cashflow', {})
        
        # Get available years
        available_years = list(income_stmt.columns)[:years_requested]
        
        # Build historical data for each year
        historical_data: List[HistoricalYearData] = []
        missing_fields: Dict[str, List[str]] = {}
        warnings: List[str] = []
        
        for year in available_years:
            year_data = self._build_year_data(
                year=year,
                income_stmt=income_stmt,
                balance_sheet=balance_sheet,
                cashflow=cashflow
            )
            historical_data.append(year_data)
            
            # Track missing fields
            for field_name, field_value in year_data.dict().items():
                if field_name not in ['year', 'status', 'source'] and field_value is None:
                    if field_name not in missing_fields:
                        missing_fields[field_name] = []
                    missing_fields[field_name].append(year)
        
        # Check for missing years
        missing_years = []
        if len(available_years) < self.MIN_YEARS_REQUIRED:
            missing_years = [f"Year {i+1}" for i in range(self.MIN_YEARS_REQUIRED - len(available_years))]
            warnings.append(f"Only {len(available_years)} years available, minimum {self.MIN_YEARS_REQUIRED} required")
        
        # Calculate metrics
        calculated_metrics = self._calculate_metrics(historical_data)
        
        # Calculate data quality score
        total_fields = len(HistoricalYearData.__fields__) - 2  # Exclude year, status, source
        total_possible = len(historical_data) * total_fields
        actual_data = sum(
            1 for hd in historical_data 
            for k, v in hd.dict().items() 
            if k not in ['year', 'status', 'source'] and v is not None
        )
        data_quality_score = (actual_data / total_possible * 100) if total_possible > 0 else 0
        
        return Step3Response(
            ticker=ticker,
            historical_data=historical_data,
            calculated_metrics=calculated_metrics,
            missing_years=missing_years,
            missing_fields=missing_fields,
            warnings=warnings,
            data_quality_score=data_quality_score
        )
    
    def _build_year_data(
        self,
        year: str,
        income_stmt: Dict,
        balance_sheet: Dict,
        cashflow: Dict
    ) -> HistoricalYearData:
        """Build data for a single year."""
        def get_value(stmt, key):
            if key in stmt.index:
                val = stmt.loc[key, year]
                return float(val) if val and val == val else None  # NaN check
            return None
        
        revenue = get_value(income_stmt, 'Total Revenue')
        cogs = get_value(income_stmt, 'Cost Of Revenue')
        gross_profit = (revenue - cogs) if revenue and cogs else None
        ebitda = get_value(income_stmt, 'EBITDA')
        ebit = get_value(income_stmt, 'EBIT')
        net_income = get_value(income_stmt, 'Net Income')
        
        total_assets = get_value(balance_sheet, 'Total Assets')
        total_debt = get_value(balance_sheet, 'Total Debt')
        shareholders_equity = get_value(balance_sheet, 'Stockholders Equity')
        
        free_cash_flow = get_value(cashflow, 'Free Cash Flow')
        capex = get_value(cashflow, 'Capital Expenditure')
        depreciation = get_value(cashflow, 'Depreciation')
        
        return HistoricalYearData(
            year=str(year),
            revenue=revenue,
            cogs=cogs,
            gross_profit=gross_profit,
            ebitda=ebitda,
            ebit=ebit,
            net_income=net_income,
            total_assets=total_assets,
            total_debt=total_debt,
            shareholders_equity=shareholders_equity,
            free_cash_flow=free_cash_flow,
            capex=capex,
            depreciation=depreciation
        )
    
    def _calculate_metrics(
        self,
        historical_data: List[HistoricalYearData]
    ) -> CalculatedMetrics:
        """Calculate historical metrics from data."""
        revenues = [hd.revenue for hd in historical_data if hd.revenue]
        ebitda_margins = []
        net_margins = []
        roes = []
        roas = []
        debt_to_equities = []
        
        for hd in historical_data:
            if hd.revenue and hd.ebitda:
                ebitda_margins.append(hd.ebitda / hd.revenue)
            if hd.revenue and hd.net_income:
                net_margins.append(hd.net_income / hd.revenue)
            if hd.net_income and hd.shareholders_equity:
                roes.append(hd.net_income / hd.shareholders_equity)
            if hd.net_income and hd.total_assets:
                roas.append(hd.net_income / hd.total_assets)
            if hd.total_debt and hd.shareholders_equity:
                debt_to_equities.append(hd.total_debt / hd.shareholders_equity)
        
        # Calculate CAGRs
        revenue_cagr_3y = None
        revenue_cagr_5y = None
        
        if len(revenues) >= 3:
            n = min(3, len(revenues))
            revenue_cagr_3y = (revenues[0] / revenues[n-1]) ** (1/(n-1)) - 1
        
        if len(revenues) >= 5:
            revenue_cagr_5y = (revenues[0] / revenues[4]) ** (1/4) - 1
        
        return CalculatedMetrics(
            revenue_cagr_3y=revenue_cagr_3y,
            revenue_cagr_5y=revenue_cagr_5y,
            avg_ebitda_margin=sum(ebitda_margins)/len(ebitda_margins) if ebitda_margins else None,
            avg_net_margin=sum(net_margins)/len(net_margins) if net_margins else None,
            avg_roe=sum(roes)/len(roes) if roes else None,
            avg_roa=sum(roas)/len(roas) if roas else None,
            debt_to_equity_avg=sum(debt_to_equities)/len(debt_to_equities) if debt_to_equities else None
        )
