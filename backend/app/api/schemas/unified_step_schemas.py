"""
Unified Step Schemas - Single Source of Truth for All 10 Steps

This module defines standardized request/response schemas for all valuation workflow steps.
Both International and Vietnamese markets MUST conform to these schemas to ensure:
- Consistent frontend integration
- Type safety across all endpoints
- Proper "3 Valuation Methods × 2 Market Versions" workflow support
- No data structure mismatches between markets

Architecture:
- Each step has UnifiedStep{N}Request and UnifiedStep{N}Response
- Nested data structures preserve context and enable proper grouping
- DataField wrapper provides status tracking, metadata, and override capabilities
- Market-specific variations handled through optional fields, not structure changes
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from enum import Enum


# =============================================================================
# CORE DATA TYPES (Used Across All Steps)
# =============================================================================

class DataStatus(str, Enum):
    """Status of data retrieval and calculation"""
    RETRIEVED = "RETRIEVED"
    CALCULATED = "CALCULATED"
    ESTIMATED = "ESTIMATED"
    MISSING = "MISSING"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"
    CACHED = "CACHED"


class ValuationMethod(str, Enum):
    """Supported valuation methods"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"


class MarketType(str, Enum):
    """Supported market types"""
    INTERNATIONAL = "international"
    VIETNAM = "vietnam"


class DataField(BaseModel):
    """
    Universal data field wrapper with status tracking.
    Used for ALL numerical and categorical values across all steps.
    
    This ensures consistent handling of:
    - Data quality indicators
    - Source attribution
    - Manual override flags
    - Confidence scoring
    """
    value: Optional[Any] = Field(None, description="Field value (any type)")
    status: DataStatus = Field(DataStatus.RETRIEVED, description="Data status")
    source: Optional[str] = Field(None, description="Data source (yfinance, vietstock, calculated, user_input, pdf_extraction)")
    formula: Optional[str] = Field(None, description="Calculation formula if calculated")
    confidence_score: Optional[float] = Field(None, ge=0, le=100, description="Confidence score 0-100")
    is_missing: bool = Field(False, description="Flag if data is missing")
    can_override: bool = Field(True, description="Whether manual override is allowed")
    unit: Optional[str] = Field(None, description="Unit of measurement (USD, VND, %, days, etc.)")
    currency: Optional[str] = Field(None, description="Currency code if applicable")
    reporting_period: Optional[str] = Field(None, description="Reporting period (FY2023, Q1-2024, etc.)")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")


class MissingDataSummary(BaseModel):
    """Comprehensive summary of missing data for any step"""
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


# =============================================================================
# STEP 1: COMPANY SEARCH & SELECTION
# =============================================================================

class UnifiedStep1Request(BaseModel):
    """Step 1: Search for company by ticker or name"""
    query: str = Field(..., min_length=1, description="Search query (ticker or company name)")
    market: MarketType = Field(MarketType.INTERNATIONAL, description="Market to search in")
    limit: int = Field(10, ge=1, le=50, description="Maximum results to return")


class CompanySearchResult(BaseModel):
    """Individual company search result"""
    ticker: str
    company_name: str
    exchange: str
    market: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    currency: Optional[str] = None
    country: Optional[str] = None


class UnifiedStep1Response(BaseModel):
    """Step 1: Search results"""
    status: str
    query: str
    market: str
    results: List[CompanySearchResult]
    total_results: int
    message: str


# =============================================================================
# STEP 2: MARKET CONFIRMATION
# =============================================================================

class UnifiedStep2Request(BaseModel):
    """Step 2: Confirm market selection"""
    session_id: str
    ticker: str
    market: MarketType
    company_name: Optional[str] = None


class UnifiedStep2Response(BaseModel):
    """Step 2: Market confirmation result"""
    status: str
    session_id: str
    ticker: str
    market: str
    company_name: str
    confirmed: bool
    message: str


# =============================================================================
# STEP 3: VALUATION METHOD SELECTION
# =============================================================================

class UnifiedStep3Request(BaseModel):
    """Step 3: Select valuation method"""
    session_id: str
    method: ValuationMethod
    market: MarketType


