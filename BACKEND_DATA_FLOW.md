# Backend Data Flow: yfinance API Inputs & Calculated Metrics

## 📥 STEP 1: RAW DATA RETRIEVED FROM YFINANCE API
*(via `/workspace/backend/app/services/yfinance_service.py`)*

### A. Income Statement (Annual)
| Field Name | yfinance Label | Description |
|------------|---------------|-------------|
| `total_revenue` | Total Revenue | Top-line revenue |
| `cost_of_revenue` | Cost Of Revenue | COGS |
| `gross_profit` | Gross Profit | Revenue - COGS |
| `operating_expense` | Operating Expense | SG&A + R&D |
| `selling_general_administrative` | Selling General And Administrative | SG&A |
| `research_development` | Research Development | R&D |
| `operating_income` | Operating Income | EBIT |
| `ebitda` | EBITDA | Earnings Before Interest, Taxes, D&A |
| `interest_expense` | Interest Expense | ⚠️ Often missing for recent periods |
| `interest_income` | Interest Income | Interest earned |
| `pretax_income` | Pretax Income | EBT |
| `tax_provision` | Tax Provision | Income tax expense |
| `net_income` | Net Income Common Stockholders | Bottom line |
| `diluted_eps` | Diluted EPS | Earnings per share (diluted) |
| `basic_eps` | Basic EPS | Earnings per share (basic) |
| `depreciation_amortization` | Depreciation Amortization Depletion | D&A |

### B. Balance Sheet (Annual)
| Field Name | yfinance Label | Description |
|------------|---------------|-------------|
| `total_assets` | Total Assets | Total assets |
| `current_assets` | Current Assets | Short-term assets |
| `non_current_assets` | Non Current Assets | Long-term assets |
| `cash_and_equivalents` | Cash Cash Equivalents And Short Term Investments | Cash & ST investments |
| `accounts_receivable` | Receivables | AR |
| `inventory` | Inventory | Inventory |
| `other_current_assets` | Other Current Assets | Other current assets |
| `property_plant_equipment` | Net PPE | PP&E (net) |
| `goodwill` | Goodwill | Goodwill |
| `intangible_assets` | Intangible Assets | Intangibles |
| `total_liabilities` | Total Liabilities Net Minority Interest | Total liabilities |
| `current_liabilities` | Current Liabilities | Short-term liabilities |
| `accounts_payable` | Payables And Accrued Expenses | AP |
| `short_term_debt` | Current Debt | ST debt |
| `long_term_debt` | Long Term Debt | LT debt |
| `total_debt` | Total Debt | Total debt (ST + LT) |
| `total_equity` | Total Equity Gross Minority Interest | Total equity |
| `stockholders_equity` | Stockholders Equity | Shareholders' equity |
| `retained_earnings` | Retained Earnings | Retained earnings |
| `shares_outstanding` | Ordinary Shares Number | Shares outstanding |

### C. Cash Flow Statement (Annual)
| Field Name | yfinance Label | Description |
|------------|---------------|-------------|
| `operating_cash_flow` | Operating Cash Flow | OCF |
| `depreciation_amortization` | Depreciation Amortization Depletion | D&A (from CF) |
| `change_in_working_capital` | Change In Working Capital | ΔWC |
| `change_in_ar` | Change In Receivables | ΔAR |
| `change_in_inventory` | Change In Inventory | ΔInventory |
| `change_in_ap` | Change In Payables And Accrued Expense | ΔAP |
| `investing_cash_flow` | Investing Cash Flow | ICF |
| `capital_expenditure` | Capital Expenditure | CapEx |
| `free_cash_flow` | Free Cash Flow | FCF |
| `financing_cash_flow` | Financing Cash Flow | FCF |
| `dividends_paid` | Cash Dividends Paid | Dividends |
| `end_cash_position` | End Cash Position | Ending cash |

