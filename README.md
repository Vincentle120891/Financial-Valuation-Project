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
2. **Shared Cache:** Store data in `session['market_data']`.
3. **Model-Specific Slicing:** 
   - User selects DCF → System slices DCF-relevant data from cache
   - User switches to DuPont → System reuses SAME cached data (NO re-fetch)
   - User switches to Comps → System reuses SAME cached data (NO re-fetch)
4. **Benefit:** Eliminates redundant API calls, prevents rate limiting, ensures data consistency.

### 🔄 3 Valuation Methods × 2 Market Versions

| | **International** | **Vietnam** |
|---|---|---|
| **DCF** | `services/international/dcf_engine.py` + 10 step processors | `services/vietnamese/vietnamese_dcf_engine.py` + 10 step processors |
| **DuPont** | `services/international/dupont_engine.py` + 10 step processors | `services/vietnamese/vietnamese_dupont_engine.py` + 10 step processors |
| **Comps** | `services/international/comps_engine.py` + 10 step processors | `services/vietnamese/vietnamese_comps_engine.py` (sector_valuation_models.py) |

**See [BACKEND_WORKFLOW_DOCUMENTATION.md](./backend/docs/ARCHITECTURE.md) for complete architectural guidelines.**

---

## 🎯 Overview

This platform enables financial analysts, investors, and students to perform institutional-quality company valuations through an intuitive, step-by-step guided workflow. It combines **live market data**, **AI-powered assumptions**, and **industry-standard valuation methodologies** to deliver comprehensive valuation analysis with full audit trails.

### ⚠️ Model Integrity Commitment

**This platform adheres to strict model completeness principles.** We never remove inputs, calculations, or outputs to "simplify" the model. Every component exists for a reason and contributes to accurate, transparent valuations.

See [MODEL_INTEGRITY_CONFIG.md](./backend/MODEL_INTEGRITY_CONFIG.md) for our complete guidelines.

### Core Valuation Models: 3×2 Matrix

| Model | International Market | Vietnamese Market | Key Output |
|-------|---------------------|-------------------|------------|
| **DCF** | ✅ `services/international/dcf_engine.py` | ✅ `services/vietnamese/vietnamese_dcf_engine.py` | Implied Share Price, Enterprise Value |
| **DuPont Analysis** | ✅ `services/international/dupont_engine.py` | ✅ `services/vietnamese/vietnamese_dupont_engine.py` | ROE Drivers, Financial Efficiency Metrics |
| **Trading Comps** | ✅ `services/international/comps_engine.py` | ✅ `services/vietnamese/vietnamese_comps_engine.py` | Comparable Valuation Multiples |

**Market-Specific Parameters:**
- **International**: Variable tax rates by country, local risk-free rates (10Y Treasury), IFRS/US GAAP standards
- **Vietnamese**: 20% corporate tax, 6.8% risk-free rate (10Y VN bond), TT99 accounting standards, VND currency

---

## 🏗️ Architecture

### ⚠️ CRITICAL DEVELOPMENT GUIDELINES

#### 1. Market Separation (DO NOT MERGE MARKETS)
**NEVER create "Generic Displayer" components that merge Vietnamese and International markets.**

- **Why?** Fundamental differences exist:
  - **Accounting Standards:** VAS (Vietnam) vs IFRS/US GAAP (International)
  - **Currency:** VND vs USD with different formatting rules
  - **Market Mechanics:** Foreign ownership limits, board types (HOSE/HNX/UPCoM), trading mechanisms
  
- **Correct Approach:**
  - **UI Layer:** Keep `VietnameseMarketData.jsx` and `InternationalMarketData.jsx` separate
  - **Service Layer:** Use `UnifiedTransformer` services ONLY for temporary normalization during peer comparison
  - **Never** lose local precision or context by forcing a lowest-common-denominator schema

#### 2. Thin Routes, Fat Services
**Route handlers must NOT contain business logic.**