class UnifiedStep3Response(BaseModel):
    """Step 3: Method selection confirmation"""
    status: str
    session_id: str
    method: str
    market: str
    selected: bool
    available_methods: List[str]
    message: str


# =============================================================================
# STEP 4: PEER COMPANY SELECTION (For Comps & WACC)
# =============================================================================

class PeerCompany(BaseModel):
    """Peer company information"""
    ticker: str
    company_name: str
    sector: str
    industry: str
    market_cap: Optional[DataField] = None
    selected: bool = False


class UnifiedStep4Request(BaseModel):
    """Step 4: Select peer companies"""
    session_id: str
    method: ValuationMethod
    market: MarketType
    suggested_peers: Optional[List[str]] = None
    custom_peers: Optional[List[str]] = None


class UnifiedStep4Response(BaseModel):
    """Step 4: Peer selection results"""
    status: str
    session_id: str
    method: str
    market: str
    target_company: str
    suggested_peers: List[PeerCompany]
    selected_peers: List[str]
    message: str


# =============================================================================
# STEP 5: ASSUMPTIONS PREPARATION
# =============================================================================

class AssumptionCategory(BaseModel):
    """Category of assumptions"""
    category_name: str
    assumptions: Dict[str, DataField]
    requires_user_input: bool
    ai_generated: bool


class UnifiedStep5Request(BaseModel):
    """Step 5: Prepare assumptions"""
    session_id: str
    method: ValuationMethod
    market: MarketType
    generate_ai: bool = True


class UnifiedStep5Response(BaseModel):
    """Step 5: Assumptions prepared"""
    status: str
    session_id: str
    method: str
    market: str
    categories: List[AssumptionCategory]
    missing_data_summary: MissingDataSummary
    ai_provider: Optional[str] = None
    message: str


# =============================================================================
# STEP 6: DATA FETCHING (CRITICAL - Most Complex)
# =============================================================================

class HistoricalFinancialsData(BaseModel):
    """
    Standardized historical financials structure.
    BOTH markets MUST return this exact structure.
    """
    # Income Statement
    revenue: Optional[DataField] = None
    cogs: Optional[DataField] = None
    ebitda: Optional[DataField] = None
    net_income: Optional[DataField] = None
    operating_expenses: Optional[DataField] = None
    sg_and_a: Optional[DataField] = None
    depreciation: Optional[DataField] = None
    
    # Cash Flow
    capex: Optional[DataField] = None
    free_cash_flow: Optional[DataField] = None
    operating_cash_flow: Optional[DataField] = None
    
    # Balance Sheet
    total_assets: Optional[DataField] = None
    total_debt: Optional[DataField] = None
    cash_and_equivalents: Optional[DataField] = None
    inventory: Optional[DataField] = None
    accounts_receivable: Optional[DataField] = None
    accounts_payable: Optional[DataField] = None
    shareholders_equity: Optional[DataField] = None
    
    # Calculated Metrics
    revenue_cagr: Optional[DataField] = None
    avg_ebitda_margin: Optional[DataField] = None
    avg_roe: Optional[DataField] = None
    avg_roa: Optional[DataField] = None


class ForecastDriversData(BaseModel):
    """Standardized forecast drivers structure"""
    # Revenue Growth
    revenue_growth_forecast: Optional[DataField] = None
    volume_growth_split: Optional[DataField] = None
    
    # Margins
    ebitda_margin_forecast: Optional[DataField] = None
    tax_rate: Optional[DataField] = None
    
    # Working Capital
    ar_days: Optional[DataField] = None
    inv_days: Optional[DataField] = None
    ap_days: Optional[DataField] = None
    
    # CapEx & Depreciation
    capex_pct_of_revenue: Optional[DataField] = None
    useful_life_existing: Optional[DataField] = None
    useful_life_new: Optional[DataField] = None
    
    # DCF Parameters
    risk_free_rate: Optional[DataField] = None
    equity_risk_premium: Optional[DataField] = None
    beta: Optional[DataField] = None
    cost_of_debt: Optional[DataField] = None
    wacc: Optional[DataField] = None
    terminal_growth_rate: Optional[DataField] = None
    terminal_ebitda_multiple: Optional[DataField] = None


