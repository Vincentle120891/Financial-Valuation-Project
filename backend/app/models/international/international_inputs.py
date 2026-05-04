"""
International Financial Report Inputs Model
Standard IFRS/US GAAP format for non-Vietnamese markets
Used when market selection is 'international'

This module defines Pydantic models for:
1. API validation - expected fields and formats for frontend requests
2. Data standardization - consistent structures for international markets
3. Input separation - clear boundary between input validation and engine logic
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date
from enum import Enum


# =============================================================================
# DCF MODEL INPUTS
# =============================================================================

class DataStatus(str, Enum):
    """Status of data retrieval and calculation"""
    RETRIEVED = "RETRIEVED"
    CALCULATED = "CALCULATED"
    ESTIMATED = "ESTIMATED"
    MISSING = "MISSING"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class ValuationModel(str, Enum):
    """Type of valuation model to use"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"


class DataField(BaseModel):
    """Individual field with status tracking"""
    value: Optional[Any] = Field(None, description="Field value")
    status: DataStatus = Field(..., description="Data retrieval/calculation status")
    source: Optional[str] = Field(None, description="Data source (yfinance, calculated, user_input, etc.)")
    formula: Optional[str] = Field(None, description="Calculation formula if calculated")
    confidence_score: Optional[float] = Field(None, description="Confidence score 0-100")
    is_missing: bool = Field(False, description="Flag if data is missing")
    can_override: bool = Field(False, description="Whether manual override is allowed")


class MissingDataSummary(BaseModel):
    """Comprehensive summary of missing data"""
    total_fields: int = Field(..., description="Total number of fields")
    retrieved_count: int = Field(0, description="Number of retrieved fields")
    calculated_count: int = Field(0, description="Number of calculated fields")
    estimated_count: int = Field(0, description="Number of estimated fields")
    missing_count: int = Field(0, description="Number of missing fields")
    manual_override_count: int = Field(0, description="Number of manually overridden fields")
    completion_percentage: float = Field(0.0, description="Overall completion percentage")
    critical_missing: List[str] = Field(default_factory=list, description="Critical missing fields")
    optional_missing: List[str] = Field(default_factory=list, description="Optional missing fields")
    valuation_ready: bool = Field(False, description="Whether sufficient data exists for valuation")
    data_quality_score: float = Field(0.0, description="Overall data quality score 0-100")
    warnings: List[str] = Field(default_factory=list, description="Data quality warnings")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improvement")


class HistoricalFinancialsDisplay(BaseModel):
    """Display model for historical financials with status tracking"""
    revenue: Optional[DataField] = Field(None, description="Revenue with status")
    cogs: Optional[DataField] = Field(None, description="COGS with status")
    ebitda: Optional[DataField] = Field(None, description="EBITDA with status")
    net_income: Optional[DataField] = Field(None, description="Net income with status")
    operating_expenses: Optional[DataField] = Field(None, description="Operating expenses with status")
    sg_and_a: Optional[DataField] = Field(None, description="SG&A with status")
    depreciation: Optional[DataField] = Field(None, description="Depreciation with status")
    capex: Optional[DataField] = Field(None, description="CapEx with status")
    free_cash_flow: Optional[DataField] = Field(None, description="Free cash flow with status")
    total_assets: Optional[DataField] = Field(None, description="Total assets with status")
    total_debt: Optional[DataField] = Field(None, description="Total debt with status")
    cash_and_equivalents: Optional[DataField] = Field(None, description="Cash with status")
    inventory: Optional[DataField] = Field(None, description="Inventory with status")
    accounts_receivable: Optional[DataField] = Field(None, description="AR with status")
    accounts_payable: Optional[DataField] = Field(None, description="AP with status")
    shareholders_equity: Optional[DataField] = Field(None, description="Shareholders' equity with status")
    revenue_cagr: Optional[DataField] = Field(None, description="Revenue CAGR with status")
    avg_ebitda_margin: Optional[DataField] = Field(None, description="Average EBITDA margin with status")
    avg_roe: Optional[DataField] = Field(None, description="Average ROE with status")


class ForecastDriversDisplay(BaseModel):
    """Display model for forecast drivers with status tracking"""
    revenue_growth_forecast: Optional[DataField] = Field(None, description="Revenue growth forecast with status", can_override=True)
    volume_growth_split: Optional[DataField] = Field(None, description="Volume growth split with status", can_override=True)
    inflation_rate: Optional[DataField] = Field(None, description="Inflation rate with status", can_override=True)
    ebitda_margin_forecast: Optional[DataField] = Field(None, description="EBITDA margin forecast with status", can_override=True)
    tax_rate: Optional[DataField] = Field(None, description="Tax rate with status", can_override=True)
    capex_pct_of_revenue: Optional[DataField] = Field(None, description="CapEx % of revenue with status", can_override=True)
    ar_days: Optional[DataField] = Field(None, description="AR days with status", can_override=True)
    inv_days: Optional[DataField] = Field(None, description="Inventory days with status", can_override=True)
    ap_days: Optional[DataField] = Field(None, description="AP days with status", can_override=True)
    risk_free_rate: Optional[DataField] = Field(None, description="Risk-free rate with status", can_override=True)
    equity_risk_premium: Optional[DataField] = Field(None, description="Equity risk premium with status", can_override=True)
    beta: Optional[DataField] = Field(None, description="Beta with status", can_override=True)
    cost_of_debt: Optional[DataField] = Field(None, description="Cost of debt with status", can_override=True)
    wacc: Optional[DataField] = Field(None, description="WACC with status", can_override=True)
    terminal_growth_rate: Optional[DataField] = Field(None, description="Terminal growth rate with status", can_override=True)
    terminal_ebitda_multiple: Optional[DataField] = Field(None, description="Terminal EBITDA multiple with status", can_override=True)
    useful_life_existing: Optional[DataField] = Field(None, description="Useful life existing with status", can_override=True)
    useful_life_new: Optional[DataField] = Field(None, description="Useful life new with status", can_override=True)


