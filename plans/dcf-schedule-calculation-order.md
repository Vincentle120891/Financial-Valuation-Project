
## Complete Execution Order (DCFEngine.calculate)

### Phase 1: WACC (Step 1) 
**Depends on:** Peer data, Risk-Free Rate, MRP, Country Risk Premium, Target D/E
```
Inputs: Peer table -> Unlevered Beta -> Avg -> Re-lever -> Cost of Equity
        Pre-Tax Cost of Debt -> After-Tax Cost of Debt
        WACC = D% x AT_Kd + E% x Ke
```
Python: `calculate_wacc()` at dcf_engine.py:518

### Phase 2: Revenue (Step 2)
**Depends on:** Historical Revenue[-1], Revenue Growth[0..5]
```
FY1 = Hist_Rev x (1 + G1), FY2 = FY1 x (1 + G2), ... Terminal = FY5 x (1 + Gt)
```
Python: `_build_revenue_schedule()` at dcf_engine.py:555

### Phase 3: COGS (Step 3)
**Depends on:** Historical COGS[-1], Inflation Rate[0..5]
```
FY1 = Hist_COGS x (1 + I1), FY2 = FY1 x (1 + I2), ...
```
Python: `_build_cogs_schedule()` at dcf_engine.py:575

### Phase 4: Gross Profit (Step 4)
**Depends on:** Revenue (Step 2), COGS (Step 3)
```
GP = Revenue - COGS
```
Python: dcf_engine.py:1614

### Phase 5: SG&A + Other OpEx (Step 5)
**Depends on:** Historical SG&A[-1], Historical Other[-1], Inflation Rate[0..5]
```
SGA_FY1 = Hist_SGA x (1 + I1), Other_FY1 = Hist_Other x (1 + I1), ...
```
Python: `_build_opex_schedule()` at dcf_engine.py:589

### Phase 6: EBITDA (Step 6)
**Depends on:** Gross Profit (Step 4), SG&A (Step 5), Other (Step 5)
```
EBITDA = GP - SGA - Other
```
Python: dcf_engine.py:1621

### Phase 7: Depreciation Schedule (rows 180-206)
**Depends on:** CapEx[0..5], Historical PPE, Dep Params (useful life, tax rates)

```
EXISTING ASSETS DEPRECIATION (row 204):
  Opening PPE = historical PPE gross book value (Inputs row 81)
  Useful Life = 16 years (Inputs row 82)
  Annual Existing Dep = Opening PPE / Useful Life (straight-line)
  Each year: remaining_life decrements by 1

NEW ASSETS DEPRECIATION (rows 197-205):
  Each year's CapEx creates a depreciation cohort
  First Year = CapEx / Useful Life x 50% (half-year convention, Inputs row 86)
  Subsequent Years = CapEx / Useful Life (100%)
  Useful Life = 20 years (Inputs row 85)
  New Dep This Year = SUM of all active cohort depreciations

TOTAL DEPRECIATION (row 206):
  Total = Existing Dep + New Dep
  Terminal CapEx = Terminal Dep (steady state: no net investment)
```

### Phase 7a: Asset Schedule (rows 216-224)
**Depends on:** CapEx (Phase 7), Acctg Depreciation (Phase 7), Tax Depreciation (Phase 7)

```
PP&E ROLL (rows 216-219):
  Beginning = Prior year ending PP&E
  CapEx = linked from Depreciation Schedule
  Acctg Depreciation = -linked from Depreciation Schedule (negative)
  Ending = Beginning + CapEx + Acctg Dep

TAX BASIS ROLL (rows 221-224):
  Beginning = Prior year ending Tax Basis (Inputs row 71)
  CapEx = linked from Depreciation Schedule
  Tax Depreciation = -(Beginning + CapEx x 50%) x 15%  (declining balance, half-year convention)
  Ending = Beginning + CapEx + Tax Dep
```

Python: Asset schedule is embedded in `_build_depreciation_schedule()` at dcf_engine.py:600
  - `gross_ppe_ending[]` = PP&E Roll (row 219)
  - `tax_basis_ending[]` = Tax Basis Roll (row 224)
  - `tax_depreciation[]` = Tax depreciation deductions for tax schedule (row 223)

