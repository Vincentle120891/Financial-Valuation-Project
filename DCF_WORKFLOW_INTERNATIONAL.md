# DCF Model (International Market) - Complete 10-Step Workflow

This document traces the complete workflow for the **DCF Model** in the **International Market**, following the updated 10-step process from company search to valuation results.

---

## 🔄 The Complete 10-Step DCF Workflow

### Step 1: Search Company
**Endpoint:** `POST /api/step-1-search`  
**Frontend Component:** `SearchStep.jsx`  
**Backend Processor:** `Step1TickerProcessor`  
**File:** `/backend/app/services/international/step1_ticker_processor.py`

**Process:**
1. User enters ticker symbol or company name
2. System queries yfinance for matching companies
3. Returns list of results with symbols, names, and exchanges

**Request:**
```json
{
  "query": "Apple",
  "market": "international"
}
```

**Response:**
```json
{
  "results": [
    {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
    {"symbol": "APLE", "name": "Apple Hospitality REIT", "exchange": "NYSE"}
  ]
}
```

---

### Step 2: Company Overview
**Endpoint:** `POST /api/step-2-company-overview` (via selectCompany)  
**Frontend Component:** `CompanySelectionStep.jsx`  
**Backend:** Session creation  

**Process:**
1. User selects company from search results
2. Backend creates session with UUID
3. Fetches basic company information
4. Returns session_id for subsequent steps

**Session Data Created:**
```python
{
    "session_id": "uuid-here",
    "ticker": "AAPL",
    "market": "international",
    "company_name": "Apple Inc.",
    "status": "company_selected"
}
```

---

### Step 3: Peer Selection
**Endpoint:** `POST /api/step-3-suggest-peers`  
**Frontend Component:** `PeerSelectionStep.jsx`  
**Backend Service:** `PeerDiscoveryService`  
**File:** `/backend/app/services/international/peer_discovery_service.py`

**Process:**
1. AI analyzes company's sector, industry, and market cap
2. Suggests 10 peer companies with similarity scores
3. Auto-selects top 5 peers by default
4. User can modify selection

**Response:**
```json
{
  "peers": [
    {"symbol": "MSFT", "score": 0.95, "reason": "Same sector, similar market cap"},
    {"symbol": "GOOGL", "score": 0.89, "reason": "Tech giant, comparable metrics"},
    ...
  ]
}
```

---

### Step 4: Select Model
**Endpoint:** `POST /api/step-4-select-models`  
**Frontend Component:** `ModelSelectionStep.jsx`  
**Backend Route:** `valuation_routes.py:select_models()`  

**Process:**
1. User selects DCF model (single selection)
2. Backend validates model compatibility
3. Updates session with selected_model = "DCF"
4. Triggers Step 5 input preparation

**Request:**
```json
{
  "session_id": "uuid",
  "model": "DCF"
}
```

---

### Step 5: Review Requirements
**Endpoint:** `POST /api/step-5-prepare-inputs`  
**Frontend Component:** `RequirementsStep.jsx`  
**Backend Processor:** `Step5AssumptionsProcessor`  
**File:** `/backend/app/services/international/step5_assumptions_processor.py`

**Process:**
1. Processor defines required inputs for DCF model
2. Groups inputs by category:
   - Historical Financials (auto-fetched)
   - Market Data (auto-fetched)
   - Forecast Drivers (user input)
   - DCF Model Inputs (user input)
   - Peer Comparison (optional)

**Required Input Categories:**
```python
{
    "historical_financials": ["Revenue", "EBITDA", "Net Income", "CapEx", "Working Capital"],
    "market_data": ["Stock Price", "Shares Outstanding", "Beta", "Debt", "Cash"],
    "forecast_drivers": ["Revenue Growth", "Margins", "Tax Rate", "CapEx %"],
    "dcf_inputs": ["Risk-Free Rate", "ERP", "WACC", "Terminal Growth"],
    "peer_comparison": ["Peer Tickers", "Multiples"]
}
```

---

### Step 6: View Retrieved Inputs
**Endpoint:** `POST /api/step-6-fetch-api-data`  
**Frontend Component:** `ApiDataStep.jsx`  
**Backend Processor:** `Step6DataReviewProcessor`  
**File:** `/backend/app/services/international/step6_data_review.py`

**Process:**
1. Comprehensive data fetch from yfinance and Alpha Vantage
2. Retrieves:
   - Company profile and current market data
   - Historical income statements (3-5 years)
   - Historical balance sheets
   - Historical cash flow statements
   - Calculated metrics and ratios
3. Stores in session['financial_data']

**Data Retrieved:**
```python
{
    "profile": {
        "current_price": 178.75,
        "shares_outstanding": 15500000000,
        "beta": 1.28,
        "sector": "Technology",
        "industry": "Consumer Electronics"
    },
    "financials": {
        "revenue": {...},  # Last 5 years
        "ebitda": {...},
        "net_income": {...},
        "capex": {...},
        "working_capital": {...}
    },
    "ratios": {
        "gross_margin": 0.44,
        "operating_margin": 0.30,
        "roe": 1.47,
        "debt_to_equity": 1.73
    }
}
```

