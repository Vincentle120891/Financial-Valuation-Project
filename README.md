# Financial Valuation Project - 12-Step Valuation Flow (Python Backend)

## Overview

This project implements a comprehensive **12-Step Valuation Flow** for financial analysis, supporting multiple valuation methodologies including:

- **DCF (Discounted Cash Flow)**: Intrinsic value based on projected free cash flows with sensitivity & scenario analysis
- **Trading Comps**: Relative valuation using peer company multiples
- **DuPont Analysis**: ROE decomposition into profit margin, asset turnover, and leverage
- **Real Estate**: Property valuation using NOI and cap rates

### 🐍 Python Backend Migration

The backend has been migrated from Node.js/Express to **Python/FastAPI** for improved performance, better yfinance integration, and enhanced AI capabilities. The original Node.js code is archived in `backend/draft/`.

## Architecture

### Backend (Python/FastAPI)
- High-performance async API server
- In-memory state management
- **yfinance** integration for reliable financial data
- **Alpha Vantage API** for supplemental data
- **AI integration** (Gemini/Groq) for intelligent assumptions
- 12-step guided workflow

### Frontend (React)
- Modern React 18 with hooks
- Responsive CSS design
- Interactive step-by-step wizard
- Real-time data visualization

## The 12-Step Flow

| Step | Action | Description |
|------|--------|-------------|
| **1** | **Search** | User inputs ticker/company name + market toggle (Vietnamese/International) |
| **2** | **Show Results** | Display up to 10 related tickers with exchange info |
| **3** | **Select Ticker** | User chooses specific ticker, creates session |
| **4** | **Choose Models** | Select valuation models (DCF, DuPont, COMPS) |
| **5** | **Review Inputs** | Show auto-retrieved vs. required manual inputs |
| **6** | **Confirm** | User confirms to proceed with data fetch |
| **7** | **Fetch Data** | yFinance & Alpha Vantage retrieve financial data |
| **8** | **Display Data** | Show fetched numbers with error handling |
| **9** | **AI Generation** | AI generates WACC, growth rates, benchmarks, trends, explanations |
| **10** | **User Review** | User accepts/edits AI suggestions with peer comparisons |
| **11** | **Valuation** | Run valuation engine |
| **12** | **Results** | Show valuation with sensitivity & scenario analysis |

### Detailed Steps

#### Step 1: Input Company Name or Ticker + Market Toggle
- User enters company name or ticker symbol
- Toggle between Vietnamese market (`.VN`) and International markets
- UI: Text input with market selector radio buttons

#### Step 2: Search & Display Matching Results
- Query yfinance/Alpha Vantage API for ticker matches
- Ranked list of up to 10 tickers + company names + exchanges
- UI: Radio-button list with "Next →" button; "No results" fallback

#### Step 3: Select Company & Ticker
- User confirms selection
- State encoded with ticker, company_name, market
- UI: Confirmation screen: "✅ Selected: [Company] ([Ticker])" + "Continue →"

#### Step 4: Select Valuation Model
- User chooses one or more: DCF | Trading Comps | DuPont Analysis
- model_type added to state
- UI: Multi-select checkboxes with model descriptions; "View Requirements →"

#### Step 5: Show Required Inputs Checklist
- Display model-specific field list from Schema definitions
- All fields marked ⏳ Pending Retrieval
- UI: Table with "Field Name" + "Status" columns; "Retrieve Data →" button

#### Step 6: Confirm Before Fetch
- Final confirmation before API calls
- UI: Summary of selected models and required fields

#### Step 7: Retrieve Live Data from APIs
- Fetch market data, financial statements, macro/FX indicators via yfinance & Alpha Vantage
- Populated API-retrieved data object
- UI: Loading indicator → auto-advance to Step 8 on success

#### Step 8: Review Fetched Data
- Display all retrieved financial metrics
- Highlight missing or incomplete data
- UI: Data table with ✓ Found / ✗ Missing indicators

#### Step 9: AI Suggestions + Benchmark Ranges ⭐ Enhanced
Side-by-side comparison for each required field:
- **API Value**: Auto-fetched from yfinance/Alpha Vantage
- **AI Suggestion**: Pre-filled value from Gemini/Groq with explanation
- **Benchmark Range**: 25th–75th percentile from peers or Damodaran
- **Source Citation**: Transparent reference (e.g., "Damodaran Sector WACC")
- **Trend Analysis**: Historical pattern insights

User Controls:
- ✏️ Manual Entry: Type custom value
- 🤖 Use AI: One-click fill with AI-suggested value
- 📊 Use Benchmark: One-click fill with benchmark median

#### Step 10: Select or Customize Assumptions
- Best / Base / Worst scenario presets
- AI-suggested ranges with confidence scores
- Peer comparison tables
- UI: Toggle between presets; expandable "Custom" section

#### Step 11: Confirm & Run Valuation Model
- Final review screen showing all inputs, sources, and assumptions
- Complete configuration object routed to selected engine
- UI: Summary table with source tags (✅ API / 🤖 AI / 📊 Bench / ✏️ Manual)

#### Step 12: Display Results + Audit Trail
Output includes:
- Primary result (Implied Share Price, EV, ROE, etc.)
- Upside/(Downside) vs. current market price
- Scenario comparison (Bull/Base/Bear)
- Sensitivity analysis tables
- Full audit trail: field-level sourcing, AI confidence scores, user overrides

## Installation

### Backend Setup (Python)