### Phase 8: EBIT (Step 8)
**Depends on:** EBITDA (Step 6), Depreciation (Step 7)
```
EBIT = EBITDA - Depreciation
```
Python: dcf_engine.py:1629

### Phase 9: Working Capital Schedule (Step 9)
**Depends on:** Revenue (Step 2), COGS (Step 3), WC Days (Inputs row 18-21)
```
AR_Balance = (AR_Days / 365) x Revenue
Inv_Balance = (Inv_Days / 365) x COGS
AP_Balance = (AP_Days / 365) x COGS
NWC = AR + Inv - AP
Change_in_NWC = Prior_NWC - Current_NWC (positive = cash inflow)
```
Python: `_build_working_capital_schedule()` at dcf_engine.py:704

### Phase 10: Debt Schedule Part 1 (rows 331-345)
**Depends on:** Cash from CF Statement (Phase 18), LT Debt from Inputs, Interest Rates

```
CASH Section:
  Beginning Balance = Prior year ending
  Change = linked from Cash Flow Statement (Phase 18)
  Ending Balance = Beginning + Change
  Interest Rate = 1% (from Inputs row 77)
  Interest Income = Cash Balance x 1%
  → FEEDS INTO: Debt Part 2 Net Interest (Phase 12)
  → FEEDS INTO: CFS Interest Income (Phase 18)

LONG-TERM DEBT Section:
  Beginning Balance = Prior year ending
  Change = hardcoded from Inputs row 23
  Ending Balance = Beginning + Change
  Interest Rate = 6% (from Inputs row 79)
  Interest Expense = LT Debt Balance x 6%
  → FEEDS INTO: Debt Part 2 Net Interest (Phase 12)
  → FEEDS INTO: IS Interest Expense (Phase 13→14)
  → FEEDS INTO: BS Long-Term Debt (Phase 19)
```

### Phase 11: Equity Schedule (rows 370-385)
**Depends on:** Net Income (Phase 17), Payout Ratio (Inputs row 80), Change in Equity (Inputs row 24)

```
COMMON EQUITY:
  Beginning = Prior year ending
  Change = hardcoded from Inputs row 24
  Ending = Beginning + Change
  → FEEDS INTO: BS Common Equity (Phase 19)
  → FEEDS INTO: CFF Change in Equity (Phase 18)

DIVIDENDS:
  Net Income (from IS, Phase 17)
  Payout Ratio (from Inputs row 80)
  Dividend = Net Income x Payout Ratio
  → FEEDS INTO: CFF Dividends (Phase 18)
  → FEEDS INTO: RE roll (below)
  → FEEDS INTO: Debt Part 2 Available Cash (Phase 12)

RETAINED EARNINGS:
  Beginning = Prior year ending
  + Net Income (from IS, Phase 17)
  - Dividends (from above)
  = Ending
  → FEEDS INTO: BS Retained Earnings (Phase 19)
```

### Phase 12: Debt Schedule Part 2 (rows 347-368)
**Depends on:** Cash (Phase 10), CF Statement (Phase 18), Equity Schedule (Phase 11)

```
AVAILABLE CASH:
  Beginning Cash = from Part 1 (Phase 10)
  + Cash from Operations (from CF Statement, Phase 18)
  + Cash from Investing (from CF Statement, Phase 18)
  + Change in LT Debt (from Inputs row 23)
  + Change in Common Equity (from Inputs row 24)
  - Dividends (from Equity Schedule, Phase 11)
  = Cash Available

REVOLVING CREDIT LINE:
  Beginning Balance = Prior year ending
  Change = -MIN(Available Cash, Beginning Balance)
  Ending Balance = IF(Beginning+Change > 0, Beginning+Change, 0)
  Interest Rate = 5% (from Inputs row 78)
  Interest Expense = Balance x 5%
  → FEEDS INTO: Net Interest (below)
  → FEEDS INTO: BS Revolving Credit (Phase 19)
  → FEEDS INTO: CFF Revolving Credit change (Phase 18)

NET INTEREST:
  Total Interest = LT Interest (Phase 10) + Revolving Interest (above)
  Less: Interest Income (from Part 1 Cash, Phase 10)
  Net Interest Expense = Total - Interest Income
  → FEEDS INTO: IS Interest Expense (Phase 13→14)
  → FEEDS INTO: UFCF (Phase 20, via EBT→Tax)
```

