# DCF Excel Schedules Completion Plan

> **Last Updated**: 2026-06-12
> **Scope**: Bring backend DCFEngine to full parity with FINAL DCF MODEL Excel — all 20 schedules visible in Step 9
> **Status**: PLANNING — Awaiting approval before implementation

---

## 1. Problem Statement

The Excel [`FINAL DCF MODEL`](excel%20models/FINAL%20DCF%20MODEL.xlsx) has **20 schedules/sheets**. The backend [`DCFEngine`](backend/app/services/international/dcf_engine.py:382) currently implements **10 of them**. The remaining **10 are missing** and need to be added so that Step 9 shows the complete financial model before the user proceeds to Step 10 valuation.

### Current State (10/20 ✅)

| # | Schedule | Status |
|---|---------|--------|
| 1 | Income Statement | ✅ Built + serialized |
| 2 | Working Capital Schedule | ✅ Built + serialized |
| 3 | Depreciation Schedule (Existing + New) | ✅ Built + serialized |
| 4 | Asset Schedule (PP&E + Tax Basis) | ✅ Built + serialized |
| 5 | Income Tax — Levered (NOL carryforward) | ✅ Built + serialized |
| 6 | Income Tax — Unlevered | ⚠️ Built but partially serialized |
| 7 | UFCF Schedule | ✅ Built + serialized |
| 8 | DCF: Perpetuity Method | ✅ Built + serialized |
| 9 | DCF: Exit Multiple Method | ✅ Built + serialized |
| 10 | WACC Calculation | ✅ Built + serialized |

### Missing State (10/20 ❌)

| # | Schedule | Excel Location | Priority |
|---|---------|---------------|----------|
| 11 | Cash Flow Statement (CFO/CFI/CFF) | Model rows 43-75 | HIGH |
| 12 | Balance Sheet | Model rows 79-117 | HIGH |
| 13 | Intrinsic Valuation — Financial Statement Extracts | Model rows 450-473 | MEDIUM |
| 14 | Intrinsic Valuation — UFCF (3 derivation methods) | Model rows 476-498 | MEDIUM |
| 15 | Intrinsic Valuation — NPV and XNPV | Model rows 522-555 | MEDIUM |
| 16 | Intrinsic Valuation — IRR and XIRR | Model rows 558-572 | LOW |
| 17 | Data Tables (Sensitivity) — serialization gap | Model rows 575-610 | HIGH |
| 18 | Relative Valuation — Trading Comps | Relative Valuation sheet | HIGH |
| 19 | Relative Valuation — Precedent Transactions | Relative Valuation sheet | HIGH |
| 20 | Football Field Chart | Football Field Chart sheet | CRITICAL |

---

## 2. Architecture Decision: Where Do Schedules Live?

### Current Flow

```
Step 9: _run_dcf_calculation()
  → Step10DCFProcessor._extract_dcf_inputs()
  → Step10DCFProcessor._build_dcf_inputs()
  → DCFEngine.calculate()
  → DCFEngine.to_dict()
  → returned as calculated_schedules in Step9ConfirmationOutput
```

### Proposed Flow

```
Step 9: _run_dcf_calculation()
  → Step10DCFProcessor._extract_dcf_inputs()
  → Step10DCFProcessor._build_dcf_inputs()
  → DCFEngine.calculate()          ← builds ALL schedules internally
  → DCFEngine.to_dict()            ← serializes ALL schedules
  → CompsEngine.run_analysis()     ← if peer data available (for Comps + Precedent + Football Field)
  → Merge into calculated_schedules
  → returned in Step9ConfirmationOutput
```

**Key Decision**: The Cash Flow Statement, Balance Sheet, and Intrinsic Valuation schedules are **byproducts of the DCF calculation** — they use the same projected data. They should be built inside `DCFEngine.calculate()` alongside the existing schedules, NOT as separate processors.

The Comps/Precedent/Football Field data comes from a **different engine** ([`comps_engine.py`](backend/app/services/international/comps_engine.py:1)) and should be run separately in Step 9 if peer data is available.

