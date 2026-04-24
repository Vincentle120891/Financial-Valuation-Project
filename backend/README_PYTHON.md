# Financial Valuation Backend - Python/FastAPI

Complete 12-step financial valuation workflow with DCF, DuPont Analysis, and COMPS models. Powered by yfinance, Alpha Vantage, and AI (Gemini/Groq) for intelligent assumptions.

## 🚀 Quick Start

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Access the API at `http://localhost:8000` and interactive docs at `http://localhost:8000/docs`.

## 📋 Table of Contents

- [Features](#features)
- [12-Step Workflow](#12-step-workflow)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Server](#running-the-server)
- [API Endpoints](#api-endpoints)
- [Data Flow](#data-flow)
- [Project Structure](#project-structure)
- [Frontend Integration](#frontend-integration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## ✨ Features

- **FastAPI Framework**: High-performance, async-ready API with automatic OpenAPI documentation
- **yfinance Integration**: Reliable Yahoo Finance data for global markets (US, Vietnam, etc.)
- **Alpha Vantage API**: Supplemental financial statements and company overview
- **DCF Valuation Engine**: Complete discounted cash flow analysis with sensitivity & scenario analysis
- **DuPont Analysis**: 3-step and 5-step ROE decomposition
- **COMPS Model**: Comparable company analysis with peer multiples
- **AI-Powered Assumptions**: Intelligent WACC, growth rates, and forecasts via Gemini/Groq
- **12-Step Guided Workflow**: Structured user journey from search to final valuation
- **Market Toggle**: Support for Vietnamese (`.VN`) and international markets

## 🔄 12-Step Workflow

| Step | Action | Endpoint | Description |
|------|--------|----------|-------------|
| 1 | **Search** | `POST /api/step-1-search` | User inputs ticker/company name + market toggle (VN/International) |
| 2 | **Show Results** | (Response from Step 1) | Display up to 10 related tickers |
| 3 | **Select Ticker** | `POST /api/step-3-select-ticker` | User chooses specific ticker, creates session |
| 4 | **Choose Models** | `POST /api/step-4-select-models` | Select valuation models (DCF, DuPont, COMPS) |
| 5 | **Review Inputs** | (Response from Step 4) | Show auto-retrieved vs. required manual inputs |
| 6 | **Confirm** | `POST /api/step-6-confirm-inputs` | User confirms to proceed with data fetch |
| 7 | **Fetch Data** | `POST /api/step-7-8-fetch-data` | yFinance & Alpha Vantage retrieve financial data |
| 8 | **Display Data** | (Response from Step 7) | Show fetched numbers with error handling |
| 9 | **AI Generation** | `POST /api/step-9-generate-ai` | AI generates WACC, growth rates, benchmarks, trends, explanations |
| 10 | **User Review** | `POST /api/step-10-confirm-assumptions` | User accepts/edits AI suggestions with peer comparisons |
| 11 | **Valuation** | `POST /api/step-11-12-valuate` | Run valuation engine |
| 12 | **Results** | (Response from Step 11) | Show valuation with sensitivity & scenario analysis |

## 🛠️ Installation

### Prerequisites

- **Python 3.9+** (recommended: 3.11 or 3.12)
- **pip** (Python package manager)
- **Virtual environment** (recommended: `venv` or `conda`)

### Setup Steps

1. **Navigate to backend directory:**
   ```bash
   cd /workspace/backend
   ```

2. **Create virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## 🔐 Configuration

### Environment Variables (.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ALPHA_VANTAGE_KEY` | ✅ Yes | `demo` | Alpha Vantage API key for financial statements |
| `GEMINI_API_KEY` | ⚠️ Recommended | - | Google Gemini API key for AI suggestions |
| `GROQ_API_KEY` | ⚠️ Optional | - | Groq API key (fallback for AI) |
| `PORT` | No | `8000` | Server port |
| `HOST` | No | `0.0.0.0` | Server host |
| `DEBUG` | No | `true` | Enable debug mode |

### AI Model Configuration

| Model | Provider | Use Case |
|-------|----------|----------|
| `gemini-3.1-flash-lite-preview` | Google Gemini | Primary AI for forecasts & benchmarks |
| `qwen/qwen3-32b` | Groq | Fallback AI model |

### Security Notice

⚠️ **Never commit `.env` to version control.** The file is included in `.gitignore` by default.

If you accidentally exposed API keys:
1. Revoke them immediately in the respective provider dashboards
2. Generate new keys
3. Update your `.env` file

## 🖥️ Running the Server

### Development Mode (with auto-reload)

```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### With Gunicorn (recommended for production)

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📡 API Endpoints

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

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 📊 Data Flow

```
┌──────────────┐
│ 1. User Input│ → Ticker + Market (VN/Intl)
└──────┬───────┘
       ↓
┌──────────────┐
│ 2. Search    │ → Up to 10 tickers
└──────┬───────┘
       ↓
┌──────────────┐
│ 3. Select    │ → Create session
└──────┬───────┘
       ↓
┌──────────────┐
│ 4. Models    │ → DCF/DuPont/COMPS
└──────┬───────┘
       ↓
┌──────────────┐
│ 5-6. Review  │ → Confirm inputs
└──────┬───────┘
       ↓
┌──────────────┐
│ 7-8. Fetch   │ → yFinance + Alpha Vantage
└──────┬───────┘
       ↓
┌──────────────┐
│ 9. AI Engine │ → WACC, growth, benchmarks
└──────┬───────┘
       ↓
┌──────────────┐
│ 10. Review   │ → User edits assumptions
└──────┬───────┘
       ↓
┌──────────────┐
│ 11. Valuation│ → DCF/DuPont/COMPS calculation
└──────┬───────┘
       ↓
┌──────────────┐
│ 12. Results  │ → Value + Sensitivity + Scenarios
└──────────────┘
```

## 📁 Project Structure

```
backend/
├── main.py                     # FastAPI application (entry point)
├── yfinance_data.py            # Yahoo Finance data fetching
├── dcf_engine.py               # DCF valuation calculations
├── dupont_engine.py            # DuPont analysis calculations
├── comps_engine.py             # COMPS valuation (if exists)
├── ai_engine.py                # AI integration (Gemini/Groq)
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (gitignored)
├── .env.example                # Example environment file
├── README.md                   # This file
├── FLOW_IMPLEMENTATION.md      # Detailed workflow documentation
├── draft/                      # Archived Node.js code
│   ├── server.js
│   └── ...
└── public/                     # Static files (if any)
```

## 🌐 Frontend Integration

### Update API Base URL

```javascript
// frontend/src/services/api.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
```

### Example API Calls

```javascript
// Step 1: Search
const searchResponse = await fetch(`${API_BASE_URL}/api/step-1-search`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'AAPL', market: 'international' })
});

// Step 3: Select Ticker
const selectResponse = await fetch(`${API_BASE_URL}/api/step-3-select-ticker`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ ticker: 'AAPL' })
});

