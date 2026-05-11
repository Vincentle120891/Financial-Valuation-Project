# 📊 Financial Valuation Platform

> **Professional-grade company valuation platform** implementing a comprehensive 11-step guided workflow for DCF, DuPont Analysis, and Trading Comps valuations.
> 
> **Version 2.0** - Now with AI-powered peer company suggestions for WACC calculation and trading comparables.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)
![React](https://img.shields.io/badge/React-18-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

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

## 🎯 Overview

This platform enables financial analysts, investors, and students to perform institutional-quality company valuations through an intuitive, step-by-step guided workflow. It combines **live market data**, **AI-powered assumptions**, and **industry-standard valuation methodologies** to deliver comprehensive valuation analysis with full audit trails.

### ⚠️ Model Integrity Commitment

**This platform adheres to strict model completeness principles.** We never remove inputs, calculations, or outputs to "simplify" the model. Every component exists for a reason and contributes to accurate, transparent valuations.

See [MODEL_INTEGRITY_CONFIG.md](./backend/MODEL_INTEGRITY_CONFIG.md) for our complete guidelines.

### Core Valuation Models

| Model | Description | Key Output |
|-------|-------------|------------|
| **DCF** | Discounted Cash Flow - Intrinsic value based on projected free cash flows | Implied Share Price, Enterprise Value |
| **DuPont Analysis** | ROE decomposition into profit margin, asset turnover, and leverage | ROE Drivers, Financial Efficiency Metrics |
| **Trading Comps** | Relative valuation using peer company multiples | Comparable Valuation Multiples |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React 18)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  11-Step Guided Wizard Interface                     │   │
│  │  • Market Toggle (VN/International)                  │   │
│  │  • Interactive Data Visualization                    │   │
│  │  • AI Assumption Review & Editing                    │   │
│  │  • Sensitivity & Scenario Analysis Charts            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/REST API
┌─────────────────────────────────────────────────────────────┐
│                 Backend (Python/FastAPI)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  DCF Engine  │  │ DuPont Engine│  │ Comps Engine │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Data Integration Layer                   │   │
│  │  • yfinance (Yahoo Finance)                          │   │
│  │  • Alpha Vantage API                                 │   │
│  │  • AI Providers (Gemini/Groq)                        │   │
│  │  • Damodaran Benchmarks                              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend (Python)**
- **FastAPI** ≥0.116.0 - Modern async web framework with auto-generated OpenAPI docs
- **uvicorn** ≥0.35.0 - High-performance ASGI server
- **pydantic** ≥2.0.0 - Data validation and settings management
- **yfinance** ≥1.0.0 - Yahoo Finance data retrieval
- **aiohttp** ≥3.9.0 - Async HTTP client for Alpha Vantage API
- **groq** ≥0.11.0 - Groq LLM client (Llama 3) for AI assumptions
- **python-dotenv** ≥1.0.0 - Environment variable management
- **gunicorn** ≥21.0.0 - Production WSGI server

**Frontend (React)**
- **React 18** - Component-based UI with hooks
- **Axios** - HTTP client for API communication
- **Recharts** - Data visualization library
- **CSS3** - Responsive design with animations

---

## 🔄 The 11-Step Workflow

### Phase 1: Company & Peer Selection (Steps 1-3)

| Step | Action | User Interface | Backend Process |
|------|--------|----------------|-----------------|
| **1** | Search Company | Text input + market toggle (VN/International) | Query yfinance for ticker matches |
| **2** | Company Overview | Display selected company details | Create session with UUID, fetch basic info |
| **3** | Peer Selection | AI-suggested peers with auto-select top 5 | Peer discovery service with scoring |

### Phase 2: Model Configuration (Steps 4-5)

| Step | Action | User Interface | Backend Process |
|------|--------|----------------|-----------------|
| **4** | Select Model | Single select (DCF, DuPont, Comps) | Validate model compatibility, store in session |
| **5** | Review Requirements | Table showing required fields per model | Load schema definitions from step5 processor |

### Phase 3: Data Retrieval & Review (Steps 6-7)

| Step | Action | User Interface | Backend Process |
|------|--------|----------------|-----------------|
| **6** | View Retrieved Inputs | Display all API-fetched financial data | Step6DataReviewProcessor fetches from yfinance/Alpha Vantage |
| **7** | Historical Data Retrieval | Display missing historical data fetched from alternative sources | Step7HistoricalDataProcessor fetches data gaps not available via standard APIs |

