# Plan: Add Missing DCF Structural Items to Steps 5-8 Pipeline

## Context

We've added critical institution-grade items to the DCF engine (Step 9/10) and TXT model documentation. Now we need to ensure these items flow through the entire data pipeline: Step 5 (requirements) → Step 6 (API fetch) → Step 7 (merge) → Step 8 (assumptions) → Step 9 (building blocks).

### Balance Sheet Items (3 new fields)
- **Non-Current Marketable Securities** (~$165B for Apple — long-term bond portfolio)
- **Other Current Liabilities** (~$75B for Apple — Accrued Expenses + Deferred Revenue)
- **Deferred Tax Liabilities** (net DTA/DTL position — non-cash tax timing differences)

### Income Statement Items (2 field fixes)
- **Interest Expense** — Already in pipeline but marked `is_required=False`; must be required for all periods to prevent ghost cash on Balance Sheet
- **Interest Income** — Missing from Step 5 requirements display (already in Steps 6/7)
- **Other Income/Expense** — Missing from Step 5 requirements display (already in Steps 6/7); must be clarified to exclude interest items to prevent double-counting

### Cash Flow Statement Items (1 field fix)
- **Share Buybacks** — Missing from Step 5 requirements display (already in Steps 6/7)

---

## Data Flow Diagram

```
Step 5: Requirements         Step 6: API Fetch           Step 7: Merge              Step 8: Assumptions        Step 9: Engine
─────────────────────       ────────────────────        ───────────────────        ────────────────────       ────────────────
DCF_RETRIEVABLE_INPUTS  →   BS_FIELDS mapping      →    BALANCE_SHEET_FIELDS  →   complete_financial    →   DCFInputs
  (DataRetrievalField)        (yfinance keys)            (alias normalization)       _statements dict          (new fields)
                                                                         ↓
                                                              historicalDataExtractor
                                                                extracts series arrays
```

---

## Step-by-Step Implementation Plan

### Task 1: Step 5 — Add Balance Sheet DataRetrievalField Entries

**File:** `backend/app/services/international/step5_required_inputs_processor.py`

**What:** Add 3 new `DataRetrievalField` entries to `DCF_RETRIEVABLE_INPUTS["balance_sheet_opening"]` (around line 360-395).

**New fields to add (after the existing `Total Liabilities (Opening)` entry):**

1. **Non-Current Marketable Securities (Opening)**
   - `field_name`: "Non-Current Marketable Securities"
   - `description`: "Long-term bond portfolio / non-current marketable securities. Critical for EV-to-Equity bridge: Equity Value = EV - Debt + Cash + ALL Securities"
   - `data_source`: "yfinance"
   - `is_required`: False
   - `api_endpoint`: "get_balance_sheet"
   - `example_response_key`: "Non Current Marketable Securities / Long Term Investments"

2. **Other Current Liabilities (Opening)**
   - `field_name`: "Other Current Liabilities"
   - `description`: "Accrued Expenses + Deferred Revenue (pre-paid services). Critical for accurate Change in Net Working Capital (ΔNWC) calculations"
   - `data_source`: "yfinance"
   - `is_required`: False
   - `api_endpoint`: "get_balance_sheet"
   - `example_response_key`: "Other Current Liabilities / Current Accrued Expenses"

3. **Deferred Tax Liabilities (Opening)**
   - `field_name`: "Deferred Tax Liabilities"
   - `description`: "Net Deferred Tax Assets/Liabilities position. Non-cash timing differences between accounting and tax depreciation. Net DTA minus DTL."
   - `data_source`: "yfinance"
   - `is_required`: False
   - `api_endpoint`: "get_balance_sheet"
   - `example_response_key`: "Net Non Current Deferred Tax Liabilities / Deferred Tax Liabilities"

---

### Task 2: Step 5 — Fix Income Statement & Cash Flow DataRetrievalField Entries

**File:** `backend/app/services/international/step5_required_inputs_processor.py`

**Change 2a:** Promote Interest Expense to `is_required=True` (line 136)

Change:
```python
DataRetrievalField(
    field_name="Interest Expense",
    description="Historical interest expense",
    data_source="yfinance",
    is_required=False,  # ← CHANGE TO True
    ...
)
```

**Why:** Interest Expense MUST be populated for ALL historical periods (2022-2025). If left blank, the Balance Sheet will collect ghost cash and fail identity checks. Apple paid ~$3.9B-$4.0B annually.

**Change 2b:** Add Interest Income to `DCF_RETRIEVABLE_INPUTS["historical_financials"]` (after Interest Expense entry)

```python
DataRetrievalField(
    field_name="Interest Income",
    description="Interest earned on cash and marketable securities (historical). Must be tracked separately from Other Income/Expense to prevent double-counting.",
    data_source="yfinance",
    is_required=False,
    api_endpoint="get_financials",
    example_response_key="Interest Income"
),
```

**Why:** Interest Income is needed for the Income Statement waterfall (EBIT + Interest Income - Interest Expense = EBT). Without it in Step 5, users don't see it as a tracked metric.

