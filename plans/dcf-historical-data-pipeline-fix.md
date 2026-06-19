# DCF Historical Data Pipeline Fix — Detailed Working Plan

## Problem Statement

The FINAL DCF MODEL Excel template requires specific historical and opening balance inputs across 7 categories. The current backend pipeline (Steps 5→6→7→8→9→10) has gaps where:

1. **Step 5** lists fields but some are missing from the requirements list
2. **Step 6** fetches data but some fields don't flow through to the response
3. **Step 7** gap-fills data but doesn't feed SEC EDGAR NOL into the pipeline
4. **Step 10** (`_build_dcf_inputs()`) is actually fairly complete but has specific gaps
5. **`build_dcf_inputs_from_confirmed_assumptions()`** in `dcf_input_manager.py` is a legacy stub that ignores most fetched data

## Architecture: Two Paths to DCFInputs

```
Path A (Legacy, broken):  dcf_input_manager.build_dcf_inputs_from_confirmed_assumptions()
                          → Used by some code paths, hardcodes defaults

Path B (Current, mostly working):  Step10DCFProcessor._build_dcf_inputs()
                          → Reads from Step 9 historical_financials_summary
                          → Maps to DCFInputs properly
```

**Decision**: Path B is the correct one. Path A should be deprecated/removed.

---

## Task 1: Ensure Step 5-6 Historical Data Coverage

### 1A. Add missing fields to Step 5 `DCF_RETRIEVABLE_INPUTS`

**File**: `backend/app/services/international/step5_required_inputs_processor.py`

**Already done** (previous session): Added 17 fields (52 total). Verify completeness against Excel model.

**Remaining gaps to add**:

| Group | New Field | yfinance Key | Excel Reference |
|---|---|---|---|
| `historical_financials` | `deferred_tax` | `DeferredIncomeTax` (cashflow) | IS row 109 |
| `historical_financials` | `interest_income` | `InterestIncome` (financials) | IS row 106 |
| `historical_financials` | `total_current_assets` | `CurrentAssets` (balance_sheet) | BS row 141 |
| `historical_financials` | `total_current_liabilities` | `CurrentLiabilities` (balance_sheet) | BS row 147 |
| `historical_financials` | `total_liabilities` | `TotalLiabilitiesNetMinorityInterest` (balance_sheet) | BS row 150 |
| `historical_financials` | `net_ppe` | `NetPPE` (balance_sheet) | BS row 142 |
| `historical_financials` | `net_debt` | `NetDebt` (balance_sheet) | Opening balance |
| `balance_sheet_opening` | `tax_loss_carryforward` | SEC EDGAR XBRL only | Inputs L64 |
| `balance_sheet_opening` | `deferred_tax_assets` | SEC EDGAR XBRL only | BS row 148 |
| `balance_sheet_opening` | `revolving_credit_line` | `CurrentDebt` (balance_sheet) | BS row 146 |

### 1B. Ensure Step 6 yfinance_service fetches all fields

**File**: `backend/app/services/international/yfinance_service.py`

**Already done** (previous session): Added 6 fetch calls. Verify the remaining fields:

| Field | yfinance Key | Status |
|---|---|---|
| `sg_and_a` | `SellingGeneralAndAdministration` | ✅ Added |
| `deferred_tax` | `DeferredIncomeTax` (cashflow) | ✅ Added |
| `net_debt` | `NetDebt` (balance_sheet) | ✅ Added |
| `total_current_assets` | `CurrentAssets` (balance_sheet) | ✅ Added |
| `total_current_liabilities` | `CurrentLiabilities` (balance_sheet) | ✅ Added |
| `working_capital_change` | `ChangeInWorkingCapital` (cashflow) | ✅ Added |
| `interest_income` | `InterestIncome` (financials) | ⚠️ Need to verify fetch |

### 1C. Ensure Step 6 response includes all fields

**File**: `backend/app/services/international/step6_dcf_data_review.py`

**Already done** (previous session): Added fields to `dcf_historical_fields`, `income_mapping`, `balance_sheet_mapping`. Verify:

