# Vietnamese Market Schema Alignment Analysis

## Executive Summary

**Current Status**: The Vietnamese market has all necessary inputs captured in its processors, but they are **NOT correctly aligned** with the unified schemas. The Vietnamese system uses local schemas and returns data in different structures than what the unified schema system expects.

## Key Findings

### 1. Schema Structure Mismatch

#### Unified Schema Requirements (unified_step_schemas.py)
- Uses `DataField` wrapper for ALL numerical values
- Nested structure with specific data models:
  - `HistoricalFinancialsData` 
  - `ForecastDriversData`
  - `MarketDataBase`
  - `DuPontMetricsData`
  - `CompsMultiplesData`
- Returns `UnifiedStep6Response`, `UnifiedStep7Response`, etc.

#### Vietnamese Current Implementation
- Uses raw dictionaries: `Dict[str, Dict[str, Any]]`
- Time-series format with period keys
- No `DataField` wrappers
- Returns custom responses: `vn_Step6FetchResponse`, `vn_Step7Response`, etc.

### 2. Step-by-Step Analysis

#### **Step 5: Requirements Collection**

**Vietnamese Schema** (`vn_Step5Request`/`vn_Step5Response`):
```python
class vn_Step5Request(BaseModel):
    session_id: str
    method: str
    # DCF parameters
    dcf_forecast_years: int = 5
    dcf_terminal_growth_rate: float = 0.03
    dcf_risk_free_rate: Optional[float] = None
    dcf_market_risk_premium: Optional[float] = None
    dcf_country_risk_premium: Optional[float] = None
    dcf_tax_rate: float = 0.20
    # DuPont parameters
    dupont_years: int = 5
    # Comps parameters
    comps_peer_count: int = 5
    comps_multiples: List[str] = ["P/E", "P/B", "EV/EBITDA"]
```

**Unified Schema** (`UnifiedStep5Request`/`UnifiedStep5Response`):
```python
class UnifiedStep5Request(BaseModel):
    session_id: str
    method: ValuationMethod
    market: MarketType
    generate_ai: bool = True

class AssumptionCategory(BaseModel):
    category_name: str
    assumptions: Dict[str, DataField]  # ← DataField wrapper required
    requires_user_input: bool
    ai_generated: bool
```

**Gap**: Vietnamese uses flat parameter structure; Unified requires categorized assumptions with DataField wrappers.

---

#### **Step 6: Data Fetching**

**Vietnamese Schema** (`vn_DataFetchInput`/`vn_Step6FetchResponse`):
```python
class vn_DataFetchInput(BaseModel):
    ticker: str
    company_name: str
    exchange: str
    history_years: int
    include_quarterly: bool
    fetch_income_statement: bool = True
    fetch_balance_sheet: bool = True
    fetch_cash_flow: bool = True
    fetch_peer_data: bool = False
    peer_tickers: List[str] = []

class RawDataBundle(BaseModel):
    source_provider: str
    fetch_timestamp: datetime
    currency_unit: str
    income_statement_raw: Dict[str, Dict[str, Any]]  # ← Raw dict, no DataField
    balance_sheet_raw: Dict[str, Dict[str, Any]]
    cash_flow_raw: Dict[str, Dict[str, Any]]
    peer_data_raw: Dict[str, Dict[str, Any]]
```

**Unified Schema** (`UnifiedStep6Request`/`UnifiedStep6Response`):
```python
class UnifiedStep6Request(BaseModel):
    session_id: str
    market: MarketType
    method: ValuationMethod
    history_years: int = 5
    include_quarterly: bool = True
    use_cache: bool = True

class HistoricalFinancialsData(BaseModel):
    revenue: Optional[DataField] = None  # ← DataField wrapper required
    cogs: Optional[DataField] = None
    ebitda: Optional[DataField] = None
    net_income: Optional[DataField] = None
    # ... more fields

class UnifiedStep6Response(BaseModel):
    status: str
    session_id: str
    ticker: str
    market: str
    method: str
    historical_financials: Optional[HistoricalFinancialsData]  # ← Nested structure
    forecast_drivers: Optional[ForecastDriversData]
    market_data: Optional[MarketDataBase]
    dupont_metrics: Optional[DuPontMetricsData]
    comps_multiples: Optional[CompsMultiplesData]
```

**Gap**: 
- Vietnamese returns raw time-series dictionaries
- Unified requires nested structure with DataField wrappers
- Missing transformation layer to convert Vietnamese outputs

---

#### **Step 7: Historical Data Processing**

**Vietnamese Schema** (`vn_HistoricalDataInput`/`vn_HistoricalDataOutput`):
```python
class vn_HistoricalDataInput(BaseModel):
    ticker: str
    company_name: str
    exchange: str
    currency_unit: str
    income_statement_raw: Dict[str, Dict[str, Any]]  # ← Raw dict
    balance_sheet_raw: Dict[str, Dict[str, Any]]
    cash_flow_raw: Dict[str, Dict[str, Any]]
    selected_model: str

class NormalizedFinancials(BaseModel):
    currency: str
    unit_multiplier: float
    revenue: Dict[str, float]  # ← Period-keyed dict, no DataField
    cost_of_revenue: Dict[str, float]
    # ... more fields as Dict[str, float]
```