**Change 2c:** Add Other Income/Expense to `DCF_RETRIEVABLE_INPUTS["historical_financials"]`

```python
DataRetrievalField(
    field_name="Other Income/Expense",
    description="Non-operating items ONLY (FX gains/losses, equity investment adjustments, legal settlements). MUST NOT include Interest Income or Interest Expense (already tracked separately). If your API pulled the consolidated SEC line, subtract Interest Income and Interest Expense to avoid double-counting.",
    data_source="yfinance",
    is_required=False,
    api_endpoint="get_financials",
    example_response_key="Other Income/Expense"
),
```

**Why:** This prevents the double-counting risk where the consolidated SEC "Other Income/Expense, Net" bundles Interest Income (~$3B) and Interest Expense (~$4B) together with the standalone interest rows.

**Change 2d:** Add Share Buybacks to `DCF_RETRIEVABLE_INPUTS["historical_financials"]`

```python
DataRetrievalField(
    field_name="Share Buybacks / Repurchases",
    description="Cash paid to repurchase shares (historical). Used in Cash Flow Statement financing section and share count projections.",
    data_source="yfinance",
    is_required=False,
    api_endpoint="get_cash_flow",
    example_response_key="Repurchase Of Capital Stock"
),
```

**Why:** Share buybacks are a critical cash outflow in the CFF section. Without this field in Step 5, users don't see it as a tracked metric.

---

### Task 3: Step 6 — Add BS_FIELDS Mapping and balance_sheet_mapping

**File:** `backend/app/services/international/step6_dcf_data_review.py`

**Change 3a:** Add new fields to `BS_FIELDS` dict (around line 240-310).

Add these key mappings:
```python
"non_current_marketable_securities": [
    "nonCurrentMarketableSecurities", "LongTermInvestments",
    "Non Current Available For Sale Securities",
    "NonCurrentMarketableSecurities", "Other Long Term Investments",
    "long_term_investments", "Available For Sale Securities"
],
"other_current_liabilities": [
    "otherCurrentLiabilities", "OtherCurrentLiabilities",
    "Current Accrued Expenses", "Other Current Liabilities",
    "Current Deferred Revenue", "Deferred Revenue Current"
],
"deferred_tax_liabilities": [
    "deferredTaxLiabilities", "DeferredTaxLiabilities",
    "Net Non Current Deferred Tax Liabilities",
    "Non Current Deferred Taxes Liabilities",
    "Deferred Tax Liabilities", "deferred_tax"
],
```

**Change 3b:** Add new fields to `balance_sheet_mapping` in `_extract_metric_from_financials` (around line 754-790).

Add these mappings:
```python
"non_current_marketable_securities": [
    "non_current_marketable_securities", "NonCurrentMarketableSecurities",
    "LongTermInvestments", "Other Long Term Investments",
    "Non Current Available For Sale Securities"
],
"other_current_liabilities": [
    "other_current_liabilities", "OtherCurrentLiabilities",
    "Current Accrued Expenses", "Other Current Liabilities"
],
"deferred_tax_liabilities": [
    "deferred_tax_liabilities", "DeferredTaxLiabilities",
    "Net Non Current Deferred Tax Liabilities",
    "Non Current Deferred Taxes Liabilities"
],
```

**Change 3c:** Add opening balance extraction for new fields (around line 1329-1345).

Add to the `opening_balance_fields` list:
```python
("non_current_marketable_securities", "Non-Current Marketable Securities (Opening)", True, "USD"),
("other_current_liabilities", "Other Current Liabilities (Opening)", True, "USD"),
("deferred_tax_liabilities", "Deferred Tax Liabilities (Opening)", True, "USD"),
```

---

### Task 4: Step 7 — Add BALANCE_SHEET_FIELDS Entries

**File:** `backend/app/services/international/step7_financial_statements_merger.py`

**What:** Add 3 new entries to `BALANCE_SHEET_FIELDS` dict (around line 88-115).

Add these field mappings:
```python
"non_current_marketable_securities": [
    "nonCurrentMarketableSecurities", "LongTermInvestments",
    "Non Current Available For Sale Securities",
    "non_current_marketable_securities", "Other Long Term Investments"
],
"other_current_liabilities": [
    "otherCurrentLiabilities", "OtherCurrentLiabilities",
    "Current Accrued Expenses", "other_current_liabilities"
],
"deferred_tax_liabilities": [
    "deferredTaxLiabilities", "DeferredTaxLiabilities",
    "Net Non Current Deferred Tax Liabilities",
    "deferred_tax_liabilities"
],
```

**Why this is sufficient:** The merger's `_fill_from_step6` and `_fill_from_step7_gaps` methods dynamically iterate over the `BALANCE_SHEET_FIELDS` dict. Adding the new entries here ensures that any data fetched in Step 6 or gap-filled in Step 7 will be correctly mapped and merged into the `complete_financial_statements["balance_sheet"]` section.

---

### Task 5: Step 8 — Verify complete_financial_statements Pass-Through