### Phase 13: Interest Expense (feeds into EBT)
**Depends on:** Net Interest from Debt Schedule Part 2 (Phase 12)
```
Interest = Net Interest Expense (from Debt Schedule Part 2)
→ FEEDS INTO: EBT (Phase 14)
→ FEEDS INTO: UFCF 3 Methods NI cross-check (Phase 22)
→ FEEDS INTO: Intrinsic Extracts (Phase 21)
```
Note: Excel has circular reference here (Interest → EBT → NI → CFS → Cash → Interest).
DCurrent DCFEngine uses constant interest to avoid the circle.

### Phase 14: EBT (Step 10)
**Depends on:** EBIT (Phase 8), Net Interest (Phase 13)
```
EBT = EBIT - Net Interest
→ FEEDS INTO: Tax Levered (Phase 15)
→ FEEDS INTO: Net Income (Phase 17)
```
Python: dcf_engine.py:1635

### Phase 15: Tax Schedule - Levered (rows 387-413)
**Depends on:** EBT (Phase 14), Depreciation (Phase 7), Tax Basis Dep (Phase 7a), Tax Rate, NOL
```
EBT_Adjusted = EBT + Acctg_Dep - Tax_Dep
NOL_Used = min(NOL_Balance, EBT_Adjusted x 80%)
Taxable_Income = max(EBT_Adjusted - NOL_Used, 0)
Current_Tax = Taxable_Income x Tax_Rate
Total_Tax = max(EBT_Adjusted x Tax_Rate, 0)
Deferred_Tax = Total_Tax - Current_Tax
→ FEEDS INTO: IS Current Tax (Phase 17)
→ FEEDS INTO: IS Deferred Tax (Phase 17)
→ FEEDS INTO: CFS Deferred Tax add-back (Phase 18)
→ FEEDS INTO: UFCF Tax Shield (Phase 20)
```
Python: `_build_tax_schedule_levered()` at dcf_engine.py:776

### Phase 16: Tax Schedule - Unlevered (rows 415-418)
**Depends on:** EBIT (Phase 8), Depreciation (Phase 7), Tax Basis Dep (Phase 7a), Tax Rate, NOL
```
Same as Levered but starting from EBIT (not EBT)
Separate NOL pool from levered schedule
→ FEEDS INTO: UFCF (Phase 20) — current_tax_unlevered
→ FEEDS INTO: UFCF 3 Methods (Phase 22) — EBIT method
```
Python: `_build_tax_schedule_unlevered()` at dcf_engine.py:870

### Phase 17: Net Income (row 111)
**Depends on:** EBT (Phase 14), Total Tax - Levered (Phase 15)
```
Net_Income = EBT - Total_Tax (levered)
→ FEEDS INTO: CFS Net Income (Phase 18)
→ FEEDS INTO: Equity Schedule Dividends (Phase 11)
→ FEEDS INTO: Equity Schedule Retained Earnings (Phase 11)
→ FEEDS INTO: UFCF 3 Methods NI cross-check (Phase 22)
→ FEEDS INTO: Intrinsic Extracts (Phase 21)
```
Python: dcf_engine.py:1645

### Phase 18: Cash Flow Statement (rows 115-134)
**Depends on:** Net Income (Phase 17), Deferred Tax (Phase 15), Depreciation (Phase 7),
               WC Changes (Phase 9), CapEx (Phase 7), Financing Items (Inputs),
               Dividends (Phase 11), LT Debt Change, Equity Change