**Unified Schema** (`UnifiedStep7Request`/`UnifiedStep7Response`):
```python
class ProcessedHistoricalPeriod(BaseModel):
    period: str
    year: int
    data: Dict[str, DataField]  # ← DataField wrapper required
    growth_rates: Optional[Dict[str, DataField]] = None
    margins: Optional[Dict[str, DataField]] = None

class UnifiedStep7Response(BaseModel):
    status: str
    session_id: str
    method: str
    market: str
    processed_periods: List[ProcessedHistoricalPeriod]  # ← List of periods
    trend_analysis: Dict[str, DataField]
    adjustments_applied: List[str]
    missing_data_summary: MissingDataSummary
```

**Gap**:
- Vietnamese uses Dict[str, float] for time-series
- Unified uses List[ProcessedHistoricalPeriod] with DataField wrappers
- Different structural approach (dict vs list of objects)

---

#### **Step 8: AI Assumptions**

**Vietnamese Schema** (`vn_AIAssumptionsInput`/`vn_AIAssumptionsOutput`):
```python
class vn_AIAssumptionItem(BaseModel):
    parameter_name: str
    suggested_value: Any
    unit: str
    confidence_score: float
    rationale: str
    source: str
    vietnam_context: str
    min_reasonable: Optional[Any] = None
    max_reasonable: Optional[Any] = None

class vn_AIAssumptionsOutput(BaseModel):
    session_id: str
    model_type: str
    assumptions: List[vn_AIAssumptionItem]  # ← Custom structure
    sector_analysis: Dict[str, Any]
    macro_integration: Dict[str, Any]
```

**Unified Schema** (`UnifiedStep8Request`/`UnifiedStep8Response`):
```python
class AssumptionItem(BaseModel):
    assumption_key: str
    display_name: str
    value: DataField  # ← DataField wrapper required
    category: str
    is_editable: bool
    validation_rules: Optional[Dict[str, Any]] = None

class UnifiedStep8Response(BaseModel):
    status: str
    session_id: str
    method: str
    market: str
    categories: List[AssumptionCategory]
    ai_generated_assumptions: List[AssumptionItem]
    missing_data_summary: MissingDataSummary
```

**Gap**:
- Vietnamese has good Vietnam-specific context fields
- Unified requires categorization and DataField wrappers
- Missing `MissingDataSummary` in Vietnamese output

---

#### **Step 9: Confirmation**

**Vietnamese Schema** (`vn_ConfirmationInput`/`vn_ConfirmationOutput`):
```python
class vn_ConfirmationInput(BaseModel):
    session_id: str
    confirmed_assumptions: Dict[str, Any]
    manual_overrides: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

class vn_ConfirmationOutput(BaseModel):
    session_id: str
    status: str
    confirmation_timestamp: datetime
    locked_assumptions: Dict[str, Any]
    audit_trail: Dict[str, Any]
```

**Unified Schema** (`UnifiedStep9Request`/`UnifiedStep9Response`):
```python
class UnifiedStep9Request(BaseModel):
    session_id: str
    method: ValuationMethod
    market: MarketType
    confirmed_assumptions: Dict[str, DataField]  # ← DataField wrapper
    manual_overrides: Optional[Dict[str, Any]] = None

class UnifiedStep9Response(BaseModel):
    status: str
    session_id: str
    method: str
    market: str
    confirmed_assumptions: Dict[str, DataField]
    valuation_inputs_ready: Dict[str, DataField]
    missing_data_summary: MissingDataSummary
    data_quality_score: float
```

**Gap**:
- Vietnamese lacks DataField wrappers
- Missing `valuation_inputs_ready` structured output
- Missing `data_quality_score`

---

#### **Step 10: Valuation**

**Vietnamese Schema** (`vn_ValuationInput`/`vn_ValuationOutput`):
```python
class vn_ValuationInput(BaseModel):
    session_id: str
    model_type: Literal["dcf", "dupont", "comps"]
    confirmed_assumptions: Dict[str, Any]
    historical_data: Dict[str, Any]
    market_data: Dict[str, Any]

class vn_ValuationOutput(BaseModel):
    session_id: str
    model_type: str
    valuation_result: Dict[str, Any]
    sensitivity_analysis: Optional[Dict[str, Any]] = None
    scenario_analysis: Optional[Dict[str, Any]] = None
```

**Unified Schema** (`UnifiedStep10Request`/`UnifiedStep10Response`):
```python
class DCFValuationResult(BaseModel):
    intrinsic_value_per_share: DataField
    equity_value: DataField
    enterprise_value: DataField
    terminal_value: DataField
    wacc: DataField
    # ... more fields

class DuPontValuationResult(BaseModel):
    roe_breakdown: Dict[str, DataField]
    # ... more fields

class UnifiedStep10Response(BaseModel):
    status: str
    session_id: str
    method: str
    market: str
    dcf_result: Optional[DCFValuationResult] = None
    dupont_result: Optional[DupontValuationResult] = None
    comps_result: Optional[CompsValuationResult] = None
    sensitivity_analysis: Optional[Dict[str, Any]] = None
    missing_data_summary: MissingDataSummary
```

