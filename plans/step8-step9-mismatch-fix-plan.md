# Step 8 → Step 9 Mismatch Fix Plan

## Overview
Fix all data mismatches between Step 8 inputs/API data and Step 9 editable inputs + calculated schedules. The issues span three categories: (A) forecast driver data flow, (B) historical data mapping, and (C) backend calculation discrepancies.

---

## Category A: Forecast Driver Data Flow (Already Fixed)

### A1. `buildInputs()` reads from `confirmedValues` for forecast arrays
**File:** `frontend/src/components/valuation-flow/step9_assumptions_step.tsx`
**Status:** ✅ Already applied
**Change:** Added `getConfirmedForecastArray()` helper that checks `confirmedValues` for each year index before falling back to `baseDrivers`.

### A2. `handleManualInput` camelCase → snake_case store update
**File:** `frontend/src/store/actions/step8_9_assumption_actions.ts`
**Status:** ✅ Already applied
**Change:** Added `CAMEL_TO_SNAKE` mapping so forecast driver field names are correctly converted when updating `forecastDriversData`.

---

## Category B: Historical Data Mapping Bugs

### B1. Retained Earnings shows Common Equity values
**Root Cause:** `extractSeries(BS, 'retained_earnings')` may not find the field if the backend returns it under a different key name. The Schedule then shows incorrect values (Common Equity instead of Retained Earnings).

**Files to modify:**
- `frontend/src/utils/historicalDataExtractor.ts` — Add alternative field names for retained_earnings extraction
- `frontend/src/components/valuation-flow/step9_assumptions_step.tsx` — Verify the equity schedule uses correct historical data

**Fix:**
```typescript
// In historicalDataExtractor.ts, line 298:
// Change:
const retainedEarnings = extractSeries(balanceSheet, 'retained_earnings');
// To:
const retainedEarnings = extractSeries(
  balanceSheet, 'retained_earnings', 'accumulated_retained_earnings', 'retained_profit'
);
```

**Verification:** The extractor must return values like [-214M, -19.2B, -14.3B] for AAPL, NOT [62.1B, 57.0B, 73.7B].

---

### B2. LT Debt uses Total Debt instead of Long-Term Debt
**Root Cause:** `extractSeries(BS, 'total_debt', 'long_term_debt')` prioritizes `total_debt` which is $98.7B (Total Debt = LT + Current). The Schedule labels this as "Long-Term Debt" but it's actually Total Debt.

**Files to modify:**
- `frontend/src/utils/historicalDataExtractor.ts` — Extract LT Debt separately from Total Debt
- `frontend/src/components/valuation-flow/step9_assumptions_step.tsx` — Use correct LT Debt for debt schedule

**Fix:**
```typescript
// In historicalDataExtractor.ts, add separate extraction:
const longTermDebt = extractSeries(balanceSheet, 'long_term_debt', 'lt_debt');
const currentDebt = extractSeries(balanceSheet, 'current_debt', 'short_term_debt');
// Keep totalDebt for backward compatibility
const totalDebt = extractSeries(balanceSheet, 'total_debt', 'long_term_debt', 'current_debt');
```

**In the HistoricalActuals interface, add:**
```typescript
longTermDebt: number[];
currentDebt: number[];
```

**In step9_assumptions_step.tsx, the equity/debt schedule should use `historical.longTermDebt` for the LT Debt opening balance, NOT `historical.totalDebt`.**

---

### B3. Missing historical years (only 3 of 5 shown)
**Root Cause:** `getPeriods()` in the extractor is hardcoded to `count: 3` (line 79).

**Files to modify:**
- `frontend/src/utils/historicalDataExtractor.ts` — Extract all available historical periods (up to 5)

**Fix:**
```typescript
// Change getPeriods default from 3 to 5:
function getPeriods(section, count = 5) { ... }
// Or make it configurable:
const periods = getPeriods(incomeStatement.revenue || incomeStatement, 5);
```

**Impact:** Schedule tables will show 5 historical columns + 5 forecast + 1 terminal = 11 columns. This may need UI width adjustments.

---

### B4. 6 extracted fields NOT displayed in any schedule
**Fields extracted but unused:** `research_development`, `interest_income`, `other_income`, `share_buybacks`, `debt_repayments`, `debt_issuance`, `tax_paid`, `interest_paid`

**Decision needed:** Should these be added as additional rows in existing schedules, or as new schedule tables?