class MarketDataBase(BaseModel):
    """Standardized market data structure"""
    current_stock_price: Optional[DataField] = None
    shares_outstanding: Optional[DataField] = None
    market_cap: Optional[DataField] = None
    beta: Optional[DataField] = None
    total_debt: Optional[DataField] = None
    cash: Optional[DataField] = None
    currency: Optional[DataField] = None
    fifty_two_week_high: Optional[DataField] = None
    fifty_two_week_low: Optional[DataField] = None
    average_volume: Optional[DataField] = None


class DuPontMetricsData(BaseModel):
    """Standardized DuPont analysis metrics"""
    # Profitability
    net_profit_margin: Optional[DataField] = None
    return_on_assets: Optional[DataField] = None
    return_on_equity: Optional[DataField] = None
    
    # Efficiency
    asset_turnover: Optional[DataField] = None
    inventory_turnover: Optional[DataField] = None
    receivables_turnover: Optional[DataField] = None
    
    # Leverage
    equity_multiplier: Optional[DataField] = None
    debt_to_equity: Optional[DataField] = None
    interest_coverage: Optional[DataField] = None


class CompsMultiplesData(BaseModel):
    """Standardized trading comparables multiples"""
    # Value Multiples
    ev_to_ebitda: Optional[DataField] = None
    ev_to_sales: Optional[DataField] = None
    ev_to_ebit: Optional[DataField] = None
    p_to_e: Optional[DataField] = None
    p_to_b: Optional[DataField] = None
    p_to_sales: Optional[DataField] = None
    
    # Industry Specific
    ev_to_subscribers: Optional[DataField] = None
    p_to_ffo: Optional[DataField] = None


class UnifiedStep6Request(BaseModel):
    """
    Step 6: Fetch API Data - UNIFIED REQUEST
    Used by BOTH International and Vietnamese markets
    """
    session_id: str = Field(..., description="Session identifier")
    market: MarketType = Field(..., description="Market type")
    method: ValuationMethod = Field(..., description="Valuation method")
    history_years: int = Field(5, ge=3, le=10, description="Historical years to fetch")
    include_quarterly: bool = Field(True, description="Include quarterly data")
    use_cache: bool = Field(True, description="Use cached data if available")


class UnifiedStep6Response(BaseModel):
    """
    Step 6: Fetch API Data - UNIFIED RESPONSE
    BOTH markets MUST return this exact structure.
    
    CRITICAL: This is the contract that prevents mapping issues.
    Vietnamese backend MUST transform its raw data into this structure.
    International backend MUST also conform to this structure.
    """
    status: str
    session_id: str
    ticker: str
    market: str
    method: str
    
    # Core data structures (ALL fields optional but structure required)
    historical_financials: Optional[HistoricalFinancialsData] = Field(
        None, 
        description="Historical financial data - NESTED structure with DataField wrappers"
    )
    forecast_drivers: Optional[ForecastDriversData] = Field(
        None,
        description="Forecast drivers and assumptions - NESTED structure"
    )
    market_data: Optional[MarketDataBase] = Field(
        None,
        description="Current market data - NESTED structure"
    )
    dupont_metrics: Optional[DuPontMetricsData] = Field(
        None,
        description="DuPont analysis metrics - NESTED structure"
    )
    comps_multiples: Optional[CompsMultiplesData] = Field(
        None,
        description="Trading comparables multiples - NESTED structure"
    )
    
    # Metadata
    data_source: str = Field(..., description="Primary data source (yfinance, vietstock, pdf_extraction)")
    fetch_timestamp: datetime = Field(..., description="When data was fetched")
    cache_used: bool = Field(False, description="Whether cached data was used")
    periods_covered: List[str] = Field(default_factory=list, description="Reporting periods included")
    
    # Quality indicators
    missing_data_summary: Optional[MissingDataSummary] = None
    data_quality_flags: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    message: str


# =============================================================================
# STEP 7: HISTORICAL DATA PROCESSING
# =============================================================================

class ProcessedHistoricalPeriod(BaseModel):
    """Processed historical period data"""
    period: str
    year: int
    data: Dict[str, DataField]
    growth_rates: Optional[Dict[str, DataField]] = None
    margins: Optional[Dict[str, DataField]] = None