| Field | In dcf_historical_fields? | In extraction mapping? | Status |
|---|---|---|---|
| `sg_and_a` | ✅ | ✅ `income_mapping` | ✅ |
| `deferred_tax` | ✅ | ✅ `income_mapping` | ✅ |
| `interest_income` | ✅ | ✅ `balance_sheet_mapping` | ✅ |
| `net_ppe` | ✅ | ✅ `balance_sheet_mapping` | ✅ |
| `net_debt` | ✅ | ✅ `balance_sheet_mapping` | ✅ |
| `total_current_assets` | ✅ | ✅ `balance_sheet_mapping` | ✅ |
| `total_current_liabilities` | ✅ | ✅ `balance_sheet_mapping` | ✅ |
| `total_liabilities` | ✅ | ✅ `balance_sheet_mapping` | ✅ |

---

## Task 2: Update Step 7 to Feed Missing Inputs

### 2A. Update `DCF_ALL_METRICS` in Step 7 DCF processor

**File**: `backend/app/services/international/step7_dcf_historical_data.py`

**Already done** (previous session): Expanded from 11 → 31 metrics. Verify completeness.

### 2B. Update `unified_field_names` in Step 7 main processor

**File**: `backend/app/services/international/step7_historical_data_processor.py`

**Already done** (previous session): Expanded from 27 → 42 fields. Verify completeness.

### 2C. Feed SEC EDGAR tax_loss_carryforward to Step 8/9/10

**File**: `backend/app/services/international/step7_financial_statements_merger.py`

**Current state**: `_fill_from_sec_edgar_xbrl()` stores `tax_loss_carryforward` in balance_sheet, but no downstream processor reads it for the DCF tax schedule.

**Fix needed**: Ensure `tax_loss_carryforward` is included in `complete_financial_statements` at the top level (not just balance_sheet) so Step 9's `historical_financials_summary` can pass it to Step 10.

### 2D. Ensure Step 9 `historical_financials_summary` includes all fields

**File**: `backend/app/services/international/step9_confirmation_processor.py`

**Current state**: Step 9 builds `historical_financials_summary` from Step 6 data. Need to verify it includes:
- `ppe_gross` (multi-year array)
- `accumulated_depreciation` (multi-year array)
- `total_current_assets` (multi-year array)
- `total_current_liabilities` (multi-year array)
- `total_liabilities` (multi-year array)
- `deferred_tax` (multi-year array)
- `interest_income` (multi-year array)
- `tax_loss_carryforward` (single value from SEC EDGAR)
- `change_in_lt_debt` (multi-year array)
- `change_in_common_equity` (multi-year array)
- `revolving_credit_line` (multi-year array)
- `dividends_paid` (multi-year array)

---

## Task 3: Rebuild `build_dcf_inputs_from_confirmed_assumptions()`

**File**: `backend/app/services/international/dcf_input_manager.py`

### Current State (Broken)
```python
def build_dcf_inputs_from_confirmed_assumptions(...):
    # Uses hardcoded defaults matching Excel template example values
    # Ignores: tax_losses_nol, ppe_gross_book, comparable_companies,
    #          change_in_lt_debt, change_in_common_equity, etc.
    tax_losses_nol=0,  # ← HARDCODED
    ppe_net = info.get('totalAssets', 0)  # ← Wrong field
    tax_basis_ppe = ppe_net * 0.8  # ← Estimate
```

### Target State (Correct)
```python
def build_dcf_inputs_from_confirmed_assumptions(
    confirmed_assumptions: Dict[str, Any],
    financial_data: Dict[str, Any],
    profile: Dict[str, Any],
    complete_statements: Dict[str, Any],  # NEW: from Step 8 merger
    sec_edgar_data: Dict[str, Any],       # NEW: from SEC EDGAR
    market: str = "international"
) -> DCFInputs:
    """
    Build DCFInputs from confirmed assumptions + complete_statements + SEC EDGAR.
    
    Sources:
    - confirmed_assumptions: Step 8 user/AI edits (forecast drivers, WACC, etc.)
    - financial_data: Step 6 yfinance data (historical financials)
    - profile: Step 2 company info (shares, price, etc.)
    - complete_statements: Step 8 merged data (Step 6 + Step 7 + SEC EDGAR)
    - sec_edgar_data: SEC EDGAR XBRL (PP&E Gross, Accum Dep, NOL, Deferred Tax)
    """
```

### Specific Changes Required

