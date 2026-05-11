# Backend Valuation Workflow Documentation

## ⚠️ CRITICAL DEVELOPER WARNING: AI TOOL LIMITATIONS

**READ BEFORE MODIFYING CODE:**

We are utilizing **AI tools** for valuation logic generation (Steps 7-9). This architecture has strict constraints to prevent failures:

### 🚫 DO NOT RUN MULTIPLE MODELS IN PARALLEL
- **Reason:** Parallel execution causes **context hallucination**, **state race conditions**, and **data corruption** in AI processing.
- **Rule:** Users must select **ONE model at a time** to complete the full valuation flow.
- **Implementation:** Step 4 uses **Radio Buttons** (single-select), NOT checkboxes.
- **Enforcement:** Steps 7-9 (AI Generation) run **sequentially** for the active model only.

### ✅ CORRECT WORKFLOW: "Fetch Once, Use Many"
1. **Unified Data Fetching (Step 6):** When a market is selected, fetch **ALL market data** needed for ANY model in one API call.
2. **Shared Cache:** Store data in `session['international_market_data']`.
3. **Model-Specific Slicing:** 
   - User selects DCF → System slices DCF-relevant data from cache
   - User switches to DuPont → System reuses SAME cached data (NO re-fetch)
4. **Benefit:** Eliminates redundant API calls, prevents rate limiting, ensures data consistency.

**See [WORKFLOW_ARCHITECTURE.md](./WORKFLOW_ARCHITECTURE.md) for complete architectural guidelines.**

---

## Overview

This document describes the complete workflow of the backend valuation system, showing how different valuation models work across international and Vietnamese markets using an 11-step guided process.

### Model & Market Architecture

**3 Distinct Models:**
- **DCF (Discounted Cash Flow)**: Intrinsic value based on projected free cash flows with rigorous WACC calculation from peer analysis
- **DuPont Analysis**: ROE decomposition into profit margin, asset turnover, and leverage components  
- **Trading Comps**: Relative valuation using peer company multiples with statistical analysis

**Market Segregation:**
- **International Market**: Uses yfinance/AlphaVantage APIs with standard GAAP/IFRS accounting
- **Vietnamese Market**: Separate input managers and calculation engines to handle local GAAP/regulatory differences (e.g., TT99 for Vietnam), VND currency, and .VN ticker suffixes

**AI Usage Clarification:**
- **Step 7 (Historical Data Retrieval)**: Uses AI specifically to extract historical data that standard APIs (yfinance/AlphaVantage) cannot provide - such as data from PDF filings, annual reports, and alternative sources
- **Step 8 (Assumption & AI Suggestion)**: AI provides suggestions for forward-looking inputs (growth rates, margins, terminal values, etc.), but all calculations remain rigorous and programmatically verified

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
│  │step1-10_     ││vietnamese_   │ │pdf_extraction_           │ │
│  │processors.py ││ticker_service│ │service.py                │ │
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

## The 11-Step Workflow

### Step 1: Search Company
**Endpoint:** `POST /api/step-1-search`
**Processor:** `Step1TickerProcessor`
**Description:** User searches for company by ticker or name
**Output:** List of matching companies with symbols and exchanges

### Step 2: Company Overview
**Endpoint:** `POST /api/step-2-company-overview` (via selectCompany)
**Processor:** Session creation with basic company info
**Description:** Display selected company details and create session
**Output:** Session ID and company information

### Step 3: Peer Selection
**Endpoint:** `POST /api/step-3-suggest-peers`
**Processor:** `PeerDiscoveryService`
**Description:** AI suggests peer companies with scoring, auto-select top 5
**Output:** List of suggested peers with similarity scores

### Step 4: Select Model
**Endpoint:** `POST /api/step-4-select-models`
**Processor:** Session update
**Description:** User selects valuation model (DCF/DuPont/Comps)
**Output:** Confirmation and next step direction

### Step 5: Review Requirements
**Endpoint:** `POST /api/step-5-prepare-inputs`
**Processor:** `Step5AssumptionsProcessor`
**Description:** Display required inputs for selected model
**Output:** List of required input fields with categories

### Step 6: View Retrieved Inputs
**Endpoint:** `POST /api/step-6-fetch-api-data`
**Processor:** `Step6DataReviewProcessor`
**Description:** Fetch all financial data from yfinance/Alpha Vantage
**Output:** Complete financial data including historicals, market data, and metrics

### Step 7: Historical Data Retrieval
**Endpoint:** `POST /api/step-7-fetch-historical-data`
**Processor:** `Step7HistoricalDataProcessor`
**Description:** Fetch historical data that cannot be retrieved via standard APIs (yfinance/AlphaVantage). Uses AI to extract data from PDF filings, annual reports, and alternative sources.
**Output:** Missing historical financial data extracted using AI from documents and alternative sources

### Step 8: Assumption & AI Suggestion
**Endpoint:** `POST /api/step-8-generate-ai-assumptions`
**Frontend:** `ForecastDriversStep` / `AssumptionsStep`
**Processor:** `Step8AssumptionProcessor`
**Description:** Dedicated phase for assumptions. Calculates values programmatically and utilizes AI for suggestions on forward-looking inputs. This is where forward-looking inputs are finalized before confirmation.
**Output:** AI-generated assumption suggestions with confidence scores and rationale, plus programmatically calculated values

### Step 9: Confirm Assumptions
**Endpoint:** `POST /api/step-9-confirm-assumptions`
**Processor:** `Step8ManualOverridesProcessor`
**Description:** Final review and confirmation of all assumptions
**Output:** Confirmed assumptions stored in session