**Proposed fix (minimal):**
- Add R&D as a row in Income Statement (it's a significant expense for AAPL: $34.5B)
- Add Interest Income as a row in Income Statement
- Add Other Income/Expense as a row in Income Statement
- The cash flow items (buybacks, debt issuance/repayments, tax paid, interest paid) are informational — add as reference rows in CFS

**Files to modify:**
- `frontend/src/components/valuation-flow/step9_assumptions_step.tsx` — Add new rows to incomeStatementRows and cashFlowStatementRows

---

### B5. Operating Cash Flow not used in CFS Schedule
**Root Cause:** The CFS Schedule computes Subtotal CFO from scratch (NI + Dep + DefTax + WC Change) instead of using the actual `operating_cash_flow` from the backend. This causes ~$33B discrepancy because the computed version includes deferred taxes while the actual OCF doesn't.

**Files to modify:**
- `frontend/src/components/valuation-flow/step9_assumptions_step.tsx` — Use actual OCF for historical periods

**Fix:**
```typescript
// In cashFlowStatementRows useMemo, for historical periods:
// Use actual operating_cash_flow instead of computing from components
subtotalCfo: padWithHistorical(
  transformed.cashFlowStatement.subtotalCfo, 
  historicalOperatingCashFlow // from extractHistoricalActuals
),
```

**Note:** This changes the historical Subtotal CFO display. The computed value includes deferred taxes; the actual OCF from the API does not. We should use the API value for consistency with Step 8.

---

## Category C: Backend Calculation Discrepancies

### C1. AR Days input (34.89) vs schedule calculation (~36 days)
**Root Cause:** The backend `ScenarioDrivers.ar_days` may be populated from session Step 8 data rather than the frontend overrides. The `build_dcf_inputs_from_frontend()` function has `pass` for arDays (line 538-539), meaning it doesn't set AR days on the DCFInputs — it only goes to ScenarioDrivers.

**Files to modify:**
- `backend/app/services/international/dcf_input_builder.py` — Ensure frontend AR days override session data
- `backend/app/services/international/dcf_input_builder.py` — In `_build_scenario_drivers_from_raw()`, verify the ar_days values come from frontend inputs

**Investigation needed:** Check if the backend `build_dcf_inputs_from_frontend` correctly passes frontend AR days to `ScenarioDrivers`. The `pass` statement on line 538-539 suggests it's a known gap.

---

### C2. COGS Growth Rate input (1.2%) vs schedule (~1.23%)
**Root Cause:** The backend may add an inflation adjustment on top of the user's COGS growth rate, or the `year_values` from Step 8's backend projection differ slightly from the displayed editable input values.

**Files to modify:**
- `backend/app/services/international/dcf_engine.py` — Check `_build_cogs_schedule()` for any additive adjustments
- `backend/app/services/international/step8_manual_overrides.py` — Check `_project_five_year_series()` for COGS growth projection

**Investigation needed:** Verify that the `cogs_growth_rate` array passed to `ScenarioDrivers` matches the frontend input exactly, with no additional adjustments.

---

### C3. Change in LT Debt / Common Equity shows ±1 instead of 0
**Root Cause:** Floating-point precision artifact when the change is essentially 0.

**Files to modify:**
- `backend/app/services/international/dcf_engine.py` — Round near-zero values to exactly 0

**Fix:**
```python
# In the debt/equity schedule builder, round near-zero changes:
change = round(change, 0) if abs(change) < 1 else change
# Or use a threshold:
change = 0.0 if abs(change) < 1.0 else change
```

---

## Implementation Order

| Phase | Task | Files | Priority |
|-------|------|-------|----------|
| 1 | A1 + A2 (already fixed) | step9, step8_9_actions | ✅ Done |
| 2 | B1: Fix Retained Earnings extraction | historicalDataExtractor.ts | 🔴 Critical |
| 3 | B2: Fix LT Debt extraction | historicalDataExtractor.ts, step9 | 🔴 Critical |
| 4 | B3: Extract 5 historical years | historicalDataExtractor.ts, step9 | ⚠️ Medium |
| 5 | B5: Use actual OCF for historical CFS | step9 | ⚠️ Medium |
| 6 | B4: Add missing schedule rows (R&D, Interest Income, etc.) | step9 | 🟡 Low |
| 7 | C1: Fix AR Days backend override | dcf_input_builder.py | 🔴 Critical |
| 8 | C2: Fix COGS Growth backend | dcf_engine.py, step8_manual_overrides.py | 🔴 Critical |
| 9 | C3: Fix ±1 floating point | dcf_engine.py | 🟡 Low |

---

## Testing Checklist

- [ ] AAPL Retained Earnings shows [-214M, -19.2B, -14.3B] in historical columns
- [ ] AAPL LT Debt shows [95.3B, 85.8B, 78.3B] (NOT Total Debt values)
- [ ] AR Balance matches input 34.89 days × Revenue / 365
- [ ] COGS matches input 1.2% growth from prior year
- [ ] 5 historical years shown (2021-2025) if backend provides them
- [ ] Change in LT Debt = 0 (not ±1) when input is 0
- [ ] Change in Common Equity = 0 (not ±1) when input is 0
- [ ] Subtotal CFO matches Step 8 Operating Cash Flow for historical periods
- [ ] All schedule totals balance (A = L + E, Balance Check ≈ 0)