```
CFO = NI + Deferred_Tax + Dep + Cash_from_AR + Cash_from_Inv + Cash_from_AP
CFI = -(CapEx)
CFF = Change_LT_Debt + Change_Equity + Dividends + Revolving_Credit
Beginning_Cash -> Ending_Cash = Beginning + CFO + CFI + CFF
→ FEEDS INTO: BS Cash (Phase 19)
→ FEEDS INTO: Debt Part 1 Cash balance (Phase 10) — circular
→ FEEDS INTO: Debt Part 2 Available Cash (Phase 12) — circular
```
Python: `_build_cash_flow_statement()` at dcf_engine.py:1019

### Phase 19: Balance Sheet (rows 138-156)
**Depends on:** Ending Cash (Phase 18), WC Balances (Phase 9), PPE (Phase 7a),
               AP (Phase 9), LT Debt (Phase 10), Revolver (Phase 12),
               Equity (Phase 11), RE (Phase 11)
```
Assets = Cash + AR + Inv + Gross_PPE
Liabilities = AP + Revolving_Credit + LT_Debt
Equity = Common_Equity + Retained_Earnings
RE = Prior_RE + Net_Income - Dividends
Check: Assets - (Liabilities + Equity) = 0
→ FEEDS INTO: Validation (balance check = 0)
```
Python: `_build_balance_sheet()` at dcf_engine.py:1160

---

## PHASES FOR STEP 10 (UFCF / DCF / Valuation)

### Phase 20: UFCF Schedule (Step 20)
**Depends on:** EBITDA (Phase 6), Unlevered Tax (Phase 16), CapEx (Phase 7), NWC Change (Phase 9)
```
UFCF = EBITDA - Current_Tax(Unlevered) - CapEx + Change_in_NWC
Tax_Shield = Current_Tax(Unlevered) - Current_Tax(Levered)
```
Python: `_calculate_ufcf()` at dcf_engine.py:965

### Phase 21: Intrinsic Extracts (Step 21)
**Depends on:** All prior schedules (NI, Dep, Interest, EBIT, Taxes, EBITDA, CapEx, WC)
Python: `_build_intrinsic_extracts()` at dcf_engine.py:1258

### Phase 22: UFCF 3 Methods Cross-Check (Step 22)
**Depends on:** EBIT (Phase 8), NI (Phase 17), EBITDA (Phase 6), Unlevered/Levered Tax, Dep, Interest, CapEx, NWC
```
EBIT Method:    NOPAT + Dep - CapEx - WC
NI Method:      NI + Dep + After-tax_Interest - CapEx - WC
EBITDA Method:  EBITDA - Unlevered_Tax - CapEx - WC
All 3 must reconcile (difference < $0.01k)
```
Python: `_build_ufcf_3methods()` at dcf_engine.py:1302

### Phase 23: DCF Perpetuity (Step 23)
**Depends on:** UFCF (Phase 20), WACC (Phase 1), Terminal Growth, Yearfractions
```
TV = Terminal_UFCF x (1+g) / (WACC - g)
PV = UFCF / (1+WACC)^Years
EV = Sum(PV_discrete) + PV_terminal
```
Python: `_discount_cash_flows()` at dcf_engine.py:1507

### Phase 24: DCF Exit Multiple (Step 24)
**Depends on:** UFCF (Phase 20), WACC (Phase 1), Terminal EBITDA, Multiple
```
TV = Terminal_EBITDA x Multiple
PV = same discounting as Perpetuity
```
Python: `_discount_cash_flows()` at dcf_engine.py:1507

### Phase 25: NPV/XNPV/IRR/XIRR (Step 25)
**Depends on:** UFCF (Phase 20), WACC (Phase 1), Dates, Net Debt, Shares
```
NPV = Sum(UFCF / (1+WACC)^Period)
XNPV = date-based discounting
IRR/XIRR = bisection method
Equity_Per_Share = (NPV - Net_Debt) / Shares
```
Python: `_build_npv_xnpv()` at dcf_engine.py:1363