---

## 3. Detailed Implementation Plan

### Phase 1: DCFEngine — New Inputs (HIGH)

**File**: [`dcf_engine.py`](backend/app/services/international/dcf_engine.py:150) — `DCFInputs` dataclass

**Add these fields**:

```python
# ── Financing items (Excel Inputs rows 58-61) ──
projected_dividends: Union[float, InputWithMetadata] = 2446.0  # USD thousands per year (can be array)
dividends_fixed: bool = True  # If True, use single value; if False, use array
change_in_lt_debt: List[Union[float, InputWithMetadata]] = field(
    default_factory=lambda: [0.0] * 6
)  # 6 periods: FY1-FY5 + Terminal
change_in_common_equity: List[Union[float, InputWithMetadata]] = field(
    default_factory=lambda: [-1000.0] * 6
)  # 6 periods: negative = buybacks
revolving_credit_line: List[Union[float, InputWithMetadata]] = field(
    default_factory=lambda: [0.0] * 6
)  # 6 periods

# ── Opening Balance Sheet (end of FY2022) ──
cash_opening: Union[float, InputWithMetadata] = 9365.0
long_term_debt_opening: Union[float, InputWithMetadata] = 20000.0
common_equity_opening: Union[float, InputWithMetadata] = 38669.70
retained_earnings_opening: Union[float, InputWithMetadata] = 5690.0
```

**Excel Reference**: Inputs rows 58-76, Model rows 58-66 (CFF), rows 79-97 (BS)

---

### Phase 2: DCFEngine — Cash Flow Statement (HIGH)

**File**: [`dcf_engine.py`](backend/app/services/international/dcf_engine.py:382)

**New dataclass**:
```python
@dataclass
class CashFlowStatement:
    years: List[str]
    # CFO
    net_income: List[float]
    deferred_taxes: List[float]
    depreciation: List[float]
    cash_from_ar: List[float]
    cash_from_inventory: List[float]
    cash_from_ap: List[float]
    subtotal_cfo: List[float]
    # CFI
    capital_expenditure: List[float]
    subtotal_cfi: List[float]
    # CFF
    change_in_lt_debt: List[float]
    change_in_common_equity: List[float]
    dividends: List[float]
    revolving_credit: List[float]
    subtotal_cff: List[float]
    # Cash Balance
    beginning_cash: List[float]
    increase_decrease: List[float]
    ending_cash: List[float]
```

**New method**: `_build_cash_flow_statement()` called inside `calculate()` after Step 13 (Net Income).

**Logic** (matching Excel Model rows 43-75):
```
CFO = Net Income + Deferred Tax + Depreciation + ΔAR + ΔInventory + ΔAP
CFI = -(CapEx)
CFF = ΔLT Debt + ΔCommon Equity + Dividends + Revolving Credit
Beginning Cash = Prior year ending cash (first year = cash_opening)
Ending Cash = Beginning Cash + CFO + CFI + CFF
```

**Wire into**: `DCFOutput.cash_flow_statement` + `to_dict()` serialization

---

### Phase 3: DCFEngine — Balance Sheet (HIGH)

**File**: [`dcf_engine.py`](backend/app/services/international/dcf_engine.py:382)

**New dataclass**:
```python
@dataclass
class BalanceSheet:
    years: List[str]
    # Assets
    cash: List[float]
    accounts_receivable: List[float]
    inventories: List[float]
    total_current_assets: List[float]
    ppe_gross: List[float]
    total_assets: List[float]
    # Liabilities
    accounts_payable: List[float]
    revolving_credit: List[float]
    total_current_liabilities: List[float]
    long_term_debt: List[float]
    total_liabilities: List[float]
    # Equity
    common_equity: List[float]
    retained_earnings: List[float]
    total_shareholders_equity: List[float]
    total_liabilities_equity: List[float]
    # Check
    balance_check: List[float]  # Assets - (L+E), should be ~0
```

**New method**: `_build_balance_sheet()` called inside `calculate()` after `_build_cash_flow_statement()`.

