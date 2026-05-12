# BACKEND-FRONTEND MAPPING ANALYSIS - Steps 3, 4, 5

## CURRENT WRONG IMPLEMENTATION

### Step 3: Historical Financial Data Processor (WRONG)
**Current Backend:** `step-3-save-peers` endpoint saves peers and fetches peer data
**Current Frontend:** PeerSelectionStep component
**Issue:** The backend naming suggests "Historical Financial Data" but it's actually handling Peer Selection

### Step 4: Peer Company Selection (WRONG)  
**Current Backend:** `step-4-select-peers` endpoint 
**Current Frontend:** ModelSelectionStep component
**Issue:** Backend endpoint is named for peer selection, but frontend shows Model Selection (DCF/DuPont/Comps)

### Step 5: Shows API inputs list (PARTIALLY CORRECT)
**Current Backend:** `step-5-prepare-assumptions` endpoint returns required inputs per model
**Current Frontend:** RequirementsStep component
**Issue:** Component shows both required inputs AND retrieved data - should ONLY show required inputs before retrieval

---

## CORRECT PURPOSES NEEDED

According to README.md workflow documentation:

### Step 3: Peer Company Selection ✅
**Purpose:** AI-suggested peers with auto-select top 5
**Backend Process:** Peer discovery service with scoring (market-specific logic)
**User Interface:** Display suggested peers, allow selection/deselection
**Current Status:** CORRECTLY IMPLEMENTED
- Backend: `/step-3-save-peers` saves selected peers
- Frontend: `PeerSelectionStep.jsx` displays peers for selection

### Step 4: Models Selection (DCF, DuPont, Comps) ✅
**Purpose:** Select ONE valuation model at a time (radio buttons, NOT checkboxes)
**Backend Process:** Validate model compatibility, store in session
**User Interface:** Single-select radio buttons for DCF/DuPont/Comps
**Current Status:** CORRECTLY IMPLEMENTED
- Backend: `/step-4-select-peers` (endpoint name is misleading but functionality is correct)
- Frontend: `ModelSelectionStep.jsx` uses radio buttons correctly

### Step 5: Show Required Inputs Needed for Each Model ✅
**Purpose:** Table showing required fields per model BEFORE data retrieval
**Backend Process:** Load schema definitions from step5 processor (market-specific)
**User Interface:** Display required inputs categorized by type, show which need manual input vs auto-fetch
**Current Status:** MOSTLY CORRECT
- Backend: `/step-5-prepare-assumptions` returns required inputs correctly
- Frontend: `RequirementsStep.jsx` shows required inputs BUT ALSO shows retrieved data (confusing)

---

## WORKFLOW ARCHITECTURE: 3 Valuation Methods × 2 Market Versions

```
┌─────────────────────────────────────────────────────────────┐
│                    Rows (Methods)                            │
│  DCF  │ DuPont  │ Trading Comps                             │
├─────────────────────────────────────────────────────────────┤
│                 Columns (Markets)                            │
│  International  │  Vietnam                                   │
└─────────────────────────────────────────────────────────────┘
```

### Backend Structure:
```
services/international/
  ├── dcf_engine.py
  ├── dupont_engine.py
  ├── comps_engine.py
  ├── step5_assumptions_processor.py    # Returns required inputs for Step 5
  ├── step6_data_review.py              # Fetches ALL data (Fetch Once, Use Many)
  └── ...

services/vietnamese/
  ├── vietnamese_dcf_engine.py
  ├── vietnamese_dupont_engine.py
  ├── vietnamese_comps_engine.py
  ├── vn_step5_requirements_processor.py  # Returns required inputs for Step 5
  ├── step6_data_fetch_processor.py       # Fetches ALL data
  └── ...
```

### Frontend State Management:
```javascript
// Matrix structure: valuationsData[market][method]
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

---

## IDENTIFIED ISSUES

### Issue #1: Backend Endpoint Naming Confusion
**Problem:** 
- `/step-4-select-peers` should be `/step-4-select-model` (it handles model selection, not peer selection)
- Peer selection is actually done in Step 3 via `/step-3-save-peers`

**Impact:** Developer confusion when reading code

**Solution:** Rename endpoint to `/step-4-select-model` for clarity

---

### Issue #2: RequirementsStep Shows Retrieved Data Prematurely
**Problem:** 
Step 5 (RequirementsStep) currently displays:
1. ✅ Required inputs list (CORRECT)
2. ❌ Retrieved data summary (WRONG - this belongs in Step 6)

**Current Code (RequirementsStep.jsx lines 107-340+):**
```javascript
const hasRetrievedData = historicalData || peerData || dcfInputs || ...;