class MarketDataDisplay(BaseModel):
    """Display model for market data with status tracking"""
    current_stock_price: Optional[DataField] = Field(None, description="Current stock price with status")
    shares_outstanding: Optional[DataField] = Field(None, description="Shares outstanding with status")
    market_cap: Optional[DataField] = Field(None, description="Market cap with status")
    beta: Optional[DataField] = Field(None, description="Beta with status")
    total_debt: Optional[DataField] = Field(None, description="Total debt with status")
    cash: Optional[DataField] = Field(None, description="Cash with status")
    currency: Optional[DataField] = Field(None, description="Currency with status")


class CalculatedMetricsDisplay(BaseModel):
    """Display model for calculated metrics with formulas"""
    wacc: Optional[DataField] = Field(None, description="WACC with formula")
    terminal_value: Optional[DataField] = Field(None, description="Terminal value with formula")
    enterprise_value: Optional[DataField] = Field(None, description="Enterprise value with formula")
    equity_value: Optional[DataField] = Field(None, description="Equity value with formula")
    fair_value_per_share: Optional[DataField] = Field(None, description="Fair value per share with formula")
    implied_upside_downside: Optional[DataField] = Field(None, description="Implied upside/downside with formula")


class DCFHistoricalFinancials(BaseModel):
    """
    Historical financial data (3-5 years) for DCF model
    Typically auto-fetched from yFinance API
    """
    
    # Income Statement History
    revenue: Optional[Dict[str, float]] = Field(None, description="Revenue by year (e.g., {'2023': 1000000, '2022': 950000})")
    cogs: Optional[Dict[str, float]] = Field(None, description="Cost of goods sold by year")
    ebitda: Optional[Dict[str, float]] = Field(None, description="EBITDA by year")
    net_income: Optional[Dict[str, float]] = Field(None, description="Net income by year")
    operating_expenses: Optional[Dict[str, float]] = Field(None, description="Operating expenses by year")
    sg_and_a: Optional[Dict[str, float]] = Field(None, description="SG&A expenses by year")
    depreciation: Optional[Dict[str, float]] = Field(None, description="Depreciation & amortization by year")
    
    # Cash Flow History
    capex: Optional[Dict[str, float]] = Field(None, description="Capital expenditures by year")
    free_cash_flow: Optional[Dict[str, float]] = Field(None, description="Free cash flow by year")
    
    # Balance Sheet History
    total_assets: Optional[Dict[str, float]] = Field(None, description="Total assets by year")
    total_debt: Optional[Dict[str, float]] = Field(None, description="Total debt by year")
    cash_and_equivalents: Optional[Dict[str, float]] = Field(None, description="Cash & equivalents by year")
    inventory: Optional[Dict[str, float]] = Field(None, description="Inventory by year")
    accounts_receivable: Optional[Dict[str, float]] = Field(None, description="Accounts receivable by year")
    accounts_payable: Optional[Dict[str, float]] = Field(None, description="Accounts payable by year")
    shareholders_equity: Optional[Dict[str, float]] = Field(None, description="Shareholders' equity by year")
    
    # Calculated Metrics
    revenue_cagr: Optional[float] = Field(None, description="Revenue CAGR (calculated)")
    avg_ebitda_margin: Optional[float] = Field(None, description="Average EBITDA margin (calculated)")
    avg_roe: Optional[float] = Field(None, description="Average ROE (calculated)")


class DCFForecastDrivers(BaseModel):
    """
    Forecast drivers for DCF model
    Requires user input or AI generation
    """
    
    # Revenue Growth (6 periods: FY1-FY5 + Terminal)
    revenue_growth_forecast: Optional[List[float]] = Field(None, description="Revenue growth rates for 5 forecast years + terminal (as decimals, e.g., 0.05 for 5%)")
    volume_growth_split: Optional[float] = Field(0.6, description="Split between volume vs price growth (0.0-1.0)")
    
    # Inflation & Margins
    inflation_rate: Optional[float] = Field(0.02, description="Inflation rate assumption for COGS/OpEx")
    ebitda_margin_forecast: Optional[List[float]] = Field(None, description="EBITDA margin forecast by year")
    
    # Tax & CapEx
    tax_rate: Optional[float] = Field(0.21, description="Corporate tax rate (as decimal)")
    capex_pct_of_revenue: Optional[float] = Field(0.05, description="CapEx as percentage of revenue")
    
    # Working Capital Days
    ar_days: Optional[float] = Field(45, description="Accounts receivable days")
    inv_days: Optional[float] = Field(60, description="Inventory days")
    ap_days: Optional[float] = Field(30, description="Accounts payable days")
    
    # DCF-Specific Parameters
    risk_free_rate: Optional[float] = Field(0.045, description="Risk-free rate (e.g., 10Y treasury)")
    equity_risk_premium: Optional[float] = Field(0.055, description="Equity risk premium")
    beta: Optional[float] = Field(1.0, description="Company beta")
    cost_of_debt: Optional[float] = Field(0.05, description="Pre-tax cost of debt")
    wacc: Optional[float] = Field(None, description="WACC (calculated if not provided)")
    terminal_growth_rate: Optional[float] = Field(0.023, description="Terminal growth rate (perpetuity method)")
    terminal_ebitda_multiple: Optional[float] = Field(8.0, description="Terminal EBITDA multiple (exit multiple method)")
    
    # Depreciation Parameters
    useful_life_existing: Optional[float] = Field(10.0, description="Useful life of existing assets (years)")
    useful_life_new: Optional[float] = Field(10.0, description="Useful life of new assets (years)")
    
    # Peer Comparison (Optional)
    peer_tickers: Optional[List[str]] = Field(None, description="List of peer ticker symbols for WACC calculation")


