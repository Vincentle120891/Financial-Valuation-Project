# Backend Valuation Workflow Documentation

## Overview

This document describes the complete workflow of the backend valuation system, showing how different valuation models work across international and Vietnamese markets.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Routes Layer                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │valuation_    ││international │ │vietnamese_reports_       │ │
│  │routes.py     ││routes.py     │ │routes.py                 │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       Services Layer                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │yfinance_     ││vietnamese_   │ │pdf_extraction_           │ │
│  │service.py    ││ticker_service│ │service.py                │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        Engines Layer                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │dcf_engine.py ││comps_engine  │ │sector_valuation_models.py│ │
│  │              ││.py           │ │(Vietnam specific)         │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         Models Layer                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │international ││vietnamese_   │ │vietnamese_               │ │
│  │_cashflow_    ││cashflow_model│ │financial_model.py        │ │
│  │model.py      ││.py           │ │                          │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Workflow 1: DCF Model (International Market)

### Endpoint Flow
```
POST /step-4-select-models
    ↓
POST /step-5-prepare-inputs
    ↓
POST /step-6-fetch-api-data
    ↓
POST /step-7-generate-ai-assumptions
    ↓
POST /step-9-confirm-assumptions
    ↓
POST /step-10-valuate
```

### Detailed Steps

#### Step 1: Model Selection (`/step-4-select-models`)
**File:** `valuation_routes.py:583`
```python
Input: {session_id, model: "dcf"}
Output: {message, next_step: "fetch_data", selected_model: "dcf"}
```
- User selects DCF valuation model
- Session state updated to "model_selected"

#### Step 2: Prepare Inputs (`/step-5-prepare-inputs`)
**File:** `valuation_routes.py:613`
```python
Input: {session_id}
Output: {required_inputs: [...]}
```
Returns required input categories:
- **Historical Financials** (auto-fetched): Revenue, EBITDA, Net Income, COGS, SG&A, Depreciation, CapEx, Working Capital
- **Market Data** (auto-fetched): Stock Price, Shares Outstanding, Debt, Cash, Beta, Market Cap
- **Forecast Drivers** (user input): Revenue Growth, Volume/Price Split, Inflation, Margins, Tax Rate, CapEx %, WC Days
- **DCF Model Inputs** (user input): Risk-Free Rate, ERP, Beta, Cost of Debt, WACC, Terminal Growth, Terminal Multiple
- **Peer Comparison** (optional): Peer Tickers, Multiples

#### Step 3: Fetch API Data (`/step-6-fetch-api-data`)
**File:** `valuation_routes.py:917`
```python
Input: {session_id, ticker_symbol, market: "international"}
Process:
  1. Calls fetch_financial_data() [line 61]
  2. Uses yfinance to fetch:
     - Company info (current price, shares, beta)
     - Financial statements (income, balance sheet, cashflow)
     - Historical metrics (revenue CAGR, EBITDA margins, ROE)
  3. Stores in session['financial_data']
Output: {financial_data: {...}, message: "Data fetched successfully"}
```

**Service Chain:**
```
valuation_routes.fetch_financial_data()
    ↓
yfinance.Ticker(ticker_symbol)
    ↓
Returns: info, financials, balance_sheet, cashflow
```

#### Step 4: Generate AI Assumptions (`/step-7-generate-ai-assumptions`)
**File:** `valuation_routes.py:1031`
```python
Input: {session_id}
Process:
  1. Calls generate_ai_assumptions() [line 196]
  2. Uses AI engine to generate:
     - Revenue growth forecasts (5 years)
     - Margin assumptions
     - Capex projections
     - Working capital days
     - Terminal value assumptions
  3. Stores in session['ai_assumptions']
Output: {assumptions: {...}, rationale: "..."}
```

**AI Engine:** `app/engines/ai_engine.py`
- Analyzes historical trends
- Industry benchmarks
- Market conditions
- Generates defensible assumptions with rationale

#### Step 5: Confirm Assumptions (`/step-9-confirm-assumptions`)
**File:** `valuation_routes.py:1089`
```python
Input: {session_id, confirmed_assumptions: {...}}
Process:
  1. User reviews AI-generated assumptions
  2. Can modify any values
  3. Stores final assumptions in session['confirmed_assumptions']
Output: {message: "Assumptions confirmed", next_step: "valuate"}
```