- **Violation Example:** `save_peers()` in `valuation_routes.py` fetching yfinance data directly
- **Correct Pattern:**
  ```python
  # ❌ WRONG - Route handling logic
  @router.post("/step-3-save-peers")
  def save_peers(data):
      peers = fetch_yfinance_data(data.tickers)  # Don't do this!
      ...
  
  # ✅ CORRECT - Delegate to service
  @router.post("/step-3-save-peers")
  def save_peers(data):
      result = PeerDiscoveryService.discover_peers(data.tickers, data.market)
      return result
  ```

- **Files to Check:**
  - `valuation_routes.py` - Should only validate and delegate
  - `search_routes.py` - Already correctly implemented

#### 3. Workflow Step Integrity
**File names MUST match their workflow step purpose.**

| Step | Purpose | Correct File | Mismatched Files (Rename to `mismatch_*.py`) |
|------|---------|--------------|---------------------------------------------|
| **3** | Peer Company Selection | `peer_discovery_service.py` | `step3_historical_processor.py` |
| **4** | Model Selection (DCF/DuPont/Comps) | `step4_selected_models_processor.py` | `step4_forecast_processor.py` |
| **5** | Required Inputs Display | `step5_required_inputs_processor.py` | `step5_assumptions_processor.py` |

- **Rule:** If a file name suggests a different purpose than its step number, rename it with `mismatch_` prefix to prevent accidental usage.

#### 4. 3×2 Matrix Architecture
The system supports **3 Valuation Methods × 2 Market Versions**:

| | **International** | **Vietnam** |
|---|---|---|
| **DCF** | `services/international/dcf_engine.py` + processors | `services/vietnamese/vietnamese_dcf_engine.py` + processors |
| **DuPont** | `services/international/dupont_engine.py` + processors | `services/vietnamese/vietnamese_dupont_engine.py` + processors |
| **Comps** | `services/international/comps_engine.py` + processors | `services/vietnamese/vietnamese_comps_engine.py` |

- **Implementation:** Data structure `valuationsData[market][method]` ensures strict separation while allowing unified orchestration.
- **Frontend:** Step 4 uses **Radio Buttons** (single-select) to enforce one model at a time, preventing AI context hallucination.

---

### Technology Stack

**Backend (Python)**
- **FastAPI** ≥0.116.0 - Modern async web framework with auto-generated OpenAPI docs
- **uvicorn** ≥0.35.0 - High-performance ASGI server
- **pydantic** ≥2.0.0 - Data validation and settings management
- **yfinance** ≥1.0.0 - Yahoo Finance data retrieval (International markets)
- **aiohttp** ≥3.9.0 - Async HTTP client for Alpha Vantage API
- **groq** ≥0.11.0 - Groq LLM client (Llama 3) for AI assumptions
- **python-dotenv** ≥1.0.0 - Environment variable management
- **gunicorn** ≥21.0.0 - Production WSGI server