class DCFMarketData(BaseModel):
    """
    Market data for DCF model
    Typically auto-fetched from yFinance API
    """
    
    current_stock_price: Optional[float] = Field(None, description="Current stock price")
    shares_outstanding: Optional[float] = Field(None, description="Shares outstanding")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    beta: Optional[float] = Field(None, description="Stock beta")
    total_debt: Optional[float] = Field(None, description="Total debt")
    cash: Optional[float] = Field(None, description="Cash & equivalents")
    currency: Optional[str] = Field("USD", description="Reporting currency")


class DCFValuationRequest(BaseModel):
    """
    Complete DCF valuation request combining all inputs
    Used for API endpoint validation
    """
    
    session_id: str = Field(..., description="Session identifier")
    valuation_model: ValuationModel = Field(ValuationModel.DCF, description="Selected valuation model")
    
    # Company identification
    ticker: str = Field(..., description="Stock ticker symbol")
    company_name: Optional[str] = Field(None, description="Company name")
    sector: Optional[str] = Field(None, description="Sector")
    industry: Optional[str] = Field(None, description="Industry")
    
    # Input data sources
    historical_financials: Optional[DCFHistoricalFinancials] = Field(None, description="Historical financial data (auto-fetched)")
    market_data: Optional[DCFMarketData] = Field(None, description="Market data (auto-fetched)")
    forecast_drivers: Optional[DCFForecastDrivers] = Field(None, description="Forecast assumptions (user/AI provided)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123",
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "forecast_drivers": {
                    "revenue_growth_forecast": [0.05, 0.05, 0.04, 0.04, 0.03, 0.02],
                    "volume_growth_split": 0.6,
                    "inflation_rate": 0.02,
                    "tax_rate": 0.21,
                    "capex_pct_of_revenue": 0.05,
                    "ar_days": 45,
                    "inv_days": 60,
                    "ap_days": 30,
                    "terminal_growth_rate": 0.023,
                    "terminal_ebitda_multiple": 8.0
                }
            }
        }


class Step6EnhancedResponse(BaseModel):
    """
    Enhanced Step 6 response showing retrieved inputs, calculated values, missing data flags, and manual override options
    """
    session_id: str = Field(..., description="Session identifier")
    ticker: str = Field(..., description="Stock ticker symbol")
    company_name: Optional[str] = Field(None, description="Company name")
    
    # Data with status tracking
    historical_financials: Optional[HistoricalFinancialsDisplay] = Field(None, description="Historical financials with retrieval status")
    forecast_drivers: Optional[ForecastDriversDisplay] = Field(None, description="Forecast drivers with override capability")
    market_data: Optional[MarketDataDisplay] = Field(None, description="Market data with retrieval status")
    calculated_metrics: Optional[CalculatedMetricsDisplay] = Field(None, description="Calculated metrics with formulas")
    
    # Missing data summary
    missing_data_summary: MissingDataSummary = Field(..., description="Comprehensive missing data analysis")
    
    # Manual override inputs (user can provide these to fill gaps)
    allowed_manual_overrides: Dict[str, bool] = Field(default_factory=dict, description="Fields that can be manually overridden")
    
    # Data quality indicators
    data_quality_score: float = Field(0.0, description="Overall data quality score 0-100")
    valuation_ready: bool = Field(False, description="Whether sufficient data exists for valuation")
    warnings: List[str] = Field(default_factory=list, description="Data quality warnings")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improvement")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123",
                "ticker": "AAPL",
                "historical_financials": {
                    "revenue": {"value": 394328000000, "status": "RETRIEVED", "source": "yfinance"},
                    "net_income": {"value": 99803000000, "status": "RETRIEVED", "source": "yfinance"},
                    "total_debt": {"value": 111088000000, "status": "MISSING", "is_missing": True}
                },
                "forecast_drivers": {
                    "revenue_growth_forecast": {"value": [0.05, 0.05, 0.04, 0.04, 0.03, 0.02], "status": "MANUAL_OVERRIDE", "can_override": True},
                    "tax_rate": {"value": 0.21, "status": "ESTIMATED", "formula": "Corporate tax rate applied to EBIT", "can_override": True}
                },
                "calculated_metrics": {
                    "wacc": {"value": 0.095, "status": "CALCULATED", "formula": "WACC = (E/V × Re) + (D/V × Rd × (1-T))"},
                    "fair_value_per_share": {"value": 180.50, "status": "CALCULATED", "formula": "Equity Value / Shares Outstanding"}
                },
                "missing_data_summary": {
                    "total_fields": 37,
                    "retrieved_count": 12,
                    "calculated_count": 8,
                    "missing_count": 11,
                    "completion_percentage": 54.1,
                    "critical_missing": ["capex", "free_cash_flow"],
                    "valuation_ready": True,
                    "data_quality_score": 72.5
                },
                "allowed_manual_overrides": {
                    "revenue_growth_forecast": True,
                    "tax_rate": True,
                    "beta": True,
                    "terminal_growth_rate": True
                }
            }
        }


# =============================================================================
# COMPARABLE COMPANIES (COMPS) MODEL INPUTS
# =============================================================================

