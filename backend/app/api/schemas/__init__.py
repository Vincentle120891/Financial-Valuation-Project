"""API Schemas module - Pydantic models for request/response validation.

This module imports unified schemas from unified_step_schemas.py to ensure
consistent data structures across all 10 steps and both markets (International & Vietnam).

The unified schemas provide:
- Single source of truth for all API contracts
- Nested data structures with DataField wrappers
- Type safety for "3 Valuation Methods × 2 Market Versions" workflow
- Prevention of mapping issues between backend and frontend
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Import unified schemas - these are the single source of truth
from .unified_step_schemas import (
    # Core types
    DataStatus,
    ValuationMethod,
    MarketType,
    DataField,
    MissingDataSummary,
    
    # Step 1-10 unified schemas
    UnifiedStep1Request,
    UnifiedStep1Response,
    CompanySearchResult,
    UnifiedStep2Request,
    UnifiedStep2Response,
    UnifiedStep3Request,
    UnifiedStep3Response,
    UnifiedStep4Request,
    UnifiedStep4Response,
    PeerCompany,
    UnifiedStep5Request,
    UnifiedStep5Response,
    AssumptionCategory,
    UnifiedStep6Request,
    UnifiedStep6Response,
    HistoricalFinancialsData,
    ForecastDriversData,
    MarketDataBase,
    DuPontMetricsData,
    CompsMultiplesData,
    UnifiedStep7Request,
    UnifiedStep7Response,
    ProcessedHistoricalPeriod,
    UnifiedStep8Request,
    UnifiedStep8Response,
    OverrideCategory,
    UnifiedStep9Request,
    UnifiedStep9Response,
    UnifiedStep10Request,
    UnifiedStep10Response,
    ValuationResultSummary,
    SensitivityAnalysis,
    
    # Utility schemas
    SessionStatusResponse,
    ErrorResponse,
)


# =============================================================================
# REQUEST MODELS WITH VALIDATION
# =============================================================================

class SearchRequest(BaseModel):
    """Request model for ticker search."""
    query: str = Field(..., min_length=1, max_length=50, description="Search query (ticker symbol or company name)")
    market: str = Field(default="international", description="Market type", examples=["international", "vietnamese"])
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate and sanitize search query."""
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()
    
    @field_validator('market')
    @classmethod
    def validate_market(cls, v: str) -> str:
        """Validate market parameter."""
        allowed_markets = ["international", "vietnamese"]
        if v.lower() not in allowed_markets:
            raise ValueError(f"Market must be one of: {allowed_markets}")
        return v.lower()


class TickerSelectRequest(BaseModel):
    """Request model for ticker selection."""
    ticker: str = Field(..., min_length=1, max_length=20, description="Selected ticker symbol")
    market: str = Field(..., description="Market type")
    
    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        """Validate ticker format."""
        if not v.strip():
            raise ValueError("Ticker cannot be empty")
        # Allow alphanumeric, dots, and dashes
        import re
        if not re.match(r'^[A-Za-z0-9.\-]+$', v):
            raise ValueError("Ticker contains invalid characters")
        return v.strip().upper()
    
    @field_validator('market')
    @classmethod
    def validate_market(cls, v: str) -> str:
        """Validate market parameter."""
        allowed_markets = ["international", "vietnamese"]
        if v.lower() not in allowed_markets:
            raise ValueError(f"Market must be one of: {allowed_markets}")
        return v.lower()


class ManualPeerRequest(BaseModel):
    """Request model for manually adding peer tickers."""
    session_id: str = Field(..., min_length=1, description="Session identifier")
    tickers: List[str] = Field(..., min_items=1, max_items=20, description="List of peer ticker symbols to validate and add")
    market: str = Field(default="international", description="Market type")
    
    @field_validator('tickers')
    @classmethod
    def validate_tickers(cls, v: List[str]) -> List[str]:
        """Validate ticker list."""
        if not v:
            raise ValueError("Ticker list cannot be empty")
        validated = []
        import re
        for ticker in v:
            if not ticker or not ticker.strip():
                raise ValueError("Ticker cannot be empty")
            cleaned = ticker.strip().upper()
            if not re.match(r'^[A-Za-z0-9.\-]+$', cleaned):
                raise ValueError(f"Ticker '{ticker}' contains invalid characters")
            validated.append(cleaned)
        return validated
    
    @field_validator('market')
    @classmethod
    def validate_market(cls, v: str) -> str:
        """Validate market parameter."""
        allowed_markets = ["international", "vietnamese"]
        if v.lower() not in allowed_markets:
            raise ValueError(f"Market must be one of: {allowed_markets}")
        return v.lower()


