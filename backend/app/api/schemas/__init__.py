"""API Schemas module - Pydantic models for request/response validation."""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


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


class ModelSelectRequest(BaseModel):
    """Request model for model selection."""
    session_id: str = Field(..., min_length=1, description="Session identifier")
    model: str = Field(..., min_length=1, description="Valuation model", examples=["DCF", "DuPont", "COMPS"])
    
    @field_validator('model')
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate valuation model."""
        allowed_models = ["DCF", "DuPont", "COMPS", "dupont", "comps", "comparable", "trading comps", "dupont analysis"]
        if v.upper() not in [m.upper() for m in allowed_models] and v.lower() not in allowed_models:
            raise ValueError(f"Model must be one of: DCF, DuPont, COMPS")
        return v


class ModelSelectResponse(BaseModel):
    """Response model for model selection."""
    message: str
    next_step: str
    selected_model: str


class PrepareInputsRequest(BaseModel):
    """Request model for prepare inputs."""
    session_id: str = Field(..., min_length=1, description="Session identifier")


class FetchDataRequest(BaseModel):
    """Request model for fetching data."""
    session_id: str = Field(..., min_length=1, description="Session identifier")


class GenerateAIRequest(BaseModel):
    """Request model for generating AI assumptions."""
    session_id: str = Field(..., min_length=1, description="Session identifier")


class ConfirmAssumptionsRequest(BaseModel):
    """Request model for confirming assumptions."""
    session_id: str = Field(..., min_length=1, description="Session identifier")
    confirmed_values: Dict[str, Any] = Field(..., description="User confirmed or modified values")


class ValuateRequest(BaseModel):
    """Request model for running valuation."""
    session_id: str = Field(..., min_length=1, description="Session identifier")


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