### Phase 26: Sensitivity Tables (Step 26)
**Depends on:** EV from Phases 23-24, WACC range, Growth/Multiple ranges
```
Perpetuity: WACC x Growth -> EV
Multiple: WACC x Multiple -> EV
```
Python: `calculate_sensitivity_perpetuity()` / `calculate_sensitivity_multiple()`

---

## STEP 9 vs STEP 10 SPLIT

### Step 9 Shows (Building Blocks = Phases 1-19):
| # | Schedule | Excel Rows | Python Method |
|---|----------|-----------|---------------|
| 1 | WACC Calculation | 26-59 | `calculate_wacc()` |
| 2 | Revenue | 96 | `_build_revenue_schedule()` |
| 3 | COGS | 97 | `_build_cogs_schedule()` |
| 4 | SG&A + Other OpEx | 99-100 | `_build_opex_schedule()` |
| 5 | Income Statement (full) | 96-111 | Revenue through Net Income |
| 6 | Working Capital | 160-175 | `_build_working_capital_schedule()` |
| 7 | Depreciation + Asset Schedule | 180-224 | `_build_depreciation_schedule()` |
| 8 | Debt Schedule Part 1 (Cash + LT Debt) | 331-345 | Cash balance, LT debt balance, interest |
| 9 | Debt Schedule Part 2 (Revolving + Net Interest) | 347-368 | Revolving credit, net interest expense |
| 10 | Equity Schedule (Common + RE + Dividends) | 370-385 | Common equity, dividends, retained earnings |
| 11 | Tax - Levered | 387-413 | `_build_tax_schedule_levered()` |
| 12 | Tax - Unlevered | 415-418 | `_build_tax_schedule_unlevered()` |
| 13 | Cash Flow Statement | 115-134 | `_build_cash_flow_statement()` |
| 14 | Balance Sheet | 138-156 | `_build_balance_sheet()` |

### Step 10 Shows (Outputs = Phases 20-26):
| # | Schedule | Excel Rows | Python Method |
|---|----------|-----------|---------------|
| 1 | UFCF Schedule | 257-275 | `_calculate_ufcf()` |
| 2 | UFCF 3 Methods | 476-498 | `_build_ufcf_3methods()` |
| 3 | Intrinsic Extracts | 450-473 | `_build_intrinsic_extracts()` |
| 4 | DCF Perpetuity | 285-315 | `_discount_cash_flows()` |
| 5 | DCF Exit Multiple | 315-340 | `_discount_cash_flows()` |
| 6 | NPV/XNPV/IRR/XIRR | 522-572 | `_build_npv_xnpv()` |
| 7 | Sensitivity - Perpetuity | Data Table | `calculate_sensitivity_perpetuity()` |
| 8 | Sensitivity - Multiple | Data Table | `calculate_sensitivity_multiple()` |

---

## DATA FLOW DIAGRAM