class PeerMultiple(BaseModel):
    """
    Standardized schema for individual peer data (EV/EBITDA, P/E, etc.).
    Used for consistent validation across comps workflows.
    """
    
    ticker: str = Field(..., description="Peer ticker symbol")
    company_name: Optional[str] = Field(None, description="Peer company name")
    
    # Valuation Multiples
    ev_ebitda_ltm: Optional[float] = Field(None, description="Enterprise Value / EBITDA (LTM)")
    ev_ebitda_fy1: Optional[float] = Field(None, description="Enterprise Value / EBITDA (FY1 Estimate)")
    ev_ebitda_fy2: Optional[float] = Field(None, description="Enterprise Value / EBITDA (FY2 Estimate)")
    
    pe_ratio_ltm: Optional[float] = Field(None, description="Price / Earnings (LTM)")
    pe_ratio_fy1: Optional[float] = Field(None, description="Price / Earnings (FY1 Estimate)")
    pe_ratio_fy2: Optional[float] = Field(None, description="Price / Earnings (FY2 Estimate)")
    
    ev_revenue_ltm: Optional[float] = Field(None, description="Enterprise Value / Revenue (LTM)")
    pb_ratio: Optional[float] = Field(None, description="Price / Book Value")
    
    # Classification
    sector: Optional[str] = Field(None, description="Sector")
    industry: Optional[str] = Field(None, description="Industry")
    selection_reason: Optional[str] = Field(None, description="Reason for peer selection")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "MSFT",
                "company_name": "Microsoft Corporation",
                "ev_ebitda_ltm": 18.5,
                "pe_ratio_ltm": 28.3,
                "sector": "Technology",
                "industry": "Software"
            }
        }


class CompsSelectionRequest(BaseModel):
    """
    Handles target_ticker, peer_list, sector, and industry filters.
    Separates peer selection criteria from valuation logic.
    """
    
    target_ticker: str = Field(..., description="Target company ticker symbol")
    peer_list: Optional[List[str]] = Field(None, description="Explicit list of peer tickers")
    sector: Optional[str] = Field(None, description="Sector filter for auto-peer selection")
    industry: Optional[str] = Field(None, description="Industry filter for auto-peer selection")
    max_peers: Optional[int] = Field(10, description="Maximum number of peers to select", ge=1, le=50)
    
    class Config:
        json_schema_extra = {
            "example": {
                "target_ticker": "AAPL",
                "peer_list": ["MSFT", "GOOGL", "META"],
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "max_peers": 10
            }
        }


class CompsPeerDataDisplay(BaseModel):
    """Display model for peer data with status tracking"""
    peer_multiples: Optional[List[DataField]] = Field(None, description="Peer multiples with status")
    median_ev_ebitda: Optional[DataField] = Field(None, description="Median EV/EBITDA with formula")
    mean_ev_ebitda: Optional[DataField] = Field(None, description="Mean EV/EBITDA with formula")
    median_pe: Optional[DataField] = Field(None, description="Median P/E with formula")
    mean_pe: Optional[DataField] = Field(None, description="Mean P/E with formula")
    outliers_removed: Optional[DataField] = Field(None, description="Outliers removed flag")


class CompsTargetDataDisplay(BaseModel):
    """Display model for target company data with status tracking"""
    market_cap: Optional[DataField] = Field(None, description="Market cap with status")
    enterprise_value: Optional[DataField] = Field(None, description="Enterprise value with status")
    revenue_ltm: Optional[DataField] = Field(None, description="Revenue LTM with status")
    ebitda_ltm: Optional[DataField] = Field(None, description="EBITDA LTM with status")
    net_income_ltm: Optional[DataField] = Field(None, description="Net income LTM with status")
    eps_ltm: Optional[DataField] = Field(None, description="EPS LTM with status")


class CompsCalculatedMetricsDisplay(BaseModel):
    """Display model for comps calculated metrics with formulas"""
    implied_ev: Optional[DataField] = Field(None, description="Implied Enterprise Value with formula")
    implied_equity_value: Optional[DataField] = Field(None, description="Implied Equity Value with formula")
    implied_share_price: Optional[DataField] = Field(None, description="Implied Share Price with formula")
    upside_downside: Optional[DataField] = Field(None, description="Upside/Downside with formula")


class Step6CompsEnhancedResponse(BaseModel):
    """
    Enhanced Step 6 Comps response showing retrieved inputs, calculated values, missing data flags, and manual override options
    """
    session_id: str = Field(..., description="Session identifier")
    target_ticker: str = Field(..., description="Target ticker symbol")
    target_company_name: Optional[str] = Field(None, description="Target company name")
    
    # Data with status tracking
    target_data: Optional[CompsTargetDataDisplay] = Field(None, description="Target data with retrieval status")
    peer_data: Optional[CompsPeerDataDisplay] = Field(None, description="Peer data with status")
    calculated_metrics: Optional[CompsCalculatedMetricsDisplay] = Field(None, description="Calculated metrics with formulas")
    
    # Missing data summary
    missing_data_summary: MissingDataSummary = Field(..., description="Comprehensive missing data analysis")
    
    # Manual override inputs
    allowed_manual_overrides: Dict[str, bool] = Field(default_factory=dict, description="Fields that can be manually overridden")
    
    # Data quality indicators
    data_quality_score: float = Field(0.0, description="Overall data quality score 0-100")
    valuation_ready: bool = Field(False, description="Whether sufficient data exists for valuation")
    warnings: List[str] = Field(default_factory=list, description="Data quality warnings")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improvement")


