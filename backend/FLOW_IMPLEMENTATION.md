# 🔄 Updated API Flow Implementation

## ✅ Implemented 12-Step Workflow

The backend has been completely refactored to follow your specified flow:

### **Flow Overview**

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: User Input                                             │
│  POST /api/step-1-search                                        │
│  { query: "AAPL", market: "international" | "vietnamese" }      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: Show Related Tickers (up to 10)                        │
│  Response: [{ symbol, name, exchange, market }, ...]            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: User Chooses Ticker                                    │
│  POST /api/step-3-select-ticker                                 │
│  { ticker: "AAPL", market: "international" }                    │
│  → Creates session, returns session_id                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: User Chooses Models                                    │
│  POST /api/step-4-select-models                                 │
│  { session_id, models: ["DCF", "DuPont", "COMPS"] }             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 5-6: Show Required Inputs & User Confirms                 │
│  POST /api/step-5-6-prepare-inputs                              │
│  Returns: { status: "ready_to_fetch", required_inputs: [...] }  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 7-8: Fetch Data (yFinance + Alpha Vantage)                │
│  POST /api/step-7-8-fetch-data                                  │
│  Returns: Financial data with profile, income stmt, balance     │
│  sheet, cash flow. Shows errors if any.                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 9: AI Engine Analysis                                     │
│  POST /api/step-9-generate-ai                                   │
│  Returns: {                                                     │
│    wacc, terminal_growth, revenue_growth_forecast,              │
│    benchmarks, trend_analysis, risk_factors, explanation        │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 10: User Review & Confirm Assumptions                     │
│  POST /api/step-10-confirm-assumptions                          │
│  User can edit AI suggestions or accept defaults                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 11: Valuation Engine                                      │
│  Internal calculation using confirmed assumptions               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step 12: Show Results                                          │
│  POST /api/step-11-12-valuate                                   │
│  Returns: {                                                     │
│    enterprise_value, equity_value, implied_share_price,         │
│    current_price, upside_downside,                              │
│    sensitivity_matrix, scenario_analysis                        │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 API Endpoints Reference

### **1. Search Tickers**
```http
POST /api/step-1-search
Content-Type: application/json

{
  "query": "Apple",
  "market": "international"  // or "vietnamese"
}
```

**Response:**
```json
{
  "results": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "exchange": "NASDAQ",
      "market": "international"
    }
  ]
}
```

---

### **2. Select Ticker**
```http
POST /api/step-3-select-ticker
Content-Type: application/json

{
  "ticker": "AAPL",
  "market": "international"
}
```

**Response:**
```json
{
  "session_id": "uuid-here",
  "status": "ready_for_model_selection"
}
```

---

### **3. Select Models**
```http
POST /api/step-4-select-models
Content-Type: application/json

{
  "session_id": "uuid-here",
  "models": ["DCF", "DuPont"]
}
```

---

### **4. Prepare Inputs**
```http
POST /api/step-5-6-prepare-inputs
Content-Type: application/json

{
  "session_id": "uuid-here"
}
```

---

### **5. Fetch Financial Data**
```http
POST /api/step-7-8-fetch-data
Content-Type: application/json

{
  "session_id": "uuid-here"
}
```

**Response:**
```json
{
  "status": "data_ready",
  "data": {
    "profile": {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "sector": "Technology",
      "current_price": 178.72,
      "beta": 1.29
    },
    "financials": {
      "revenue": {...},
      "ebitda": {...},
      "net_income": {...}
    }
  }
}
```

---

### **6. Generate AI Assumptions**
```http
POST /api/step-9-generate-ai
Content-Type: application/json

{
  "session_id": "uuid-here"
}
```

**Response:**
```json
{
  "status": "ai_ready",
  "suggestions": {
    "wacc": 0.1157,
    "terminal_growth": 0.023,
    "revenue_growth_forecast": [0.08, 0.07, 0.06, 0.05, 0.04],
    "benchmarks": {
      "peer_ev_ebitda": 25.5,
      "sector_operating_margin": 0.28
    },
    "trend_analysis": "Company shows strong revenue growth...",
    "risk_factors": ["Interest rate risk", "Competition"],
    "explanation": "WACC calculated at 11.57% based on beta of 1.29..."
  }
}
```

---

### **7. Confirm Assumptions**
```http
POST /api/step-10-confirm-assumptions
Content-Type: application/json

{
  "session_id": "uuid-here",
  "assumptions": {
    "wacc": 0.10,  // User modified
    "terminal_growth": 0.025  // User modified
  }
}
```

---

### **8. Run Valuation**
```http
POST /api/step-11-12-valuate
Content-Type: application/json

{
  "session_id": "uuid-here"
}
```

**Response:**
```json
{
  "status": "completed",
  "results": {
    "enterprise_value": 2850000000000,
    "equity_value": 2780000000000,
    "implied_share_price": 185.50,
    "current_price": 178.72,
    "upside_downside": "3.79%",
    "sensitivity_matrix": {
      "wacc_range": [0.09, 0.10, 0.11],
      "tg_range": [0.02, 0.025, 0.03],
      "values": [[...], [...], [...]]
    },
    "scenario_analysis": {
      "bull_case": 222.60,
      "base_case": 185.50,
      "bear_case": 148.40
    }
  }
}
```

---

### **9. Check Session Status**
```http
GET /api/session/{session_id}
```

---

## 🔧 Key Features

### **Market Support**
- ✅ **International**: US stocks (NYSE, NASDAQ)
- ✅ **Vietnamese**: HOSE, HNX (`.VN` suffix auto-applied)

### **Session Management**
- In-memory session store (replace with Redis for production)
- Tracks state through all 12 steps
- Prevents invalid state transitions

### **AI Integration**
- Uses Gemini/Groq for assumption generation
- Provides benchmarks, trends, and explanations
- Falls back to safe defaults if AI unavailable

### **Error Handling**
- Clear error messages at each step
- Validates session state before proceeding
- Handles missing financial data gracefully

---

## 🚀 Running the Server

```bash
cd /workspace/backend
python main.py
```

Server starts on `http://localhost:8000`

**API Docs:** `http://localhost:8000/docs`

---

## 📁 File Structure

```
/workspace/backend/
├── main.py                 # ← New flow-based API
├── .env                    # API keys (secure)
├── dcf_engine.py           # DCF calculations
├── dupont_engine.py        # DuPont analysis
├── yfinance_data.py        # Data fetching utilities
└── draft/                  # Old Node.js code
    ├── server.js
    └── main_old.py
```

---

## ⚠️ Security Reminder

**Revoke and regenerate all exposed API keys immediately:**
- Alpha Vantage: `6C9PVD26RCB82IKQ`
- Google Gemini: `AIzaSyC2lANxt0DEUjDY-wiajpu__sGe2Qc9sfA`
- Groq: `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`

Then update `/workspace/backend/.env` with new keys.