```
INPUTS SHEET
  Revenue_Growth ──────────┐
  Cost_Increase ───────────┤
  CapEx ───────────────────┤
  WC_Days ─────────────────┤
  WACC_Inputs ─────────────┤
  Terminal_g/Multiple ─────┤
  Opening_Balances ────────┤
  Interest_Rates ──────────┤
  Shares/Price ────────────┤
  Dates ───────────────────┤
  Dep_Params ──────────────┘
           │
           v
  ┌─── PHASE 1: WACC ───────────────────────────┐
  │  Peer Table -> Unlevered Beta -> Re-lever    │
  │  -> Cost of Equity -> WACC                   │
  └──────────────────────────────────────────────┘
           │
           v
  ┌─── PHASE 2-6: INCOME STATEMENT ─────────────┐
  │  Revenue (Growth)                            │
  │  COGS (Inflation)                            │
  │  Gross Profit = Rev - COGS                   │
  │  SG&A + Other (Inflation)                    │
  │  EBITDA = GP - SGA - Other                   │
  └──────────────────────────────────────────────┘
           │
           v
  ┌─── PHASE 7: DEPRECIATION ───────────────────┐
  │  Existing Dep (SL) + New Dep (Cohort)        │
  │  Tax Basis Roll (Declining Balance 15%)      │
  │  Gross PPE Roll                              │
  │  Terminal CapEx = Terminal Dep                │
  └──────────────────────────────────────────────┘
           │
           v
  ┌─── PHASE 8-10: EBIT -> EBT ─────────────────┐
  │  EBIT = EBITDA - Dep                         │
  │  Interest = LT_Debt x 6%                     │
  │  EBT = EBIT - Interest                       │
  └──────────────────────────────────────────────┘
           │
           v
  ┌─── PHASE 11: WORKING CAPITAL ───────────────┐
  │  AR = (AR_Days/365) x Revenue                │
  │  Inv = (Inv_Days/365) x COGS                 │
  │  AP = (AP_Days/365) x COGS                   │
  │  NWC = AR + Inv - AP                         │
  │  Change = Prior - Current                    │
  └──────────────────────────────────────────────┘
           │
           v
  ┌─── PHASE 12-13: TAX SCHEDULES ──────────────┐
  │  Levered: EBT-based with NOL utilization     │
  │  Unlevered: EBIT-based with NOL utilization  │
  │  Both: Adj = EBT/EBIT + Acctg_Dep - Tax_Dep │
  └──────────────────────────────────────────────┘
           │
           v
  ┌─── PHASE 14: NET INCOME ────────────────────┐
  │  NI = EBT - Total_Tax (levered)              │
  └──────────────────────────────────────────────┘
           │
           v
  ┌─── PHASE 15: CASH FLOW STATEMENT ───────────┐
  │  CFO = NI + Def_Tax + Dep + WC_Changes       │
  │  CFI = -(CapEx)                              │
  │  CFF = LT_Debt + Equity + Div + Revolver     │
  │  Ending_Cash = Beginning + CFO + CFI + CFF   │
  └──────────────────────────────────────────────┘
           │
           v
  ┌─── PHASE 16: BALANCE SHEET ─────────────────┐
  │  Assets = Cash + AR + Inv + PPE              │
  │  Liab = AP + Revolver + LT_Debt              │
  │  Equity = Common + Retained_Earnings         │
  │  Check: Assets = Liab + Equity               │
  └──────────────────────────────────────────────┘
           │
    ═══════╪══════════════════════════════════════
    STEP 9 │ (Building Blocks - User Reviews)
    ═══════╪══════════════════════════════════════
           │
           v
  ┌─── PHASE 17: UFCF ──────────────────────────┐
  │  UFCF = EBITDA - Unlev_Tax - CapEx + WC     │
  │  Tax_Shield = Unlev_Tax - Lev_Tax           │
  └──────────────────────────────────────────────┘
           │
           v
  ┌─── PHASE 18-19: EXTRACTS + 3-METHOD ────────┐
  │  Intrinsic Extracts (NI, Dep, Int, EBIT...)  │
  │  UFCF via EBIT/NI/EBITDA (must reconcile)   │
  └──────────────────────────────────────────────┘
           │
           v
  ┌─── PHASE 20-21: DCF VALUATION ──────────────┐
  │  Perpetuity: TV = UFCF x (1+g) / (WACC - g) │
  │  Multiple: TV = EBITDA x Multiple            │
  │  Discount: PV = CF / (1+WACC)^Years          │
  │  EV = Sum(PV_discrete) + PV_terminal         │
  └──────────────────────────────────────────────┘
           │
           v
  ┌─── PHASE 22: NPV/XNPV ─────────────────────┐
  │  NPV = Sum(UFCF / (1+WACC)^Period)          │
  │  XNPV = date-based discounting              │
  │  Equity/Share = (NPV - Net_Debt) / Shares   │
  └──────────────────────────────────────────────┘
           │
           v
  ┌─── PHASE 23: SENSITIVITY ───────────────────┐
  │  Perpetuity: WACC x Growth -> EV table       │
  │  Multiple: WACC x Multiple -> EV table       │
  └──────────────────────────────────────────────┘
           │
    ═══════╪══════════════════════════════════════
    STEP 10│ (Outputs - Valuation Dashboard)
    ═══════╪══════════════════════════════════════
```