#### Step 6: Run Valuation (`/step-10-valuate`)
**File:** `valuation_routes.py:1119`
```python
Input: {session_id}
Process:
  1. Calls run_valuation_engine() [line 279]
  2. Initializes DCFEngine with confirmed inputs
  3. Executes DCF calculation:
     a. Calculate WACC from comparables
     b. Build revenue schedule (volume × price growth)
     c. Build COGS schedule (inflation-adjusted)
     d. Build OpEx schedule
     e. Build depreciation schedule (existing + new assets)
     f. Build working capital schedule
     g. Build tax schedule (levered & unlevered)
     h. Calculate UFCF
     i. Discount cash flows (perpetuity & exit multiple methods)
     j. Calculate equity value and per-share value
  4. Returns comprehensive valuation result
Output: {
  enterprise_value,
  equity_value,
  equity_value_per_share,
  implied_premium_discount,
  wacc,
  terminal_value,
  supporting_schedules: {...}
}
```

**DCF Engine:** `app/engines/dcf_engine.py`
```python
DCFEngine.calculate_wacc()
    → Returns: WACC, avg_unlevered_beta, levered_beta, cost_of_equity

DCFEngine._build_revenue_schedule()
    → Revenue[t] = Revenue[t-1] × (1 + Volume Growth) × (1 + Price Growth)

DCFEngine._build_cogs_schedule()
    → Inflation-adjusted COGS forecast

DCFEngine._build_depreciation_schedule()
    → Existing assets + New capex depreciation

DCFEngine._build_working_capital_schedule()
    → AR, Inventory, AP based on days outstanding

DCFEngine._build_tax_schedule()
    → Current tax, deferred tax, NOL utilization

DCFEngine._calculate_ufcf()
    → EBITDA - Tax - CapEx - ΔNWC

DCFEngine._discount_cash_flows()
    → PV of discrete CFs + PV of terminal value

DCFEngine.run_valuation()
    → Returns: perpetuity_method, exit_multiple_method results
```

---

## Workflow 2: Comparable Companies Model (International Market)

### Endpoint Flow
Same as DCF, but model selection is `"comparable"` or `"comps"`

### Step 2: Prepare Inputs (Comps-Specific)
**File:** `valuation_routes.py:696-780`

Required inputs for Comps model:
- **Market Data** (auto-fetched): Stock Price, Shares, Market Cap, Debt, Cash, Enterprise Value
- **Historical Financials** (auto-fetched): Revenue LTM, EBITDA LTM, EBIT LTM, Net Income LTM, EPS LTM, FCF LTM, Book Equity
- **Forward Estimates** (user input): EBITDA FY2023/2024, EPS FY2023/2024
- **Peer Selection** (user input): Peer Group Tickers (5-10), Rationale, Primary Comparable
- **Multiple Analysis** (user input): 
  - Primary Multiple Selection (EV/EBITDA, P/E, etc.)
  - EV/EBITDA LTM/FY2023/FY2024
  - P/E LTM/FY2023/FY2024
  - EV/Sales, EV/EBIT, P/B, P/FCF
- **Statistical Analysis** (user input): Outlier filtering (IQR method), Mean vs Median
- **Implied Valuation** (calculated): Implied EV, Implied Equity Value, Implied Share Price
- **Football Field Chart** (calculated): Low/High/Mean valuation ranges

### Step 6: Run Valuation (Comps Engine)
**File:** `app/engines/comps_engine.py`

```python
CompsEngine.calculate_peer_multiples()
    → Fetches data for all peer companies
    → Calculates LTM and forward multiples

CompsEngine.apply_outlier_filtering()
    → IQR method to remove statistical outliers
    → Returns cleaned peer set

CompsEngine.calculate_statistics()
    → Mean, median, min, max for each multiple
    → Standard deviation analysis

CompsEngine.apply_multiple_to_target()
    → Target EBITDA × Peer Median EV/EBITDA
    → Target EPS × Peer Median P/E
    → Returns implied valuations

CompsEngine.create_football_field()
    → Valuation range chart
    → Low (25th percentile), High (75th percentile)
    → Mean and current price comparison

CompsEngine.run_comparable_valuation()
    → Returns: {
        implied_enterprise_value,
        implied_equity_value,
        implied_share_price,
        football_field_data,
        peer_analysis,
        recommendation
      }
```

---

## Workflow 3: DCF Model (Vietnamese Market)

### Key Differences from International DCF

#### Step 3: Fetch API Data (Vietnamese)
**File:** `valuation_routes.py:917` + `international_routes.py:121`

```python
Input: {session_id, ticker_symbol: "VNM", market: "vietnamese"}
Process:
  1. Appends ".VN" suffix if not present
  2. Calls VietnameseTickerService.fetch_vietnamese_data()
  3. Additional data fetched:
     - Sector peers (Vietnamese banking, real estate, etc.)
     - VNINDEX/HNXINDEX performance
     - Foreign ownership status
     - VND/USD exchange rate
     - Trading calendar
     - Regulatory notes
  4. Enhanced mode includes:
     - vietnam_metrics: Local GAAP adjustments
     - calculated_ratios: TT99-compliant ratios
Output: {financial_data, vietnam_metrics, market_context}
```