class CompsValuationRequest(BaseModel):
    """
    Includes target financials, peer multiples, and outlier filtering parameters (IQR settings).
    Complete request structure for comps valuation engine.
    """
    
    session_id: str = Field(..., description="Session identifier")
    
    # Target company data
    target_ticker: str = Field(..., description="Target company ticker")
    target_company_name: Optional[str] = Field(None, description="Target company name")
    target_market_cap: Optional[float] = Field(None, description="Target market cap")
    target_enterprise_value: Optional[float] = Field(None, description="Target enterprise value")
    
    # Target financials (LTM)
    target_revenue_ltm: Optional[float] = Field(None, description="Target revenue LTM")
    target_ebitda_ltm: Optional[float] = Field(None, description="Target EBITDA LTM")
    target_net_income_ltm: Optional[float] = Field(None, description="Target net income LTM")
    target_eps_ltm: Optional[float] = Field(None, description="Target EPS LTM")
    
    # Peer multiples
    peer_multiples: List[PeerMultiple] = Field(default_factory=list, description="List of peer company multiples")
    
    # Outlier filtering parameters
    apply_outlier_filtering: Optional[bool] = Field(True, description="Apply IQR-based outlier filtering")
    iqr_multiplier: Optional[float] = Field(1.5, description="IQR multiplier for outlier detection (default 1.5)")
    
    # Analysis options
    include_football_field: Optional[bool] = Field(True, description="Include football field chart data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123",
                "target_ticker": "AAPL",
                "target_company_name": "Apple Inc.",
                "target_market_cap": 2800000000000,
                "target_ebitda_ltm": 120000000000,
                "peer_multiples": [
                    {
                        "ticker": "MSFT",
                        "ev_ebitda_ltm": 18.5,
                        "pe_ratio_ltm": 28.3
                    }
                ],
                "apply_outlier_filtering": True,
                "iqr_multiplier": 1.5
            }
        }


class CompsTargetCompany(BaseModel):
    """
    Target company data for comparable companies analysis
    """
    
    ticker: str = Field(..., description="Stock ticker symbol")
    company_name: Optional[str] = Field(None, description="Company name")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    enterprise_value: Optional[float] = Field(None, description="Enterprise value")
    
    # Financial metrics (LTM = Last Twelve Months)
    revenue_ltm: Optional[float] = Field(None, description="Revenue LTM")
    ebitda_ltm: Optional[float] = Field(None, description="EBITDA LTM")
    ebit_ltm: Optional[float] = Field(None, description="EBIT LTM")
    net_income_ltm: Optional[float] = Field(None, description="Net income LTM")
    free_cash_flow_ltm: Optional[float] = Field(None, description="Free cash flow LTM")
    book_equity: Optional[float] = Field(None, description="Book value of equity")
    
    # Share data
    shares_outstanding: Optional[float] = Field(None, description="Shares outstanding")
    share_price: Optional[float] = Field(None, description="Current share price")
    currency: Optional[str] = Field("USD", description="Currency")


class CompsPeerCompany(BaseModel):
    """
    Peer company data for comparable companies analysis
    """
    
    ticker: str = Field(..., description="Peer ticker symbol")
    company_name: Optional[str] = Field(None, description="Peer company name")
    
    # Financial metrics
    ebitda_ltm: Optional[float] = Field(None, description="EBITDA LTM")
    ebitda_fy2023: Optional[float] = Field(None, description="EBITDA FY2023 estimate")
    ebitda_fy2024: Optional[float] = Field(None, description="EBITDA FY2024 estimate")
    
    eps_ltm: Optional[float] = Field(None, description="EPS LTM")
    eps_fy2023: Optional[float] = Field(None, description="EPS FY2023 estimate")
    eps_fy2024: Optional[float] = Field(None, description="EPS FY2024 estimate")
    
    # Valuation metrics
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    enterprise_value: Optional[float] = Field(None, description="Enterprise value")
    share_price: Optional[float] = Field(None, description="Share price")
    shares_outstanding: Optional[float] = Field(None, description="Shares outstanding")
    
    # Classification
    sector: Optional[str] = Field(None, description="Sector")
    industry: Optional[str] = Field(None, description="Industry")
    selection_reason: Optional[str] = Field(None, description="Reason for peer selection")


class CompsAnalysisRequest(BaseModel):
    """
    Comparable companies analysis request
    """
    
    session_id: str = Field(..., description="Session identifier")
    target: CompsTargetCompany = Field(..., description="Target company data")
    peers: Optional[List[CompsPeerCompany]] = Field(None, description="Peer companies (auto-generated if not provided)")
    
    # Analysis options
    apply_outlier_filtering: Optional[bool] = Field(True, description="Apply IQR-based outlier filtering")
    include_football_field: Optional[bool] = Field(True, description="Include football field chart data")


# =============================================================================
# DU PONT ANALYSIS INPUTS
# =============================================================================

class DuPontComponents(BaseModel):
    """
    Strict schema for DuPont analysis component breakdowns.
    Separates validation from calculation logic.
    """
    
    # Net Profit Margin breakdown
    net_profit_margin: Optional[float] = Field(None, description="Net Profit Margin (Net Income / Revenue)")
    net_income: Optional[float] = Field(None, description="Net Income")
    revenue: Optional[float] = Field(None, description="Revenue")
    
    # Asset Turnover breakdown
    asset_turnover: Optional[float] = Field(None, description="Asset Turnover (Revenue / Total Assets)")
    total_assets: Optional[float] = Field(None, description="Total Assets")
    
    # Equity Multiplier breakdown
    equity_multiplier: Optional[float] = Field(None, description="Equity Multiplier (Total Assets / Shareholders' Equity)")
    shareholders_equity: Optional[float] = Field(None, description="Shareholders' Equity")
    
    # Calculated ROE
    roe: Optional[float] = Field(None, description="Return on Equity (calculated as NPM × AT × EM)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "net_profit_margin": 0.25,
                "asset_turnover": 1.2,
                "equity_multiplier": 2.0,
                "roe": 0.60
            }
        }