**Logic** (matching Excel Model rows 79-117):
```
Cash = from Cash Flow Statement ending balance
AR = from Working Capital Schedule
Inventory = from Working Capital Schedule
PP&E = from Depreciation Schedule gross_ppe_ending
AP = from Working Capital Schedule
LT Debt = Opening + sum of changes
Common Equity = Opening + sum of changes
Retained Earnings = Opening + (Net Income - Dividends) cumulative
```

**Wire into**: `DCFOutput.balance_sheet` + `to_dict()` serialization

---

### Phase 4: DCFEngine — Intrinsic Valuation Extracts (MEDIUM)

**File**: [`dcf_engine.py`](backend/app/services/international/dcf_engine.py:382)

**New dataclass**:
```python
@dataclass
class IntrinsicExtracts:
    """Financial statement extracts for intrinsic valuation (Excel rows 450-473)"""
    years: List[str]
    net_income: List[float]
    depreciation: List[float]
    interest_expense: List[float]
    tax_rate: List[float]
    after_tax_interest: List[float]
    ebit: List[float]
    unlevered_taxes: List[float]
    ebitda: List[float]
    capex: List[float]
    change_in_working_capital: List[float]
    long_term_debt: List[float]
    cash: List[float]
```

**New method**: `_build_intrinsic_extracts()` — simply extracts from already-computed schedules.

---

### Phase 5: DCFEngine — UFCF 3 Methods (MEDIUM)

**File**: [`dcf_engine.py`](backend/app/services/international/dcf_engine.py:382)

**New dataclass**:
```python
@dataclass
class UFCFMethods:
    """UFCF derivation via 3 methods (Excel rows 476-498)"""
    years: List[str]
    # EBIT Method
    ebit_method: List[float]
    # Net Income Method
    net_income_method: List[float]
    # EBITDA Method
    ebitda_method: List[float]
    # Cross-check
    methods_reconcile: bool
```

**New method**: `_build_ufcf_3methods()` — derives UFCF from 3 starting points:
```
EBIT method:     NOPAT + Dep - CapEx - ΔWC
Net Income method: NI + Dep + After-tax Interest - CapEx - ΔWC
EBITDA method:   EBITDA - Unlevered Taxes - CapEx - ΔWC
```

---

### Phase 6: DCFEngine — NPV/XNPV (MEDIUM)

**File**: [`dcf_engine.py`](backend/app/services/international/dcf_engine.py:382)

**New dataclass**:
```python
@dataclass
class NPVResult:
    """NPV and XNPV valuation results (Excel rows 522-555)"""
    # End-of-period discounting
    npv_end_of_period: float
    xnpv_end_of_period: float
    equity_per_share_end: float
    # Mid-period discounting
    npv_mid_period: float
    xnpv_mid_period: float
    equity_per_share_mid: float
    # IRR
    irr: float
    xirr_end_of_period: float
    xirr_mid_period: float
```

**New method**: `_build_npv_xnpv()` — implements NPV/XNPV/IRR/XIRR:
```
NPV: Sum of CF / (1+r)^t for integer periods
XNPV: Sum of CF / (1+r)^((date - valuation_date)/365)
IRR: Rate where NPV = 0
XIRR: IRR with actual dates
```

---

### Phase 7: DCFEngine — Sensitivity Serialization (HIGH)

**File**: [`dcf_engine.py`](backend/app/services/international/dcf_engine.py:1228)

**Issue**: `calculate_sensitivity_perpetuity()` and `calculate_sensitivity_multiple()` exist but their results are NOT included in `to_dict()`.

**Fix**: Add sensitivity results to `DCFOutput` and serialize in `to_dict()`:

```python
# In DCFOutput
sensitivity_perpetuity: Optional[Dict] = None
sensitivity_multiple: Optional[Dict] = None

# In to_dict()
"sensitivity_tables": {
    "perpetuity_wacc_vs_growth": output.sensitivity_perpetuity,
    "multiple_wacc_vs_terminal_multiple": output.sensitivity_multiple,
}
```