---

### Step 7: Historical Data Retrieval
**Endpoint:** `POST /api/step-7-fetch-historical-data`  
**Frontend Component:** `ApiDataStep.jsx` (extended)  
**Backend Processor:** `Step7HistoricalDataProcessor`  
**File:** `/backend/app/services/international/step7_historical_data.py`

**Process:**
1. Identifies data gaps not available via standard APIs (yfinance/AlphaVantage)
2. Uses AI to extract missing historical data from PDF filings, annual reports, and alternative sources
3. **AI is used specifically for data extraction** from documents that APIs cannot access
4. No forward-looking inputs are generated here - strictly historical data retrieval

**Data Retrieved:**
```python
{
    "missing_historical_data": {
        # Additional historical metrics extracted using AI from documents
    },
    "data_sources": ["PDF_filings", "annual_reports", "alternative_sources"]
}
```

---

### Step 8: Assumption & AI Suggestion
**Endpoint:** `POST /api/step-8-generate-ai-assumptions`  
**Frontend Component:** `ForecastDriversStep.jsx` / `AssumptionsStep.jsx`  
**Backend Processor:** `Step8AssumptionProcessor`  
**File:** `/backend/app/services/international/step8_assumption_processor.py`

**Process:**
1. Calculates values programmatically based on historical trends
2. AI engine (Gemini/Groq) generates suggestions for forward-looking inputs:
   - Revenue growth rates
   - Margin assumptions
   - Capex projections
   - Working capital days
   - Terminal value assumptions
   - WACC components
3. Provides confidence scores and rationale
4. Falls back to deterministic calculations if AI fails

**AI Output:**
```json
{
  "equity_risk_premium": {
    "value": 0.055,
    "rationale": "Based on historical market returns and current market conditions",
    "confidence": "high"
  },
  "country_risk_premium": {
    "value": 0.02,
    "rationale": "Additional premium for emerging market exposure",
    "confidence": "medium"
  },
  "terminal_growth_rate": {
    "value": 0.025,
    "rationale": "Aligned with long-term GDP growth expectations",
    "confidence": "high"
  },
  "terminal_ebitda_multiple": {
    "value": 10.0,
    "rationale": "Based on sector peer analysis and industry standards",
    "confidence": "medium"
  }
}
```

**Vietnam-Specific Considerations:**
For Vietnamese companies, AI adjusts suggestions for emerging market factors:
- Higher ERP (6-8%) reflecting VNINDEX volatility
- CRP (2-5%) for VND currency risk and institutional factors
- Terminal growth aligned with Vietnam GDP (~5-6%)
- Lower terminal multiples (8-12x) due to liquidity discount

---

### Step 9: Modify Forecast Drivers
**Frontend Component:** `ForecastDriversStep.jsx`  
**Backend Processor:** `Step9ManualOverridesProcessor`  
**File:** `/backend/app/services/international/step9_manual_overrides.py`

**Process:**
1. User reviews AI-suggested assumptions from Step 8
2. Can manually override any values
3. Adjust scenario settings (Bull/Base/Bear)
4. System validates input ranges

**User Actions:**
- Edit growth rates
- Modify margin assumptions
- Change terminal value inputs
- Select scenario preset

---

### Step 9: Modify Forecast Drivers
**Frontend Component:** `ForecastDriversStep.jsx`  
**Backend Processor:** `Step9ManualOverridesProcessor`  
**File:** `/backend/app/services/international/step9_manual_overrides.py`

**Process:**
1. User reviews AI-suggested assumptions from Step 8
2. Can manually override any values
3. Adjust scenario settings (Bull/Base/Bear)
4. System validates input ranges

**User Actions:**
- Edit growth rates
- Modify margin assumptions
- Change terminal value inputs
- Select scenario preset

---

### Step 10: Confirm Assumptions
**Endpoint:** `POST /api/step-9-confirm-assumptions`  
**Frontend Component:** `AssumptionsStep.jsx`  
**Backend Processor:** `Step9ManualOverridesProcessor`  
**File:** `/backend/app/services/international/step9_manual_overrides.py`

**Process:**
1. Final review of all assumptions
2. User confirms or makes final adjustments
3. Backend stores confirmed_assumptions in session
4. Validates completeness before proceeding

**Confirmed Assumptions Structure:**
```python
{
    "revenue_growth": [...],
    "ebitda_margin": [...],
    "tax_rate": 0.21,
    "wacc": 0.089,
    "terminal_growth": 0.025,
    "scenario": "base_case"
}
```

---

### Step 11: Run Valuation
**Endpoint:** `POST /api/step-10-valuate`  
**Frontend Component:** `RunValuationStep.jsx`  
**Backend Processor:** `Step10ValuationProcessor`  
**File:** `/backend/app/services/international/step10_valuation_processor.py`