#### Historical Financials (from financial_data + complete_statements)
| DCFInputs Field | Source | Current | Fix |
|---|---|---|---|
| `historical_revenue` | `financial_data.revenue` | ✅ Works | No change |
| `historical_cogs` | `financial_data.cogs` | ✅ Works | No change |
| `historical_sga` | `financial_data.sga` | ⚠️ Est: `rev * 0.25` | Read from `financial_data.sga` or `complete_statements.income_statement.selling_general_administrative` |
| `historical_other_opex` | `financial_data.other_opex` | ⚠️ Est: `rev * 0.05` | Read from `complete_statements` |
| `historical_depreciation` | `financial_data.depreciation` | ⚠️ Not populated | Read from `financial_data.depreciation_amortization` |
| `historical_interest` | `financial_data.interest` | ⚠️ Not populated | Read from `financial_data.interest_expense` |
| `historical_capex` | `financial_data.capex` | ⚠️ Not populated | Read from `financial_data.capital_expenditure` |

#### Historical Balance Sheet (from complete_statements)
| DCFInputs Field | Source | Current | Fix |
|---|---|---|---|
| `historical_ar` | `complete_statements.accounts_receivable` | ⚠️ Est: `rev * 0.1` | Read from complete_statements |
| `historical_inventory` | `complete_statements.inventory` | ⚠️ Est: `rev * 0.08` | Read from complete_statements |
| `historical_ap` | `complete_statements.accounts_payable` | ⚠️ Est: `rev * 0.07` | Read from complete_statements |

#### Opening Balances (from complete_statements + SEC EDGAR)
| DCFInputs Field | Source | Current | Fix |
|---|---|---|---|
| `net_debt_opening` | `complete_statements.net_debt` | ✅ Works | No change |
| `ppe_gross_book` | SEC EDGAR `ppe_gross` | ⚠️ Uses `ppe_net` (Total Assets) | Read from `sec_edgar_data.ppe_gross` or `complete_statements.ppe_gross` |
| `tax_basis_ppe` | SEC EDGAR / proxy | ⚠️ Hardcoded `ppe_net * 0.8` | Read from `sec_edgar_data` or use `net_ppe` as proxy |
| `tax_losses_nol` | SEC EDGAR `tax_loss_carryforward` | ❌ **HARDCODED TO 0** | Read from `sec_edgar_data.tax_loss_carryforward` or `complete_statements.tax_loss_carryforward` |

#### Opening Balance Sheet (from complete_statements)
| DCFInputs Field | Source | Current | Fix |
|---|---|---|---|
| `cash_opening` | `complete_statements.cash` | ❌ Not populated | Read from `complete_statements.cash_and_equivalents` |
| `long_term_debt_opening` | `complete_statements.long_term_debt` | ❌ Not populated | Read from `complete_statements.long_term_debt` |
| `common_equity_opening` | `complete_statements.shareholders_equity` | ❌ Not populated | Read from `complete_statements.shareholders_equity` |
| `retained_earnings_opening` | `complete_statements.retained_earnings` | ❌ Not populated | Read from `complete_statements.retained_earnings` |

#### Financing Items (from complete_statements)
| DCFInputs Field | Source | Current | Fix |
|---|---|---|---|
| `change_in_lt_debt` | `complete_statements.change_in_long_term_debt` | ❌ Uses [0]*6 | Read from complete_statements (multi-year array) |
| `change_in_common_equity` | `complete_statements.change_in_common_equity` | ❌ Uses [-1000]*6 | Read from complete_statements (multi-year array) |
| `revolving_credit_line` | `complete_statements.change_in_revolver` | ❌ Uses [0]*6 | Read from complete_statements (multi-year array) |
| `projected_dividends` | `complete_statements.dividends_paid` | ❌ Uses default 2446 | Read from complete_statements |
| `projected_interest_expense` | Derived from `long_term_debt * interest_rate` | ⚠️ Uses `net_debt * 0.05` | Calculate: `long_term_debt_opening * LT_interest_rate` |

#### WACC Inputs (from peer data + confirmed assumptions)
| DCFInputs Field | Source | Current | Fix |
|---|---|---|---|
| `comparable_companies` | Step 6 peer data | ❌ Not populated | Pass peer companies from confirmed_assumptions or session |
| `risk_free_rate` | confirmed_assumptions | ✅ Works | No change |
| `market_risk_premium` | confirmed_assumptions | ⚠️ Default 4.7% | Read from confirmed_assumptions |
| `country_risk_premium` | confirmed_assumptions | ⚠️ Default 3.6% | Read from confirmed_assumptions |
| `target_debt_weight` | confirmed_assumptions | ⚠️ Default 15% | Read from confirmed_assumptions |
| `pre_tax_cost_of_debt` | confirmed_assumptions | ⚠️ Hardcoded 5% | Read from confirmed_assumptions |
| `statutory_tax_rate` | confirmed_assumptions | ✅ Works | No change |