class DuPontComponentsDisplay(BaseModel):
    """Display model for DuPont components with status tracking"""
    net_profit_margin: Optional[DataField] = Field(None, description="Net profit margin with status and formula")
    asset_turnover: Optional[DataField] = Field(None, description="Asset turnover with status and formula")
    equity_multiplier: Optional[DataField] = Field(None, description="Equity multiplier with status and formula")
    roe: Optional[DataField] = Field(None, description="ROE with status and formula (NPM × AT × EM)")


class DuPontTrendAnalysisDisplay(BaseModel):
    """Display model for DuPont trend analysis"""
    yoy_npm_change: Optional[DataField] = Field(None, description="YoY NPM change")
    yoy_at_change: Optional[DataField] = Field(None, description="YoY AT change")
    yoy_em_change: Optional[DataField] = Field(None, description="YoY EM change")
    yoy_roe_change: Optional[DataField] = Field(None, description="YoY ROE change")
    primary_driver: Optional[DataField] = Field(None, description="Primary ROE driver")


class Step6DuPontEnhancedResponse(BaseModel):
    """
    Enhanced Step 6 DuPont response showing retrieved inputs, calculated values, missing data flags, and manual override options
    """
    session_id: str = Field(..., description="Session identifier")
    ticker: str = Field(..., description="Stock ticker symbol")
    company_name: Optional[str] = Field(None, description="Company name")
    
    # Data with status tracking
    duPont_components: Optional[DuPontComponentsDisplay] = Field(None, description="DuPont components with retrieval status")
    trend_analysis: Optional[DuPontTrendAnalysisDisplay] = Field(None, description="Trend analysis with status")
    
    # Missing data summary
    missing_data_summary: MissingDataSummary = Field(..., description="Comprehensive missing data analysis")
    
    # Manual override inputs
    allowed_manual_overrides: Dict[str, bool] = Field(default_factory=dict, description="Fields that can be manually overridden")
    
    # Data quality indicators
    data_quality_score: float = Field(0.0, description="Overall data quality score 0-100")
    valuation_ready: bool = Field(False, description="Whether sufficient data exists for valuation")
    warnings: List[str] = Field(default_factory=list, description="Data quality warnings")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improvement")


class DuPontRequest(BaseModel):
    """
    Captures ticker, years, and optional custom_ratios for DuPont analysis.
    Strict input validation separated from engine logic.
    """
    
    ticker: str = Field(..., description="Stock ticker symbol")
    years: List[int] = Field(..., description="List of years for analysis (e.g., [2023, 2022, 2021])", min_length=1)
    custom_ratios: Optional[DuPontComponents] = Field(None, description="Optional custom ratio overrides")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "years": [2023, 2022, 2021],
                "custom_ratios": {
                    "net_profit_margin": 0.25,
                    "asset_turnover": 1.2,
                    "equity_multiplier": 2.0
                }
            }
        }


class DuPontCustomInputs(BaseModel):
    """
    Custom inputs for DuPont analysis
    """
    
    net_profit_margin: Optional[float] = Field(None, description="Net profit margin override")
    asset_turnover: Optional[float] = Field(None, description="Asset turnover override")
    equity_multiplier: Optional[float] = Field(None, description="Equity multiplier override")
    
    # Or provide raw financials for calculation
    net_income: Optional[float] = Field(None, description="Net income")
    revenue: Optional[float] = Field(None, description="Revenue")
    total_assets: Optional[float] = Field(None, description="Total assets")
    shareholders_equity: Optional[float] = Field(None, description="Shareholders' equity")


class DuPontAnalysisRequest(BaseModel):
    """
    DuPont analysis request
    """
    
    session_id: str = Field(..., description="Session identifier")
    ticker: str = Field(..., description="Stock ticker symbol")
    custom_inputs: Optional[DuPontCustomInputs] = Field(None, description="Custom input overrides")


# =============================================================================
# BALANCE SHEET (IFRS/US GAAP FORMAT)
# =============================================================================

class InternationalBalanceSheet(BaseModel):
    """
    International Balance Sheet (IFRS/US GAAP format)
    Corresponds to Vietnamese B01-DN but with international terminology
    """
    
    # Assets - Current
    cash_and_cash_equivalents: Optional[float] = Field(None, description="Cash and cash equivalents")
    short_term_investments: Optional[float] = Field(None, description="Short-term investments/marketable securities")
    accounts_receivable: Optional[float] = Field(None, description="Trade and other receivables")
    inventory: Optional[float] = Field(None, description="Inventories")
    prepaid_expenses: Optional[float] = Field(None, description="Prepaid expenses and other current assets")
    other_current_assets: Optional[float] = Field(None, description="Other current assets")
    
    # Assets - Non-Current
    property_plant_equipment: Optional[float] = Field(None, description="Property, plant and equipment (net)")
    investment_property: Optional[float] = Field(None, description="Investment property (net)")
    intangible_assets: Optional[float] = Field(None, description="Intangible assets (net)")
    goodwill: Optional[float] = Field(None, description="Goodwill")
    long_term_investments: Optional[float] = Field(None, description="Long-term investments and associates")
    deferred_tax_assets: Optional[float] = Field(None, description="Deferred tax assets")
    other_non_current_assets: Optional[float] = Field(None, description="Other non-current assets")
    
    # Liabilities - Current
    accounts_payable: Optional[float] = Field(None, description="Trade and other payables")
    short_term_debt: Optional[float] = Field(None, description="Short-term borrowings")
    current_portion_long_term_debt: Optional[float] = Field(None, description="Current portion of long-term debt")
    accrued_expenses: Optional[float] = Field(None, description="Accrued expenses and other liabilities")
    deferred_revenue_current: Optional[float] = Field(None, description="Deferred revenue (current)")
    income_tax_payable: Optional[float] = Field(None, description="Income tax payable")
    other_current_liabilities: Optional[float] = Field(None, description="Other current liabilities")
    
    # Liabilities - Non-Current
    long_term_debt: Optional[float] = Field(None, description="Long-term borrowings")
    deferred_tax_liabilities: Optional[float] = Field(None, description="Deferred tax liabilities")
    deferred_revenue_non_current: Optional[float] = Field(None, description="Deferred revenue (non-current)")
    pension_obligations: Optional[float] = Field(None, description="Pension and post-employment benefits")
    provisions_non_current: Optional[float] = Field(None, description="Non-current provisions")
    other_non_current_liabilities: Optional[float] = Field(None, description="Other non-current liabilities")
    
    # Equity
    share_capital: Optional[float] = Field(None, description="Share capital/issued capital")
    share_premium: Optional[float] = Field(None, description="Share premium/additional paid-in capital")
    retained_earnings: Optional[float] = Field(None, description="Retained earnings")
    other_comprehensive_income: Optional[float] = Field(None, description="Other comprehensive income")
    treasury_shares: Optional[float] = Field(None, description="Treasury shares (negative value)")
    non_controlling_interest: Optional[float] = Field(None, description="Non-controlling interest")
    other_equity: Optional[float] = Field(None, description="Other equity reserves")