**File:** `backend/app/services/international/step8_manual_overrides.py`

**What:** Verify that the new balance sheet fields flow through Step 8 without being dropped.

**Analysis:** Step 8's `Step8UnifiedTransformer` receives `complete_financial_statements` from the merger and builds trendlines from it. The new fields (Non-Current Marketable Securities, Other Current Liabilities, Deferred Tax Liabilities) are opening balance items — they don't need trendline calculations (no historical YoY growth needed). They just need to pass through to Step 9.

**Action:** No code changes needed in Step 8. The merger's output dict already includes all balance_sheet fields dynamically. The new fields will be present in `complete_financial_statements["balance_sheet"]` and will flow to Step 9's `_extract_historical_summary()`.

**Verification:** Confirm that `step9_confirmation_processor.py`'s `_extract_historical_summary()` method (line 943) correctly reads the new fields from the balance_sheet section. The existing code already calls `get_from_section('balance_sheet', field_name)` which works for any field present in the balance_sheet dict.

---

### Task 6: Frontend — Verify step6_api_data_step.tsx Displays New Fields

**File:** `frontend/src/components/valuation-flow/step6_api_data_step.tsx`

**What:** The Step 6 UI shows a "Balance Sheet (Opening)" section that lists the retrieved balance sheet fields. We need to verify that the new fields appear in this display.

**Action:** Check if the display is dynamically generated from the API response keys (likely yes). If it's a hardcoded list, add the new fields. If dynamic, no changes needed.

---

## Summary of Files to Modify

| # | File | Change Type | Description |
|---|------|-------------|-------------|
| 1 | `step5_required_inputs_processor.py` | Add 3 BS entries | Non-Current Marketable Securities, Other Current Liabilities, Deferred Tax Liabilities |
| 2 | `step5_required_inputs_processor.py` | Fix 4 IS/CF entries | Interest Expense → required, add Interest Income, Other Income/Expense, Share Buybacks |
| 3 | `step6_dcf_data_review.py` | Add mappings | 3 new BS_FIELDS + balance_sheet_mapping + opening balances |
| 4 | `step7_financial_statements_merger.py` | Add entries | 3 new BALANCE_SHEET_FIELDS entries |
| 5 | `step8_manual_overrides.py` | Verify only | No changes needed — dynamic pass-through |
| 6 | `step6_api_data_step.tsx` | Verify display | Check if new fields appear in UI |

---

## Execution Order

1. **Step 5 Balance Sheet** — Add 3 new DataRetrievalField entries
2. **Step 5 Income/Cash Flow** — Fix Interest Expense required, add 3 new fields
3. **Step 6** — Add BS_FIELDS + balance_sheet_mapping for new balance sheet items
4. **Step 7** — Add BALANCE_SHEET_FIELDS entries for new balance sheet items
5. **Step 8** (verify) — Confirm pass-through to Step 9
6. **Frontend** (verify) — Confirm display in Step 6 UI

---

## Risk Assessment

- **Low risk:** All changes are additive (new fields in existing dicts/mappings)
- **No breaking changes:** Existing fields are untouched
- **Graceful degradation:** Balance sheet items are optional (`is_required=False`); if yfinance doesn't return them, the engine already has fallback logic in `_build_balance_sheet()` to set them to 0
- **Interest Expense promotion to required:** This is a semantic change only — the field is already fetched and mapped. Making it required just ensures the UI highlights it if missing.
- **Backward compatible:** Old sessions without these fields will still work (default values = empty list = 0)

---

## Verification Checklist

### Balance Sheet Items
- [ ] Step 5 shows Non-Current Marketable Securities, Other Current Liabilities, Deferred Tax Liabilities in requirements
- [ ] Step 6 fetches new BS fields from yfinance (or gracefully handles missing)
- [ ] Step 7 merger includes new BS fields in complete_financial_statements.balance_sheet
- [ ] Step 8 passes new BS fields through to Step 9
- [ ] Step 9's historicalDataExtractor extracts new BS series arrays
- [ ] Step 9's DCFInputs receives new BS historical arrays
- [ ] Step 9's _build_balance_sheet() uses new BS values correctly
- [ ] Balance Sheet identity check (A = L + E) passes with new items

### Income Statement Items
- [ ] Step 5 shows Interest Expense as required, Interest Income and Other Income/Expense as tracked
- [ ] Interest Expense is populated for ALL historical periods (2022-2025) — no blank periods
- [ ] Other Income/Expense contains ONLY non-interest items (no double-counting with Interest Income/Expense)
- [ ] EBITDA = Gross Profit − Cash Operating Expenses (SG&A + R&D + Other)
- [ ] EBIT = EBITDA − Depreciation (correct waterfall order)

### Cash Flow Statement Items
- [ ] Step 5 shows Share Buybacks as a tracked metric
- [ ] EXACTLY ONE CapEx row in Cash Flow Statement (no duplicate positive row)
- [ ] All sign conventions enforced: outflows negative, inflows positive
- [ ] Net Change in Cash = CFO + CFI + CFF → links to Balance Sheet Cash
