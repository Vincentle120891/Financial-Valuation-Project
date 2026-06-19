# Step 8 Forecast Inputs vs Excel DCF Model — Full Comparison

## Excel Inputs Sheet (rows 5-83) — Complete Field List

### [A] Scenario Switch
- D7 = Outputs!F6 → 1=Best, 2=Base, 3=Worst

### [B] Revenue Growth (rows 5-8)
- Row 5: Active = CHOOSE($D$7, row6, row7, row8)
- Row 6: Best case growth rates
- Row 7: Base case growth rates
- Row 8: Worst case growth rates
- Each row has 6 periods: FY1-FY5 + Terminal

### [C] Cost Projection Increases (rows 9-12)
- Row 9: Active = CHOOSE($D$7, row10, row11, row12)
- Row 10-12: Per-scenario cost increase rates
- Drives COGS and OpEx (SG&A and Other) growth
- Each row has 6 periods

### [D] Capital Expenditure (rows 13-16)
- Row 13: Active = CHOOSE($D$7, row14, row15, row16)
- Row 14-16: Per-scenario capex amounts
- Each row has 6 periods

### [E] Inflation Rate (row 17)
- Non-scenario-switched inflation series
- Context row (not operative driver)

### [F] Working Capital (rows 18-21)
- Row 19: AR Days
- Row 20: Inventory Days
- Row 21: AP Days
- Terminal columns = prior year (K column)

### [G] Other Annual Inputs (rows 22-24)
- Row 23: Term Debt Increase/(Decrease) per year
- Row 24: Common Equity Increase/(Decrease) per year

### [H] WACC Inputs (rows 26-59)
- Peer table (rows 30-39): Debt, Equity, Tax Rate, Levered Beta per company
- D/E Ratio: =Debt / Equity
- D/Capital: =Debt / (Debt + Equity)
- Unlevered Beta: =Levered / (1 + (1-Tax) x D/E)
- Averages/Medians (rows 41-42)
- Risk-Free Rate (row 44)
- Market Risk Premium (row 45)
- Country Risk Premium (row 46)
- Avg Unlevered Beta (row 47)
- Levered Beta (row 48): =Unlevered x (1 + (1-Tax) x Target D/E)
- Equity Risk Premium (row 49): =MRP x Levered Beta
- Target D weight (row 50)
- Target E weight (row 51)
- Target D/E (row 52): =D weight / E weight
- Pre-Tax Cost of Debt (row 53)
- Tax Rate (row 54)
- After-Tax Cost of Debt (row 55): =Pre-Tax x (1 - Tax)
- Total Debt (row 56)
- Market Cap (row 57)
- Current D/Capital, E/Capital (rows 58-59)
- WACC (row 59): =D weight x AT Cost of Debt + E weight x Cost of Equity

### [I] Other Inputs (rows 61-83)
- Valuation Date (row 61)
- First CF Date (row 62)
- Fiscal Year End (row 63)
- Date Validation (row 64): =IF(date1 > date2, 1, 0)
- Net Debt Opening (row 68)
- PP&E Gross Book (row 69)
- Tax Basis PPE (row 70)
- Tax Losses NOL (row 71)
- 52-Week High (row 72)
- 52-Week Low (row 73)
- Shares Outstanding (row 74)
- Stock Price (row 75)
- Terminal Growth Rate (row 76)
- Terminal EBITDA Multiple (row 77)
- Cash Interest Rate (row 77): 1%
- Revolving Credit Interest Rate (row 78): 5%
- LT Debt Interest Rate (row 79): 6%
- Dividend Payout Ratio (row 80)
- Useful Life Existing (row 82): 16 years
- Useful Life New (row 85): 20 years
- First Year Tax Dep Rate (row 86): 50%
- Blended Tax Dep Rate: 15%
- First Year Acctg Dep Rate (row 86): 50%

---

## Step 8 DCF Categories — Complete Field List

### Category 1: REVENUE_DRIVERS
- Revenue Growth (multi-year): Annual revenue growth rate