### D. Key Statistics & Market Data
| Field Name | yfinance Label | Description |
|------------|---------------|-------------|
| `company_name` | longName | Company name |
| `sector` | sector | Sector |
| `industry` | industry | Industry |
| `currency` | currency | Currency |
| `current_price` | currentPrice | Current stock price |
| `market_cap` | marketCap | Market capitalization |
| `enterprise_value` | enterpriseValue | Enterprise value |
| `beta` | beta | Beta (3-year historical) |
| `pe_ratio` | trailingPE | P/E ratio |
| `forward_pe` | forwardPE | Forward P/E |
| `peg_ratio` | pegRatio | PEG ratio |
| `price_to_book` | priceToBook | P/B ratio |
| `price_to_sales` | priceToSalesTrailing12Months | P/S ratio |
| `ev_to_revenue` | enterpriseToRevenue | EV/Revenue |
| `ev_to_ebitda` | enterpriseToEbitda | EV/EBITDA |
| `profit_margin` | profitMargins | Net profit margin |
| `operating_margin` | operatingMargins | Operating margin |
| `return_on_assets` | returnOnAssets | ROA |
| `return_on_equity` | returnOnEquity | ROE |
| `total_debt` | totalDebt | Total debt (from stats) |
| `total_cash` | totalCash | Total cash (from stats) |
| `debt_to_equity` | debtToEquity | D/E ratio |
| `current_ratio` | currentRatio | Current ratio |
| `quick_ratio` | quickRatio | Quick ratio |

### E. Analyst Estimates
| Field Name | Source | Description |
|------------|--------|-------------|
| `revenue_estimates` | revenue_estimate | Revenue forecasts |
| `earnings_estimates` | earnings_estimate | EPS forecasts |
| `target_prices` | analyst_price_targets | Price targets |
| `recommendation_trend` | recommendations | Analyst ratings |
| `growth_estimates` | growth_estimates | Growth projections |

---

## ❌ DATA NOT AVAILABLE FROM YFINANCE (Requires AI/External Sources)

| Metric | Reason | Solution |
|--------|--------|----------|
| **Risk-Free Rate** | Macro input, not company-specific | Treasury yield API or AI estimation |
| **Equity Risk Premium (ERP)** | Market-wide premium | AI estimation based on market/industry |
| **Country Risk Premium** | Country-specific risk | AI estimation or external macro data |
| **Terminal EBITDA Multiple** | Forward-looking valuation metric | AI estimation based on industry comps |
| **Forward-looking Beta** | Requires regression calculation | Calculate from historical prices or use AI |
| **Segment Data** | Not in yfinance free tier | Company reports/SEC filings |
| **Management Guidance** | Not structured data | Company reports/press releases |

---

## 🧮 STEP 2: CALCULATED METRICS
*(via `/workspace/backend/app/services/metrics_calculator.py`)*

### A. Margin Metrics
| Metric | Formula | Source Data |
|--------|---------|-------------|
| **EBITDA Margin** | EBITDA / Revenue | income_stmt |
| **Net Margin** | Net Income / Revenue | income_stmt |
| **FCF Margin** | Free Cash Flow / Revenue | cash_flow, income_stmt |
| **Operating Margin** | Operating Income / Revenue | income_stmt |
| **Gross Margin** | Gross Profit / Revenue | income_stmt |

*All margins calculated as: historical series + latest + 3Y average*

### B. Growth Rates
| Metric | Formula | Source Data |
|--------|---------|-------------|
| **Revenue CAGR (3Y)** | (Latest Revenue / Oldest Revenue)^(1/3) - 1 | income_stmt |
| **Revenue CAGR (5Y)** | (Latest Revenue / Oldest Revenue)^(1/5) - 1 | income_stmt |
| **EBITDA CAGR (3Y)** | (Latest EBITDA / Oldest EBITDA)^(1/3) - 1 | income_stmt |
| **Net Income CAGR (3Y)** | (Latest NI / Oldest NI)^(1/3) - 1 | income_stmt |
| **EPS CAGR (3Y)** | (Latest EPS / Oldest EPS)^(1/3) - 1 | income_stmt |
| **YoY Growth** | (Current Year - Prior Year) / Prior Year | All metrics above |