class ModelSelectRequest(BaseModel):
    """Request model for model selection."""
    session_id: str = Field(..., min_length=1, description="Session identifier")
    model: str = Field(..., min_length=1, description="Valuation model", examples=["DCF", "DuPont", "COMPS"])
    market: str = Field(default="international", description="Market version", examples=["international", "vietnam"])
    
    @field_validator('model')
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate valuation model."""
        allowed_models = ["DCF", "DuPont", "COMPS", "dupont", "comps", "comparable", "trading comps", "dupont analysis"]
        if v.upper() not in [m.upper() for m in allowed_models] and v.lower() not in allowed_models:
            raise ValueError(f"Model must be one of: DCF, DuPont, COMPS")
        return v
    
    @field_validator('market')
    @classmethod
    def validate_market(cls, v: str) -> str:
        """Validate market parameter."""
        allowed_markets = ["international", "vietnam", "vietnamese"]
        if v.lower() not in allowed_markets:
            raise ValueError(f"Market must be one of: international, vietnam")
        # Normalize to 'international' or 'vietnam'
        return "vietnam" if v.lower() in ["vietnam", "vietnamese"] else "international"


class ModelSelectResponse(BaseModel):
    """Response model for model selection."""
    message: str
    next_step: str
    selected_model: str


class PrepareInputsRequest(BaseModel):
    """Request model for prepare inputs."""
    session_id: str = Field(..., min_length=1, description="Session identifier")
    market: str = Field(default="international", description="Market version")
    method: str = Field(default="DCF", description="Valuation method")


class FetchDataRequest(BaseModel):
    """Request model for fetching data."""
    session_id: str = Field(..., min_length=1, description="Session identifier")
    market: str = Field(default="international", description="Market version")
    method: str = Field(default="DCF", description="Valuation method")


class GenerateAIRequest(BaseModel):
    """Request model for generating AI assumptions."""
    session_id: str = Field(..., min_length=1, description="Session identifier")
    market: str = Field(default="international", description="Market version")
    method: str = Field(default="DCF", description="Valuation method")


class GenerateAISuggestionRequest(BaseModel):
    """Request model for generating AI suggestions for a specific category (Step 8)."""
    session_id: str = Field(..., min_length=1, description="Session identifier")
    category: str = Field(..., description="Assumption category (e.g., REVENUE_DRIVERS, COST_MARGINS)")
    market: str = Field(default="international", description="Market version")
    method: str = Field(default="DCF", description="Valuation method")


class ConfirmAssumptionsRequest(BaseModel):
    """Request model for confirming assumptions."""
    session_id: str = Field(..., min_length=1, description="Session identifier")
    confirmed_values: Dict[str, Any] = Field(..., description="User confirmed or modified values")
    market: str = Field(default="international", description="Market version")
    method: str = Field(default="DCF", description="Valuation method")


class ValuateRequest(BaseModel):
    """Request model for running valuation."""
    session_id: str = Field(..., min_length=1, description="Session identifier")
    market: str = Field(default="international", description="Market version")
    method: str = Field(default="DCF", description="Valuation method")


class MultiMethodValuateRequest(BaseModel):
    """Request model for running multi-method valuation in parallel.
    
    This endpoint allows executing multiple valuation methods simultaneously
    using asyncio.gather for true parallel processing.
    """
    session_id: str = Field(..., min_length=1, description="Session identifier")
    methods: List[str] = Field(..., min_items=1, description="List of valuation methods to execute", examples=[["dcf", "dupont", "comps"]])
    market: str = Field(default="international", description="Market version")
    
    @field_validator('methods')
    @classmethod
    def validate_methods(cls, v: List[str]) -> List[str]:
        """Validate valuation methods."""
        allowed_methods = ["dcf", "dupont", "comps", "DCF", "DuPont", "COMPS"]
        normalized = [m.lower() for m in v]
        for method in normalized:
            if method not in ["dcf", "dupont", "comps"]:
                raise ValueError(f"Method must be one of: dcf, dupont, comps")
        return normalized


class MultiMethodValuateResponse(BaseModel):
    """Response model for multi-method valuation endpoint."""
    status: str
    market: str
    methods_requested: List[str]
    methods_completed: List[str]
    methods_failed: List[str]
    summary: Dict[str, Any]
    results: List[Dict[str, Any]]
    message: str


class ConfirmAssumptionsResponse(BaseModel):
    """Response model for confirm assumptions endpoint."""
    status: str
    message: str


class ValuateResponse(BaseModel):
    """Response model for valuation endpoint."""
    status: str
    valuation_results: List[Dict[str, Any]]
    message: str


class AssumptionConfirmRequest(BaseModel):
    """Request model for confirming assumptions."""
    session_id: str = Field(..., min_length=1, description="Session identifier")
    assumptions: Dict[str, Any] = Field(..., description="User modified or accepted assumptions")
    
    @field_validator('assumptions')
    @classmethod
    def validate_assumptions(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate assumptions structure."""
        if not isinstance(v, dict):
            raise ValueError("Assumptions must be a dictionary")
        if len(v) == 0:
            raise ValueError("Assumptions cannot be empty")
        return v


