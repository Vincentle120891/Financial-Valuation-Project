# DCF Model Data Architecture - Enhanced Implementation

## Overview
This document describes the enhanced data handling architecture for the DCF model workflow, implementing strict schema mapping, validation middleware, and adapter patterns to prevent data mismatches.

## New Components Created

### 1. Metric Registry (`backend/app/core/metric_registry.py`)
**Purpose**: Centralized source of truth for all financial metrics

**Features**:
- Maps internal metric IDs to external API keys (yfinance, Alpha Vantage, FMP)
- Defines data types, units, and validation rules for each metric
- Specifies which metrics are required for each valuation method (DCF, DuPont, COMPS)
- Includes calculation formulas for derived metrics
- Categorizes metrics (Income Statement, Balance Sheet, Cash Flow, Market Data, Ratios, Forecast)

**Example Structure**:
```python
"revenue": {
    "display_name": "Total Revenue",
    "category": MetricCategory.INCOME_STATEMENT,
    "type": DataType.FLOAT,
    "unit": "currency",
    "sources": {
        "yfinance": "total_revenue",
        "alpha_vantage": "totalRevenue",
        "financial_modeling_prep": "revenue"
    },
    "validation": {"min_value": 0},
    "required_for_methods": ["DCF", "COMPS"]
}
```

### 2. API Adapter Layer (`backend/app/services/api_adapter.py`)
**Purpose**: Separates fetching logic from mapping/normalization logic

**Key Classes**:
- `APIAdapter`: Unified interface for all data providers
- `DataValidationError`: Custom exception for validation failures

**Pipeline Steps**:
1. **Fetch Raw Data**: Provider-specific API calls
2. **Map & Normalize**: Convert API keys to internal IDs, normalize units
3. **Validate**: Check types, ranges, completeness
4. **Calculate**: Compute derived metrics using formulas
5. **Aggregate**: Combine company + peer data with averages

**Key Methods**:
- `fetch_raw_data(ticker, metrics)`: Get raw API response
- `map_and_normalize(raw_data, ticker)`: Apply registry mappings
- `calculate_derived_metrics(fetched_data)`: Calculate ratios/derived values
- `process_ticker(ticker, required_metrics)`: Full pipeline execution
- `process_multiple_tickers(tickers, method)`: Process company + peers together

### 3. Validation Middleware (`backend/app/middleware/validation_middleware.py`)
**Purpose**: Pre-save validation layer ensuring data quality

**Key Features**:
- Field-level validation (type, range, completeness)
- Statistical outlier detection (z-score analysis vs peers)
- Step transition validation (ensures required data before proceeding)
- Data quality scoring and warnings

**Validation Levels**:
1. **Single Field**: Type checking, range validation, status verification
2. **Complete Dataset**: Completeness scoring, missing required fields
3. **Peer Comparison**: Outlier detection using statistical analysis
4. **Step Transition**: Workflow gatekeeping based on data readiness

**Validation Report Structure**:
```python
{
    "status": "VALID|INVALID|INCOMPLETE|PARTIAL",
    "completeness_score": 0.85,
    "validation_errors": [...],
    "warnings": [...],
    "missing_required": [...],
    "invalid_fields": [...],
    "data_quality_issues": [...]
}
```

## Integration with Existing Workflow

### Step 6 Enhancement (Fetch API Data)
The `/step-6-fetch-api-data` endpoint now uses the new architecture:

```python
# 1. Create validator for the method
validator = create_validation_middleware(method)

# 2. Process all tickers through APIAdapter
adapter_result = process_multiple_tickers(all_tickers, method)

# 3. Validate before saving
validation_report = validator.validate_complete_dataset({...})

# 4. Build structured response with status tracking
structured_data = {...}
missing_inputs = [...]

# 5. Transform to unified schema and save
unified_response = Step6UnifiedTransformer.transform_any_response(...)
```

### Data Flow from Step 4 to Step 9

#### Step 4: Peer Selection
- User selects 5-10 peer companies
- Peer tickers saved to session: `session["peer_tickers"]`
- Passed to subsequent steps

#### Step 5: Requirements Review
- Shows required inputs based on selected method
- Uses `MetricRegistry.get_required_metrics_for_method(method)`
- All fields initially marked as MISSING

