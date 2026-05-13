# Workflow Alignment Decision: Option A Implementation

## Executive Decision

**Date**: Current Session  
**Decision**: Implement **Option A - Align Frontend to Backend 10-Step Workflow**

## Rationale

After analyzing the mismatch between frontend's 11-step workflow and backend's 10-step unified schema architecture, we chose Option A because:

1. **Respects existing architecture**: Backend unified schemas (Steps 1-10) are already well-designed and implemented
2. **Minimal backend changes**: No need to create Step 11 schema or refactor endpoints
3. **Cleaner separation**: Results display is output of Step 10, not a separate workflow step
4. **Aligns with "3 Valuation Methods × 2 Market Versions" design**: Unified schemas work for both markets

## Changes Required

### Frontend Changes (ValuationFlow.jsx)

| Old Step | New Step | Name | Backend Match |
|----------|----------|------|---------------|
| 1 | 1 | Search Company | ✅ Step 1 |
| 2 | 2 | Company Overview/Market Confirmation | ✅ Step 2 |
| 3 | **4** | Peer Selection | ✅ Step 4 |
| 4 | **3** | Model/Method Selection | ✅ Step 3 |
| 5 | 5 | Review Requirements → Assumptions Prep | ✅ Step 5 |
| 6 | 6 | View Retrieved Inputs → Fetch Data | ✅ Step 6 |
| 7 | 7 | Historical Data Extraction | ✅ Step 7 |
| 8 | 8 | Forecast Drivers → Manual Overrides | ✅ Step 8 |
| 9 | 9 | Confirm Assumptions | ✅ Step 9 |
| 10 | 10 | Run Valuation → Execute | ✅ Step 10 |
| ~~11~~ | **(merged)** | ~~View Results~~ | **(part of Step 10)** |

### Critical Changes

1. **Swap Steps 3 and 4**: Method Selection (Step 3) must come BEFORE Peer Selection (Step 4)
   - Logical flow: Choose valuation method first, then select peers relevant to that method
   - Backend expects: Step 3 = Method Selection, Step 4 = Peer Selection

2. **Merge Results into Step 10**: Remove Step 11 as separate step
   - Results display becomes part of Step 10 execution output
   - No separate navigation to "Step 11"

3. **Update Progress Indicator**: Change from "Step X of 11" to "Step X of 10"

4. **Fix Navigation Functions**: Update all `setCurrentStep()` calls to match new numbering

### Backend Alignment

Backend is already correct with 10 unified step schemas:
- `UnifiedStep1Request/Response` through `UnifiedStep10Request/Response`
- Endpoints: `/step-1-search` through `/step-10-valuate`
- No changes needed to backend schemas

## Implementation Status

- [x] Decision documented
- [ ] Frontend ValuationFlow.jsx updated
- [ ] Progress indicator updated (11 → 10)
- [ ] Step labels updated
- [ ] Navigation functions verified
- [ ] Testing completed

## Notes

- Vietnam market remains Version 2 (separate implementation)
- International market is current focus
- Unified schemas prevent backend/frontend miss-mapping
- Never simplify calculations or reduce inputs unless specifically asked