**Prerequisites**: Python 3.9+

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python main.py
```

The backend server will run on `http://localhost:8000`

### Frontend Setup (React)

```bash
cd frontend
npm install
npm start
```

The frontend will run on `http://localhost:3000`

**Note**: Update the frontend API base URL to `http://localhost:8000` (was 5000 for Node.js)

## API Endpoints

### Core Workflow Endpoints

| Method | Endpoint | Step | Description |
|--------|----------|------|-------------|
| `POST` | `/api/step-1-search` | 1 | Search tickers (body: `{query, market}`) |
| `POST` | `/api/step-3-select-ticker` | 3 | Select ticker, create session |
| `POST` | `/api/step-4-select-models` | 4 | Choose models (DCF, DuPont, COMPS) |
| `POST` | `/api/step-6-confirm-inputs` | 6 | Confirm before data fetch |
| `POST` | `/api/step-7-8-fetch-data` | 7-8 | Retrieve financial data |
| `POST` | `/api/step-9-generate-ai` | 9 | Generate AI assumptions |
| `POST` | `/api/step-10-confirm-assumptions` | 10 | User confirms/edits assumptions |
| `POST` | `/api/step-11-12-valuate` | 11-12 | Run valuation & get results |

### Utility Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/models` | List available models |
| `GET` | `/api/scenarios` | Get scenario templates |
| `POST` | `/api/reset` | Reset session state |

### Interactive Documentation

Once running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Project Structure

```
/workspace
├── backend/
│   ├── main.py                     # FastAPI application (entry point)
│   ├── yfinance_data.py            # Yahoo Finance data fetching
│   ├── dcf_engine.py               # DCF valuation calculations
│   ├── dupont_engine.py            # DuPont analysis calculations
│   ├── requirements.txt            # Python dependencies
│   ├── .env                        # Environment variables (gitignored)
│   ├── .env.example                # Example environment file
│   ├── README_PYTHON.md            # Python backend documentation
│   ├── FLOW_IMPLEMENTATION.md      # Detailed workflow docs
│   └── draft/                      # Archived Node.js code
│       ├── server.js
│       └── ...
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
├── README.md                       # This file
└── README_PYTHON_SETUP.md          # Quick Python setup guide
```

## Features

- ✅ **12-Step Guided Workflow**: Structured user journey from search to valuation
- ✅ **Multiple Valuation Models**: DCF, Trading Comps, DuPont Analysis
- ✅ **Market Toggle**: Support for Vietnamese (.VN) and international markets
- ✅ **Live Data Integration**: yfinance + Alpha Vantage API retrieval
- ✅ **AI-Powered Assumptions**: Gemini/Groq for WACC, growth rates, benchmarks
- ✅ **Benchmark Comparisons**: Industry-standard reference ranges from Damodaran
- ✅ **Scenario Analysis**: Best/Base/Worst case modeling
- ✅ **Sensitivity Analysis**: Tornado charts and data tables
- ✅ **Audit Trail**: Complete transparency on data sources
- ✅ **Responsive Design**: Works on desktop and mobile
- ✅ **Modern UI/UX**: Clean, professional interface
- ✅ **Interactive API Docs**: Auto-generated Swagger/ReDoc documentation

## Technologies Used

### Backend (Python)
- **FastAPI**: Modern async web framework
- **uvicorn**: ASGI server
- **yfinance**: Yahoo Finance data library
- **aiohttp**: Async HTTP client for Alpha Vantage
- **groq**: Groq LLM client
- **pydantic**: Data validation
- **python-dotenv**: Environment variable management
- **gunicorn**: Production WSGI server

### Frontend (React)
- React 18
- Axios (HTTP client)
- CSS3 (with animations)
- Fetch API

## Configuration

### Environment Variables (.env)

```bash
ALPHA_VANTAGE_KEY=your_key_here        # Required for financial statements
GEMINI_API_KEY=your_key_here           # Recommended for AI features
GROQ_API_KEY=your_key_here             # Optional fallback AI
PORT=8000                              # Server port
DEBUG=true                             # Enable debug mode
```

⚠️ **Security Notice**: Never commit `.env` to version control. Revoke and regenerate any exposed API keys immediately.

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py

# Frontend (in new terminal)
cd frontend
npm install
npm start
```

Access the app at http://localhost:3000

## Future Enhancements

1. ✅ **Python Migration**: Completed - Better yfinance integration
2. ✅ **12-Step Workflow**: Enhanced from 10 steps
3. ✅ **AI Integration**: Gemini/Groq for intelligent assumptions
4. 🔄 **Database Persistence**: Replace in-memory state with PostgreSQL/MongoDB
5. 🔄 **Authentication**: User accounts and saved valuations
6. 🔄 **Export Functionality**: PDF/Excel report generation
7. 🔄 **Advanced Charts**: Interactive sensitivity analysis visualizations
8. 🔄 **Multi-Currency Support**: FX conversion for international companies
9. 🔄 **SEC Filings Parser**: Extract guidance from 10-K/10-Q documents
10. 🔄 **Peer Group Automation**: Intelligent peer selection algorithm

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues or questions:
1. Check the [backend/README_PYTHON.md](./backend/README_PYTHON.md) for detailed Python backend docs
2. Review the interactive API docs at http://localhost:8000/docs
3. Check the [FLOW_IMPLEMENTATION.md](./backend/FLOW_IMPLEMENTATION.md) for workflow details