### Phase 4: Assumption & AI Suggestion (Steps 8-9)

| Step | Action | User Interface | Backend Process |
|------|--------|----------------|-----------------|
| **8** | Assumption & AI Suggestion | Review AI-suggested assumptions with confidence scores, edit forecast drivers | Step8AssumptionProcessor calculates values programmatically and utilizes AI for suggestions on forward-looking inputs |
| **9** | Confirm Assumptions | Final review before calculation | Store confirmed assumptions with source tags |

### Phase 5: Valuation & Results (Steps 10-11)

| Step | Action | User Interface | Backend Process |
|------|--------|----------------|-----------------|
| **10** | Run Valuation | Execute selected model | Step10ValuationProcessor runs DCF/DuPont/Comps engines |
| **11** | View Results | Implied price, upside/downside, sensitivity matrix, charts | Return comprehensive valuation output |

---

## 🚀 Quick Start

### Prerequisites

- **Python** 3.9 or higher
- **Node.js** 16 or higher
- **npm** or **yarn**

### ⚠️ Important: Model Integrity

Before getting started, please review our [Model Integrity Manifesto](./MODEL_INTEGRITY_MANIFESTO.md). This platform follows strict principles to maintain complete, transparent, and accurate valuation models. **We do not remove features for simplicity.**

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys (see Configuration section)

# Start the server
python main.py
```

The backend will run on **http://localhost:8000**

Interactive API documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

The frontend will run on **http://localhost:3000**

> **Note**: Ensure the backend is running before starting the frontend. The frontend API base URL should point to `http://localhost:8000`.

---

## ⚙️ Configuration

### Environment Variables (.env)

Create a `.env` file in the `backend/` directory:

```bash
# Server Configuration
PORT=8000
DEBUG=true

# Financial Data APIs (Required)
ALPHA_VANTAGE_KEY=your_key_here
# Get your free key at: https://www.alphavantage.co/support/#api-key

# AI APIs (Optional - falls back to mock data if not provided)
# Google Gemini API - Primary AI provider
GEMINI_API_KEY=your_key_here
# Get your free key at: https://makersuite.google.com/app/apikey

# Groq API - Fallback AI provider (Llama 3)
GROQ_API_KEY=your_key_here
# Get your free key at: https://console.groq.com/keys

# AI Configuration (optional, uses defaults if not set)
AI_PRIMARY_MODEL=gemini
AI_FALLBACK_MODEL=groq
AI_CONFIDENCE_THRESHOLD=0.7
```

> ⚠️ **Security Notice**: Never commit `.env` to version control. Revoke and regenerate any exposed API keys immediately.

---

## 📡 API Endpoints

### Core Workflow Endpoints

| Method | Endpoint | Step | Description | Request Body | Response |
|--------|----------|------|-------------|--------------|----------|
| `POST` | `/api/step-1-search` | 1 | Search tickers | `{query, market}` | `{results: [...]}` |
| `POST` | `/api/step-2-company-overview` | 2 | Get company details | `{ticker, market}` | `{session_id, company_info}` |
| `POST` | `/api/step-3-suggest-peers` | 3 | Suggest peer companies | `{ticker, market, limit}` | `{peers: [...]}` |
| `POST` | `/api/step-4-select-models` | 4 | Select valuation model | `{session_id, model}` | `{status, next_step}` |
| `POST` | `/api/step-5-prepare-inputs` | 5 | Get required inputs | `{session_id}` | `{required_inputs: [...]}` |
| `POST` | `/api/step-6-fetch-api-data` | 6 | Fetch financial data | `{session_id}` | `{financial_data: {...}}` |
| `POST` | `/api/step-7-fetch-historical-data` | 7 | Fetch missing historical data | `{session_id}` | `{historical_data: {...}}` |
| `POST` | `/api/step-8-generate-ai-assumptions` | 8 | Generate AI assumption suggestions | `{session_id}` | `{suggestions: {...}}` |
| `POST` | `/api/step-9-confirm-assumptions` | 9 | Confirm assumptions | `{session_id, confirmed_values}` | `{status}` |
| `POST` | `/api/step-10-valuate` | 10 | Run valuation | `{session_id}` | `{valuation_results: [...]}` |

### Utility Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check endpoint |
| `GET` | `/api/models` | List available valuation models |
| `GET` | `/api/scenarios` | Get scenario templates (Bull/Base/Bear) |
| `POST` | `/api/reset` | Reset session state |

---

## 📁 Project Structure