### Step 10: Run Valuation
**Endpoint:** `POST /api/step-10-valuate`
**Processor:** `Step10ValuationProcessor`
**Description:** Execute selected valuation engine (DCF/DuPont/Comps)
**Output:** Comprehensive valuation results

### Step 11: View Results
**Frontend:** `ResultsStep`
**Description:** Display valuation output with charts, sensitivity analysis, and recommendations

---

## Service Processor Architecture

The backend uses a modular service processor pattern where each step has a dedicated processor class:

### International Market Processors (`/backend/app/services/international/`)

| Processor | File | Purpose |
|-----------|------|---------|
| Step1TickerProcessor | `step1_ticker_processor.py` | Handle company search and ticker validation |
| Step2MarketDataProcessor | `step2_market_data_processor.py` | Fetch current market data and company profile |
| Step3HistoricalProcessor | `step3_historical_processor.py` | Retrieve historical financial statements |
| Step4ForecastProcessor | `step4_forecast_processor.py` | Build forecast driver templates |
| Step5AssumptionsProcessor | `step5_assumptions_processor.py` | Define required inputs per model |
| Step6DataReviewProcessor | `step6_data_review.py` | Comprehensive data fetching and validation |
| Step7HistoricalDataProcessor | `step7_historical_data.py` | Fetch missing historical data from alternative sources (NO AI) |
| Step8AssumptionProcessor | `step8_assumption_processor.py` | Calculate assumptions programmatically and generate AI suggestions for forward-looking inputs |
| Step9FinalCalculation | `step9_final_calculation.py` | Pre-calculation validation and preparation |
| Step10ValuationProcessor | `step10_valuation_processor.py` | Execute valuation engines |

### Vietnamese Market Services (`/backend/app/services/vietnamese/`)

| Service | File | Purpose |
|---------|------|---------|
| VietnamTickerService | `vietnamese_ticker_service.py` | Handle .VN ticker suffixes and local data |
| VietnamDataAggregator | `vietnam_data_aggregator.py` | Aggregate VND financial data |
| VietnameseDCFEngine | `vietnamese_dcf_engine.py` | DCF with Vietnam-specific adjustments |
| SectorValuationModels | `sector_valuation_models.py` | Banking, Real Estate, Manufacturing models |

---

## Valuation Engines

### DCF Engine
**File:** `/backend/app/engines/dcf_engine.py`
**Purpose:** Calculate intrinsic value using discounted cash flow methodology
**Key Methods:**
- `calculate_wacc()` - Weighted average cost of capital
- `_build_revenue_schedule()` - Volume × price growth projection
- `_build_depreciation_schedule()` - Existing + new asset depreciation
- `_calculate_ufcf()` - Unlevered free cash flow calculation
- `_discount_cash_flows()` - PV calculation with terminal value

### DuPont Engine
**File:** `/backend/app/engines/dupont_engine.py`
**Purpose:** Decompose ROE into component drivers
**Key Outputs:**
- Profit Margin
- Asset Turnover
- Financial Leverage
- Tax Burden
- Interest Burden

### Comps Engine
**File:** `/backend/app/engines/comps_engine.py`
**Purpose:** Relative valuation using peer company multiples
**Key Methods:**
- `calculate_peer_multiples()` - Fetch and calculate peer metrics
- `apply_outlier_filtering()` - IQR-based outlier removal
- `calculate_statistics()` - Mean, median, percentiles
- `create_football_field()` - Valuation range visualization

---

## Data Flow Example: DCF Valuation

```
User Input → Step1 Search → Step2 Company Overview → Step3 Peer Selection
                                                    ↓
                                        Step4 Select DCF Model
                                                    ↓
                                    Step5 Review Required Inputs
                                                    ↓
                                  Step6 Fetch Financial Data
                                                    ↓
                                  Step7 Collect Historical Data
                                                    ↓
                                    Step8 Generate AI Assumptions
                                                    ↓
                                    Step9 Confirm Assumptions
                                                    ↓
                                      Step10 Run DCF Engine
                                                    ↓
                                      Step11 View Results
```

---

## Session Management

All workflow state is managed through `SessionService` (`/backend/app/core/session_service.py`):

- **Session Creation:** Step 2 (Company Overview)
- **Session Updates:** Each step stores its output
- **Session Retrieval:** Processors access previous step data
- **Session Cleanup:** After valuation completion or timeout

### Session Data Structure
```python
{
    "session_id": "uuid",
    "ticker": "AAPL",
    "market": "international",
    "company_name": "Apple Inc.",
    "peer_tickers": ["MSFT", "GOOGL", ...],
    "selected_model": "DCF",
    "financial_data": {...},  # From Step 6
    "historical_data": {...},  # From Step 7 (missing historical data)
    "ai_suggestions": {...},  # From Step 8 (AI assumption suggestions)
    "confirmed_assumptions": {...},  # From Step 9
    "valuation_result": {...},  # From Step 10
    "status": "valuation_complete"
}
```

---

## Error Handling

Each processor implements comprehensive error handling:

1. **Data Validation:** Pydantic models validate all inputs
2. **API Fallbacks:** Multiple data sources (yfinance → Alpha Vantage)
3. **AI Fallbacks:** Gemini → Groq → Deterministic calculations
4. **Graceful Degradation:** Missing data flagged but doesn't block workflow

---

## Integration Points

### External APIs
- **yfinance:** Primary source for international market data
- **Alpha Vantage:** Secondary source for financial statements
- **Groq/Gemini:** AI assumption generation

### Internal Services
- **SessionService:** Centralized session state management
- **LoggingConfig:** Structured logging throughout workflow
- **Schemas:** Pydantic models for request/response validation

---

*Last Updated: Reflects 11-step workflow architecture*
