--- frontend/ARCHITECTURE.md (原始)


+++ frontend/ARCHITECTURE.md (修改后)
# Frontend Architecture - Financial Valuation Platform

## ⚠️ CRITICAL DEVELOPMENT GUIDELINES

### 1. Market Separation (DO NOT MERGE MARKETS)
**NEVER create "Generic Displayer" components that merge Vietnamese and International markets.**

- **Why?** Fundamental differences exist:
  - **Accounting Standards:** VAS/TT99 (Vietnam) vs IFRS/US GAAP (International)
  - **Currency:** VND vs USD with different formatting rules and magnitudes (VND is ~25,000x USD)
  - **Market Mechanics:** Foreign ownership limits, board types (HOSE/HNX/UPCoM), trading mechanisms
  
- **Correct Approach:**
  - **Keep Separate:** `VietnameseMarketData.jsx` and `InternationalMarketData.jsx` must remain separate
  - **No Generic Components:** Do not create unified displayers that force lowest-common-denominator schemas
  - **Service Layer Only:** Use `UnifiedTransformer` services ONLY for temporary normalization during peer comparison

### 2. Component Responsibilities
**UI components should ONLY display data, not process it.**

- **Violation Example:** Components fetching API data directly or containing business logic
- **Correct Pattern:**
  ```jsx
  // ❌ WRONG - Component handling logic
  function MarketDataDisplay({ ticker }) {
      const data = await fetch(`/api/market-data/${ticker}`); // Don't do this!
      const processed = calculateMetrics(data); // Don't do this!
      ...
  }
  
  // ✅ CORRECT - Component only displays
  function MarketDataDisplay({ data }) {
      return <div>{data.companyName}</div>;
  }
  ```

- **Files to Check:**
  - `ValuationFlow.jsx` - Should orchestrate steps, not process data
  - Market-specific components - Should only render passed props

### 3. Workflow Step Integrity
**Component names and step rendering MUST match backend workflow steps.**

| Step | Purpose | Frontend Component | Backend Endpoint |
|------|---------|-------------------|------------------|
| **3** | Peer Company Selection | `PeerSelectionStep.jsx` | `/step-3-save-peers` |
| **4** | Model Selection (DCF/DuPont/Comps) | Radio buttons in `ValuationFlow.jsx` | `/step-4-select-models` |
| **5** | Required Inputs Display | `RequirementsStep.jsx` | `/step-5-prepare-inputs` |