**Wire into**: Call sensitivity methods in `calculate()` after valuation, store results.

---

### Phase 8: Step 9 — Comps + Precedent + Football Field (HIGH/CRITICAL)

**File**: [`step9_confirmation_processor.py`](backend/app/services/international/step9_confirmation_processor.py:811)

**In `_run_dcf_calculation()`** (or new method `_run_comps_analysis()`), after DCF calculation:

```python
# After DCF calculation
calculated_schedules = engine.to_dict(output)

# Add sensitivity tables
sensitivity_perp = engine.calculate_sensitivity_perpetuity(output, wacc_range, growth_range)
sensitivity_mult = engine.calculate_sensitivity_multiple(output, wacc_range, multiple_range)
calculated_schedules['sensitivity_tables'] = {
    'perpetuity': sensitivity_perp,
    'multiple': sensitivity_mult,
}

# Run Comps engine if peer data available
from app.services.international.comps_engine import TradingCompsAnalyzer
comps_analyzer = TradingCompsAnalyzer()
# ... build TargetCompanyData + PeerCompanyData from Step 6 data
comps_output = comps_analyzer.analyze(target_data, peer_data, transaction_data)
calculated_schedules['relative_valuation'] = {
    'trading_comps': comps_output.to_dict(),
    'precedent_transactions': comps_output.precedent_transactions,
    'football_field_chart': comps_output.chart_data,
}
```

**Football Field Chart data** will combine:
- DCF Perpetuity range (from sensitivity: Low/Middle/High)
- DCF Multiple range (from sensitivity: Low/Middle/High)
- Trading Comps range (from comps engine)
- Precedent Transactions range (from comps engine)
- 52-Week High/Low (from market data)

---

### Phase 9: Step 9 Response Schema Update

**File**: [`unified_step_schemas.py`](backend/app/api/schemas/unified_step_schemas.py)

Update `UnifiedStep9Response` to include the expanded `calculated_schedules`:

```python
class CalculatedSchedules(BaseModel):
    """Complete DCF model schedules visible in Step 9"""
    # Existing
    main_outputs: Dict[str, Any]
    wacc_calculation: Dict[str, Any]
    income_statement: Dict[str, Any]
    working_capital: Dict[str, Any]
    depreciation: Dict[str, Any]
    tax_levered: Dict[str, Any]
    tax_unlevered: Dict[str, Any]
    ufcf: Dict[str, Any]
    dcf_details: Dict[str, Any]
    
    # NEW
    cash_flow_statement: Optional[Dict[str, Any]] = None
    balance_sheet: Optional[Dict[str, Any]] = None
    intrinsic_extracts: Optional[Dict[str, Any]] = None
    ufcf_3_methods: Optional[Dict[str, Any]] = None
    npv_xnpv: Optional[Dict[str, Any]] = None
    sensitivity_tables: Optional[Dict[str, Any]] = None
    relative_valuation: Optional[Dict[str, Any]] = None
    football_field_chart: Optional[List[Dict]] = None
```

---

### Phase 10: Frontend — Step 9 Schedule Display

**File**: [`AssumptionsStep.tsx`](frontend/src/components/valuation-flow/AssumptionsStep.tsx)

**Add tabbed/collapsible sections** for all schedules:

```tsx
// New tabs for Step 9
<Tabs>
  <Tab label="Income Statement">
    <IncomeStatementTable data={schedules.income_statement} />
  </Tab>
  <Tab label="Cash Flow Statement">
    <CashFlowTable data={schedules.cash_flow_statement} />
  </Tab>
  <Tab label="Balance Sheet">
    <BalanceSheetTable data={schedules.balance_sheet} />
  </Tab>
  <Tab label="Working Capital">
    <WorkingCapitalTable data={schedules.working_capital} />
  </Tab>
  <Tab label="Depreciation">
    <DepreciationTable data={schedules.depreciation} />
  </Tab>
  <Tab label="Tax Schedules">
    <TaxScheduleTable levered={schedules.tax_levered} unlevered={schedules.tax_unlevered} />
  </Tab>
  <Tab label="UFCF">
    <UFCFTable data={schedules.ufcf} methods3={schedules.uffc_3_methods} />
  </Tab>
  <Tab label="DCF Valuation">
    <DCFValuationTable perpetuity={schedules.dcf_details.perpetuity_method} multiple={schedules.dcf_details.exit_multiple_method} />
  </Tab>
  <Tab label="Sensitivity">
    <SensitivityHeatmap data={schedules.sensitivity_tables} />
  </Tab>
  <Tab label="Comps">
    <CompsTable data={schedules.relative_valuation} />
  </Tab>
  <Tab label="Football Field">
    <FootballFieldChart ranges={schedules.football_field_chart} />
  </Tab>
</Tabs>
```

