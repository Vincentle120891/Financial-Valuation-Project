# Financial Valuation Backend - Python/FastAPI

This is the Python migration of the financial valuation backend, originally built with Node.js/Express. The migration was done to resolve issues with the yahoo-finance2 npm package by using the more reliable yfinance Python library.

## Features

- **FastAPI Framework**: Modern, fast (high-performance), easy-to-use API framework
- **yfinance Integration**: Reliable Yahoo Finance data fetching
- **DCF Valuation Engine**: Complete discounted cash flow analysis
- **DuPont Analysis**: 3-step and 5-step ROE decomposition
- **AI-Powered Suggestions**: Integration with Gemini and Groq for intelligent input suggestions
- **Alpha Vantage Integration**: Additional financial data source

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (optional):
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
- `ALPHA_VANTAGE_KEY`: Your Alpha Vantage API key (default: 'demo')
- `GEMINI_API_KEY`: Google Gemini API key (optional, for AI features)
- `GROQ_API_KEY`: Groq API key (optional, for AI fallback)
- `PORT`: Server port (default: 8000)

## Running the Server

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

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:

- **Interactive API Docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative API Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

## Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/search?q=AAPL` | Search for tickers |
| POST | `/api/select-company` | Select a company for analysis |
| GET | `/api/models` | Get available valuation models |
| POST | `/api/select-model` | Select a valuation model |
| GET | `/api/required-fields?model=DCF` | Get required input fields |
| POST | `/api/retrieve-data` | Fetch financial data for a ticker |
| GET | `/api/financial-data/{ticker}` | Get comprehensive financial data |
| GET | `/api/ai-inputs/{ticker}` | Get AI-suggested inputs |
| POST | `/api/confirm-values` | Confirm input values |
| GET | `/api/scenarios` | Get scenario templates |
| POST | `/api/select-scenario` | Select a scenario |
| POST | `/api/run-valuation` | Run valuation calculation |
| GET | `/api/results` | Get valuation results |
| POST | `/api/reset` | Reset state |

## Project Structure

```
backend/
├── main.py                 # FastAPI application (main entry point)
├── yfinance_data.py        # Yahoo Finance data fetching
├── dcf_engine.py           # DCF valuation calculations
├── dupont_engine.py        # DuPont analysis calculations
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create from .env.example)
└── README_PYTHON.md       # This file
```

## Migration Notes

### From Node.js to Python

The following components were migrated:

1. **Server**: Express.js → FastAPI
2. **Yahoo Finance**: yahoo-finance2 npm → yfinance Python
3. **DCF Engine**: JavaScript → Python
4. **DuPont Engine**: JavaScript → Python

### API Compatibility

The Python backend maintains API compatibility with the original Node.js version where possible. However, some endpoints may have slight differences in response structure.

### Frontend Configuration

Update your frontend's API base URL to point to the Python backend:

```javascript
// frontend/src/services/api.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
```

Note: The default port changed from 5000 (Node.js) to 8000 (FastAPI).

## Testing

### Test Individual Modules

```bash
# Test yfinance data fetching
python yfinance_data.py AAPL

# Test DCF engine
python dcf_engine.py

# Test DuPont engine
python dupont_engine.py
```

### Test API Endpoints

Using curl:
```bash
# Health check
curl http://localhost:8000/api/health

# Search for a ticker
curl "http://localhost:8000/api/search?q=AAPL"

# Get financial data
curl http://localhost:8000/api/financial-data/AAPL
```

## Troubleshooting

### Port Already in Use

If port 8000 is already in use, change it:
```bash
export PORT=8001
python main.py
```

### yfinance Issues

If yfinance fails to fetch data:
1. Check your internet connection
2. Verify the ticker symbol is correct
3. Some international tickers may require exchange suffix (e.g., `VNM.HM` for Vietnam)

### AI Features Not Working

AI features are optional. If API keys are not provided, the system will use heuristic-based suggestions instead.

## Performance Considerations

- The Python backend uses async/await for I/O operations
- For production, consider using gunicorn with uvicorn workers
- Implement caching for frequently accessed data
- Consider using a database instead of in-memory state storage

## License

Same as the original project.
