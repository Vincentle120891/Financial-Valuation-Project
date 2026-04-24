# Python Backend Setup Guide

## Migration Complete

The Node.js backend has been migrated to Python/FastAPI. All original Node.js files have been moved to `/workspace/backend/draft/` for reference.

## Project Structure

```
/workspace/
├── backend/
│   ├── main.py              # Main FastAPI application (entry point)
│   ├── dcf_engine.py        # DCF valuation engine
│   ├── dupont_engine.py     # DuPont analysis engine
│   ├── yfinance_data.py     # Yahoo Finance data provider
│   ├── .env                 # Environment variables (API keys)
│   ├── .env.example         # Template for environment variables
│   ├── requirements.txt     # Python dependencies
│   └── draft/               # Original Node.js code (archived)
│       ├── server.js
│       ├── dcf-engine.js
│       ├── dupont-engine.js
│       └── ...
└── frontend/                # React frontend (unchanged)
```

## Configuration

### API Keys

Your API keys are now stored securely in `/workspace/backend/.env`:

- **Alpha Vantage**: `6C9PVD26RCB82IKQ`
- **Google Gemini**: `AIzaSyC2lANxt0DEUjDY-wiajpu__sGe2Qc9sfA` (model: `gemini-3.1-flash-lite-preview`)
- **Groq**: `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` (model: `qwen/qwen3-32b`)

⚠️ **Security Warning**: These keys are hardcoded in the `.env` file. In production:
1. Never commit `.env` to version control
2. Use secret management services (AWS Secrets Manager, Azure Key Vault, etc.)
3. Rotate keys regularly

## Installation

```bash
cd /workspace/backend

# Install dependencies
pip install -r requirements.txt

# Or install manually
pip install fastapi uvicorn aiohttp yfinance groq pydantic python-dotenv
```

## Running the Server

```bash
cd /workspace/backend
python main.py
```

The server will start on `http://localhost:8000` (or the port specified in `.env`).

## API Endpoints

The Python backend provides the same API endpoints as the Node.js version:

- `GET /api/health` - Health check
- `POST /api/company/select` - Select company ticker
- `POST /api/model/select` - Select valuation model
- `POST /api/data/fetch` - Fetch financial data
- `POST /api/dcf/calculate` - Calculate DCF valuation
- `POST /api/dcf/validate` - Validate DCF inputs
- `POST /api/dupont/calculate` - Calculate DuPont analysis
- `POST /api/dupont/validate` - Validate DuPont inputs
- `GET /api/required-inputs-checklist` - Get required inputs checklist

## Frontend Integration

Update your frontend configuration to point to the new Python backend:

```javascript
// In your frontend config
const API_BASE_URL = 'http://localhost:8000/api';
```

## Key Changes from Node.js

1. **Framework**: Express.js → FastAPI
2. **Port**: Default changed from 5000 to 8000
3. **Environment Variables**: Using `python-dotenv` instead of `dotenv`
4. **Async Handling**: Native Python async/await
5. **Data Validation**: Pydantic models for request/response validation

## Testing

```bash
# Test health endpoint
curl http://localhost:8000/api/health

# Test with your frontend
# Start the backend first, then run your frontend dev server
```