### C. Working Capital Days
| Metric | Formula | Source Data |
|--------|---------|-------------|
| **DSO** (Days Sales Outstanding) | (Accounts Receivable / Revenue) × 365 | balance_sheet, income_stmt |
| **DIO** (Days Inventory Outstanding) | (Inventory / COGS) × 365 | balance_sheet, income_stmt |
| **DPO** (Days Payables Outstanding) | (Accounts Payable / COGS) × 365 | balance_sheet, income_stmt |
| **CCC** (Cash Conversion Cycle) | DSO + DIO - DPO | Calculated from above |

*All days calculated as: historical series + latest + 3Y average*

### D. CapEx Ratios
| Metric | Formula | Source Data |
|--------|---------|-------------|
| **CapEx to Revenue** | CapEx / Revenue | cash_flow, income_stmt |
| **FCF to Revenue** | Free Cash Flow / Revenue | cash_flow, income_stmt |
| **CapEx to OCF** | CapEx / Operating Cash Flow | cash_flow |

### E. Cost of Debt (Implied)
| Metric | Formula | Source Data |
|--------|---------|-------------|
| **Implied Cost of Debt** | Interest Expense / Total Debt | income_stmt, balance_sheet |

⚠️ *Note: Often unavailable if Interest Expense is missing from yfinance*

### F. Debt Ratios
| Metric | Formula | Source Data |
|--------|---------|-------------|
| **Debt to Equity** | Total Debt / Total Equity | balance_sheet |
| **Debt to Assets** | Total Debt / Total Assets | balance_sheet |
| **Net Debt** | Total Debt - Cash & Equivalents | balance_sheet |
| **Debt to EBITDA** | Total Debt / EBITDA | balance_sheet, income_stmt |

### G. Profitability Ratios
| Metric | Formula | Source Data |
|--------|---------|-------------|
| **Return on Assets (ROA)** | Net Income / Total Assets | income_stmt, balance_sheet |
| **Return on Equity (ROE)** | Net Income / Shareholders' Equity | income_stmt, balance_sheet |
| **Return on Invested Capital (ROIC)** | NOPAT / Invested Capital | Calculated |

### H. Market Multiples
| Metric | Formula | Source Data |
|--------|---------|-------------|
| **P/E Ratio** | Market Cap / Net Income | key_stats |
| **EV/EBITDA** | Enterprise Value / EBITDA | key_stats, income_stmt |
| **EV/Revenue** | Enterprise Value / Revenue | key_stats, income_stmt |
| **P/B Ratio** | Market Cap / Book Value | key_stats |
| **PEG Ratio** | P/E / Growth Rate | key_stats |

---

## 🔢 STEP 3: DCF MODEL CALCULATIONS
*(via `/workspace/backend/app/engines/dcf_engine.py`)*

### A. WACC Calculation
```
WACC = (E/V × Re) + (D/V × Rd × (1-T))

Where:
- E = Market value of equity
- D = Market value of debt
- V = E + D (Total value)
- Re = Cost of Equity
- Rd = Cost of Debt (pre-tax)
- T = Tax rate

Cost of Equity (CAPM):
Re = Risk-Free Rate + (Beta × Equity Risk Premium) + Country Risk Premium
```

**Inputs Required:**
- Risk-Free Rate (❌ External/AI)
- Beta (✅ From yfinance or calculated)
- Equity Risk Premium (❌ External/AI)
- Country Risk Premium (❌ External/AI)
- Pre-tax Cost of Debt (✅ Calculated or input)
- Target Debt/Equity weights (✅ Input or industry avg)
- Tax Rate (✅ Calculated from financials)

### B. Free Cash Flow Forecast
```
UFCF = EBIT × (1 - Tax Rate) + D&A - CapEx - ΔWorking Capital

Revenue Forecast:
Revenue[t] = Revenue[t-1] × (1 + Volume Growth[t]) × (1 + Price Growth[t])

COGS Forecast:
COGS[t] = COGS[t-1] × (1 + Inflation Rate[t])
```