### Category 2: COST_MARGINS
- Inflation Rate (multi-year): Projected annual cost increase
- COGS % of Revenue: Cost of goods sold as % of revenue
- OpEx Growth: YoY growth rate of operating expenses
- Effective Tax Rate: Expected effective tax rate

### Category 3: WORKING_CAPITAL
- Accounts Receivable Days: Average days to collect
- Inventory Days: Average days inventory held
- Accounts Payable Days: Average days to pay suppliers
- Capital Expenditure: Absolute value from cash flow statement

### Category 4: WACC_COMPONENTS
- Risk-Free Rate: 10-year government bond yield
- Market Risk Premium: Expected excess return
- Country Risk Premium: Additional risk for country exposure
- Pre-Tax Cost of Debt: Interest rate on debt before tax
- Target Debt-to-Equity: Target D/E ratio
- Beta: Levered beta from peer analysis
- WACC: Calculated from components

### Category 5: TERMINAL_VALUE
- Terminal Growth Rate: Perpetual growth after forecast
- Terminal EBITDA Multiple: Exit multiple

---

## COMPARISON TABLE

| # | Excel Inputs Sheet | Excel Row(s) | Step 8 Metric | Match? | Notes |
|---|-------------------|-------------|---------------|--------|-------|
| 1 | Scenario Switch | D7 | — | N/A | Web app uses separate API calls per scenario |
| 2 | Revenue Growth (Best) | 5-8 | Revenue Growth (multi-year) | ✅ | Step 8 has single multi-year input; Excel has 3 scenarios |
| 3 | Revenue Growth (Base) | 5-8 | Revenue Growth (multi-year) | ✅ | Same |
| 4 | Revenue Growth (Worst) | 5-8 | Revenue Growth (multi-year) | ✅ | Same |
| 5 | Cost Increase (Best) | 9-12 | Inflation Rate (multi-year) | ✅ | Same pattern |
| 6 | Cost Increase (Base) | 9-12 | Inflation Rate (multi-year) | ✅ | Same |
| 7 | Cost Increase (Worst) | 9-12 | Inflation Rate (multi-year) | ✅ | Same |
| 8 | CapEx (Best) | 13-16 | Capital Expenditure | ⚠️ | Step 8: single value; Excel: per-scenario multi-year |
| 9 | CapEx (Base) | 13-16 | Capital Expenditure | ⚠️ | Same |
| 10 | CapEx (Worst) | 13-16 | Capital Expenditure | ⚠️ | Same |
| 11 | Inflation Rate | 17 | Inflation Rate | ✅ | Context row in Excel |
| 12 | AR Days | 19 | Accounts Receivable Days | ✅ | |
| 13 | Inventory Days | 20 | Inventory Days | ✅ | |
| 14 | AP Days | 21 | Accounts Payable Days | ✅ | |
| 15 | Term Debt Increase | 23 | — | ❌ | MISSING: affects Debt Schedule Part 1 |
| 16 | Common Equity Increase | 24 | — | ❌ | MISSING: affects Equity Schedule + CFF |
| 17 | Peer Table (Debt) | 30 | — | ✅ | From Step 4 peer data |
| 18 | Peer Table (Equity) | 31 | — | ✅ | From Step 4 peer data |
| 19 | Peer Table (Tax Rate) | 32 | — | ✅ | From Step 4 peer data |
| 20 | Peer Table (Levered Beta) | 33 | Beta | ✅ | From peer analysis |
| 21 | D/E Ratio | 34 | — | ✅ | Calculated from peer data |
| 22 | D/Capital | 35 | — | ✅ | Calculated from peer data |
| 23 | Unlevered Beta | 36 | — | ✅ | Calculated from peer data |
| 24 | Avg Unlevered Beta | 41 | — | ✅ | Calculated from peer averages |
| 25 | Risk-Free Rate | 44 | Risk-Free Rate | ✅ | |
| 26 | Market Risk Premium | 45 | Market Risk Premium | ✅ | |
| 27 | Country Risk Premium | 46 | Country Risk Premium | ✅ | |
| 28 | Avg Unlevered Beta | 47 | — | ✅ | From peer analysis |
| 29 | Levered Beta | 48 | Beta | ✅ | |
| 30 | Target D weight | 50 | — | ✅ | Derived from D/E |
| 31 | Target E weight | 51 | — | ✅ | Derived from D/E |
| 32 | Target D/E | 52 | Target Debt-to-Equity | ✅ | |
| 33 | Pre-Tax Cost of Debt | 53 | Pre-Tax Cost of Debt | ✅ | |
| 34 | Tax Rate | 54 | Effective Tax Rate | ✅ | |
| 35 | After-Tax Cost of Debt | 55 | — | ✅ | Calculated |
| 36 | Total Debt | 56 | — | ✅ | From historical data |
| 37 | Market Cap | 57 | — | ✅ | From market data |
| 38 | WACC | 59 | WACC | ✅ | Calculated from components |
| 39 | Valuation Date | 61 | — | ✅ | Default in DCFInputs |
| 40 | First CF Date | 62 | — | ✅ | Default in DCFInputs |
| 41 | Fiscal Year End | 63 | — | ✅ | Default in DCFInputs |
| 42 | Net Debt Opening | 68 | — | ✅ | From historical data |
| 43 | PP&E Gross Book | 69 | — | ✅ | From historical data |
| 44 | Tax Basis PPE | 70 | — | ✅ | From historical data |
| 45 | Tax Losses NOL | 71 | — | ✅ | From SEC EDGAR XBRL |
| 46 | 52-Week High | 72 | — | ✅ | From market data |
| 47 | 52-Week Low | 73 | — | ✅ | From market data |
| 48 | Shares Outstanding | 74 | — | ✅ | From market data |
| 49 | Stock Price | 75 | — | ✅ | From market data |
| 50 | Terminal Growth Rate | 76 | Terminal Growth Rate | ✅ | |
| 51 | Terminal EBITDA Multiple | 77 | Terminal EBITDA Multiple | ✅ | |
| 52 | Cash Interest Rate | 77 | — | ❌ | MISSING: hardcoded 1% in DCFInputs |
| 53 | Revolving Credit Rate | 78 | — | ❌ | MISSING: hardcoded 5% in DCFInputs |
| 54 | LT Debt Interest Rate | 79 | — | ❌ | MISSING: hardcoded 6% in DCFInputs |
| 55 | Dividend Payout Ratio | 80 | — | ❌ | MISSING: uses absolute dividends |
| 56 | Useful Life Existing | 82 | — | ❌ | MISSING: hardcoded 16 years |
| 57 | Useful Life New | 85 | — | ❌ | MISSING: hardcoded 20 years |
| 58 | First Year Tax Dep Rate | 86 | — | ❌ | MISSING: hardcoded 50% |
| 59 | Blended Tax Dep Rate | — | — | ❌ | MISSING: hardcoded 15% |
| 60 | First Year Acctg Dep Rate | 86 | — | ❌ | MISSING: hardcoded 50% |

