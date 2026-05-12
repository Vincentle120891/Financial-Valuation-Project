# Backend-Frontend Mapping Analysis
## 2.2 Data Handling Refactor - Issues & Recommendations

### Current Architecture: 3 Valuation Methods × 2 Market Versions

The system correctly implements the matrix workflow:
- **Rows (Methods)**: DCF, DuPont, Trading Comps
- **Columns (Markets)**: International, Vietnam
- **Unified Schema**: `unified_step_schemas.py` defines the contract

---

## CRITICAL MAPPING ISSUES IDENTIFIED

### Issue #1: Vietnamese Endpoint Returns Non-Unified Response ❌

**Location**: `/backend/app/api/routes/vietnamese_market_data_routes.py:768`

**Problem**:
```python
@router.post("/vn-step-6-fetch-data", response_model=vn_Step6FetchResponse)
```

The Vietnamese endpoint returns `vn_Step6FetchResponse` (legacy format) instead of `UnifiedStep6Response`.

**Frontend Impact**: 
- Frontend in `ValuationFlow.jsx:695-722` must manually transform Vietnamese response
- Creates duplicate transformation logic in frontend
- Violates "Backend provides unified schema" principle

**Solution**:
```python
@router.post("/vn-step-6-fetch-data", response_model=UnifiedStep6Response)
async def fetch_vn_data(request: vn_Step6FetchRequest):
    # ... existing fetch logic ...
    
    # ADD: Transform to unified schema before returning
    unified_response = VNStep6UnifiedTransformer.transform_to_unified(
        raw_data=fetch_result,
        method=request.method,
        session_cache=session
    )
    return unified_response
```

---

### Issue #2: Frontend Handles Both Legacy & Unified Formats ❌

**Location**: `/frontend/src/components/valuation-flow/ApiDataStep.jsx:92-132`

**Problem**:
```javascript
// Helper function to extract values from data_fields array format used by backend
// Backend returns: { years: [2020, 2021], data_fields: [{ field_name: 'Revenue_2020', value: 100 }, ...] }
// Frontend expects: { revenue: { 2020: 100, 2021: 110 }, ... }
const getFieldValues = (data, fieldNamePatterns) => { ... }
```

**Root Cause**: 
- Backend has TWO different response formats:
  1. Legacy: `{ years: [], data_fields: [{field_name, value, status, ...}] }`
  2. Unified: `{ historical_financials: { revenue: DataField, cogs: DataField, ... } }`

**Frontend Workaround**:
- ApiDataStep.jsx must handle BOTH formats simultaneously
- Complex pattern matching logic (`getFieldValues` function)
- Multiple fallback checks throughout component

**Solution**:
1. **Backend**: Ensure ALL endpoints return ONLY unified schema
2. **Frontend**: Simplify to expect ONLY unified format:
```javascript
// AFTER refactor - much simpler
const revenue = historicalData.revenue?.value || null;
const revenueStatus = historicalData.revenue?.status || 'MISSING';
const revenueSource = historicalData.revenue?.source || 'unknown';
```

---

### Issue #3: Missing Currency/Unit Conversion Utilities ❌

**Location**: Frontend-wide

**Problem**:
- Vietnamese data uses `millions_VND`
- International data uses `USD`
- No standardized conversion utilities in frontend

**Current Ad-hoc Approach**:
```javascript
// ApiDataStep.jsx:140-147
const formatCurrency = (num) => {
  if (num === null || num === undefined) return 'N/A';
  const absNum = Math.abs(num);
  if (absNum >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
  // ... hardcoded USD formatting
};
```

**Issues**:
- No VND support
- No currency detection from `DataField.currency` field
- No unit conversion (millions → actual values)

**Solution**: Create utility module
```javascript
// frontend/src/utils/currency.js
export const formatValue = (dataField, options = {}) => {
  const { value, currency, unit } = dataField;
  
  // Handle millions conversion
  let multiplier = 1;
  if (unit?.includes('millions')) multiplier = 1e6;
  if (unit?.includes('billions')) multiplier = 1e9;
  
  const actualValue = value * multiplier;
  
  // Format based on currency
  if (currency === 'VND') {
    return formatVND(actualValue, options);
  } else if (currency === 'USD') {
    return formatUSD(actualValue, options);
  }
  
  return formatNumber(actualValue, options);
};

export const convertCurrency = (amount, fromCurrency, toCurrency, rate) => {
  // Implementation
};
```

---

### Issue #4: State Management Not Aligned with Unified Schema ❌

**Location**: `/frontend/src/components/ValuationFlow.jsx:103-114`

**Current Structure**:
```javascript
const [valuationsData, setValuationsData] = useState({
  international: {
    dcf: null,
    dupont: null,
    comps: null
  },
  vietnam: {
    dcf: null,
    dupont: null,
    comps: null
  }
});
```

**Problem**:
- Matrix structure is correct ✅
- BUT stored data format varies between markets
- International: May receive unified OR legacy format
- Vietnamese: Receives legacy format, requires manual transformation

**Impact**:
- Inconsistent data access patterns
- Need for defensive coding throughout components
- Difficult to add new markets/methods

**Solution**:
1. Ensure backend ALWAYS returns unified schema
2. Standardize state update logic:
```javascript
const setValuationData = (method, data) => {
  // Validate data conforms to unified schema
  if (!isValidUnifiedStep6Response(data)) {
    console.error('Invalid unified schema received');
    return;
  }
  
  setValuationsData(prev => ({
    ...prev,
    [market]: {
      ...prev[market],
      [method.toLowerCase()]: data
    }
  }));
};
```