#### Step 6: API Data Fetch (ENHANCED)
- **Before**: Direct yfinance calls with hardcoded mappings
- **After**: 
  1. `APIAdapter.process_multiple_tickers()` fetches company + peer data
  2. Registry mappings convert API keys → internal IDs
  3. Normalization handles units, percentages, signs
  4. Derived metrics calculated automatically
  5. `ValidationMiddleware` checks data quality
  6. Results categorized: FETCHED, CALCULATED, MISSING
  7. Missing inputs identified for Step 7

#### Step 7: Historical Data Extraction
- Receives missing inputs list from Step 6
- Three retrieval options:
  1. PDF Upload → OCR extraction
  2. AI Web Search → targeted queries
  3. External AI Tools → specialized extraction
- Only fills historical gaps (no forecast generation)
- Updates data status: MISSING → FETCHED (PDF/AI)

#### Step 8: Forecast Assumptions
**Part A - Historical Trendlines** (Automatic):
- Calculates mean, median, average, CAGR, volatility
- Uses historical data from Steps 6-7
- Displays in UI for user reference

**Part B - AI Suggestions** (User-triggered):
- User clicks "Suggestion by AI"
- AI generates forecasts per category with explanations
- Historical trendlines included in prompts
- User can modify each suggestion manually
- Status: AI_SUGGESTION (requires confirmation)

#### Step 9: Confirm Assumptions
- Consolidates ALL inputs from Steps 6, 7, 8
- Final validation before calculation:
  - All required metrics present?
  - No invalid fields?
  - Completeness score > threshold?
- User can modify any value
- Click "Calculate" → Step 10

#### Step 10: Run Valuation
- Executes valuation models (DCF/DuPont/COMPS)
- Generates charts and visual outputs
- Exports results

## Benefits of New Architecture

### 1. Prevents Data Mismatches
- **Centralized Registry**: Single source of truth for field mappings
- **Type Safety**: Explicit data types prevent type errors
- **Validation Gates**: Catches errors before saving to session

### 2. Handles API Changes Gracefully
- **Adapter Pattern**: Change API keys in registry only, no code changes
- **Fallback Logic**: Multiple sources per metric
- **Calculated Fallbacks**: Derive missing data from available data

### 3. Improves Data Quality
- **Range Validation**: Catches outliers and impossible values
- **Statistical Analysis**: Z-score detection vs peer group
- **Completeness Scoring**: Quantifies data readiness

### 4. Enables Traceability
- **Source Tracking**: Each value tagged with source (API/CALCULATED/AI/PDF)
- **Timestamp Logging**: When each value was fetched/calculated
- **Error Messages**: Detailed validation failure reasons

### 5. Supports Multi-Method Workflows
- **Method-Specific Requirements**: Different metrics for DCF vs DuPont vs COMPS
- **Independent Tracks**: Each method's data stored separately
- **Peer Comparisons**: Automatic peer average calculations

## Testing Recommendations

### Unit Tests Needed
1. `test_metric_registry.py`: Verify all mappings and helper functions
2. `test_api_adapter.py`: Test each pipeline stage independently
3. `test_validation_middleware.py`: Test validation rules and outlier detection

### Integration Tests Needed
1. `test_step6_full_pipeline.py`: End-to-end Step 6 with real API calls
2. `test_step_transitions.py`: Validate step gating logic
3. `test_multi_method_workflow.py`: Test parallel DCF/DuPont/COMPS flows

### Mock Data Tests
1. Test with incomplete API responses
2. Test with invalid/outlier values
3. Test with missing peer data
4. Test edge cases (zero values, negative equity, etc.)

## Migration Notes

### Backward Compatibility
- Existing endpoints maintain same signatures
- Unified schema transformers handle legacy formats
- Session structure unchanged

### Gradual Rollout
1. Deploy registry and adapter (non-breaking)
2. Enable validation middleware in logging-only mode
3. Switch Step 6 to use new adapter
4. Enable validation gates for step transitions

## Future Enhancements

### Planned Improvements
1. **Multi-Provider Failover**: Try yfinance → Alpha Vantage → FMP automatically
2. **Smart Imputation**: ML-based estimation for missing values
3. **Real-time Validation**: Frontend validation using shared registry
4. **Audit Trail**: Complete history of all data changes
5. **Performance Caching**: Redis cache for API responses

### Extensibility
- Add new providers by extending `APIAdapter`
- Add new metrics by updating `METRIC_REGISTRY`
- Add new valuation methods with minimal code changes
- Support additional markets (Vietnam, Japan, etc.)