class CalculationRequest(BaseModel):
    """Request model for running valuation calculation."""
    session_id: str = Field(..., min_length=1, description="Session identifier")


class SessionFetchRequest(BaseModel):
    """Request model for fetching data in a session."""
    session_id: str = Field(..., min_length=1, description="Session identifier")


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class SearchResult(BaseModel):
    """Individual search result item."""
    symbol: str
    name: str
    exchange: str
    market: str


class SearchResponse(BaseModel):
    """Response model for ticker search."""
    results: List[SearchResult]
    message: Optional[str] = None


class SessionCreateResponse(BaseModel):
    """Response model for session creation."""
    session_id: str
    status: str
    message: Optional[str] = None
    company_data: Optional[Dict[str, Any]] = None


class SessionStatusResponse(BaseModel):
    """Response model for session status."""
    session_id: str
    status: str
    ticker: Optional[str] = None
    market: Optional[str] = None
    selected_model: Optional[str] = None
    financial_data: Optional[Dict[str, Any]] = None
    ai_suggestions: Optional[Dict[str, Any]] = None
    confirmed_assumptions: Optional[Dict[str, Any]] = None
    valuation_result: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class InputRequirement(BaseModel):
    """Model for required input fields."""
    category: str
    name: str
    requiresInput: bool = False
    defaultValue: Optional[Any] = None
    unit: Optional[str] = None
    description: Optional[str] = None


class PrepareInputsResponse(BaseModel):
    """Response model for prepare inputs endpoint."""
    status: str
    required_inputs: List[InputRequirement]
    message: str


class FetchDataResponse(BaseModel):
    """Response model for data fetch endpoint."""
    status: str
    data: Dict[str, Any]
    message: str


class AIAssumptionsResponse(BaseModel):
    """Response model for AI assumptions generation."""
    status: str
    suggestions: Dict[str, Any]
    message: str
    
    class Config:
        extra = "allow"  # Allow additional fields like _metadata with provider_errors and fallback_reason


class GenerateAIResponse(BaseModel):
    """Response model for generating AI assumptions."""
    status: str
    suggestions: Dict[str, Any]
    message: str
    
    class Config:
        extra = "allow"


class AISuggestionCategoryResponse(BaseModel):
    """Response model for Step 8 AI suggestion generation for a category."""
    status: str
    category: str
    category_name: str
    assumptions: List[Dict[str, Any]]
    ai_generated: bool = True
    message: str = ""
    
    class Config:
        extra = "allow"


class ValuationResultResponse(BaseModel):
    """Response model for valuation calculation result."""
    status: str
    result: Dict[str, Any]
    inputs_used: Dict[str, Any]


# =============================================================================
# HEALTH CHECK MODELS
# =============================================================================

class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str
    version: str
    environment: str
    timestamp: str


class ReadinessCheckResponse(BaseModel):
    """Response model for readiness check endpoint."""
    status: str
    api_keys: Dict[str, bool]
    missing_keys: List[str]
    ai_fallback_available: bool
    timestamp: str


# =============================================================================
# ERROR MODELS
# =============================================================================

class ErrorResponse(BaseModel):
    """Standard error response model."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    type: str