# =============================================================================
# INCOME STATEMENT (IFRS/US GAAP FORMAT)
# =============================================================================

class InternationalIncomeStatement(BaseModel):
    """
    International Income Statement (IFRS/US GAAP format)
    Corresponds to Vietnamese B02-DN but with international terminology
    """
    
    # Revenue Section
    gross_revenue: Optional[float] = Field(None, description="Gross revenue/sales")
    sales_returns_allowances: Optional[float] = Field(None, description="Sales returns and allowances")
    revenue_deductions: Optional[float] = Field(None, description="Other revenue deductions")
    
    # Calculated: Net Revenue = Gross Revenue - Deductions
    net_revenue: Optional[float] = Field(None, description="Net revenue")
    
    # Cost of Sales
    cost_of_goods_sold: Optional[float] = Field(None, description="Cost of goods sold/cost of sales")
    
    # Calculated: Gross Profit = Net Revenue - COGS
    gross_profit: Optional[float] = Field(None, description="Gross profit")
    
    # Operating Expenses
    selling_expenses: Optional[float] = Field(None, description="Selling and distribution expenses")
    general_administrative_expenses: Optional[float] = Field(None, description="General and administrative expenses")
    research_development_expenses: Optional[float] = Field(None, description="Research and development expenses")
    depreciation_amortization: Optional[float] = Field(None, description="Depreciation and amortization expense")
    other_operating_expenses: Optional[float] = Field(None, description="Other operating expenses")
    
    # Other Income/Expenses
    investment_property_gain_loss: Optional[float] = Field(None, description="Gain/loss on investment property")
    financial_income: Optional[float] = Field(None, description="Finance income (interest, dividends, FX gains)")
    financial_expenses: Optional[float] = Field(None, description="Finance expenses (interest, FX losses)")
    interest_expense: Optional[float] = Field(None, description="Interest expense (subset of financial expenses)")
    share_of_profit_associates: Optional[float] = Field(None, description="Share of profit/loss of associates")
    other_income: Optional[float] = Field(None, description="Other income")
    other_expenses: Optional[float] = Field(None, description="Other expenses")
    
    # Calculated: Operating Profit
    operating_profit: Optional[float] = Field(None, description="Operating profit (EBIT)")
    
    # Calculated: Other Profit
    other_profit_loss: Optional[float] = Field(None, description="Other profit/loss")
    
    # Calculated: Profit Before Tax
    profit_before_tax: Optional[float] = Field(None, description="Profit before tax")
    
    # Tax
    current_tax_expense: Optional[float] = Field(None, description="Current tax expense")
    deferred_tax_expense: Optional[float] = Field(None, description="Deferred tax expense")
    
    # Calculated: Net Profit
    net_profit: Optional[float] = Field(None, description="Net profit for the period")
    
    # Per Share Data (for joint-stock companies)
    basic_eps: Optional[float] = Field(None, description="Basic earnings per share")
    diluted_eps: Optional[float] = Field(None, description="Diluted earnings per share")
    
    # Additional Metrics
    ebitda: Optional[float] = Field(None, description="EBITDA")
    weighted_average_shares_outstanding: Optional[float] = Field(None, description="Weighted average shares outstanding")


# =============================================================================
# CASH FLOW STATEMENT (IAS 7 / US GAAP)
# =============================================================================

class InternationalCashFlowStatement(BaseModel):
    """
    International Cash Flow Statement (IAS 7 / US GAAP)
    Optional supplementary data
    """
    
    # Operating Activities
    cash_from_operating_activities: Optional[float] = Field(None, description="Net cash from operating activities")
    depreciation_amortization_cashflow: Optional[float] = Field(None, description="Depreciation and amortization (cashflow)")
    changes_working_capital: Optional[float] = Field(None, description="Changes in working capital")
    
    # Investing Activities
    cash_from_investing_activities: Optional[float] = Field(None, description="Net cash from investing activities")
    capital_expenditures: Optional[float] = Field(None, description="Capital expenditures (CAPEX)")
    acquisitions: Optional[float] = Field(None, description="Acquisitions, net of cash acquired")
    proceeds_asset_sales: Optional[float] = Field(None, description="Proceeds from sale of assets")
    investment_purchases: Optional[float] = Field(None, description="Purchase of investments")
    investment_sales: Optional[float] = Field(None, description="Sale of investments")
    
    # Financing Activities
    cash_from_financing_activities: Optional[float] = Field(None, description="Net cash from financing activities")
    proceeds_from_borrowings: Optional[float] = Field(None, description="Proceeds from borrowings")
    repayment_of_borrowings: Optional[float] = Field(None, description="Repayment of borrowings")
    dividends_paid: Optional[float] = Field(None, description="Dividends paid")
    proceeds_share_issue: Optional[float] = Field(None, description="Proceeds from share issues")
    share_buybacks: Optional[float] = Field(None, description="Share buybacks")
    
    # Net Change
    net_change_in_cash: Optional[float] = Field(None, description="Net change in cash and cash equivalents")
    cash_beginning_of_period: Optional[float] = Field(None, description="Cash at beginning of period")
    cash_end_of_period: Optional[float] = Field(None, description="Cash at end of period")