**Service Chain:**
```
valuation_routes.fetch_financial_data()
    ↓
yf.Ticker("VNM.VN")
    ↓
VietnameseTickerService.fetch_vietnamese_data_enhanced()
    ↓
Returns: Standard financials + Vietnam-specific metrics
```

#### Step 4: Generate AI Assumptions (Vietnamese Context)
**File:** `valuation_routes.py:196`

Additional considerations for Vietnam:
- Higher country risk premium (3.6% vs developed markets)
- Higher risk-free rate (Vietnamese government bonds ~11%)
- Sector-specific growth rates (banking, real estate dominate)
- Currency considerations (VND inflation, USD/VND forex)
- Regulatory constraints (foreign ownership limits)

#### Step 6: Run Valuation (Vietnamese DCF)
**File:** `app/engines/dcf_engine.py` + `app/models/vietnamese_cashflow_model.py`

Adjustments for Vietnamese market:
```python
inputs.risk_free_rate = 0.11  # 11% Vietnam gov bond yield
inputs.market_risk_premium = 0.07  # 7% Vietnam ERP
inputs.country_risk_premium = 0.036  # Additional CRP

# Currency handling
if currency == "VND":
    # Convert to USD for modeling if needed
    # Apply VND inflation assumptions
    pass

# Sector-specific adjustments
if sector == "Banking":
    # Use Dividend Discount Model instead
    # Focus on ROE, NPL ratios, CAR
    pass
elif sector == "Real Estate":
    # Use NAV/RNAV methodology
    # Land bank valuation critical
    pass
```

---

## Workflow 4: Vietnamese Sector-Specific Models

### Banking Sector (Dividend Discount Model)
**File:** `app/engines/vietnam/sector_valuation_models.py:178`

```python
Input: BankingValuationInputs
  - Asset Quality: NPL ratio, LLR ratio, Cost of risk
  - Capital Adequacy: CAR ratio, Tier 1 capital
  - Profitability: ROA, ROE, NIM, CIR
  - Growth: Loan growth, Deposit growth
  - Dividends: Payout ratio, Dividend yield
  - Book Value: BVPS, Tangible book value

Process:
  1. DDM (Gordon Growth):
     - Sustainable growth = ROE × (1 - payout)
     - Cost of equity = Rf + β × ERP
     - DDM value = D1 / (r - g)
  
  2. Residual Income Model:
     - RI = (ROE - r) × Book Value
     - PV of RI over 5 years with fade
     - RIM value = BV + PV(RI)
  
  3. P/BV Relative:
     - Adjusted for ROE, NPL, CAR
     - Justified P/B = Peer avg + adjustments
  
  4. Blend: 40% DDM + 40% RIM + 20% P/B

Output: SectorValuationResult
  - Fair value (VND)
  - Upside/downside %
  - Recommendation (BUY/HOLD/SELL)
  - Sensitivity: ROE, NPL scenarios
```

### Real Estate Sector (NAV Model)
**File:** `app/engines/vietnam/sector_valuation_models.py:298`

```python
Input: RealEstateValuationInputs
  - Land Bank: Total area, Developable area, Land cost/sqm
  - Projects: Number, Under construction, Ready for sale
  - Sales: ASP/sqm, Pre-sales rate, Velocity
  - Financials: NAV/share, RNAV/share, D/E, Interest coverage
  - Pipeline: Future development value, Completion rate

Process:
  1. Basic NAV:
     - Land value = Area × Market price × 30%
     - NAV = Land value - Debt
  
  2. RNAV (Revalued NAV):
     - Apply discounts: Liquidity (25%), Execution (15%), Financing (5-10%)
     - RNAV = NAV × (1 - total discount)
  
  3. Pipeline Value:
     - Annual pipeline value / 5 years
     - Apply completion probability
     - Discount at 15% (development risk)
  
  4. Blend: 50% RNAV + 30% NAV + 20% Pipeline
  5. Apply market NAV multiple (typically 0.8x)

Output: SectorValuationResult
  - Fair value (VND)
  - NAV/sqm, RNAV/sqm breakdown
  - Risks: Legal delays, Pre-sales execution, Interest rates
```

### Manufacturing Sector (Commodity-Adjusted DCF)
**File:** `app/engines/vietnam/sector_valuation_models.py:404`