---

## Task 4: Also Fix Step 10 `_build_dcf_inputs()` Gaps

**File**: `backend/app/services/international/step10_dcf_processor.py`

The Step 10 processor's `_build_dcf_inputs()` is already quite comprehensive (lines 322-481), but has these remaining gaps:

| Gap | Current | Fix |
|---|---|---|
| `tax_losses_nol` | Not mapped | Add: `inputs.tax_losses_nol = _first_nonzero(data.get('historical_tax_loss_carryforward', []))` |
| `change_in_lt_debt` | Not mapped | Add: `inputs.change_in_lt_debt = _last_3(data.get('historical_change_in_lt_debt', []))` |
| `change_in_common_equity` | Not mapped | Add: `inputs.change_in_common_equity = _last_3(data.get('historical_change_in_equity', []))` |
| `revolving_credit_line` | Not mapped | Add: `inputs.revolving_credit_line = _last_3(data.get('historical_revolver', []))` |
| `projected_interest_expense` | Not mapped | Add: derive from `long_term_debt_opening * interest_rate` |
| `comparable_companies` | Not mapped | Add: pass from Step 6 peer data through Step 9 |

---

## Execution Order

### Phase 1: Step 5-6 Data Collection (Already mostly done)
1. ✅ Verify Step 5 `DCF_RETRIEVABLE_INPUTS` completeness
2. ✅ Verify Step 6 `yfinance_service.py` fetches all fields
3. ✅ Verify Step 6 `step6_dcf_data_review.py` includes all fields in response
4. ⚠️ Add `interest_income` to Step 6 income_mapping if missing

### Phase 2: Step 7 Gap-Filling
5. ✅ Verify `DCF_ALL_METRICS` completeness
6. ✅ Verify `unified_field_names` completeness
7. ⚠️ Ensure `tax_loss_carryforward` flows from SEC EDGAR to `complete_statements` top level

### Phase 3: Step 9 Historical Summary
8. ⚠️ Verify Step 9 `historical_financials_summary` includes all new fields
9. ⚠️ Ensure `tax_loss_carryforward` is included in summary

### Phase 4: Step 10 DCFInputs Construction
10. ⚠️ Add `tax_losses_nol` mapping to `_build_dcf_inputs()`
11. ⚠️ Add financing items mapping (`change_in_lt_debt`, `change_in_common_equity`, `revolving_credit_line`)
12. ⚠️ Add `projected_interest_expense` derivation
13. ⚠️ Add `comparable_companies` passthrough

### Phase 5: Rebuild `build_dcf_inputs_from_confirmed_assumptions()`
14. Add `complete_statements` and `sec_edgar_data` parameters
15. Replace hardcoded defaults with actual data reads
16. Add all missing field mappings
17. Add financing items from complete_statements
18. Add WACC peer companies passthrough

---

## Files to Modify (Ordered)

| # | File | Change |
|---|---|---|
| 1 | `step5_required_inputs_processor.py` | Add remaining missing fields (if any) |
| 2 | `yfinance_service.py` | Verify `interest_income` fetch |
| 3 | `step6_dcf_data_review.py` | Verify all fields in extraction mapping |
| 4 | `step7_financial_statements_merger.py` | Ensure `tax_loss_carryforward` at top level |
| 5 | `step9_confirmation_processor.py` | Ensure `historical_financials_summary` includes all fields |
| 6 | `step10_dcf_processor.py` | Add `tax_losses_nol`, financing items, interest expense, peers |
| 7 | `dcf_input_manager.py` | Full rebuild of `build_dcf_inputs_from_confirmed_assumptions()` |

## Testing Strategy

After each phase:
1. Run Python syntax check on modified files
2. Run `python -c "import ast; ast.parse(open('file').read())"` for each modified file
3. After Phase 5: Run a test valuation for AAPL to verify the full pipeline produces correct DCFInputs