---

## SUMMARY

### ✅ Matched (40/60 = 67%)
All core valuation inputs: Revenue Growth, Inflation, WC Days, WACC components, Terminal Value, Opening Balances, Market Data, Dates

### ⚠️ Partial Match (3/60 = 5%)
CapEx: Step 8 has single value; Excel has per-scenario multi-year

### ❌ Missing from Step 8 (17/60 = 28%)
1. Term Debt Increase/(Decrease) — affects Debt Schedule
2. Common Equity Increase/(Decrease) — affects Equity Schedule + CFF
3. Cash Interest Rate (1%) — affects Debt Part 1
4. Revolving Credit Rate (5%) — affects Debt Part 2
5. LT Debt Interest Rate (6%) — affects Debt Part 1 + IS
6. Dividend Payout Ratio — affects Equity Schedule + CFS
7. Useful Life Existing (16yr) — affects Depreciation
8. Useful Life New (20yr) — affects Depreciation
9. First Year Tax Dep Rate (50%) — affects Tax Basis
10. Blended Tax Dep Rate (15%) — affects Tax Basis
11. First Year Acctg Dep Rate (50%) — affects Depreciation
12. COGS % of Revenue (Step 8 extra) — not in Excel
13. OpEx Growth (Step 8 extra) — not in Excel