const renderRetrievedData = () => {
  if (!hasRetrievedData) return null;
  // Renders historical data, forecast drivers, peer data, DCF inputs, etc.
};
```

**Expected Behavior:**
Step 5 should ONLY show:
- List of required inputs per model
- Which inputs require manual input vs auto-fetch
- A "Retrieve Data" button that navigates to Step 6

Step 6 (ApiDataStep) should show:
- All retrieved financial data
- Success/failure status per field
- Continue button to next step

**Solution:** Remove `renderRetrievedData()` from RequirementsStep, keep only `renderAllRequiredInputs()`

---

### Issue #3: Missing API Function in Frontend
**Problem:**
Frontend calls `selectModels()` function (ValuationFlow.jsx line 428) but this function doesn't exist in api.js

**Current Code:**
```javascript
// ValuationFlow.jsx line 428
const data = await selectModels(sessionId, modelType, market);
```

**Missing Function:**
No `selectModels` export in `/frontend/src/services/api.js`

**Solution:** Add `selectModels` function to api.js that calls `/step-4-select-peers` endpoint

---

### Issue #4: Step Numbering Inconsistency
**Problem:**
README documents 11 steps, but implementation has some steps merged or numbered differently

**Documentation (README.md):**
1. Search Company
2. Company Overview  
3. Peer Selection
4. Select Model
5. Review Requirements
6. View Retrieved Inputs
7. Historical Data Retrieval
8. Assumption & AI Suggestion
9. Confirm Assumptions
10. Run Valuation
11. View Results

**Implementation:**
- Steps 2-3 are somewhat merged in frontend flow
- Step 7 (Historical Data) is VN-market specific (PDF extraction)

**Solution:** Ensure consistent step numbering across all components and documentation

---

## RECOMMENDED FIXES

### Fix #1: Add Missing selectModels API Function
**File:** `/frontend/src/services/api.js`

Add after `selectPeers` function:
```javascript
// Step 4: Select Valuation Model
export const selectModels = async (sessionId, method, market = 'international') => {
  const response = await api.post('/step-4-select-peers', { 
    session_id: sessionId,
    method: method.toUpperCase(),
    market: market.toLowerCase(),
    suggested_peers: [], // Peers already saved in Step 3
    custom_peers: []
  });
  return response.data;
};
```

---

### Fix #2: Clean Up RequirementsStep Component
**File:** `/frontend/src/components/valuation-flow/RequirementsStep.jsx`

Remove the entire `renderRetrievedData()` function and its usage.
Keep only the required inputs display.

Change button text from "Retrieve Data" to "Continue to Data Review" since data retrieval happens in Step 6.

---

### Fix #3: Rename Backend Endpoint (Optional)
**File:** `/backend/app/api/routes/valuation_routes.py`

Rename endpoint for clarity:
```python
@router.post("/step-4-select-model", response_model=UnifiedStep4Response)
async def select_model(request: UnifiedStep4Request):
    # Same implementation, just clearer naming
```

Update frontend api.js to call new endpoint name.

---

## VERIFICATION CHECKLIST

After fixes, verify:

- [ ] Step 3: Peer Selection works correctly (save peers, fetch peer data)
- [ ] Step 4: Model Selection uses radio buttons (single select only)
- [ ] Step 4: `selectModels` API function exists and calls backend
- [ ] Step 5: Shows ONLY required inputs (no retrieved data)
- [ ] Step 5: Categorizes inputs by "User Input Required" vs "Auto-Fetched"
- [ ] Step 6: Shows ALL retrieved financial data with status indicators
- [ ] Matrix structure preserved: `valuationsData[market][method]`
- [ ] Both International and Vietnamese markets supported
- [ ] All 3 models (DCF, DuPont, Comps) work independently

---

## CONCLUSION

The current implementation is **MOSTLY CORRECT** but has these issues:

1. **Minor:** Endpoint naming confusion (`step-4-select-peers` should be `step-4-select-model`)
2. **Moderate:** Missing `selectModels` API function in frontend
3. **Significant:** RequirementsStep shows retrieved data prematurely (should be Step 6's job)

The core architecture (3×2 matrix, single model selection, fetch-once-use-many) is correctly implemented and should be preserved.

**Priority Fixes:**
1. Add missing `selectModels` function (blocks Step 4→5 navigation)
2. Clean up RequirementsStep to show only required inputs
3. Optional: Rename backend endpoint for clarity