### C. Terminal Value (Two Methods)
**1. Perpetuity Growth Method:**
```
TV = UFCF[Terminal Year] × (1 + g) / (WACC - g)
Where g = Terminal Growth Rate (❌ AI/Manual input)
```

**2. Exit Multiple Method:**
```
TV = EBITDA[Terminal Year] × Terminal EBITDA Multiple
Where Multiple = Terminal EBITDA Multiple (❌ AI/Manual input)
```

### D. Enterprise Value & Equity Value
```
Enterprise Value = PV(Discrete FCF) + PV(Terminal Value)
Equity Value = Enterprise Value - Net Debt + Cash
Share Price = Equity Value / Shares Outstanding
```

---

## 📊 SUMMARY: DATA FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                    YFINANCE API (Raw Data)                   │
│  - Income Statement (16 fields)                              │
│  - Balance Sheet (19 fields)                                 │
│  - Cash Flow (14 fields)                                     │
│  - Key Stats (28 fields)                                     │
│  - Analyst Estimates (6 categories)                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Metrics Calculator (Derived Metrics)            │
│  - Margins (4 types × 3 variants each)                       │
│  - Growth Rates (CAGR 3Y/5Y, YoY)                            │
│  - Working Capital Days (DSO, DIO, DPO, CCC)                 │
│  - CapEx Ratios (3 types)                                    │
│  - Cost of Debt (Implied)                                    │
│  - Debt Ratios (4 types)                                     │
│  - Profitability Ratios (ROA, ROE, ROIC)                     │
│  - Market Multiples (5 types)                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           External Inputs (AI Estimation / Manual)           │
│  - Risk-Free Rate                                            │
│  - Equity Risk Premium                                       │
│  - Country Risk Premium                                      │
│  - Terminal Growth Rate                                      │
│  - Terminal EBITDA Multiple                                  │
│  - Useful Life of Assets                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  DCF Engine (Valuation)                      │
│  - WACC Calculation                                          │
│  - Revenue/Cost Forecast (5 years)                           │
│  - Free Cash Flow Projection                                 │
│  - Terminal Value (Perpetuity + Multiple)                    │
│  - Discounted Cash Flow                                      │
│  - Sensitivity Analysis                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Final Output                              │
│  - Enterprise Value                                          │
│  - Equity Value                                              │
│  - Implied Share Price                                       │
│  - Upside/Downside vs Current Price                          │
│  - Valuation Range (Bear/Base/Bull)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 COMPLETE FIELD MAPPING FOR FRONTEND DISPLAY

### Step 6: Historical Financials Display
All fields currently displayed in `ApiDataStep.jsx`:

1. ✅ Revenue (3-5 years)
2. ✅ COGS
3. ✅ EBITDA (3-5 years)
4. ✅ Net Income (3-5 years)
5. ✅ SG&A / OpEx
6. ✅ Depreciation & Amortization
7. ✅ CapEx
8. ✅ Working Capital Items:
   - Accounts Receivable
   - Inventory
   - Accounts Payable

### Additional Fields Available but Not Yet Displayed:
- Gross Profit
- Operating Income
- Interest Expense
- Tax Provision
- Total Assets
- Total Debt
- Free Cash Flow
- Cash & Equivalents
- Shareholders Equity
- Operating Cash Flow
- Revenue CAGR
- Avg EBITDA Margin
- Avg ROE

---

## 🔍 KEY FILES REFERENCE

| File | Purpose | Lines |
|------|---------|-------|
| `/backend/app/services/yfinance_service.py` | Raw data fetching | 1-576 |
| `/backend/app/services/metrics_calculator.py` | Derived calculations | 1-500+ |
| `/backend/app/engines/dcf_engine.py` | DCF valuation engine | 1-1200+ |
| `/backend/app/api/routes/v1/valuation_routes.py` | API endpoints | 1-900+ |
| `/frontend/src/components/valuation-flow/ApiDataStep.jsx` | Step 6 UI | Frontend |