# =============================================================================
# COMPLETE FINANCIAL INPUTS PACKAGE
# =============================================================================

class InternationalFinancialInputs(BaseModel):
    """
    Complete International Financial Inputs Package
    Used for international market valuation models
    Currency: USD (or local currency converted to USD)
    """
    
    company_name: str = Field(..., description="Company name")
    ticker: str = Field(..., description="Stock ticker symbol")
    currency: str = Field("USD", description="Reporting currency (default USD)")
    fiscal_year_end: Optional[date] = Field(None, description="Fiscal year end date")
    reporting_period: Optional[str] = Field(None, description="Reporting period (e.g., 'FY2023', 'Q1 2024')")
    
    balance_sheet: Optional[InternationalBalanceSheet] = Field(None, description="Balance sheet data")
    income_statement: Optional[InternationalIncomeStatement] = Field(None, description="Income statement data")
    cash_flow_statement: Optional[InternationalCashFlowStatement] = Field(None, description="Cash flow statement data")
    
    # Market Data
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    shares_outstanding: Optional[float] = Field(None, description="Shares outstanding")
    current_stock_price: Optional[float] = Field(None, description="Current stock price")
    
    # Metadata
    data_source: Optional[str] = Field(None, description="Source of financial data")
    last_updated: Optional[date] = Field(None, description="Last update date")
    accounting_standard: str = Field("IFRS", description="Accounting standard (IFRS or US GAAP)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Apple Inc.",
                "ticker": "AAPL",
                "currency": "USD",
                "fiscal_year_end": "2023-09-30",
                "reporting_period": "FY2023",
                "accounting_standard": "US GAAP",
                "balance_sheet": {
                    "cash_and_cash_equivalents": 29965000000,
                    "accounts_receivable": 29508000000,
                    "inventory": 6331000000,
                    "property_plant_equipment": 43715000000,
                    "total_assets": 352755000000,
                    "accounts_payable": 62611000000,
                    "short_term_debt": 15807000000,
                    "long_term_debt": 95281000000,
                    "share_capital": 73812000000,
                    "retained_earnings": -214000000
                },
                "income_statement": {
                    "gross_revenue": 383285000000,
                    "net_revenue": 383285000000,
                    "cost_of_goods_sold": 214137000000,
                    "gross_profit": 169148000000,
                    "operating_expenses": 55013000000,
                    "operating_profit": 114301000000,
                    "net_profit": 96995000000,
                    "basic_eps": 6.16,
                    "diluted_eps": 6.13
                }
            }
        }


# =============================================================================
# VIETNAMESE TO INTERNATIONAL MAPPING HELPER
# =============================================================================

class VN_to_International_Mapping:
    """
    Helper class to map Vietnamese TT99 fields to International format
    """
    
    BALANCE_SHEET_MAPPING = {
        # Current Assets
        "110": "cash_and_cash_equivalents",
        "120": "short_term_investments",
        "130": "accounts_receivable",
        "140": "inventory",
        "160": "other_current_assets",
        
        # Non-Current Assets
        "220": "property_plant_equipment",
        "240": "investment_property",
        "227": "intangible_assets",
        "260": "long_term_investments",
        "272": "deferred_tax_assets",
        
        # Current Liabilities
        "310": "accounts_payable",
        "321": "short_term_debt",
        "316": "accrued_expenses",
        "319": "deferred_revenue_current",
        "314": "income_tax_payable",
        
        # Non-Current Liabilities
        "339": "long_term_debt",
        "342": "deferred_tax_liabilities",
        "337": "deferred_revenue_non_current",
        "343": "provisions_non_current",
        
        # Equity
        "411": "share_capital",
        "412": "share_premium",
        "420": "retained_earnings",
        "416": "other_comprehensive_income",
        "415": "treasury_shares",
    }
    
    INCOME_STATEMENT_MAPPING = {
        "01": "gross_revenue",
        "02": "revenue_deductions",
        "10": "net_revenue",
        "11": "cost_of_goods_sold",
        "20": "gross_profit",
        "21": "investment_property_gain_loss",
        "22": "financial_income",
        "23": "financial_expenses",
        "24": "interest_expense",
        "25": "selling_expenses",
        "26": "general_administrative_expenses",
        "30": "operating_profit",
        "31": "other_income",
        "32": "other_expenses",
        "40": "other_profit_loss",
        "50": "profit_before_tax",
        "51": "current_tax_expense",
        "52": "deferred_tax_expense",
        "60": "net_profit",
        "70": "basic_eps",
        "71": "diluted_eps",
    }
    
    @classmethod
    def convert_vn_to_international(cls, vn_data: dict) -> InternationalFinancialInputs:
        """
        Convert Vietnamese TT99 format to International format
        """
        # Implementation would map Vietnamese field codes to international fields
        # This is a placeholder for the conversion logic
        pass