---

### Issue #5: API Service Layer Has Market-Specific Routing Logic ❌

**Location**: `/frontend/src/services/api.js:80-103`

**Problem**:
```javascript
export const fetchApiData = async (sessionId, method, market = 'international') => {
  // Route to Vietnamese-specific endpoint if market is vietnamese/vietnam
  if (market && market.toLowerCase() === 'vietnamese' || market.toLowerCase() === 'vietnam') {
    const response = await api.post('/vietnamese/vn-step-6-fetch-data', { ... });
    return response.data;
  } else {
    const response = await api.post('/step-6-fetch-api-data', { ... });
    return response.data;
  }
};
```

**Issues**:
- Frontend knows about backend routing details
- Different request payloads for different markets
- Violates abstraction layer principle

**Better Design**:
```javascript
// Backend should have SINGLE endpoint that routes internally
export const fetchApiData = async (sessionId, method, market = 'international') => {
  const response = await api.post('/step-6-fetch-api-data', { 
    session_id: sessionId,
    method,
    market,
    // Same payload for ALL markets
  });
  return response.data; // Always returns UnifiedStep6Response
};
```

Backend routes internally:
```python
@router.post("/step-6-fetch-api-data", response_model=UnifiedStep6Response)
async def fetch_api_data(request: UnifiedStep6Request):
    if request.market == MarketType.VIETNAM:
        # Call Vietnamese processor
        result = await vn_processor.fetch_data(...)
        return VNStep6UnifiedTransformer.transform(result)
    else:
        # Call International processor
        result = await intl_processor.fetch_data(...)
        return Step6UnifiedTransformer.transform(result)
```

---

## RECOMMENDED REFACTOR PLAN

### Phase 1: Backend Unification (Priority: HIGH)

1. **Update Vietnamese endpoint** to return `UnifiedStep6Response`
   - File: `vietnamese_market_data_routes.py`
   - Add transformer call before return
   - Update tests

2. **Deprecate legacy response models**
   - Mark `vn_Step6FetchResponse` as deprecated
   - Keep for backward compatibility during transition
   - Document migration path

3. **Create single Step 6 endpoint** (optional but recommended)
   - Merge `/step-6-fetch-api-data` and `/vn-step-6-fetch-data`
   - Internal routing based on `request.market`
   - Simplifies frontend API calls

### Phase 2: Frontend Simplification (Priority: HIGH)

1. **Remove legacy format handling**
   - Delete `getFieldValues()` function in ApiDataStep.jsx
   - Remove pattern matching logic
   - Assume unified schema always

2. **Create currency/unit utilities**
   - New file: `frontend/src/utils/currency.js`
   - Functions: `formatValue()`, `convertCurrency()`, `parseUnit()`
   - Support VND, USD, millions/billions conversions

3. **Update state management**
   - Add validation for unified schema
   - Standardize access patterns
   - Add TypeScript types (if migrating)

### Phase 3: API Service Cleanup (Priority: MEDIUM)

1. **Simplify API calls**
   - Remove market-specific routing from frontend
   - Single endpoint for all markets
   - Consistent request/response contracts

2. **Add response validation**
   - Validate responses conform to expected schema
   - Better error messages for malformed data
   - Logging for debugging

---

## TESTING CHECKLIST

### Backend Tests
- [ ] Vietnamese endpoint returns `UnifiedStep6Response`
- [ ] All fields present and correctly typed
- [ ] DataField wrappers include status, source, currency
- [ ] Transformer preserves all original calculations
- [ ] Both markets return identical structure

### Frontend Tests
- [ ] ApiDataStep renders unified format correctly
- [ ] Currency formatting works for VND and USD
- [ ] Unit conversion (millions → actual) works
- [ ] Status indicators display correctly
- [ ] Missing data handled gracefully

### Integration Tests
- [ ] End-to-end workflow for DCF International
- [ ] End-to-end workflow for DCF Vietnam
- [ ] End-to-end workflow for DuPont (both markets)
- [ ] End-to-end workflow for Comps (both markets)
- [ ] Switching between methods preserves data integrity

---

## FILES TO MODIFY

### Backend
1. `/backend/app/api/routes/vietnamese_market_data_routes.py`
   - Update response model
   - Add transformer call

2. `/backend/app/services/vietnamese/vn_step6_unified_transformer.py`
   - Ensure complete transformation coverage
   - Add missing field mappings

3. `/backend/app/api/routes/valuation_routes.py` (optional)
   - Consider merging endpoints

### Frontend
1. `/frontend/src/components/valuation-flow/ApiDataStep.jsx`
   - Remove legacy format handling
   - Simplify data access

2. `/frontend/src/components/ValuationFlow.jsx`
   - Add schema validation
   - Standardize state updates

3. `/frontend/src/services/api.js`
   - Simplify market routing (optional)
   - Add response validation

4. **NEW**: `/frontend/src/utils/currency.js`
   - Currency formatting utilities
   - Unit conversion functions

---

## SUCCESS CRITERIA

✅ Backend returns ONLY `UnifiedStep6Response` for all markets/methods
✅ Frontend assumes ONLY unified schema (no legacy handling)
✅ Currency/unit utilities work for VND and USD
✅ API service layer has consistent interface
✅ All 6 combinations (3 methods × 2 markets) work identically
✅ No data loss or calculation changes during refactor
✅ Frontend code reduced by ~30% (removing legacy handling)