- **Rule:** Step 5 should ONLY show required inputs list, NOT retrieved data tables (that's Step 6)

### 4. Single Model Execution
**Step 4 uses Radio Buttons (single-select) to prevent AI context corruption.**

- **Never** allow multiple models to run in parallel through Steps 7-9
- **Reason:** Parallel execution causes context hallucination and state race conditions in AI processing
- **Implementation:** Radio buttons enforce one model at a time

---

## Overview
Complete React-based frontend for DCF, DuPont Analysis, and Trading Comps valuation models with AI-powered data retrieval and assumption generation.

## Technology Stack
- **Framework**: React 18 with Vite
- **Styling**: Custom CSS with responsive design
- **HTTP Client**: Axios
- **State Management**: React Hooks (useState, useEffect)
- **Build Tool**: Vite 5.4.21

## File Structure
```
frontend/
├── index.html                 # Entry point
├── package.json              # Dependencies
├── vite.config.js           # Build configuration
├── src/
│   ├── index.jsx            # React entry point
│   ├── index.css            # Global styles
│   ├── components/
│   │   └── ValuationFlow.jsx    # Main component (900+ lines)
│   └── services/
│       └── api.js           # API service layer
└── build/                   # Production build output
```

## Component Architecture

### ValuationFlow.jsx - Main Component

**State Management** (30+ state variables):
- `currentStep`: Tracks user progress through 11-step workflow
- `selectedModel`: 'DCF', 'DuPont', or 'Comps' (single-select via radio buttons)
- `market`: 'international' or 'vietnamese' (determines data sources & calculation engines)
- `searchResults`: Company search results from Step 1
- `historicalData`: 3-8 years of financial history
- `forecastDrivers`: Best/Base/Worst case scenarios
- `peerData`: Comparable company analysis
- `dupontResults`: DuPont decomposition outputs
- `compsResults`: Trading comps multiples
- `missingData`: Retrieved historical data gaps from alternative sources
- `confirmedValues`: User-confirmed assumptions
- `valuationsData`: Matrix storing results for all 6 combinations [market][method]

**11-Step Workflow**:

1. **Step 1 - Search Company** (`renderStep1`)
   - Market toggle: International vs Vietnamese
   - Ticker/company name search
   - Real-time search results display

2. **Step 2-3 - Company Selection** (handled in `handleSelectCompany`)
   - API call to `/step-3-select-ticker`
   - Session initialization with market-specific data

3. **Step 4 - Model Selection** (`renderStep4`)
   - Three model cards: DCF, DuPont, Comps
   - **Radio buttons** (single-select only - prevents AI context corruption)
   - Detailed descriptions for each model

4. **Step 5 - Required Inputs** (`renderStep5`)
   - Dynamic requirements based on selected model
   - Data requirement summaries
   - "Change Model" back button

5. **Step 6 - Fetch API Data** (`handleFetchApiData`)
   - **Fetch Once, Use Many**: Single API call fetches ALL data for ANY model
   - Data stored in shared cache `session['market_data']`
   - Populates historicalData with standard API data

6. **Step 7 - Historical Data Retrieval** (`handleFetchHistoricalData`)
   - API call to `/step-7-fetch-historical-data` (missing historical data from alternative sources)
   - **Uses AI to extract data** from PDF filings, annual reports, and documents that APIs cannot access
   - Displays retrieved historical data in UI with source attribution

7. **Step 8 - Assumption & AI Suggestion** (`handleGenerateAiAssumptions`)
   - API call to `/step-8-generate-ai-assumptions` (AI suggestions for forward-looking inputs)
   - Renders AI suggestion interface for assumptions
   - Interactive table with:
     - AI suggestions with confidence scores
     - Rationale & sources display
     - Manual input fields
     - Confirm/Use AI buttons
   - Model-specific: DCF/DuPont/Comps each have unique assumption processors

8. **Step 9 - Assumptions Confirmation** (`renderStep9`)
   - Scenario selection (Best/Base/Worst)
   - Summary of all confirmed inputs
   - "Run Valuation" trigger

9. **Step 10 - Run Valuation** (`runValuation`)
   - Executes selected model with confirmed assumptions
   - Market-specific engine (international/vietnamese)
   - Returns comprehensive valuation output

10. **Step 11 - Results Display** (`renderStep10`)
    - Model-specific result rendering
    - Charts and visualizations
    - Export options
    - Currency formatting (USD/VND)

## API Integration (api.js)

**Core Endpoints**:
```javascript
// Search & Selection
searchCompanies(query, market)           // POST /step-1-search
selectCompany(sessionId, ticker, market) // POST /step-3-select-ticker
selectModels(sessionId, models)          // POST /step-4-select-models

// Data Preparation - Fetch Once, Use Many
prepareInputs(sessionId)                 // POST /step-5-6-prepare-inputs
fetchApiData(sessionId)                  // POST /step-6-fetch-api-data (ALL data for ANY model)
fetchHistoricalData(sessionId)           // POST /step-7-fetch-historical-data

// Assumption Generation (Model-Specific)
generateAI(sessionId, model)             // POST /step-8-generate-ai-assumptions (DCF/DuPont/Comps specific)

// Valuation Execution
confirmAssumptions(sessionId, assumptions, scenario) // POST /step-9-confirm-assumptions
runValuation(sessionId, model, market, scenario)     // POST /step-10-valuate

// Specialized Endpoints
getDcfInputs(sessionId)                  // POST /dcf/inputs
getPeerData(sessionId, minPeers)         // POST /comps/peers
getDupontAnalysis(sessionId, years)      // POST /dupont/analyze
getForecastBenchmarks(sessionId)         // POST /forecast/benchmarks

// Market-Specific Routes
getInternationalMarketData(ticker)       // GET /international/*
getVietnameseMarketData(ticker)          // GET /vietnamese/*
```

**Dual-Market Support:**
- International routes: `/international/valuate`, `/international/comps`, `/international/dupont`
- Vietnamese routes: `/vietnamese/vn-valuate`, `/vietnamese/vn-comps`, `/vietnamese/vn-dupont`
- Market parameter determines which engine and data sources are used

## DuPont-Specific Features

### State Variables
```javascript
const [dupontResults, setDupontResults] = useState(null);
```

### Data Flow
1. **Step 6**: Fetches DuPont ratios via `/step-6-fetch-api-data`
   ```javascript
   if (fetchApiData.data.dupont_ratios) {
     setDupontResults(fetchApiData.data.dupont_ratios);
   }
   ```
2. **Step 7**: Retrieves missing historical data via `/step-7-generate-ai-assumptions`
3. **Step 8**: User modifies forecast drivers manually

2. **Step 10**: Displays DuPont results
   ```javascript
   {selectedModel === 'DuPont' && valuationResults.dupont_outputs && (
     <div className="results-section">
       <h3>DuPont Analysis Summary</h3>
       {/* ROE Decomposition */}
       <div className="metric-row">
         <span>ROE</span>
         <span>{(valuationResults.dupont_outputs.roe_latest * 100).toFixed(1)}%</span>
       </div>
       {/* 3-Step Components */}
       <div className="metric-row">
         <span>Net Profit Margin</span>
         <span>{(valuationResults.dupont_outputs.net_margin_latest * 100).toFixed(1)}%</span>
       </div>
       <div className="metric-row">
         <span>Asset Turnover</span>
         <span>{valuationResults.dupont_outputs.asset_turnover_latest.toFixed(2)}x</span>
       </div>
       <div className="metric-row">
         <span>Equity Multiplier</span>
         <span>{valuationResults.dupont_outputs.equity_multiplier_latest.toFixed(2)}x</span>
       </div>
       {/* Trend Analysis */}
       {valuationResults.dupont_outputs.trends && (...)}
     </div>
   )}
   ```

### Expected API Response Format
```json
{
  "dupont_outputs": {
    "roe_latest": 0.214,
    "net_margin_latest": 0.057,
    "asset_turnover_latest": 1.12,
    "equity_multiplier_latest": 3.38,
    "trends": {
      "years": [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
      "roe": [0.12, 0.14, 0.16, 0.18, 0.15, 0.19, 0.21, 0.214],
      "net_margin": [0.03, 0.04, 0.045, 0.05, 0.04, 0.05, 0.055, 0.057],
      "asset_turnover": [1.05, 1.08, 1.10, 1.12, 1.09, 1.11, 1.12, 1.12],
      "equity_multiplier": [3.2, 3.25, 3.3, 3.35, 3.4, 3.38, 3.38, 3.38]
    },
    "dupont_check_3step": "OK",
    "dupont_check_5step": "OK"
  }
}
```

## UI/UX Features

### Design Elements
- **Model Cards**: Clickable cards with hover effects for model selection
- **Summary Boxes**: Highlighted sections for key metrics
- **Data Tables**: Enhanced tables with sortable columns
- **Rationale Cells**: Expandable AI explanation sections
- **Progress Indicators**: Step-by-step workflow visualization
- **Loading States**: Spinner animations during API calls
- **Error Handling**: User-friendly error messages

### Responsive Design
- Grid layouts for metric displays
- Mobile-friendly table scrolling
- Adaptive button sizing
- Flexible container widths

## Build & Deployment

### Development
```bash
cd frontend
npm install
npm run dev    # Starts Vite dev server on port 5173
```

### Production Build
```bash
npm run build  # Outputs to /build directory
```

**Build Output** (verified):
```
build/index.html                   0.62 kB │ gzip:  0.35 kB
build/assets/index-C4q2hKH4.css    6.67 kB │ gzip:  1.87 kB
build/assets/index-CLP28rLk.js   167.45 kB │ gzip: 51.02 kB
```

### Environment Configuration
- Default API URL: `http://localhost:8000/api`
- Override via `REACT_APP_API_URL` environment variable

## Integration Points

### Backend Requirements
1. **Session Management**: Maintain state across 11-step workflow
2. **Multi-Model Support**: Handle DCF, DuPont, and Comps in single session (one at a time)
3. **Dual-Market Architecture**: Separate engines for International (IFRS/GAAP) and Vietnamese (TT99) markets
4. **AI Integration**: Generate suggestions with rationale and confidence scores (model-specific processors)
5. **Historical Data**: Provide 3-8 years of financial statements
6. **Peer Analysis**: Automatic comparable company identification (market-specific logic)
7. **Scenario Planning**: Best/Base/Worst case support
8. **Fetch Once, Use Many**: Unified data caching to prevent redundant API calls
9. **Currency Formatting**: USD for international, VND for Vietnamese valuations
10. **PDF Extraction**: AI-powered extraction for Vietnamese annual reports

### Data Validation
- Array parsing for multi-period inputs (e.g., "0.05, 0.04, 0.03")
- Percentage conversion for display (multiply by 100)
- Decimal formatting for ratios (2 decimal places)
- Null/undefined handling with fallback values

## Testing Checklist

✅ **Build Verification**: Production build completes successfully
✅ **Component Structure**: All render functions defined (11 steps)
✅ **State Management**: All required state variables initialized (including valuationsData matrix)
✅ **API Integration**: All endpoint functions implemented with dual-market support
✅ **DuPont Support**: Specific handlers for DuPont data
✅ **Comps Support**: Trading comparables with market-specific peer filtering
✅ **DCF Support**: Full DCF workflow with WACC calculation
✅ **Market Separation**: International and Vietnamese routes properly isolated
✅ **Single-Select Enforcement**: Radio buttons prevent multiple model selection
✅ **Fetch Once, Use Many**: Data caching prevents redundant API calls
✅ **Error Handling**: Try-catch blocks around async operations
✅ **Loading States**: Loading indicators for all async actions
✅ **Responsive Design**: CSS grid and flexbox layouts
✅ **Currency Formatting**: USD/VND display based on market selection

## Future Enhancements

1. **Chart Integration**: Add Recharts or Chart.js for visualization
2. **Export Functionality**: PDF/Excel report generation
3. **Real-time Updates**: WebSocket for live data streaming
4. **Advanced Scenarios**: Sensitivity analysis tables
5. **Comparison Mode**: Side-by-side company comparison
6. **User Authentication**: Save sessions and portfolios

---

**Last Updated**: 2025
**Version**: 2.0 - Dual-Market Architecture
**Status**: Production Ready
**Workflow**: 3 Valuation Methods × 2 Market Versions (6 combinations)
**Critical Requirements**: 
- Single model selection (radio buttons) to prevent AI context corruption
- Fetch Once, Use Many caching strategy
- No input/calculation simplification (model integrity commitment)
- Strict market separation (International vs Vietnamese)