**Dual-Market Services:**
- `services/international/` - 40+ processors for DCF, DuPont, Comps (IFRS/US GAAP)
- `services/vietnamese/` - 30+ processors for VN-specific valuations (TT99 standards)

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
| **1** | Search Company | Text input + market toggle (VN/International) | Query yfinance (Int'l) or VNStockDatabase (VN) for ticker matches |
| **2** | Company Overview | Display selected company details | Create session with UUID, fetch basic info from market-specific service |
| **3** | Peer Selection | AI-suggested peers with auto-select top 5 | Peer discovery service with scoring (market-specific logic) |

### Phase 2: Model Configuration (Steps 4-5)

| Step | Action | User Interface | Backend Process |
|------|--------|----------------|-----------------|
| **4** | Select Model | **Single select** (DCF, DuPont, Comps) - Radio buttons | Validate model compatibility, store in session |
| **5** | Review Requirements | Table showing required fields per model | Load schema definitions from step5 processor (market-specific) |

### Phase 3: Data Retrieval & Review (Steps 6-7)

| Step | Action | User Interface | Backend Process |
|------|--------|----------------|-----------------|
| **6** | View Retrieved Inputs | Display all API-fetched financial data | **Fetch Once, Use Many**: Step6DataReviewProcessor fetches ALL data for ANY model into shared cache |
| **7** | Historical Data Retrieval | Display missing historical data fetched from alternative sources | Step7HistoricalDataProcessor fetches data gaps not available via standard APIs (AI extraction from PDFs for VN market) |

### Phase 4: Assumption & AI Suggestion (Steps 8-9)

| Step | Action | User Interface | Backend Process |
|------|--------|----------------|-----------------|
| **8** | Assumption & AI Suggestion | Review AI-suggested assumptions with confidence scores, edit forecast drivers | Step8AssumptionProcessor calculates values programmatically and utilizes AI for suggestions on forward-looking inputs (model-specific: DCF/DuPont/Comps) |
| **9** | Confirm Assumptions | Final review before calculation | Store confirmed assumptions with source tags (API/AI/Benchmark/Manual) |

### Phase 5: Valuation & Results (Steps 10-11)

| Step | Action | User Interface | Backend Process |
|------|--------|----------------|-----------------|
| **10** | Run Valuation | Execute selected model | Step10ValuationProcessor runs DCF/DuPont/Comps engines (market-specific: international/vietnamese) |
| **11** | View Results | Implied price, upside/downside, sensitivity matrix, charts | Return comprehensive valuation output with currency formatting (USD/VND) |

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
│   │   │   │   ├── international_market_data_routes.py  # /international/* endpoints
│   │   │   │   ├── vietnamese_market_data_routes.py   # /vietnamese/* endpoints
│   │   │   │   ├── search_routes.py          # Step 1 search endpoints
│   │   │   │   ├── valuation_routes.py       # Steps 4-10 valuation endpoints
│   │   │   │   ├── pdf_extraction_routes.py  # VN PDF extraction
│   │   │   │   └── vietnamese_reports_routes.py
│   │   │   └── schemas.py            # Pydantic request/response models
│   │   ├── services/                 # Business logic layer
│   │   │   ├── international/        # International market services (40+ files)
│   │   │   │   ├── dcf_engine.py             # DCF calculations (IFRS/GAAP)
│   │   │   │   ├── dupont_engine.py          # DuPont analysis
│   │   │   │   ├── comps_engine.py           # Trading comparables
│   │   │   │   ├── step1_ticker_processor.py
│   │   │   │   ├── step2_market_data_processor.py
│   │   │   │   ├── step3_historical_processor.py
│   │   │   │   ├── step4_forecast_processor.py
│   │   │   │   ├── step5_assumptions_processor.py
│   │   │   │   ├── step6_data_review.py      # Fetch Once, Use Many
│   │   │   │   ├── step7_historical_data_processor.py
│   │   │   │   ├── step8_dcf_assumptions.py  # Model-specific AI
│   │   │   │   ├── step8_dupont_assumptions.py
│   │   │   │   ├── step8_comps_assumptions.py
│   │   │   │   ├── step9_final_calculation.py
│   │   │   │   └── step10_valuation_processor.py
│   │   │   └── vietnamese/           # Vietnamese market services (30+ files)
│   │   │       ├── vietnamese_dcf_engine.py    # DCF (TT99, 20% tax, VND)
│   │   │       ├── vietnamese_dupont_engine.py # DuPont (TT99 standards)
│   │   │       ├── vietnamese_comps_engine.py  # Comps (VNINDEX/VN30)
│   │   │       ├── sector_valuation_models.py  # VN sector models
│   │   │       ├── step1_ticker_processor.py
│   │   │       ├── step2_market_data_processor.py
│   │   │       ├── step3_historical_processor.py
│   │   │       ├── step4_model_processor.py
│   │   │       ├── step5_requirements_processor.py
│   │   │       ├── step6_data_fetch_processor.py
│   │   │       ├── step7_historical_processor.py
│   │   │       ├── step8_dcf_assumptions.py
│   │   │       ├── step8_dupont_assumptions.py
│   │   │       ├── step8_comps_assumptions.py
│   │   │       ├── step9_confirmation_processor.py
│   │   │       └── step10_valuation_processor.py
│   │   ├── models/                 # Pydantic schemas
│   │   │   ├── international/      # International market models
│   │   │   └── vietnamese/         # TT99-compliant VN models
│   │   └── core/                   # Core utilities
│   │       ├── session_service.py  # Session management
│   │       └── logging_config.py   # Logging configuration
│   ├── requirements.txt            # Python dependencies
│   ├── .env                        # Environment variables (gitignored)
│   ├── docs/
│   │   ├── ARCHITECTURE.md         # Backend architecture
│   │   ├── VIETNAMESE_VS_INTERNATIONAL_MODELS.md  # TT99 vs IFRS/GAAP
│   │   └── vietnamese_report_auto_fetch.md  # Auto-fetch VN reports
│   └── test/                       # Test suites
│
├── frontend/                         # React 18 Frontend
│   ├── package.json                  # Dependencies (React, Axios, Recharts)
│   ├── public/
│   │   └── index.html                # HTML entry point
│   ├── src/
│   │   ├── components/
│   │   │   ├── ValuationFlow.jsx     # Main 11-step wizard component
│   │   │   └── valuation-flow/       # Individual step components
│   │   │       ├── SearchStep.jsx
│   │   │       ├── CompanySelectionStep.jsx
│   │   │       ├── PeerSelectionStep.jsx
│   │   │       ├── ModelSelectionStep.jsx    # Radio buttons (single-select)
│   │   │       ├── RequirementsStep.jsx
│   │   │       ├── ApiDataStep.jsx           # Step 6: Fetch Once
│   │   │       ├── AiAssumptionsStep.jsx
│   │   │       ├── ForecastDriversStep.jsx
│   │   │       ├── AssumptionsStep.jsx
│   │   │       ├── RunValuationStep.jsx
│   │   │       └── ResultsStep.jsx
│   │   └── services/
│   │       └── api.js                # API service layer
│   └── ARCHITECTURE.md               # Frontend documentation
│
├── excel models/                     # Reference Excel models
│   ├── DCF_Model_Specification.xlsx
│   ├── DuPont_Analysis_Spec.xlsx
│   └── Comps_Valuation_Spec.xlsx
│
├── README.md                         # This file - Main project documentation
└── backend/
    ├── MODEL_INTEGRITY_CONFIG.md     # Model integrity guidelines
    ├── FLOW_IMPLEMENTATION.md        # Dual-market API implementation
    ├── INPUT_SOURCE_DOCUMENTATION.md # Input source tracking
    └── VIETNAMESE_PDF_EXTRACTION_GUIDE.md  # PDF extraction for VN
```

---

## ✨ Key Features

- ✅ **11-Step Guided Workflow**: Structured user journey from company search to valuation results
- ✅ **3×2 Valuation Matrix**: DCF, Trading Comps, DuPont Analysis × International & Vietnamese markets
- ✅ **Market Toggle**: Support for Vietnamese (.VN) and international markets with strict separation
- ✅ **Live Data Integration**: Real-time financial data via yfinance (Int'l) + VNDirect/CafeF/VNStockDB (VN)
- ✅ **AI-Powered Assumptions**: Intelligent WACC, growth rates, and benchmark suggestions via Gemini/Groq
- ✅ **Benchmark Comparisons**: Industry-standard reference ranges from Damodaran data
- ✅ **Scenario Analysis**: Bull/Base/Bear case modeling with confidence scores
- ✅ **Sensitivity Analysis**: WACC vs Terminal Growth matrices and tornado charts
- ✅ **Audit Trail**: Complete transparency with field-level sourcing (API/AI/Benchmark/Manual)
- ✅ **Responsive Design**: Optimized for desktop and mobile devices
- ✅ **Modern UI/UX**: Clean, professional interface with smooth animations
- ✅ **Interactive API Docs**: Auto-generated Swagger/ReDoc documentation
- ✅ **Fetch Once, Use Many**: Unified data caching prevents redundant API calls across models
- ✅ **TT99 Compliance**: Vietnamese market follows Thông Tư 99/2025/TT-BTC accounting standards
- ✅ **PDF Extraction**: AI-powered extraction from Vietnamese annual reports and filings

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