```python
Input: ManufacturingValuationInputs
  - Production: Capacity, Utilization, Actual production
  - Costs: Raw material, Energy, Labor per tonne
  - Pricing: ASP/tonne, Price realization vs market
  - Margins: EBITDA margin, Gross margin
  - Commodity Exposure: Iron ore, Coal, FX exposure
  - Capex: Maintenance, Expansion

Process:
  1. Standard DCF with commodity adjustments:
     - Link COGS to commodity prices (iron ore, coal)
     - Apply FX sensitivity (USD/VND)
     - Scenario analysis on commodity cycles
  
  2. Capacity utilization impact:
     - Fixed cost absorption at different utilization rates
     - Operating leverage effect on margins
  
  3. Commodity price scenarios:
     - Base case: Current forward curves
     - Bull case: +20% commodity prices
     - Bear case: -30% commodity prices

Output: SectorValuationResult
  - Fair value with commodity sensitivity
  - Break-even commodity prices
  - FX sensitivity analysis
```

---

## Workflow 5: PDF Extraction for Vietnamese Reports

### Endpoint Flow
```
POST /vietnamese-reports/search
    ↓
POST /vietnamese-reports/fetch
    ↓
POST /vietnamese-reports/auto-fetch-extract
```

### Step 1: Search Reports (`/vietnamese-reports/search`)
**File:** `vietnamese_reports_routes.py:34`
```python
Input: {ticker: "VNM", year: 2023, report_type: "annual"}
Process:
  1. VietnameseReportScraper.search_reports()
  2. Searches:
     - Company official website
     - HOSE/HNX portals
     - Cafef, Vietstock (fallback)
  3. Returns metadata without downloading
Output: {
  success: true,
  count: 3,
  reports: [
    {url, source, report_type, fiscal_year, file_size},
    ...
  ]
}
```

### Step 2: Fetch Report (`/vietnamese-reports/fetch`)
**File:** `vietnamese_reports_routes.py:76`
```python
Input: {ticker, year, report_type, extract_data: true}
Process:
  1. Search for reports
  2. Download first available report
  3. Optionally extract financial data using PDF extractor
  4. TT99-compliant extraction:
     - B01: Balance Sheet
     - B02: Income Statement
     - B03: Cash Flow Statement
Output: {
  success: true,
  file_path: "/tmp/reports/VNM_2023_annual.pdf",
  extraction: {
    success: true,
    data: {balance_sheet, income_statement, cash_flow}
  }
}
```

### Step 3: Auto-Fetch-Extract (`/vietnamese-reports/auto-fetch-extract`)
**File:** `vietnamese_reports_routes.py:141`
```python
Complete pipeline in one call:
  Search → Download → Extract → Return TT99 data

PDF Extraction Service: app/services/pdf_extraction_service.py
  - Uses pdfplumber for text extraction
  - Regex patterns for Vietnamese financial terms
  - Table detection for structured data
  - Validation against accounting equations
```

---

## Data Flow Diagram

```
User Request
    ↓
FastAPI Router (valuation_routes.py)
    ↓
Session Store (in-memory dict)
    ↓
┌─────────────────────────────────────┐
│  Step 6: Fetch Financial Data       │
│  ┌─────────────────────────────┐    │
│  │ Market = "international"    │    │
│  │   → yfinance.Ticker()       │    │
│  │   → info, financials        │    │
│  │                             │    │
│  │ Market = "vietnamese"       │    │
│  │   → yfinance.Ticker("VNM.VN")│   │
│  │   → +VietnameseTickerService│    │
│  │   → +VNINDEX, peers, FX     │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Step 7: Generate AI Assumptions    │
│  ┌─────────────────────────────┐    │
│  │ AI Engine                   │    │
│  │ - Historical trend analysis │    │
│  │ - Industry benchmarks       │    │
│  │ - Market conditions         │    │
│  │ - Rationale generation      │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Step 9: User Confirmation          │
│  - Review AI assumptions            │
│  - Manual overrides                 │
│  - Finalize inputs                  │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Step 10: Run Valuation Engine      │
│  ┌─────────────────────────────┐    │
│  │ Model = "dcf"               │    │
│  │   → DCFEngine               │    │
│  │   → WACC calculation        │    │
│  │   → Forecast schedules      │    │
│  │   → UFCF projection         │    │
│  │   → Discounting             │    │
│  │                             │    │
│  │ Model = "comps"             │    │
│  │   → CompsEngine             │    │
│  │   → Peer multiple analysis  │    │
│  │   → Outlier filtering       │    │
│  │   → Implied valuation       │    │
│  │                             │    │
│  │ Sector = "Banking" (VN)     │    │
│  │   → VNSectorValuationEngine │    │
│  │   → DDM + RIM + P/BV        │    │
│  │                             │    │
│  │ Sector = "Real Estate" (VN) │    │
│  │   → VNSectorValuationEngine │    │
│  │   → NAV + RNAV + Pipeline   │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
    ↓
Valuation Result Response
  - Enterprise Value
  - Equity Value
  - Per Share Value
  - Supporting Schedules
  - Sensitivity Analysis
```

