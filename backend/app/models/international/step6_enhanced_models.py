"""
Step 6 Enhanced Response Models
Shows retrieved inputs, calculated values, missing data flags, and manual input overrides
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class DataStatus(str, Enum):
    """Status of data retrieval/calculation"""
    RETRIEVED = "retrieved"  # Successfully fetched from API
    CALCULATED = "calculated"  # Derived from other fields
    ESTIMATED = "estimated"  # AI/model estimated
    MISSING = "missing"  # Not available
    MANUAL_OVERRIDE = "manual_override"  # User provided


class DataField(BaseModel):
    """Individual data field with status and metadata"""
    field_name: str = Field(..., description="Field identifier")
    value: Optional[Any] = Field(None, description="Field value")
    status: DataStatus = Field(..., description="Data retrieval/calculation status")
    source: Optional[str] = Field(None, description="Data source (e.g., 'yfinance', 'calculated', 'user_input')")
    is_missing: bool = Field(False, description="Flag if data is missing")
    requires_manual_input: bool = Field(False, description="Flag if manual input is needed")
    calculation_formula: Optional[str] = Field(None, description="Formula used if calculated")
    confidence_score: Optional[float] = Field(None, description="Confidence score (0-1) for estimated data", ge=0, le=1)
    notes: Optional[str] = Field(None, description="Additional notes or warnings")


class HistoricalFinancialsDisplay(BaseModel):
    """Historical financials with status tracking"""
    revenue: Optional[DataField] = None
    cogs: Optional[DataField] = None
    ebitda: Optional[DataField] = None
    net_income: Optional[DataField] = None
    operating_expenses: Optional[DataField] = None
    depreciation: Optional[DataField] = None
    capex: Optional[DataField] = None
    free_cash_flow: Optional[DataField] = None
    total_assets: Optional[DataField] = None
    total_debt: Optional[DataField] = None
    cash_and_equivalents: Optional[DataField] = None
    shareholders_equity: Optional[DataField] = None
    
    # Calculated metrics
    revenue_cagr: Optional[DataField] = None
    avg_ebitda_margin: Optional[DataField] = None
    avg_roe: Optional[DataField] = None


class ForecastDriversDisplay(BaseModel):
    """Forecast drivers with status tracking"""
    revenue_growth_forecast: Optional[DataField] = None
    volume_growth_split: Optional[DataField] = None
    inflation_rate: Optional[DataField] = None
    ebitda_margin_forecast: Optional[DataField] = None
    tax_rate: Optional[DataField] = None
    capex_pct_of_revenue: Optional[DataField] = None
    ar_days: Optional[DataField] = None
    inv_days: Optional[DataField] = None
    ap_days: Optional[DataField] = None
    risk_free_rate: Optional[DataField] = None
    equity_risk_premium: Optional[DataField] = None
    beta: Optional[DataField] = None
    cost_of_debt: Optional[DataField] = None
    wacc: Optional[DataField] = None
    terminal_growth_rate: Optional[DataField] = None
    terminal_ebitda_multiple: Optional[DataField] = None


class MarketDataDisplay(BaseModel):
    """Market data with status tracking"""
    current_stock_price: Optional[DataField] = None
    shares_outstanding: Optional[DataField] = None
    market_cap: Optional[DataField] = None
    beta: Optional[DataField] = None
    total_debt: Optional[DataField] = None
    cash: Optional[DataField] = None


class CalculatedMetricsDisplay(BaseModel):
    """Key calculated metrics from the DCF model"""
    wacc: Optional[DataField] = None
    terminal_value: Optional[DataField] = None
    enterprise_value: Optional[DataField] = None
    equity_value: Optional[DataField] = None
    fair_value_per_share: Optional[DataField] = None
    upside_downside: Optional[DataField] = None
    
    # Intermediate calculations
    projected_revenues: Optional[DataField] = None
    projected_ebitda: Optional[DataField] = None
    projected_ucff: Optional[DataField] = None
    pv_of_fcf: Optional[DataField] = None


class MissingDataSummary(BaseModel):
    """Summary of missing data requiring manual input"""
    total_fields: int = Field(..., description="Total number of input fields")
    retrieved_count: int = Field(..., description="Number of successfully retrieved fields")
    calculated_count: int = Field(..., description="Number of calculated fields")
    missing_count: int = Field(..., description="Number of missing fields")
    manual_override_count: int = Field(..., description="Number of user-provided overrides")
    
    critical_missing: List[str] = Field(default_factory=list, description="Critical fields required for valuation")
    optional_missing: List[str] = Field(default_factory=list, description="Optional fields that can be estimated")
    
    completion_percentage: float = Field(..., description="Overall data completeness (0-100)", ge=0, le=100)
    ready_for_valuation: bool = Field(..., description="Whether sufficient data exists to run valuation")


class ManualInputOverride(BaseModel):
    """Structure for manual input overrides"""
    field_name: str = Field(..., description="Field to override")
    new_value: Any = Field(..., description="New user-provided value")
    reason: Optional[str] = Field(None, description="Reason for override")


class Step6EnhancedResponse(BaseModel):
    """
    Enhanced Step 6 response showing:
    1. All retrieved inputs with sources
    2. All calculated values with formulas
    3. Missing data flags
    4. Manual input override capability
    """
    
    session_id: str = Field(..., description="Session identifier")
    ticker: str = Field(..., description="Stock ticker symbol")
    company_name: Optional[str] = Field(None, description="Company name")
    
    # Input data sections with status tracking
    historical_financials: Optional[HistoricalFinancialsDisplay] = Field(None, description="Historical financials with status")
    forecast_drivers: Optional[ForecastDriversDisplay] = Field(None, description="Forecast drivers with status")
    market_data: Optional[MarketDataDisplay] = Field(None, description="Market data with status")
    
    # Calculated metrics from the model
    calculated_metrics: Optional[CalculatedMetricsDisplay] = Field(None, description="Key calculated valuation metrics")
    
    # Missing data summary
    missing_data_summary: MissingDataSummary = Field(..., description="Summary of missing data and completeness")
    
    # Data quality indicators
    data_quality_score: float = Field(..., description="Overall data quality score (0-100)", ge=0, le=100)
    warnings: List[str] = Field(default_factory=list, description="Data quality warnings")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improving data quality")
    
    # Manual input interface
    allowed_overrides: List[str] = Field(default_factory=list, description="List of fields that can be manually overridden")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123",
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "historical_financials": {
                    "revenue": {
                        "field_name": "revenue",
                        "value": {"2023": 383285000000, "2022": 394328000000},
                        "status": "retrieved",
                        "source": "yfinance",
                        "is_missing": False
                    }
                },
                "missing_data_summary": {
                    "total_fields": 45,
                    "retrieved_count": 38,
                    "calculated_count": 5,
                    "missing_count": 2,
                    "manual_override_count": 0,
                    "critical_missing": ["beta"],
                    "optional_missing": ["volume_growth_split"],
                    "completion_percentage": 95.6,
                    "ready_for_valuation": True
                },
                "data_quality_score": 92.5,
                "warnings": ["Beta estimated from sector average"],
                "recommendations": ["Provide custom beta if available"]
            }
        }


# =============================================================================
# COMPS ENHANCED RESPONSE
# =============================================================================

class CompsPeerDataDisplay(BaseModel):
    """Peer data with status tracking"""
    ticker: str
    company_name: Optional[str] = None
    ev_ebitda_ltm: Optional[DataField] = None
    ev_ebitda_fy1: Optional[DataField] = None
    pe_ratio_ltm: Optional[DataField] = None
    pe_ratio_fy1: Optional[DataField] = None
    ev_revenue_ltm: Optional[DataField] = None
    pb_ratio: Optional[DataField] = None
    selection_reason: Optional[str] = None
    is_outlier: Optional[DataField] = None


class CompsTargetDataDisplay(BaseModel):
    """Target company data with status tracking"""
    ticker: str
    company_name: Optional[str] = None
    market_cap: Optional[DataField] = None
    enterprise_value: Optional[DataField] = None
    revenue_ltm: Optional[DataField] = None
    ebitda_ltm: Optional[DataField] = None
    net_income_ltm: Optional[DataField] = None
    eps_ltm: Optional[DataField] = None


class CompsCalculatedMetricsDisplay(BaseModel):
    """Calculated comps metrics"""
    median_ev_ebitda: Optional[DataField] = None
    mean_ev_ebitda: Optional[DataField] = None
    median_pe_ratio: Optional[DataField] = None
    mean_pe_ratio: Optional[DataField] = None
    implied_ev_ebitda: Optional[DataField] = None
    implied_pe_ratio: Optional[DataField] = None
    implied_market_cap: Optional[DataField] = None
    implied_share_price: Optional[DataField] = None
    upside_downside: Optional[DataField] = None


class Step6CompsEnhancedResponse(BaseModel):
    """Enhanced Step 6 response for Comps analysis"""
    
    session_id: str
    target_ticker: str
    target_company_name: Optional[str] = None
    
    # Target data with status
    target_data: Optional[CompsTargetDataDisplay] = None
    
    # Peer data with status
    peer_data: List[CompsPeerDataDisplay] = Field(default_factory=list)
    
    # Calculated metrics
    calculated_metrics: Optional[CompsCalculatedMetricsDisplay] = None
    
    # Missing data summary
    missing_data_summary: MissingDataSummary
    
    # Data quality
    data_quality_score: float
    outliers_removed: int = Field(0, description="Number of outliers removed via IQR filtering")
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    # Manual overrides
    allowed_overrides: List[str] = Field(default_factory=list)


# =============================================================================
# DUPONT ENHANCED RESPONSE
# =============================================================================

class DuPontComponentsDisplay(BaseModel):
    """DuPont components with status tracking"""
    net_profit_margin: Optional[DataField] = None
    asset_turnover: Optional[DataField] = None
    equity_multiplier: Optional[DataField] = None
    roe: Optional[DataField] = None
    
    # Raw components
    net_income: Optional[DataField] = None
    revenue: Optional[DataField] = None
    total_assets: Optional[DataField] = None
    shareholders_equity: Optional[DataField] = None


class DuPontTrendAnalysisDisplay(BaseModel):
    """Multi-year trend analysis"""
    years: List[int] = Field(default_factory=list)
    roe_trend: Optional[DataField] = None
    margin_trend: Optional[DataField] = None
    turnover_trend: Optional[DataField] = None
    leverage_trend: Optional[DataField] = None


class Step6DuPontEnhancedResponse(BaseModel):
    """Enhanced Step 6 response for DuPont analysis"""
    
    session_id: str
    ticker: str
    company_name: Optional[str] = None
    
    # DuPont components with status
    dupont_components: Optional[DuPontComponentsDisplay] = None
    
    # Trend analysis
    trend_analysis: Optional[DuPontTrendAnalysisDisplay] = None
    
    # Missing data summary
    missing_data_summary: MissingDataSummary
    
    # Data quality
    data_quality_score: float
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    # Manual overrides
    allowed_overrides: List[str] = Field(default_factory=list)
