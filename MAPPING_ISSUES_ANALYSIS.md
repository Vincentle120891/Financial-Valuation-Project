# Backend-Frontend Mapping Issues Analysis
## 3 Valuation Methods × 2 Market Versions Architecture

---

## Executive Summary

The codebase supports the **3 Valuation Methods × 2 Market Versions** structure but has **6 critical mapping issues** between frontend and backend that risk data contamination, routing errors, and incorrect valuation engine usage.

---

## Issue #1: Market Parameter Format Mismatch ⚠️ MEDIUM

### Problem
Frontend and backend use inconsistent market parameter values:

| Component | International | Vietnamese |
|-----------|--------------|------------|
| **Backend Schema** (`MarketType` enum) | `"international"` | `"vietnam"` |
| **Frontend State** | `"international"` | `"vietnamese"` |
| **Vietnamese Route** | N/A | Returns `"vietnamese"` |

### Location
- **Backend**: `/backend/app/api/schemas/unified_step_schemas.py:45-48`
  ```python
  class MarketType(str, Enum):
      INTERNATIONAL = "international"
      VIETNAM = "vietnam"  # ← Backend expects "vietnam"
  ```

- **Frontend**: `/frontend/src/components/ValuationFlow.jsx:91-95`
  ```javascript
  const [marketValidation, setMarketValidation] = useState({
    isValid: true,
    message: '',
    selectedMarket: 'international'
  });
  // User sets market to 'vietnamese' via radio buttons
  ```

- **Vietnamese Search Response**: `/backend/app/api/routes/international_market_data_routes.py:142`
  ```python
  formatted_results.append({
      "symbol": stock["ticker"],
      "name": stock["name"],
      "exchange": stock.get("market", "VN"),
      "sector": stock.get("sector"),
      "market": "vietnamese"  # ← Returns "vietnamese" not "vietnam"
  })
  ```

### Impact
- **Routing Errors**: When frontend sends `market='vietnamese'` to endpoints expecting `MarketType` enum, Pydantic validation may fail
- **Session Context**: SessionService stores market as string without enum validation, risking mismatched engine selection
- **Data Matrix**: `valuationsData[market]` uses frontend's `"vietnamese"` key but backend responses may use `"vietnam"`

### Fix Required
**Option A (Recommended)**: Standardize on `"vietnam"` everywhere
- Frontend: Change radio button value from `"vietnamese"` to `"vietnam"`
- Vietnamese search route: Return `"vietnam"` instead of `"vietnamese"`

**Option B**: Add normalization layer in backend to accept both variants

---

## Issue #2: Field Name Mismatch in Search Results ⚠️ LOW

### Problem
Backend returns different field names than frontend expects:

| Field | Backend (International) | Backend (Vietnamese) | Frontend Expects |
|-------|------------------------|---------------------|------------------|
| Ticker | `ticker` | `symbol` | `symbol` |
| Company Name | `company_name` | `name` | `name` |

### Location
- **International Search**: `/backend/app/api/routes/search_routes.py:77-86`
  ```python
  company_results.append(CompanySearchResult(
      ticker=r.get('symbol', ''),      # ← Maps to 'ticker' field
      company_name=r.get('name', ''),  # ← Maps to 'company_name' field
      exchange=r.get('exchange', ''),
      ...
  ))
  ```

- **Vietnamese Search**: `/backend/app/api/routes/international_market_data_routes.py:137-143`
  ```python
  formatted_results.append({
      "symbol": stock["ticker"],       # ← Uses 'symbol' directly
      "name": stock["name"],           # ← Uses 'name' directly
      "exchange": stock.get("market", "VN"),
      ...
  })
  ```

- **Frontend Display**: `/frontend/src/components/valuation-flow/SearchStep.jsx:147-148`
  ```javascript
  <span style={{ fontWeight: 'bold' }}>{result.name}</span>
  <span style={{ marginLeft: '8px', color: '#666' }}>({result.symbol})</span>
  ```

### Impact
- **UI Confusion**: International results work correctly (Pydantic model maps fields), Vietnamese results work by accident (direct dict matches frontend expectations)
- **Schema Inconsistency**: `CompanySearchResult` model defines `ticker` and `company_name`, but Vietnamese endpoint bypasses this model

### Fix Required
Standardize Vietnamese search to use `CompanySearchResult` model like international search does.

---

## Issue #3: Vietnamese Search Route Not Using Unified Schema ⚠️ MEDIUM

### Problem
Vietnamese search uses a legacy GET endpoint with custom response format instead of the unified POST `/step-1-search` endpoint.

### Location
- **International**: POST `/api/step-1-search`
  - Request: `UnifiedStep1Request` (query, market, limit)
  - Response: `UnifiedStep1Response` (status, query, market, results, total_results, message)

- **Vietnamese**: GET `/api/vietnam/search?q={query}`
  - Request: Query parameter only
  - Response: Custom dict format (not `UnifiedStep1Response`)

### Code
- **Frontend API Service**: `/frontend/src/services/api.js:24-34`
  ```javascript
  export const searchCompanies = async (query, market = 'international') => {
    if (market === 'vietnamese') {
      const response = await api.get('/vietnam/search', { params: { q: query } });
      return response.data;
    } else {
      const response = await api.post('/step-1-search', { query, market });
      return response.data;
    }
  };
  ```

