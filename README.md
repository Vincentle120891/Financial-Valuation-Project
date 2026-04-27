# 📊 Financial Valuation Platform

> **Professional-grade company valuation platform** implementing a comprehensive 12-step guided workflow for DCF, DuPont Analysis, Trading Comps, and Real Estate valuations.
> 
> **Version 2.0** - Now with AI-powered peer company suggestions for WACC calculation and trading comparables.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)
![React](https://img.shields.io/badge/React-18-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 🎯 Overview

This platform enables financial analysts, investors, and students to perform institutional-quality company valuations through an intuitive, step-by-step guided workflow. It combines **live market data**, **AI-powered assumptions**, and **industry-standard valuation methodologies** to deliver comprehensive valuation analysis with full audit trails.

### ⚠️ Model Integrity Commitment

**This platform adheres to strict model completeness principles.** We never remove inputs, calculations, or outputs to "simplify" the model. Every component exists for a reason and contributes to accurate, transparent valuations.

See [MODEL_INTEGRITY_MANIFESTO.md](./MODEL_INTEGRITY_MANIFESTO.md) for our complete guidelines.

### Core Valuation Models

| Model | Description | Key Output |
|-------|-------------|------------|
| **DCF** | Discounted Cash Flow - Intrinsic value based on projected free cash flows | Implied Share Price, Enterprise Value |
| **DuPont Analysis** | ROE decomposition into profit margin, asset turnover, and leverage | ROE Drivers, Financial Efficiency Metrics |
| **Trading Comps** | Relative valuation using peer company multiples | Comparable Valuation Multiples |
| **Real Estate** | Property valuation using NOI and cap rates | Property Value, Cap Rate Analysis |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React 18)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  12-Step Guided Wizard Interface                     │   │
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

## 🔄 The 12-Step Workflow

### Phase 1: Company Selection (Steps 1-3)

| Step | Action | User Interface | Backend Process |
|------|--------|----------------|-----------------|
| **1** | Search | Text input + market toggle (VN/International) | Query yfinance for ticker matches |
| **2** | Results | Radio list of up to 10 tickers with exchange info | Return ranked search results |
| **3** | Select | Confirmation screen: "✅ Selected: [Company]" | Create session with UUID |

### Phase 2: Model Configuration (Steps 4-6)

| Step | Action | User Interface | Backend Process |
|------|--------|----------------|-----------------|
| **4** | Choose Models | Multi-select checkboxes (DCF, DuPont, COMPS) | Validate model compatibility |
| **5** | Review Inputs | Table showing required fields per model | Load schema definitions |
| **6** | Confirm | Summary of models and required fields | Prepare for data fetch |

### Phase 3: Data Acquisition (Steps 7-8)

| Step | Action | User Interface | Backend Process |
|------|--------|----------------|-----------------|
| **7** | Fetch Data | Loading indicator | Call yfinance + Alpha Vantage APIs |
| **8** | Display Data | Data table with ✓ Found / ✗ Missing indicators | Parse and validate retrieved data |

### Phase 4: AI-Powered Assumptions (Steps 9-10)

| Step | Action | User Interface | Backend Process |
|------|--------|----------------|-----------------|
| **9** | AI Generation | Side-by-side: API Value | AI Suggestion | Benchmark Range | Generate WACC, growth rates, trends via Gemini/Groq |
| **10** | Review | Toggle presets (Bull/Base/Bear), manual edits | Store confirmed assumptions with source tags |

### Phase 5: Valuation & Results (Steps 11-12)

| Step | Action | User Interface | Backend Process |
|------|--------|----------------|-----------------|
| **11** | Run Valuation | Summary table with source tags | Execute valuation engines |
| **12** | Results | Implied price, upside/downside, sensitivity matrix, scenario analysis | Return comprehensive valuation output |

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
| `POST` | `/api/step-3-select-ticker` | 3 | Select ticker, create session | `{ticker, market}` | `{session_id, status}` |
| `POST` | `/api/step-4-select-models` | 4 | Choose valuation models | `{session_id, models}` | `{status}` |
| `POST` | `/api/step-6-confirm-inputs` | 6 | Confirm before data fetch | `{session_id}` | `{status}` |
| `POST` | `/api/step-7-8-fetch-data` | 7-8 | Retrieve financial data | `{session_id}` | `{data: {...}}` |
| `POST` | `/api/step-9-generate-ai` | 9 | Generate AI assumptions | `{session_id}` | `{suggestions: {...}}` |
| `POST` | `/api/step-10-confirm-assumptions` | 10 | Confirm/edit assumptions | `{session_id, assumptions}` | `{status}` |
| `POST` | `/api/step-11-12-valuate` | 11-12 | Run valuation | `{session_id}` | `{result: {...}}` |

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
│   ├── dcf_engine.py                 # DCF valuation calculations
│   ├── dcf_engine_full.py            # Advanced DCF with full forecasting
│   ├── dcf_forecast_config.py        # DCF forecast configuration schemas
│   ├── dupont_engine.py              # DuPont analysis calculations
│   ├── dupont_module.py              # Extended DuPont module
│   ├── comps_engine.py               # Trading comparables engine
│   ├── input.py                      # Input validation & schemas
│   ├── input_ai.py                   # AI input generation logic
│   ├── input_dcf.py                  # DCF-specific input handlers
│   ├── requirements.txt              # Python dependencies
│   ├── .env                          # Environment variables (gitignored)
│   ├── .env.example                  # Template for environment setup
│   ├── README_PYTHON.md              # Detailed backend documentation
│   ├── FLOW_IMPLEMENTATION.md        # 12-step workflow API reference
│   └── COMPLETE_MODEL_REFERENCE.md   # Comprehensive model documentation
│
├── frontend/                         # React 18 Frontend
│   ├── package.json                  # Dependencies (React, Axios, Recharts)
│   ├── public/
│   │   └── index.html                # HTML entry point
│   └── src/
│       ├── index.js                  # React entry point
│       ├── components/
│       │   └── ValuationFlow.js      # Main 12-step wizard component
│       └── services/
│           └── api.js                # API service layer
│
├── README.md                         # This file - Main project documentation
└── README_PYTHON_SETUP.md            # Quick Python setup guide
```

---

## ✨ Key Features

- ✅ **12-Step Guided Workflow**: Structured user journey from company search to valuation results
- ✅ **Multiple Valuation Models**: DCF, Trading Comps, DuPont Analysis, Real Estate
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

### 2. AI-Assisted Assumptions
When manual inputs are required, the AI engine:
- Analyzes historical trends and peer comparisons
- Generates reasonable assumption ranges with confidence scores
- Provides transparent explanations for each suggestion
- Allows users to accept, edit, or override AI recommendations

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
- [x] 12-step workflow implementation
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