**Gap**:
- Vietnamese returns generic Dict[str, Any]
- Unified requires structured result models with DataField wrappers
- Missing standardized sensitivity analysis structure

---

## Complete Input Coverage Analysis

### ✅ All Inputs ARE Present in Vietnamese System

| Input Category | Vietnamese Processor | Unified Schema | Status |
|---------------|---------------------|----------------|--------|
| **Company Info** | ✓ ticker, company_name, exchange | ✓ ticker, company_name, market | ✅ Covered |
| **Historical Financials** | ✓ IS, BS, CF (raw dicts) | ✓ HistoricalFinancialsData (DataField) | ✅ Covered, ❌ Structure |
| **Market Data** | ✓ current_price, beta, risk_free_rate | ✓ MarketDataBase (DataField) | ✅ Covered, ❌ Structure |
| **Forecast Drivers** | ✓ In AI assumptions | ✓ ForecastDriversData | ✅ Covered, ❌ Location |
| **DuPont Metrics** | ✓ In vn_dupont_engine | ✓ DuPontMetricsData | ✅ Covered, ❌ Structure |
| **Comps Multiples** | ✓ In vn_comps_engine | ✓ CompsMultiplesData | ✅ Covered, ❌ Structure |
| **AI Assumptions** | ✓ vn_AIAssumptionItem | ✓ AssumptionItem | ✅ Covered, ❌ Wrapper |
| **User Overrides** | ✓ manual_overrides | ✓ manual_overrides | ✅ Aligned |
| **Peer Data** | ✓ peer_tickers, peer_data_raw | ✓ PeerCompany | ✅ Covered, ❌ Structure |
| **Vietnam Context** | ✓ vietnam_macro, vietnam_context | ✗ Not in unified | ⚠️ Extra (good) |

### ❌ Structural Alignment Issues

1. **No DataField Wrappers**: Vietnamese uses raw values instead of DataField wrappers
2. **Time-Series Format**: Vietnamese uses Dict[period, value]; Unified uses List[Period Objects]
3. **Missing Categorization**: Vietnamese uses flat structures; Unified uses categories
4. **Missing MissingDataSummary**: Vietnamese doesn't include standardized missing data summaries
5. **Different Response Models**: Each step has custom response instead of UnifiedStep{N}Response

---

## Required Transformations

To align Vietnamese backend with unified schemas, we need to create transformation layers:

### Transformation Layer Architecture

```
Vietnamese Processor Output → Transformation Layer → Unified Schema Response
         (raw dicts)              (converter)            (DataField wrapped)
```

### Required Converter Classes

1. **VietnameseToUnifiedConverter** (main orchestrator)
   - `convert_step6_output(vn_output) -> UnifiedStep6Response`
   - `convert_step7_output(vn_output) -> UnifiedStep7Response`
   - `convert_step8_output(vn_output) -> UnifiedStep8Response`
   - `convert_step9_output(vn_output) -> UnifiedStep9Response`
   - `convert_step10_output(vn_output) -> UnifiedStep10Response`

2. **DataFieldFactory**
   - `wrap_value(value, source, status) -> DataField`
   - `wrap_dict_to_datafield(dict_data) -> Dict[str, DataField]`
   - `wrap_time_series_to_historical_financials(ts_dict) -> HistoricalFinancialsData`

3. **StructureTransformers**
   - `time_series_dict_to_period_list(dict) -> List[ProcessedHistoricalPeriod]`
   - `flat_params_to_categories(flat_dict) -> List[AssumptionCategory]`
   - `raw_valuation_to_structured(raw_dict, method) -> DCF/DuPont/Comps Result`

---

## Priority Action Items

### Phase 1: Core Data Structure Alignment (HIGH PRIORITY)
1. ✅ Create `VietnameseToUnifiedConverter` class
2. ✅ Implement DataField wrapping for all numerical values
3. ✅ Transform Step 6 output to unified structure
4. ✅ Transform Step 7 output to unified structure

### Phase 2: Assumption & Workflow Alignment (MEDIUM PRIORITY)
5. ✅ Align Step 8 assumptions with unified categories
6. ✅ Add MissingDataSummary to all Vietnamese responses
7. ✅ Transform Step 9 confirmation to unified format
8. ✅ Transform Step 10 valuation results to unified format

### Phase 3: Integration & Testing (LOW PRIORITY)
9. ⏳ Update Vietnamese route handlers to use converters
10. ⏳ Test all 3 methods × 2 markets workflow
11. ⏳ Validate frontend compatibility

---

## Conclusion

**All inputs are present** in the Vietnamese system, but they require **significant structural transformation** to align with unified schemas. The Vietnamese implementation captures Vietnam-specific context well (macro indicators, TT99 standards, exchange info) which should be preserved during transformation.

**Key Recommendation**: Create a dedicated transformation layer rather than modifying existing Vietnamese processors. This maintains separation of concerns and allows both legacy and unified schemas to coexist during migration.
