"""API Schemas module - Pydantic models for request/response validation."""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# =============================================================================
# REQUEST MODELS
# =============================================================================

class SearchRequest(BaseModel):
    """Request model for ticker search."""
    query: str = Field(..., description="Search query (ticker symbol or company name)")
    market: str = Field(default="international", description="Market type", examples=["international", "vietnamese"])


class TickerSelectRequest(BaseModel):
    """Request model for ticker selection."""
    ticker: str = Field(..., description="Selected ticker symbol")
    market: str = Field(..., description="Market type")


class ModelSelectRequest(BaseModel):
    """Request model for model selection."""
    session_id: str = Field(..., description="Session identifier")
    model: str = Field(..., description="Valuation model", examples=["DCF", "DuPont", "COMPS"])


class AssumptionConfirmRequest(BaseModel):
    """Request model for confirming assumptions."""
    session_id: str = Field(..., description="Session identifier")
    assumptions: Dict[str, Any] = Field(..., description="User modified or accepted assumptions")


class CalculationRequest(BaseModel):
    """Request model for running valuation calculation."""
    session_id: str = Field(..., description="Session identifier")


class SessionFetchRequest(BaseModel):
    """Request model for fetching data in a session."""
    session_id: str = Field(..., description="Session identifier")


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