**New components needed** (in `frontend/src/components/valuation-flow/`):
- `CashFlowStatementTable.tsx`
- `BalanceSheetTable.tsx`
- `IntrinsicExtractsTable.tsx`
- `NPVXNPVTable.tsx`
- `CompsResultsTable.tsx`

**Reuse existing**:
- `FootballFieldChart.tsx` ✅ already exists
- `SensitivityHeatmap.tsx` ✅ already exists

---

## 4. Implementation Order

| Phase | What | Files Changed | Depends On |
|-------|------|--------------|-----------|
| 1 | DCFInputs — add financing + BS opening balances | `dcf_engine.py` | None |
| 2 | Cash Flow Statement schedule | `dcf_engine.py` | Phase 1 |
| 3 | Balance Sheet schedule | `dcf_engine.py` | Phase 2 |
| 4 | Intrinsic Valuation Extracts | `dcf_engine.py` | Phase 2-3 |
| 5 | UFCF 3 Methods cross-check | `dcf_engine.py` | Phase 4 |
| 6 | NPV/XNPV/IRR/XIRR | `dcf_engine.py` | Phase 5 |
| 7 | Sensitivity serialization | `dcf_engine.py` | None (already exists) |
| 8 | Comps + Precedent + Football Field in Step 9 | `step9_confirmation_processor.py` | Phase 7 |
| 9 | Schema update | `unified_step_schemas.py` | Phase 1-8 |
| 10 | Frontend Step 9 display | `AssumptionsStep.tsx` + new components | Phase 9 |

---

## 5. Testing Strategy

| Test | File | What to Verify |
|------|------|---------------|
| Unit: Cash Flow Statement | `test_dcf_engine.py` | CFO + CFI + CFF = ending cash matches Excel |
| Unit: Balance Sheet | `test_dcf_engine.py` | Assets = L+E within rounding tolerance |
| Unit: UFCF 3 Methods | `test_dcf_engine.py` | All 3 methods produce identical UFCF |
| Unit: NPV/XNPV | `test_dcf_engine.py` | XNPV matches Excel's XNPV function |
| Integration: Step 9 response | `test_step8_step9_flow.py` | `calculated_schedules` contains all 20 schedules |
| Frontend: Step 9 tabs | Manual | All tabs render without errors |

---

## 6. Excel Formulas to Implement

### Cash Flow Statement (Model rows 43-75)

```
CFO:
  Net Income        = Model!F39 (from Income Statement)
  Deferred Taxes    = Model!F36 (from Income Statement)
  Depreciation      = Model!F29 (from Income Statement)
  Cash from AR      = Prior NWC_AR - Current NWC_AR
  Cash from Inv     = Prior NWC_Inv - Current NWC_Inv
  Cash from AP      = Current NWC_AP - Prior NWC_AP
  Subtotal CFO      = SUM(above)

CFI:
  CapEx             = -(Inputs scenario capex)
  Subtotal CFI      = CapEx

CFF:
  ΔLT Debt          = Inputs change_in_lt_debt[i]
  ΔCommon Equity    = Inputs change_in_common_equity[i]
  Dividends         = Inputs.projected_dividends (negative)
  Revolving Credit  = Inputs.revolving_credit_line[i]
  Subtotal CFF      = SUM(above)

Cash:
  Beginning         = Prior year ending (first year = cash_opening)
  Change            = CFO + CFI + CFF
  Ending            = Beginning + Change
```