### Impact
- **Inconsistent Error Handling**: Different response structures make unified error handling difficult
- **Missing Metadata**: Vietnamese response lacks standardized fields like `total_results` validation
- **Maintenance Burden**: Two separate search implementations to maintain

### Fix Required
Create Vietnamese Step1 processor and migrate `/vietnam/search` to use unified schema.

---

## Issue #4: Weak Market Validation ⚠️ MEDIUM

### Problem
Market validation state exists but doesn't block workflow progression. Users can select a company in one market and potentially proceed with wrong market context.

### Location
- **Frontend State**: `/frontend/src/components/ValuationFlow.jsx:91-95`
  ```javascript
  const [marketValidation, setMarketValidation] = useState({
    isValid: true,
    message: '',
    selectedMarket: 'international'
  });
  ```

- **Validation Logic**: Line 697 checks market but only for data transformation, not blocking
  ```javascript
  if (market && (market.toLowerCase() === 'vietnamese' || market.toLowerCase() === 'vietnam')) {
    // Transform Vietnamese response
  }
  ```

- **No Blocking**: No code prevents user from continuing if market validation fails

### Impact
- **Data Contamination Risk**: User could theoretically search in Vietnamese market, select company, then switch to international before proceeding
- **Wrong Engine Usage**: Session created with one market type might be used with another market's valuation engine

### Fix Required
Add strict market locking after Step 1 completion and validate market consistency at each step transition.

---

## Issue #5: Session Market Context Critical ⚠️ CRITICAL

### Problem
SessionService stores market as a simple string without validation, risking wrong valuation engine being used.

### Location
- **Session Creation**: `/backend/app/api/routes/search_routes.py:119-122`
  ```python
  session_id = session_service.create_session(
      ticker=request.ticker,
      market=request.market  # ← Stored as-is, no enum validation
  )
  ```

- **No Cross-Validation**: Nothing prevents an international ticker from being stored with vietnam market or vice versa

### Impact
- **Wrong Valuation Engine**: If session has `market="vietnam"` but ticker is "AAPL", Vietnamese DCF engine will fail or produce garbage results
- **Currency Mismatch**: VND calculations applied to USD financials
- **Tax Rate Errors**: Vietnam's 20% corporate tax applied to international companies with different tax rates

### Fix Required
Add ticker-market validation in SessionService:
- Vietnamese tickers must match HOSE/HNX/UPCOM patterns
- International tickers must be valid yfinance symbols
- Reject sessions with mismatched ticker/market combinations

---

## Issue #6: Late Matrix Population ⚠️ MEDIUM

### Problem
The `valuationsData[market][method]` matrix is initialized in Steps 1-3 but not populated until Step 6, creating a window where market switching could cause data loss or confusion.

### Location
- **Matrix Initialization**: `/frontend/src/components/ValuationFlow.jsx:103-114`
  ```javascript
  const [valuationsData, setValuationsData] = useState({
    international: { dcf: null, dupont: null, comps: null },
    vietnam: { dcf: null, dupont: null, comps: null }
  });
  ```

- **First Population**: Step 6 (Line 734)
  ```javascript
  setValuationData(method, financialData);  // ← First time data is set
  ```

- **Steps 1-5**: Matrix remains all `null` values

### Impact
- **Mid-Workflow Switching Bugs**: If user changes market radio button between Steps 1-5, they lose their search context
- **No Early Market Binding**: Market-specific data requirements aren't established until too late
- **Confusing UI State**: Components may try to access `valuationsData[market][method]` before it's populated

### Fix Required
Populate matrix earlier:
- Step 1: Store search results in matrix
- Step 2-3: Store company confirmation and method selection in matrix
- This creates market-method binding from the start

---

## Summary Table

| Issue | Severity | Component | Risk |
|-------|----------|-----------|------|
| #1 Market Parameter Format | Medium | Frontend↔Backend | Routing errors |
| #2 Field Name Mismatch | Low | Frontend Display | UI confusion |
| #3 Vietnamese Non-Unified Route | Medium | Backend API | Maintenance burden |
| #4 Weak Market Validation | Medium | Frontend Flow | Data contamination |
| #5 Session Market Context | **Critical** | Backend Session | Wrong valuation engine |
| #6 Late Matrix Population | Medium | Frontend State | Mid-workflow bugs |

---

## Recommended Priority Order

1. **#5 Session Market Context** (CRITICAL) - Prevent wrong engine usage
2. **#1 Market Parameter Format** (MEDIUM) - Fix routing foundation
3. **#4 Weak Market Validation** (MEDIUM) - Add workflow guards
4. **#6 Late Matrix Population** (MEDIUM) - Improve state management
5. **#3 Vietnamese Non-Unified Route** (MEDIUM) - Long-term architecture
6. **#2 Field Name Mismatch** (LOW) - Cosmetic cleanup

---

## Next Steps

Would you like me to:
1. **Fix Issue #5** (Critical) - Add ticker-market validation in SessionService?
2. **Fix Issue #1** (Medium) - Standardize market parameter format?
3. **Fix Issue #4** (Medium) - Add market locking mechanism?
4. Create individual fix PRs for each issue?

Please specify which issue(s) you'd like me to address first.