```
/workspace
├── backend/                          # Python/FastAPI Backend
│   ├── main.py                       # FastAPI application (entry point)
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/               # API route handlers
│   │   │   │   ├── valuation_routes.py       # Steps 4-10 valuation endpoints
│   │   │   │   ├── search_routes.py          # Step 1 search endpoints
│   │   │   │   ├── international_market_data_routes.py  # Market data
│   │   │   │   └── vietnamese_market_data_routes.py   # Vietnam market
│   │   │   └── schemas.py            # Pydantic request/response models
│   │   ├── services/                 # Business logic layer
│   │   │   ├── international/        # International market services
│   │   │   │   ├── step1_ticker_processor.py
│   │   │   │   ├── step2_market_data_processor.py
│   │   │   │   ├── step3_historical_processor.py
│   │   │   │   ├── step4_forecast_processor.py
│   │   │   │   ├── step5_assumptions_processor.py
│   │   │   │   ├── step6_data_review.py
│   │   │   │   ├── step7_ai_suggestions.py
│   │   │   │   ├── step8_manual_overrides.py
│   │   │   │   ├── step9_final_calculation.py
│   │   │   │   └── step10_valuation_processor.py
│   │   │   └── vietnamese/           # Vietnamese market services
│   │   ├── engines/                  # Valuation calculation engines
│   │   │   ├── dcf_engine.py         # DCF calculations
│   │   │   ├── dupont_engine.py      # DuPont analysis
│   │   │   └── comps_engine.py       # Trading comparables
│   │   └── core/                     # Core utilities
│   │       ├── session_service.py    # Session management
│   │       └── logging_config.py     # Logging configuration
│   ├── requirements.txt              # Python dependencies
│   ├── .env                          # Environment variables (gitignored)
│   └── .env.example                  # Template for environment setup
│
├── frontend/                         # React 18 Frontend
│   ├── package.json                  # Dependencies (React, Axios, Recharts)
│   ├── public/
│   │   └── index.html                # HTML entry point
│   └── src/
│       ├── components/
│       │   ├── ValuationFlow.jsx     # Main 11-step wizard component
│       │   └── valuation-flow/       # Individual step components
│       │       ├── SearchStep.jsx
│       │       ├── CompanySelectionStep.jsx
│       │       ├── PeerSelectionStep.jsx
│       │       ├── ModelSelectionStep.jsx
│       │       ├── RequirementsStep.jsx
│       │       ├── ApiDataStep.jsx
│       │       ├── AiAssumptionsStep.jsx
│       │       ├── ForecastDriversStep.jsx
│       │       ├── AssumptionsStep.jsx
│       │       ├── RunValuationStep.jsx
│       │       └── ResultsStep.jsx
│       └── services/
│           └── api.js                # API service layer
│
├── README.md                         # This file - Main project documentation
├── BACKEND_WORKFLOW_DOCUMENTATION.md # Detailed backend workflow guide
└── DCF_WORKFLOW_INTERNATIONAL.md     # DCF-specific workflow documentation
```

---

## ✨ Key Features

- ✅ **11-Step Guided Workflow**: Structured user journey from company search to valuation results
- ✅ **Multiple Valuation Models**: DCF, Trading Comps, DuPont Analysis
- ✅ **Market Toggle**: Support for Vietnamese (.VN) and international markets
- ✅ **Live Data Integration**: Real-time financial data via yfinance + Alpha Vantage API
- ✅ **AI-Powered Assumptions**: Intelligent WACC, growth rates, and benchmark suggestions via Gemini/Groq
- ✅ **Benchmark Comparisons**: Industry-standard reference ranges from Damodaran data
- ✅ **Scenario Analysis**: Bull/Base/Bear case modeling with confidence scores
- ✅ **Sensitivity Analysis**: WACC vs Terminal Growth matrices and tornado charts
- ✅ **Audit Trail**: Complete transparency with field-level sourcing (API/AI/Benchmark/Manual)
- ✅ **Responsive Design**: Optimized for desktop and mobile devices
- ✅ **Modern UI/UX**: Clean, professional interface with smooth animations
- ✅ **Interactive API Docs**: Auto-generated Swagger/ReDoc documentation

---

## 📊 Sample Valuation Output