**Process:**
1. Retrieves confirmed assumptions from session
2. Initializes DCFEngine with inputs
3. Executes comprehensive DCF calculation:
   - Calculate WACC from CAPM components
   - Build revenue schedule (volume × price)
   - Build COGS and OpEx schedules
   - Calculate depreciation (existing + new)
   - Build working capital schedule
   - Calculate unlevered free cash flow
   - Discount cash flows to present value
   - Calculate terminal value (perpetuity + exit multiple)
   - Derive equity value and per-share price
4. Returns comprehensive valuation result

**Valuation Output:**
```json
{
  "enterprise_value": 2850000000000,
  "equity_value": 2750000000000,
  "equity_value_per_share": 185.50,
  "current_market_price": 178.75,
  "upside_downside": "3.79%",
  "recommendation": "BUY",
  "wacc": 0.089,
  "terminal_value": 2100000000000,
  "supporting_schedules": {...}
}
```

---

### Step 11: View Results
**Frontend Component:** `ResultsStep.jsx`  
**Display:**
- Implied share price vs. current market price
- Upside/downside percentage
- Buy/Hold/Sell recommendation
- Sensitivity analysis matrix (WACC vs Terminal Growth)
- Scenario comparison (Bull/Base/Bear)
- Historical vs. projected metrics charts
- Audit trail showing data sources

---

## 🔧 DCF Engine Deep Dive

### File: `/backend/app/engines/dcf_engine.py`

**Key Calculation Methods:**

```python
class DCFEngine:
    def calculate_wacc(self):
        """Calculate weighted average cost of capital"""
        # Cost of Equity = Rf + β × ERP
        # Cost of Debt = Interest Rate × (1 - Tax Rate)
        # WACC = (E/V × Re) + (D/V × Rd × (1-T))
        
    def _build_revenue_schedule(self):
        """Project revenue using volume and price growth"""
        # Revenue[t] = Revenue[t-1] × (1 + Volume Growth) × (1 + Price Growth)
        
    def _build_depreciation_schedule(self):
        """Calculate depreciation on existing and new assets"""
        # Existing Asset Depreciation
        # New Capex Depreciation (straight-line over useful life)
        
    def _build_working_capital_schedule(self):
        """Project working capital based on days outstanding"""
        # AR = Revenue × AR Days / 365
        # Inventory = COGS × Inv Days / 365
        # AP = COGS × AP Days / 365
        
    def _calculate_ufcf(self):
        """Calculate unlevered free cash flow"""
        # UFCF = EBITDA - Tax - CapEx - ΔNWC
        
    def _discount_cash_flows(self):
        """Discount projected cash flows to present value"""
        # PV = Σ (FCF[t] / (1+WACC)^t)
        # Terminal Value = FCF[n+1] / (WACC - g)
        
    def run_valuation(self):
        """Execute complete DCF valuation"""
        # Returns: enterprise_value, equity_value, per_share_value
```

---

## 📊 Data Flow Summary

```
┌─────────────┐
│ Step 1      │ Search: AAPL
│ Search      │
└──────┬──────┘
       ↓
┌─────────────┐
│ Step 2      │ Create Session, Get Company Info
│ Overview    │
└──────┬──────┘
       ↓
┌─────────────┐
│ Step 3      │ Suggest Peers: MSFT, GOOGL, etc.
│ Peer Select │
└──────┬──────┘
       ↓
┌─────────────┐
│ Step 4      │ Select DCF Model
│ Model       │
└──────┬──────┘
       ↓
┌─────────────┐
│ Step 5      │ Show Required Inputs
│ Requirements│
└──────┬──────┘
       ↓
┌─────────────┐
│ Step 6      │ Fetch: Financials, Market Data, Ratios
│ Fetch Data  │
└──────┬──────┘
       ↓
┌─────────────┐
│ Step 7      │ Fetch: Missing Historical Data (AI Extraction)
│ Hist. Data  │ from PDFs/Reports
└──────┬──────┘
       ↓
┌─────────────┐
│ Step 8      │ Generate: AI Suggestions for Assumptions
│ AI Suggest  │
└──────┬──────┘
       ↓
┌─────────────┐
│ Step 10     │ Confirm All Assumptions
│ Confirm     │
└──────┬──────┘
       ↓
┌─────────────┐
│ Step 11     │ Execute DCF Engine
│ Valuation   │ → Enterprise Value, Equity Value, Share Price
└──────┬──────┘
       ↓
┌─────────────┐
│ Step 12     │ View Results
│ Results     │
└─────────────┘
```

---

## ✅ Model Integrity Notice

This workflow maintains complete model transparency:
- All inputs are visible and editable
- All calculations follow standard financial methodologies
- All outputs include audit trails with source attribution
- No simplifications or hidden assumptions
- **Step 7**: Collects historical data from non-API sources (NO AI)
- **Step 8**: AI suggests ONLY 4 forward-looking assumptions for DCF (ERP, CRP, Terminal Growth, Terminal Multiple)
- **DuPont/Comps**: 100% calculated, NO AI involvement

*Last Updated: Reflects updated workflow with Step 7 (Historical Data Collection) and Step 8 (AI Assumptions Generation)*