### Balance Sheet (Model rows 79-117)

```
Assets:
  Cash              = CFS ending balance
  AR                = Working Capital !AR balance
  Inventory         = Working Capital !Inventory balance
  Total Current     = Cash + AR + Inventory
  PP&E Gross        = Depreciation Schedule !gross_ppe_ending
  Total Assets      = Total Current + PP&E

Liabilities:
  AP                = Working Capital !AP balance
  Revolving Credit  = Inputs.revolving_credit_line
  Total Current Liab = AP + Revolving Credit
  LT Debt           = Prior LT Debt + change_in_lt_debt
  Total Liabilities = Total Current Liab + LT Debt

Equity:
  Common Equity     = Prior + change_in_common_equity
  Retained Earnings = Prior + Net Income - ABS(Dividends)
  Total Equity      = Common Equity + Retained Earnings
  Total L+E         = Total Liabilities + Total Equity

Check: Total Assets - Total L+E ≈ 0
```

### UFCF 3 Methods (Model rows 476-498)

```
EBIT Method:
  UFCF = EBIT - Unlevered Taxes + Depreciation - CapEx - ΔWC

Net Income Method:
  UFCF = Net Income + Depreciation + After-tax Interest - CapEx - ΔWC
  After-tax Interest = Interest Expense × (1 - Tax Rate)

EBITDA Method:
  UFCF = EBITDA - Unlevered Taxes - CapEx - ΔWC

Cross-check: All 3 should produce identical UFCF
```

### NPV/XNPV (Model rows 522-555)

```
End-of-Period:
  Discount Period = 1, 2, 3, ... (integer years)
  PV = CF / (1 + WACC)^period

Mid-Period:
  Discount Period = 0.75, 1.75, 2.75, ... (half-year convention)
  PV = CF / (1 + WACC)^period

XNPV:
  Date factor = (CF_date - Valuation_date) / 365
  PV = CF / (1 + WACC)^date_factor

IRR:
  Rate where Sum(CF / (1+r)^t) = 0

XIRR:
  Rate where Sum(CF / (1+r)^((date_i - date_0)/365)) = 0
```

---

## 7. Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Balance Sheet may not balance perfectly | Rounding tolerance check; Excel has same issue (Check row shows growing imbalance) |
| Circular reference in Retained Earnings | Retained Earnings depends on Net Income which depends on Interest which depends on Debt — use projected (constant) interest to break circularity |
| Comps engine needs peer financial data | Step 6 already fetches peer data; pass to Step 9 |
| Frontend complexity with 11 tabs | Use clean tab design with collapse/expand; prioritize most important schedules |
| Performance: running DCF + Comps in Step 9 | Both are fast (<100ms); no concern |

---

## 8. Files Changed Summary

| File | Change Type | Phase |
|------|------------|-------|
| `backend/app/services/international/dcf_engine.py` | MODIFY — add inputs, schedules, serialization | 1-7 |
| `backend/app/services/international/step9_confirmation_processor.py` | MODIFY — add Comps + Football Field | 8 |
| `backend/app/api/schemas/unified_step_schemas.py` | MODIFY — expand CalculatedSchedules | 9 |
| `frontend/src/components/valuation-flow/AssumptionsStep.tsx` | MODIFY — add schedule tabs | 10 |
| `frontend/src/components/valuation-flow/CashFlowStatementTable.tsx` | NEW | 10 |
| `frontend/src/components/valuation-flow/BalanceSheetTable.tsx` | NEW | 10 |
| `frontend/src/components/valuation-flow/IntrinsicExtractsTable.tsx` | NEW | 10 |
| `frontend/src/components/valuation-flow/NPVXNPVTable.tsx` | NEW | 10 |
| `frontend/src/components/valuation-flow/CompsResultsTable.tsx` | NEW | 10 |
| `backend/test/test_dcf_schedules.py` | NEW — unit tests for all new schedules | Testing |
