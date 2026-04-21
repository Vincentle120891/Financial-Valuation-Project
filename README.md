# Financial Valuation Project - 10-Step Valuation Flow

## Overview

This project implements a comprehensive **10-Step Valuation Flow** for financial analysis, supporting multiple valuation methodologies including:

- **DCF (Discounted Cash Flow)**: Intrinsic value based on projected free cash flows
- **Trading Comps**: Relative valuation using peer company multiples
- **DuPont Analysis**: ROE decomposition into profit margin, asset turnover, and leverage
- **Real Estate**: Property valuation using NOI and cap rates

## Architecture

### Backend (Node.js/Express)
- RESTful API server
- In-memory state management
- Mock data integration for yfinance/Alpha Vantage APIs
- Benchmark data from Damodaran and other sources

### Frontend (React)
- Modern React 18 with hooks
- Responsive CSS design
- Interactive step-by-step wizard
- Real-time data visualization

## The 10-Step Flow

### Step 1: Input Company Name or Ticker
- User enters company name or ticker symbol
- Clean search query validation
- UI: Text input with placeholder examples (e.g., "AAPL", "Tesla")

### Step 2: Search & Display Matching Results
- Query yfinance/Alpha Vantage API for ticker matches
- Ranked list of tickers + company names + exchanges
- UI: Radio-button list with "Next →" button; "No results" fallback

### Step 3: Select Company & Ticker
- User confirms selection
- State encoded with ticker, company_name
- UI: Confirmation screen: "✅ Selected: [Company] ([Ticker])" + "Continue →"

### Step 4: Select Valuation Model
- User chooses one of: DCF | Trading Comps | DuPont Analysis | Real Estate
- model_type added to state
- UI: Radio buttons with model descriptions; "View Requirements →"

### Step 5: Show Required Inputs Checklist
- Display model-specific field list from Schema definitions
- All fields marked ⏳ Pending Retrieval
- UI: Table with "Field Name" + "Status" columns; "Retrieve Data →" button

### Step 6: Retrieve Live Data from APIs
- Fetch market data, financial statements, macro/FX indicators via API
- Populated Schema 1 (API-Retrieved & Calculated) data object
- UI: Loading indicator → auto-advance to Step 7 on success

### Step 7: Review Data + AI Suggestions + Benchmark Ranges ⭐ Enhanced
Side-by-side comparison for each required field:
- **API Value**: Auto-fetched from yfinance/Alpha Vantage (✓ Found / ✗ Missing)
- **AI Suggestion**: Pre-filled value from Schema 2 (footnote parsing, guidance extraction)
- **Benchmark Range**: 25th–75th percentile from peers or published sources (Schema 3)
- **Source Citation**: Transparent reference (e.g., "Damodaran Sector WACC")

User Controls:
- ✏️ Manual Entry: Type custom value
- 🤖 Use AI: One-click fill with AI-suggested value
- 📊 Use Benchmark: One-click fill with benchmark median

### Step 8: Select or Customize Assumption Scenarios
- Best / Base / Worst scenario presets
- AI-suggested ranges
- UI: Toggle between presets; expandable "Custom" section

### Step 9: Confirm & Run Valuation Model
- Final review screen showing all inputs, sources, and assumptions
- Complete configuration object routed to selected engine
- UI: Summary table with source tags (✅ API / 🤖 AI / 📊 Bench / ✏️ Manual)

### Step 10: Display Results + Audit Trail
Output includes:
- Primary result (Implied Share Price, EV, ROE, etc.)
- Upside/(Downside) vs. current market price
- Scenario comparison (Bull/Base/Bear)
- Full audit trail: field-level sourcing, AI confidence scores, user overrides

## Installation

### Backend Setup

```bash
cd backend
npm install
npm start
```

The backend server will run on `http://localhost:5000`

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

The frontend will run on `http://localhost:3000`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/search?q={query}` | Search for tickers |
| POST | `/api/select-company` | Select a company |
| GET | `/api/models` | Get available valuation models |
| POST | `/api/select-model` | Select a valuation model |
| GET | `/api/required-fields?model={type}` | Get required fields for model |
| POST | `/api/retrieve-data` | Retrieve live data from APIs |
| GET | `/api/ai-suggestions` | Get AI suggestions and benchmarks |
| POST | `/api/confirm-values` | Submit user-confirmed values |
| GET | `/api/scenarios` | Get scenario presets |
| POST | `/api/select-scenario` | Select a scenario |
| POST | `/api/run-valuation` | Execute valuation model |
| GET | `/api/results` | Get final valuation results |
| POST | `/api/reset` | Reset application state |
| GET | `/api/health` | Health check endpoint |

## Project Structure

```
/workspace
├── backend/
│   ├── package.json
│   └── server.js          # Express API server
├── frontend/
│   ├── package.json
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── index.js
│       ├── index.css
│       ├── components/
│       │   └── ValuationFlow.js
│       ├── services/
│       │   └── api.js
│       └── hooks/
└── README.md
```

## Features

- ✅ **10-Step Guided Workflow**: Intuitive step-by-step valuation process
- ✅ **Multiple Valuation Models**: DCF, Trading Comps, DuPont, Real Estate
- ✅ **Live Data Integration**: API-based data retrieval (simulated)
- ✅ **AI-Powered Suggestions**: Smart defaults from document parsing
- ✅ **Benchmark Comparisons**: Industry-standard reference ranges
- ✅ **Scenario Analysis**: Best/Base/Worst case modeling
- ✅ **Audit Trail**: Complete transparency on data sources
- ✅ **Responsive Design**: Works on desktop and mobile
- ✅ **Modern UI/UX**: Clean, professional interface

## Technologies Used

### Backend
- Node.js
- Express.js
- CORS
- dotenv

### Frontend
- React 18
- Axios (HTTP client)
- CSS3 (with animations)
- Fetch API

## Future Enhancements

1. **Real API Integration**: Connect to actual yfinance and Alpha Vantage APIs
2. **Database Persistence**: Replace in-memory state with PostgreSQL/MongoDB
3. **Authentication**: User accounts and saved valuations
4. **Export Functionality**: PDF/Excel report generation
5. **Advanced Charts**: Interactive sensitivity analysis visualizations
6. **Machine Learning**: Enhanced AI suggestions from SEC filings
7. **Peer Comparison**: Automated peer group selection and analysis
8. **Multi-Currency Support**: FX conversion for international companies

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.