class UnifiedStep7Request(BaseModel):
    """Step 7: Process historical data"""
    session_id: str
    method: ValuationMethod
    market: MarketType
    adjustments: Optional[Dict[str, Any]] = None


class UnifiedStep7Response(BaseModel):
    """Step 7: Historical data processed"""
    status: str
    session_id: str
    method: str
    market: str
    processed_periods: List[ProcessedHistoricalPeriod]
    trend_analysis: Dict[str, DataField]
    adjustments_applied: List[str]
    missing_data_summary: MissingDataSummary
    message: str


# =============================================================================
# STEP 8: MANUAL OVERRIDES & AI SUGGESTIONS
# =============================================================================

class OverrideCategory(BaseModel):
    """Category with override values"""
    category: str
    original_values: Dict[str, DataField]
    suggested_values: Dict[str, DataField]
    user_overrides: Dict[str, DataField]
    final_values: Dict[str, DataField]


class UnifiedStep8Request(BaseModel):
    """Step 8: Manual overrides"""
    session_id: str
    method: ValuationMethod
    market: MarketType
    category: str
    overrides: Dict[str, Any]
    generate_ai_suggestion: bool = True


class UnifiedStep8Response(BaseModel):
    """Step 8: Overrides applied"""
    status: str
    session_id: str
    method: str
    market: str
    category: str
    original_values: Dict[str, DataField]
    ai_suggestions: Optional[Dict[str, DataField]] = None
    user_overrides: Dict[str, DataField]
    final_values: Dict[str, DataField]
    impact_on_valuation: Optional[Dict[str, Any]] = None
    message: str


# =============================================================================
# STEP 9: ASSUMPTIONS CONFIRMATION
# =============================================================================

class UnifiedStep9Request(BaseModel):
    """Step 9: Confirm all assumptions"""
    session_id: str
    method: ValuationMethod
    market: MarketType
    confirmed_assumptions: Dict[str, Any]


class UnifiedStep9Response(BaseModel):
    """Step 9: Assumptions confirmed"""
    status: str
    session_id: str
    method: str
    market: str
    all_categories_confirmed: bool
    confirmed_assumptions: Dict[str, Any]
    ready_for_valuation: bool
    validation_errors: List[str] = Field(default_factory=list)
    message: str


# =============================================================================
# STEP 10: VALUATION EXECUTION
# =============================================================================

class ValuationResultSummary(BaseModel):
    """Summary of valuation results"""
    enterprise_value: Optional[DataField] = None
    equity_value: Optional[DataField] = None
    fair_value_per_share: Optional[DataField] = None
    current_price: Optional[DataField] = None
    implied_upside_downside: Optional[DataField] = None
    valuation_range_low: Optional[DataField] = None
    valuation_range_high: Optional[DataField] = None


class SensitivityAnalysis(BaseModel):
    """Sensitivity analysis results"""
    variable_1: str
    variable_2: str
    ranges: Dict[str, List[float]]
    results_matrix: List[List[float]]


class UnifiedStep10Request(BaseModel):
    """Step 10: Execute valuation"""
    session_id: str
    method: ValuationMethod
    market: MarketType
    run_sensitivity: bool = True
    scenario_analysis: bool = True


class UnifiedStep10Response(BaseModel):
    """Step 10: Valuation completed"""
    status: str
    session_id: str
    method: str
    market: str
    ticker: str
    company_name: str
    
    # Results
    valuation_summary: ValuationResultSummary
    detailed_outputs: Dict[str, Any]
    
    # Analysis
    sensitivity_analysis: Optional[SensitivityAnalysis] = None
    scenario_analysis: Optional[Dict[str, ValuationResultSummary]] = None
    
    # Quality
    confidence_level: str
    key_assumptions_summary: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)
    
    calculation_timestamp: datetime
    message: str


# =============================================================================
# UTILITY SCHEMAS
# =============================================================================

class SessionStatusResponse(BaseModel):
    """Universal session status check"""
    session_id: str
    current_step: int
    market: str
    method: str
    ticker: Optional[str] = None
    company_name: Optional[str] = None
    completed_steps: List[int]
    data_completeness: Dict[str, float]
    ready_for_next_step: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Standardized error response"""
    success: bool = False
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None
    suggestions: List[str] = Field(default_factory=list)
