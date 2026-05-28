"""API Schemas module - Pydantic models for request/response validation.

This module re-exports unified schemas from unified_step_schemas.py to ensure
consistent data structures across all 10 steps and both markets (International & Vietnam).

The unified schemas provide:
- Single source of truth for all API contracts
- Nested data structures with DataField wrappers
- Type safety for "3 Valuation Methods × 2 Market Versions" workflow
- Prevention of mapping issues between backend and frontend

LEGACY SCHEMAS DEPRECATED: All legacy schemas (SearchRequest, TickerSelectRequest, etc.)
have been removed. Use UnifiedStep{N}Request/Response schemas instead.
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Import ALL unified schemas - these are the single source of truth
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
    # Step 8 - Assumptions & AI Suggestion Studio
    OverrideStatus,
    AssumptionCategoryType,
    HistoricalTrendPoint,
    HistoricalTrendline,
    AISuggestion,
    AssumptionInput,
    AssumptionCategoryResponse,
    FullAssumptionsResponse,
    UnifiedStep8InitializeRequest,
    UnifiedStep8GenerateAISuggestionRequest,
    UnifiedStep8ApplyOverrideRequest,
    UnifiedStep8Response,
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
# BACKWARD COMPATIBILITY ALIASES (DEPRECATED - For transition period only)
# These will be removed in future versions. Update your code to use unified schemas.
# =============================================================================

# Step 1 aliases (deprecated - use UnifiedStep1Request/Response)
SearchRequest = UnifiedStep1Request
SearchResponse = UnifiedStep1Response

# Step 2 aliases (deprecated - use UnifiedStep2Request/Response)  
TickerSelectRequest = UnifiedStep2Request
SessionCreateResponse = UnifiedStep2Response

# Step 3 aliases (deprecated - use UnifiedStep3Request/Response)
ModelSelectRequest = UnifiedStep3Request
ModelSelectResponse = UnifiedStep3Response

# Step 4 aliases (deprecated - use UnifiedStep4Request/Response)
ManualPeerRequest = UnifiedStep4Request

# Step 5 aliases (deprecated - use UnifiedStep5Request/Response)
PrepareInputsRequest = UnifiedStep5Request
PrepareInputsResponse = UnifiedStep5Response

# Step 6 aliases (deprecated - use UnifiedStep6Request/Response)
FetchDataRequest = UnifiedStep6Request
FetchDataResponse = UnifiedStep6Response

# Step 7 aliases (deprecated - use UnifiedStep7Request/Response)
# No direct alias - Step 7 uses UnifiedStep7Request/Response

# Step 8 aliases (deprecated - use UnifiedStep8* schemas)
GenerateAIRequest = UnifiedStep8InitializeRequest
GenerateAIResponse = UnifiedStep8Response
GenerateAISuggestionRequest = UnifiedStep8GenerateAISuggestionRequest

# Step 9 aliases (deprecated - use UnifiedStep9Request/Response)
ConfirmAssumptionsRequest = UnifiedStep9Request
ConfirmAssumptionsResponse = UnifiedStep9Response
AssumptionConfirmRequest = UnifiedStep9Request

# Step 10 aliases (deprecated - use UnifiedStep10Request/Response)
ValuateRequest = UnifiedStep10Request
ValuateResponse = UnifiedStep10Response
MultiMethodValuateRequest = UnifiedStep10Request  # Note: Multi-method has special handling
MultiMethodValuateResponse = UnifiedStep10Response
CalculationRequest = UnifiedStep10Request
SessionFetchRequest = UnifiedStep10Request
ValuationResultResponse = UnifiedStep10Response

# Legacy response schemas (deprecated - use specific unified response schemas)
AISuggestionCategoryResponse = AssumptionCategoryResponse