```json
{
  "enterprise_value": 2850000000000,
  "equity_value": 2750000000000,
  "implied_share_price": 185.50,
  "current_market_price": 178.75,
  "upside_downside": "3.79%",
  "recommendation": "BUY",
  "scenario_analysis": {
    "bull_case": {"price": 210.00, "probability": 0.25},
    "base_case": {"price": 185.50, "probability": 0.50},
    "bear_case": {"price": 155.00, "probability": 0.25}
  },
  "sensitivity_matrix": {
    "wacc_range": [0.07, 0.08, 0.09, 0.10],
    "terminal_growth_range": [0.015, 0.02, 0.025, 0.03],
    "values": [[...], [...], [...], [...]]
  },
  "audit_trail": {
    "wacc": {"value": 0.085, "source": "AI", "confidence": 0.92},
    "terminal_growth": {"value": 0.025, "source": "Benchmark", "peer_median": 0.023}
  }
}
```

---

## 🔍 How It Works

### 1. Data Collection
The platform retrieves live financial data from multiple sources:
- **yfinance**: Stock prices, historical data, company profile
- **Alpha Vantage API**: Income statements, balance sheets, cash flow statements
- **Damodaran Database**: Industry benchmarks and sector WACC data

### 2. AI-Assisted Assumptions (Step 8)
In Step 8 (Assumption & AI Suggestion), the AI engine provides suggestions for forward-looking inputs:
- Analyzes historical trends and peer comparisons
- Generates reasonable assumption ranges with confidence scores
- Provides transparent explanations for each suggestion
- Allows users to accept, edit, or override AI recommendations

**Note**: Step 7 (Historical Data Retrieval) uses AI specifically to extract historical data that standard APIs (yfinance/AlphaVantage) cannot provide - such as data from PDF filings, annual reports, and alternative sources. This is distinct from Step 8 where AI provides suggestions for forward-looking assumptions.

### 3. Valuation Execution
Each valuation model runs independently:
- **DCF**: Projects free cash flows, calculates terminal value, discounts to present
- **DuPont**: Decomposes ROE into margin, turnover, and leverage components
- **Comps**: Calculates trading multiples and applies to target company
- **Real Estate**: Capitalizes NOI using appropriate cap rates

### 4. Results Synthesis
Final output includes:
- Primary valuation metric (implied share price, EV, etc.)
- Upside/downside analysis vs. current market price
- Scenario comparison (Bull/Base/Bear)
- Sensitivity analysis tables
- Complete audit trail with source citations

---

## 🛠️ Development

### Running Tests

```bash
# Backend tests (if implemented)
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Style

```bash
# Backend linting (if configured)
flake8 backend/

# Frontend linting
cd frontend
npm run lint
```

---

## 📈 Roadmap

### Completed ✅
- [x] Python backend migration from Node.js
- [x] 11-step workflow implementation
- [x] AI integration (Gemini/Groq)
- [x] yfinance and Alpha Vantage integration
- [x] DCF, DuPont, and Comps engines
- [x] Interactive API documentation

### In Progress 🔄
- [ ] Database persistence (PostgreSQL/MongoDB)
- [ ] User authentication and saved valuations
- [ ] PDF/Excel report export functionality

### Planned 📋
- [ ] Interactive sensitivity analysis charts
- [ ] Multi-currency FX conversion
- [ ] SEC filings parser (10-K/10-Q)
- [ ] Automated peer group selection algorithm
- [ ] Real-time collaboration features
- [ ] Mobile app (React Native)

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Contribution Guidelines
- Follow existing code style and conventions
- Write clear commit messages
- Include tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🆘 Support

For issues, questions, or feedback:

1. **Documentation**: Check the detailed guides:
   - [Backend Documentation](./backend/README_PYTHON.md)
   - [Workflow Implementation](./backend/FLOW_IMPLEMENTATION.md)
   - [Model Reference](./backend/COMPLETE_MODEL_REFERENCE.md)
   - [Python Setup Guide](./README_PYTHON_SETUP.md)

2. **API Docs**: Access interactive documentation at http://localhost:8000/docs

3. **GitHub Issues**: Report bugs or request features via GitHub Issues

4. **Email**: Contact the maintainers for direct support

---

## 🙏 Acknowledgments

- **Yahoo Finance** and **yfinance** library for market data
- **Alpha Vantage** for financial statement APIs
- **Aswath Damodaran** for benchmark data and valuation methodologies
- **Google Gemini** and **Groq** for AI capabilities
- **FastAPI** and **React** communities for excellent frameworks

---

## 📞 Contact

For business inquiries or partnerships, please contact the project maintainers through GitHub.

---

*Built with ❤️ for the finance community*