// Step 9: Generate AI Assumptions
const aiResponse = await fetch(`${API_BASE_URL}/api/step-9-generate-ai`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ models: ['DCF', 'DuPont'] })
});
```

### CORS Configuration

The backend is configured to accept requests from common frontend ports. To customize:

```python
# In main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🧪 Testing

### Test Individual Modules

```bash
# Test yfinance data fetching
python yfinance_data.py AAPL

# Test DCF engine
python dcf_engine.py

# Test DuPont engine
python dupont_engine.py
```

### Test API Endpoints (curl)

```bash
# Health check
curl http://localhost:8000/api/health

# Step 1: Search
curl -X POST http://localhost:8000/api/step-1-search \
  -H "Content-Type: application/json" \
  -d '{"query": "Apple", "market": "international"}'

# Step 7-8: Fetch data (after selecting ticker)
curl -X POST http://localhost:8000/api/step-7-8-fetch-data \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}'
```

### Pytest (if installed)

```bash
pip install pytest httpx pytest-asyncio
pytest tests/
```

## 🔧 Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
export PORT=8001
python main.py
```

### yfinance Data Issues

1. **Check internet connection**
2. **Verify ticker symbol**: Some tickers require exchange suffix (e.g., `VNM.HM` for Vietnam)
3. **Rate limiting**: Wait a few seconds between requests
4. **Try Alpha Vantage fallback**: Ensure `ALPHA_VANTAGE_KEY` is set

### AI Features Not Working

1. **Check API keys**: Verify `GEMINI_API_KEY` and/or `GROQ_API_KEY` in `.env`
2. **Network issues**: Ensure outbound HTTPS access
3. **Fallback mode**: System uses heuristics if AI is unavailable

### Dependencies Issues

```bash
# Upgrade pip
pip install --upgrade pip

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python version
python --version  # Should be 3.9+
```

### Virtual Environment Issues

```bash
# Deactivate and reactivate
deactivate
source venv/bin/activate  # Windows: venv\Scripts\activate

# Verify activation
which python  # Should point to venv
```

## 📦 Dependencies

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | ≥0.116.0 | Web framework |
| `uvicorn[standard]` | ≥0.35.0 | ASGI server |
| `aiohttp` | ≥3.9.0 | Async HTTP client |
| `yfinance` | ≥1.0.0 | Yahoo Finance data |
| `pydantic` | ≥2.0.0 | Data validation |
| `python-dotenv` | ≥1.0.0 | Environment variables |

### Optional Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `groq` | ≥0.11.0 | Groq LLM client |
| `google-generativeai` | ≥0.8.0 | Google Gemini SDK |
| `pytest` | ≥8.0.0 | Testing framework |
| `httpx` | ≥0.27.0 | Async testing client |

### Install All (including optional)

```bash
pip install fastapi uvicorn[standard] aiohttp yfinance pydantic python-dotenv groq google-generativeai pytest httpx
```

## 📝 License

Same as the original project.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📞 Support

For issues or questions:
1. Check the [FLOW_IMPLEMENTATION.md](./FLOW_IMPLEMENTATION.md) for detailed workflow docs
2. Review the interactive API docs at `/docs`
3. Check the troubleshooting section above
