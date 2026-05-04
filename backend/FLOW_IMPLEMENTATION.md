# 🔄 Updated API Flow Implementation

## ✅ Implemented Dual-Market Architecture

The backend has been completely refactored to support **strictly separated** International and Vietnamese workflows:

### **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────────┐
│                        MARKET ROUTING                           │
│  /api/* or /international/* → International Workflow            │
│  /vietnamese/*              → Vietnamese Workflow               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    INTERNATIONAL WORKFLOW                       │
│  Models: international_inputs.py                                │
│  Service: dcf_input_manager.py (ValuationInputManager)          │
│  Engines: dcf_engine.py, dupont_engine.py, comps_engine.py      │
│  Data: yfinance, Alpha Vantage                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     VIETNAMESE WORKFLOW                         │
│  Models: vietnamese_inputs.py                                   │
│  Service: vietnamese_input_manager.py                           │
│  Engines: vietnamese_dcf_engine.py                              │
│  Data: vndirect, cafef, VNStockDatabase                         │
│  Standards: TT99 accounting, VND currency, 20% tax rate         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 International API Endpoints

### **1. DCF Valuation**
```http
POST /international/valuate
Content-Type: application/json

{
  "ticker": "AAPL",
  "years": [2024, 2025, 2026, 2027, 2028],
  "risk_free_rate": 0.045,
  "market_risk_premium": 0.06,
  "terminal_growth_rate": 0.025,
  "shares_outstanding": 15552000000,
  "custom_assumptions": {
    "revenue_growth": [0.08, 0.07, 0.06, 0.05, 0.04],
    "ebitda_margin": [0.30, 0.31, 0.32, 0.32, 0.33]
  }
}
```

**Response:**
```json
{
  "status": "success",
  "results": {
    "enterprise_value": 2850000000000,
    "equity_value": 2780000000000,
    "implied_share_price": 185.50,
    "current_price": 178.72,
    "upside_downside": "3.79%",
    "wacc": 0.1157,
    "sensitivity_matrix": {...},
    "scenario_analysis": {
      "bull_case": 222.60,
      "base_case": 185.50,
      "bear_case": 148.40
    }
  }
}
```

---

### **2. Comparable Company Analysis**
```http
POST /international/comps
Content-Type: application/json

{
  "target_ticker": "AAPL",
  "peer_list": ["MSFT", "GOOGL", "META"],
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "apply_outlier_filtering": true,
  "iqr_multiplier": 1.5
}
```

**Response:**
```json
{
  "status": "success",
  "results": {
    "target_multiple": 28.5,
    "peer_median_ev_ebitda": 25.5,
    "peer_mean_ev_ebitda": 26.8,
    "implied_valuation": 2750000000000,
    "filtered_peers": ["MSFT", "GOOGL"],
    "outliers_removed": ["META"]
  }
}
```

---

### **3. DuPont Analysis**
```http
POST /international/dupont
Content-Type: application/json

{
  "ticker": "AAPL",
  "years": [2021, 2022, 2023, 2024],
  "custom_ratios": null
}
```

**Response:**
```json
{
  "status": "success",
  "results": {
    "roe_breakdown": [
      {
        "year": 2024,
        "net_profit_margin": 0.256,
        "asset_turnover": 1.12,
        "equity_multiplier": 6.5,
        "roe": 1.86
      }
    ],
    "trend_analysis": "Improving ROE driven by margin expansion..."
  }
}
```

---

## 📋 Vietnamese API Endpoints

### **1. Vietnamese DCF Valuation**
```http
POST /vietnamese/vn-valuate
Content-Type: application/json

{
  "ticker": "VNM",
  "exchange": "HOSE",
  "years": [2024, 2025, 2026, 2027, 2028],
  "risk_free_rate": 0.068,
  "market_risk_premium": 0.075,
  "terminal_growth_rate": 0.05,
  "tax_rate": 0.20,
  "shares_outstanding": 865000000,
  "custom_assumptions": {
    "revenue_growth": [0.10, 0.09, 0.08, 0.07, 0.06],
    "ebitda_margin": [0.18, 0.19, 0.20, 0.20, 0.21]
  }
}
```

**Response:**
```json
{
  "status": "success",
  "currency": "VND",
  "results": {
    "enterprise_value": 185000000000000,
    "equity_value": 178000000000000,
    "implied_share_price": 205800,
    "current_price": 195000,
    "upside_downside": "5.54%",
    "wacc": 0.1220,
    "tax_rate_applied": 0.20
  }
}
```

---

### **2. Vietnamese Comps**
```http
POST /vietnamese/vn-comps
Content-Type: application/json

{
  "target_ticker": "VNM",
  "peer_list": ["MSN", "SAB", "GVR"],
  "sector": "Consumer Goods",
  "index_filter": "VNINDEX",
  "apply_outlier_filtering": true,
  "iqr_multiplier": 1.5
}
```

**Response:**
```json
{
  "status": "success",
  "currency": "VND",
  "results": {
    "target_multiple": 15.2,
    "peer_median_ev_ebitda": 12.5,
    "implied_valuation": 165000000000000,
    "filtered_peers": ["MSN", "SAB"],
    "outliers_removed": []
  }
}
```

---

### **3. Vietnamese DuPont**
```http
POST /vietnamese/vn-dupont
Content-Type: application/json

{
  "ticker": "VCB",
  "exchange": "HOSE",
  "years": [2021, 2022, 2023, 2024]
}
```

**Response:**
```json
{
  "status": "success",
  "currency": "VND",
  "accounting_standard": "TT99",
  "results": {
    "roe_breakdown": [
      {
        "year": 2024,
        "net_profit_margin": 0.32,
        "asset_turnover": 0.08,
        "equity_multiplier": 12.5,
        "roe": 0.32
      }
    ],
    "trend_analysis": "Strong ROE driven by high equity multiplier typical in banking..."
  }
}
```

---

## 🔧 Key Features

### **Market Isolation**
- ✅ **International**: US stocks (NYSE, NASDAQ) with USD, US GAAP
- ✅ **Vietnamese**: HOSE/HNX/UPCOM with VND, TT99 standards
- ✅ **No cross-contamination**: Separate models, services, engines, routes

### **Vietnam-Specific Features**
- Ticker validation (rejects non-VN formats like AAPL, MSFT)
- VND currency throughout
- 20% corporate tax rate (vs. 21% US)
- 6.8% risk-free rate (10-year government bond)
- 7.5% market risk premium (emerging market)
- Terminal growth capped at 6% (aligned with GDP growth)
- TT99 accounting standards compliance

### **Data Sources**
- **International**: yfinance, Alpha Vantage
- **Vietnamese**: vndirect, cafef, VNStockDatabase

### **Error Handling**
- Clear error messages for invalid tickers
- Validates market-specific constraints
- Handles missing financial data gracefully
- IQR outlier filtering for comps analysis

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
├── main.py                          # Entry point
├── .env                             # API keys (secure)
│
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── international_routes.py
│   │       └── vietnamese_routes.py  # ← Dedicated VN routes
│   │
│   ├── models/
│   │   ├── international_inputs.py   # ← International models
│   │   └── vietnamese_inputs.py      # ← VN models (TT99, VND)
│   │
│   ├── services/
│   │   ├── dcf_input_manager.py          # ← International service
│   │   └── vietnamese_input_manager.py   # ← VN service
│   │
│   └── engines/
│       ├── dcf_engine.py                 # ← International DCF
│       ├── dupont_engine.py
│       ├── comps_engine.py
│       └── vietnamese_dcf_engine.py      # ← VN DCF (20% tax)
│
└── draft/                         # Legacy code (deprecated)
```

---

## ⚠️ Security Reminder

**Never commit API keys to version control.** All sensitive credentials must be stored in `.env` file and excluded from git.

If any keys are accidentally exposed:
1. Revoke them immediately via the provider's dashboard
2. Generate new keys
3. Update `.env` locally
4. Never push `.env` to remote repositories