---

## File Reference Summary

| Component | File Path | Purpose |
|-----------|-----------|---------|
| **Routes** | `backend/app/api/routes/valuation_routes.py` | Main valuation workflow endpoints |
| **Routes** | `backend/app/api/routes/international_routes.py` | International & Vietnamese ticker endpoints |
| **Routes** | `backend/app/api/routes/vietnamese_reports_routes.py` | Vietnamese PDF report automation |
| **Engines** | `backend/app/engines/dcf_engine.py` | DCF calculation engine |
| **Engines** | `backend/app/engines/comps_engine.py` | Comparable companies analysis |
| **Engines** | `backend/app/engines/vietnam/sector_valuation_models.py` | Vietnam sector-specific models |
| **Services** | `backend/app/services/yfinance_service.py` | Yahoo Finance data fetching |
| **Services** | `backend/app/services/vietnamese_ticker_service.py` | Vietnamese market data |
| **Services** | `backend/app/services/pdf_extraction_service.py` | TT99 PDF extraction |
| **Models** | `backend/app/models/international_cashflow_model.py` | International cash flow model |
| **Models** | `backend/app/models/vietnamese_cashflow_model.py` | Vietnamese cash flow model |
| **Core** | `backend/app/core/model_integrity.py` | Model validation |
| **Core** | `backend/app/core/exceptions.py` | Custom exceptions |

---

## Supported Markets

### International Markets
- **US**: No suffix (e.g., AAPL, MSFT)
- **Japan**: .T (e.g., 7203.T - Toyota)
- **UK**: .L (e.g., HSBA.L - HSBC)
- **Germany**: .DE (e.g., VOW3.DE - VW)
- **Canada**: .TO (e.g., RY.TO - RBC)
- **Australia**: .AX (e.g., CBA.AX - CommBank)

### Vietnamese Markets
- **HOSE**: .VN (e.g., VNM.VN - Vinamilk)
- **HNX**: .HA (e.g., ABC.HA)
- **UPCOM**: .VC (e.g., XYZ.VC)

---

## Key Features

1. **Dual Market Support**: Seamless handling of both international and Vietnamese markets
2. **Sector-Specific Models**: Specialized valuation for Banking, Real Estate, Manufacturing in Vietnam
3. **AI-Assisted Assumptions**: Machine learning-generated forecasts with rationale
4. **TT99 Compliance**: Vietnamese accounting standards for PDF extraction
5. **Multiple Valuation Methods**: DCF, Comps, DDM, NAV, RIM
6. **Comprehensive Outputs**: Full financial schedules, sensitivity analysis, football field charts
7. **Session Management**: Stateful workflow across multiple API calls
8. **Error Handling**: Robust exception handling with detailed error messages

---

## Testing the Workflow

### Example: International DCF Valuation

```bash
# 1. Select model
curl -X POST "http://localhost:8000/step-4-select-models" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test123", "model": "dcf"}'

# 2. Prepare inputs
curl -X POST "http://localhost:8000/step-5-prepare-inputs" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test123"}'

# 3. Fetch data
curl -X POST "http://localhost:8000/step-6-fetch-api-data" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test123", "ticker_symbol": "AAPL", "market": "international"}'

# 4. Generate AI assumptions
curl -X POST "http://localhost:8000/step-7-generate-ai-assumptions" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test123"}'

# 5. Confirm assumptions (with optional modifications)
curl -X POST "http://localhost:8000/step-9-confirm-assumptions" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test123", "confirmed_assumptions": {...}}'

# 6. Run valuation
curl -X POST "http://localhost:8000/step-10-valuate" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test123"}'
```

### Example: Vietnamese Banking Valuation

```bash
# Fetch enhanced Vietnamese data
curl -X GET "http://localhost:8000/vietnam/fetch-enhanced?ticker=VCB&market_code=VN&include_peers=true"

# The sector-specific model is automatically selected based on:
# - Market: vietnamese
# - Sector: Banking (detected from company profile)
# → Uses VNSectorValuationEngine.valuate_banking_stock()
```

---

This documentation provides a complete overview of how the backend valuation system works across different models and markets. Each workflow is self-contained but shares common infrastructure for data fetching, AI assistance, and calculation engines.
