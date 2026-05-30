# Complete API Response Format Reference
## 3 Valuation Methods × 2 Markets Architecture
**Current Focus: International Market Only** (Vietnam = Version 2)

---

## Table of Contents
1. [Core Data Types](#core-data-types)
2. [Step 1: Company Search & Selection](#step-1-company-search--selection)
3. [Step 2: Market Confirmation & Market Data](#step-2-market-confirmation--market-data)
4. [Step 3: Valuation Method Selection](#step-3-valuation-method-selection)
5. [Step 4: Peer Company Selection](#step-4-peer-company-selection)
6. [Step 5: Assumptions Preparation](#step-5-assumptions-preparation)
7. [Step 6: Data Fetching](#step-6-data-fetching)
8. [Step 7: Historical Data Processing](#step-7-historical-data-processing)
9. [Step 8: Assumptions & AI Suggestion Studio](#step-8-assumptions--ai-suggestion-studio)
10. [Step 9: Assumptions Confirmation](#step-9-assumptions-confirmation)
11. [Step 10: Valuation Execution](#step-10-valuation-execution)
12. [Utility Responses](#utility-responses)

---

## Core Data Types

### DataStatus Enum
```json
{
  "status": "RETRIEVED" | "CALCULATED" | "ESTIMATED" | "MISSING" | "MANUAL_OVERRIDE" | "CACHED"
}
```

### DataField (Universal Wrapper)
**Used for ALL numerical and categorical values across all steps**
```json
{
  "value": <any_type>,
  "status": "RETRIEVED",
  "source": "yfinance|vietstock|calculated|user_input|pdf_extraction",
  "formula": "string (if calculated)",
  "confidence_score": 85.5,
  "is_missing": false,
  "can_override": true,
  "unit": "USD|VND|%|days|x",
  "currency": "USD|VND",
  "reporting_period": "FY2023|Q1-2024",
  "last_updated": "2024-01-15T10:30:00Z",
  "description": "Field description for UI display"
}
```

### MissingDataSummary
```json
{
  "total_fields": 50,
  "retrieved_count": 45,
  "calculated_count": 3,
  "estimated_count": 1,
  "missing_count": 1,
  "manual_override_count": 0,
  "completion_percentage": 90.0,
  "critical_missing": ["risk_free_rate"],
  "optional_missing": ["country_risk_premium"],
  "valuation_ready": true,
  "data_quality_score": 85.5,
  "warnings": ["Some data is estimated"],
  "recommendations": ["Provide manual risk-free rate"]
}
```

### ValuationMethod Enum
```json
{
  "method": "DCF" | "DUPONT" | "COMPS"
}
```

### MarketType Enum
```json
{
  "market": "international" | "vietnam"
}
```

---

## Step 1: Company Search & Selection

### Endpoint
- **Frontend Call**: `searchCompanies(query, market)`
- **Backend Route**: `POST /api/step-1-search`
- **Service**: `step1_ticker_processor.py`

### Request Format
```json
{
  "query": "AAPL",
  "market": "international",
  "limit": 10
}
```

### Response Format: `UnifiedStep1Response`
```json
{
  "status": "success",
  "query": "AAPL",
  "market": "international",
  "results": [
    {
      "ticker": "AAPL",
      "company_name": "Apple Inc.",
      "exchange": "NASDAQ",
      "market": "international",
      "sector": "Technology",
      "industry": "Consumer Electronics",
      "currency": "USD",
      "country": "United States"
    }
  ],
  "total_results": 1,
  "message": "Found 1 company matching 'AAPL'"
}
```

---

## Step 2: Market Confirmation & Market Data

### Endpoint
- **Frontend Call**: `selectCompany(sessionId, ticker, market)`
- **Backend Route**: `POST /api/step-2-create-session`
- **Service**: `shared_context_service.py`

### Request Format
```json
{
  "session_id": "uuid-string",
  "ticker": "AAPL",
  "market": "international",
  "company_name": "Apple Inc."
}
```

### Response Format: `UnifiedStep2Response`
```json
{
  "status": "completed",
  "session_id": "uuid-string",
  "ticker": "AAPL",
  "market": "international",
  "company_name": "Apple Inc.",
  "confirmed": true,
  "market_data": [
    {
      "metric": "current_price",
      "value": 178.72,
      "source": "yfinance",
      "status": "RETRIEVED",
      "confidence_score": 100.0,
      "currency": "USD",
      "unit": "USD"
    },
    {
      "metric": "beta",
      "value": 1.29,
      "source": "yfinance",
      "status": "RETRIEVED",
      "confidence_score": 95.0,
      "currency": null,
      "unit": "ratio"
    },
    {
      "metric": "market_cap",
      "value": 2780000000000,
      "source": "yfinance",
      "status": "RETRIEVED",
      "confidence_score": 100.0,
      "currency": "USD",
      "unit": "USD"
    }
  ],
  "risk_metrics": {
    "risk_free_rate": {
      "value": 4.25,
      "status": "RETRIEVED",
      "source": "fred",
      "unit": "%",
      "confidence_score": 98.0
    },
    "market_risk_premium": {
      "value": 5.5,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "historical_equity_premium",
      "unit": "%",
      "confidence_score": 85.0
    },
    "beta": {
      "value": 1.29,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "ratio",
      "confidence_score": 95.0
    },
    "levered_beta": {
      "value": 1.29,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "beta",
      "unit": "ratio"
    },
    "unlevered_beta": {
      "value": 1.15,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "beta / (1 + (1 - tax_rate) * debt/equity)",
      "unit": "ratio"
    },
    "equity_risk_premium": {
      "value": 11.32,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "risk_free_rate + market_risk_premium * beta",
      "unit": "%"
    },
    "country_risk_premium": {
      "value": 0.0,
      "status": "RETRIEVED",
      "source": "default",
      "unit": "%"
    }
  },
  "market_code": null,
  "exchange_info": null,
  "missing_data": [],
  "warnings": [],
  "data_quality_score": 95.5,
  "message": "Market selection confirmed for AAPL (International)"
}
```

---

## Step 3: Valuation Method Selection

### Endpoint
- **Frontend Call**: `selectModels(sessionId, method, market)`
- **Backend Route**: `POST /api/step-3-select-models`
- **Service**: `step3_selected_models_processor.py`

### Request Format
```json
{
  "session_id": "uuid-string",
  "method": "DCF",
  "market": "international"
}
```

### Response Format: `UnifiedStep3Response`
```json
{
  "status": "success",
  "session_id": "uuid-string",
  "method": "DCF",
  "market": "international",
  "selected": true,
  "available_methods": ["DCF", "DUPONT", "COMPS"],
  "message": "DCF model selected for International market"
}
```

---

## Step 4: Peer Company Selection

### Endpoint
- **Frontend Call**: `suggestPeers(ticker, market, maxPeers, method, sessionId)`
- **Backend Route**: `POST /api/step-4-discover-peers`
- **Service**: `step4_dcf_discovery.py` | `step4_comps_discovery.py` | `step4_dupont_discovery.py`
- **Schema**: `UnifiedStep4Request` → `UnifiedStep4Response`

### Request Format
```json
{
  "ticker": "AAPL",
  "market": "international",
  "max_peers": 10,
  "method": "DCF",
  "session_id": "uuid-string"
}
```

**Field Descriptions:**
- `ticker`: Target company ticker symbol (string)
- `market`: Market type - "international" or "vietnam" (string, default: "international")
- `max_peers`: Maximum number of peers to return (integer, default: 10)
- `method`: Valuation method - "DCF", "DUPONT", or "COMPS" (string, optional)
- `session_id`: Session identifier for storing results (string)

### Response Format: `UnifiedStep4Response`
```json
{
  "status": "success",
  "session_id": "uuid-string",
  "method": "DCF",
  "market": "international",
  "target_company": "AAPL",
  "suggested_peers": [
    {
      "ticker": "MSFT",
      "company_name": "Microsoft Corporation",
      "sector": "Technology",
      "industry": "Software",
      "market_cap": {
        "value": 2800000000000,
        "status": "RETRIEVED",
        "source": "yfinance",
        "unit": "USD",
        "confidence_score": 100.0
      },
      "selected": false,
      "match_score": 92.5,
      "match_reasons": [
        "Segment overlap detected",
        "Industry: Software",
        "Market Cap: $2.80B"
      ],
      "segments": {
        "Cloud": 40,
        "Productivity": 35,
        "Personal Computing": 25
      },
      "pe_ratio": 35.2,
      "ev_to_ebitda": 22.5,
      "ps_ratio": 12.8
    },
    {
      "ticker": "GOOGL",
      "company_name": "Alphabet Inc.",
      "sector": "Technology",
      "industry": "Internet Content & Information",
      "market_cap": {
        "value": 1700000000000,
        "status": "RETRIEVED",
        "source": "yfinance",
        "unit": "USD",
        "confidence_score": 100.0
      },
      "selected": false,
      "match_score": 88.0,
      "match_reasons": [
        "Segment overlap detected",
        "Industry: Internet Content & Information",
        "Market Cap: $1.70B"
      ],
      "segments": {
        "Google Services": 88,
        "Google Cloud": 9,
        "Other Bets": 3
      },
      "pe_ratio": 25.8,
      "ev_to_ebitda": 18.2,
      "ps_ratio": 5.5
    }
  ],
  "selected_peers": [],
  "message": "Found 2 DCF peers using multi-segment analysis",
  "mandatory": false,
  "min_peers_recommended": 3,
  "diagnostics": {
    "engine_message": "Found 2 DCF peers using multi-segment analysis",
    "vendor_api_status": "SUCCESS",
    "local_db_fallback_triggered": false,
    "applied_constraints": {
      "initial_market_cap_range": "50% - 200%",
      "relaxed_constraints_applied": false,
      "sector_match_required": true,
      "industry_preference": "strict"
    },
    "critical_missing_metrics": [],
    "search_criteria": {
      "target_ticker": "AAPL",
      "method": "DCF",
      "max_peers_requested": 10,
      "market": "international"
    },
    "warnings": []
  }
}
```

**Field Descriptions:**
- `status`: Operation status - "success" or "error" (string)
- `session_id`: Session identifier (string)
- `method`: Valuation method used - "DCF", "DUPONT", or "COMPS" (string)
- `market`: Market type - "international" or "vietnam" (string)
- `target_company`: Target company ticker (string)
- `suggested_peers`: Array of peer company objects (array)
  - `ticker`: Peer company ticker symbol (string)
  - `company_name`: Full company name (string)
  - `sector`: Industry sector (string)
  - `industry`: Specific industry classification (string)
  - `market_cap`: DataField wrapper for market capitalization (object)
  - `selected`: Whether peer is selected by user (boolean, default: false)
  - `match_score`: Match score 0-100 (number)
  - `match_reasons`: Array of human-readable match reasons (array of strings)
  - `segments`: Business segment breakdown as percentages (object)
  - `pe_ratio`: P/E ratio (number, optional)
  - `ev_to_ebitda`: EV/EBITDA multiple (number, optional)
  - `ps_ratio`: P/S ratio (number, optional)
- `selected_peers`: Array of selected peer tickers (array of strings)
- `message`: Human-readable result message (string)
- `mandatory`: Whether peer selection is mandatory for this method (boolean)
  - DCF: false (optional for beta estimation)
  - DuPont: false (minimal peer requirement)
  - COMPS: true (strict peer requirement)
- `min_peers_recommended`: Minimum recommended peers for reliable analysis (number, optional)
- `diagnostics`: Diagnostic information for debugging and UI feedback (object)
  - `engine_message`: Detailed engine processing message (string)
  - `vendor_api_status`: External API status - "SUCCESS", "FAILED", "TIMEOUT" (string)
  - `local_db_fallback_triggered`: Whether local database fallback was used (boolean)
  - `applied_constraints`: Constraints applied during peer discovery (object)
    - `initial_market_cap_range`: Market cap range applied (string)
    - `relaxed_constraints_applied`: Whether constraints were relaxed (boolean)
    - `sector_match_required`: Whether sector match was required (boolean)
    - `industry_preference`: Industry matching strictness - "strict", "moderate", "broad" (string)
  - `critical_missing_metrics`: Array of critical missing metrics (array of strings)
  - `search_criteria`: Original search parameters (object)
  - `warnings`: Array of warning messages (array of strings)

**Method-Specific Behavior:**
- **DCF**: Market cap range 50%-200% (tight), focuses on similar risk profiles for beta estimation
- **DuPont**: Minimal peer requirement, returns empty or small set (optional for this method)
- **COMPS**: Strict sector/industry matching, enforces minimum peer count (mandatory)

### Step 4B: Save Selected Peers Endpoint

**Endpoint**
- **Frontend Call**: `savePeers(sessionId, peers)`
- **Backend Route**: `POST /api/step-4-save-peers`
- **Service**: `step4_peer_management_service.py`
- **Schema**: `SavePeersRequest` → `SavePeersResponse`

**Request Format**
```json
{
  "session_id": "uuid-string",
  "peers": [
    {
      "ticker": "MSFT",
      "company_name": "Microsoft Corporation",
      "sector": "Technology",
      "industry": "Software",
      "market_cap": 2800000000000,
      "selected": true,
      "match_score": 92.5
    },
    {
      "ticker": "GOOGL",
      "company_name": "Alphabet Inc.",
      "sector": "Technology",
      "industry": "Internet Content & Information",
      "market_cap": 1700000000000,
      "selected": true,
      "match_score": 88.0
    }
  ]
}
```

**Response Format: `SavePeersResponse`**
```json
{
  "status": "success",
  "message": "Successfully saved 2 peer companies for AAPL",
  "peers_saved": 2,
  "peer_data": {
    "tickers": ["MSFT", "GOOGL"],
    "stored_in_session": true,
    "ready_for_step_5": true
  }
}
```

**Field Descriptions:**
- `status`: Operation status - "success" or "error" (string)
- `message`: Human-readable result message (string)
- `peers_saved`: Number of peers successfully saved (number)
- `peer_data`: Optional detailed peer data stored in session (object, optional)
  - `tickers`: Array of saved peer tickers (array of strings)
  - `stored_in_session`: Confirmation that data is stored in session (boolean)
  - `ready_for_step_5`: Whether peer selection is complete for next step (boolean)

---

## Step 5: Assumptions Preparation

### Endpoint
- **Frontend Call**: `prepareAssumptions(sessionId, method, market, generateAi)`
- **Backend Route**: `POST /api/step-5-prepare-assumptions`
- **Service**: `step8_dcf_assumptions.py` | `step8_comps_assumptions.py` | `dupont_engine.py`

### Request Format
```json
{
  "session_id": "uuid-string",
  "method": "DCF",
  "market": "international",
  "generate_ai": true
}
```

### Response Format: `UnifiedStep5Response`
```json
{
  "status": "success",
  "session_id": "uuid-string",
  "method": "DCF",
  "market": "international",
  "categories": [
    {
      "category_name": "Revenue Drivers",
      "assumptions": {
        "revenue_growth_rate": {
          "value": 8.5,
          "status": "ESTIMATED",
          "source": "ai_generated",
          "unit": "%",
          "confidence_score": 75.0,
          "description": "Projected annual revenue growth rate"
        }
      },
      "requires_user_input": true,
      "ai_generated": true
    },
    {
      "category_name": "Margins",
      "assumptions": {
        "ebitda_margin": {
          "value": 30.2,
          "status": "CALCULATED",
          "source": "historical_average",
          "formula": "avg(ebitda/revenue) last 5 years",
          "unit": "%",
          "confidence_score": 90.0
        }
      },
      "requires_user_input": true,
      "ai_generated": false
    }
  ],
  "missing_data_summary": {
    "total_fields": 25,
    "retrieved_count": 20,
    "calculated_count": 3,
    "estimated_count": 2,
    "missing_count": 0,
    "manual_override_count": 0,
    "completion_percentage": 100.0,
    "critical_missing": [],
    "optional_missing": [],
    "valuation_ready": true,
    "data_quality_score": 88.5,
    "warnings": [],
    "recommendations": []
  },
  "ai_provider": "openai_gpt4",
  "message": "Assumptions prepared for DCF valuation"
}
```

---

## Step 6: Data Fetching (CRITICAL - Most Complex)

### Endpoint
- **Frontend Call**: `fetchApiData(sessionId, method, market)`
- **Backend Route**: `POST /api/step-6-fetch-api-data`
- **Service**: `step6_dcf_data_review.py` | `step6_comps_data_review.py` | `step6_dupont_data_review.py`
- **Transformer**: `step6_unified_transformer.py`

### Request Format
```json
{
  "session_id": "uuid-string",
  "market": "international",
  "method": "DCF",
  "history_years": 5,
  "include_quarterly": true,
  "use_cache": true
}
```

### Response Format: `UnifiedStep6Response`
```json
{
  "status": "success",
  "session_id": "uuid-string",
  "ticker": "AAPL",
  "market": "international",
  "method": "DCF",
  
  "historical_financials": {
    "revenue": {
      "value": 383285000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD",
      "reporting_period": "FY2023",
      "confidence_score": 100.0
    },
    "cogs": {
      "value": 214137000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD",
      "reporting_period": "FY2023"
    },
    "ebitda": {
      "value": 125820000000,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "operating_income + depreciation",
      "unit": "USD"
    },
    "net_income": {
      "value": 96995000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "operating_expenses": {
      "value": 54780000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "sg_and_a": {
      "value": 24932000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "depreciation": {
      "value": 11519000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "capex": {
      "value": -10959000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "free_cash_flow": {
      "value": 99584000000,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "operating_cash_flow + capex",
      "unit": "USD"
    },
    "operating_cash_flow": {
      "value": 110543000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "total_assets": {
      "value": 352755000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "total_debt": {
      "value": 111088000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "cash_and_equivalents": {
      "value": 29965000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "inventory": {
      "value": 6331000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "accounts_receivable": {
      "value": 29508000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "accounts_payable": {
      "value": 62611000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "shareholders_equity": {
      "value": 62146000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "revenue_cagr": {
      "value": 7.8,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "CAGR(revenue, 5 years)",
      "unit": "%"
    },
    "avg_ebitda_margin": {
      "value": 32.5,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "avg(ebitda/revenue)",
      "unit": "%"
    },
    "avg_roe": {
      "value": 156.2,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "avg(net_income/equity)",
      "unit": "%"
    },
    "avg_roa": {
      "value": 27.5,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "avg(net_income/assets)",
      "unit": "%"
    }
  },
  
  "forecast_drivers": {
    "revenue_growth_forecast": {
      "value": 6.5,
      "status": "ESTIMATED",
      "source": "analyst_consensus",
      "unit": "%"
    },
    "volume_growth_split": {
      "value": 4.2,
      "status": "ESTIMATED",
      "source": "ai_generated",
      "unit": "%"
    },
    "ebitda_margin_forecast": {
      "value": 32.0,
      "status": "CALCULATED",
      "source": "historical_average",
      "unit": "%"
    },
    "tax_rate": {
      "value": 15.8,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "tax_expense/pre_tax_income",
      "unit": "%"
    },
    "ar_days": {
      "value": 28,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "(AR/revenue)*365",
      "unit": "days"
    },
    "inv_days": {
      "value": 11,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "(inventory/cogs)*365",
      "unit": "days"
    },
    "ap_days": {
      "value": 107,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "(AP/cogs)*365",
      "unit": "days"
    },
    "capex_pct_of_revenue": {
      "value": 2.9,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "abs(capex)/revenue",
      "unit": "%"
    },
    "useful_life_existing": {
      "value": 7,
      "status": "ESTIMATED",
      "source": "industry_standard",
      "unit": "years"
    },
    "useful_life_new": {
      "value": 7,
      "status": "ESTIMATED",
      "source": "industry_standard",
      "unit": "years"
    },
    "risk_free_rate": {
      "value": 4.25,
      "status": "RETRIEVED",
      "source": "fred",
      "unit": "%"
    },
    "equity_risk_premium": {
      "value": 5.5,
      "status": "RETRIEVED",
      "source": "damodaran",
      "unit": "%"
    },
    "beta": {
      "value": 1.29,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "ratio"
    },
    "cost_of_debt": {
      "value": 3.8,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "interest_expense/total_debt",
      "unit": "%"
    },
    "wacc": {
      "value": 9.2,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "Re*E/V + Rd*(1-T)*D/V",
      "unit": "%"
    },
    "terminal_growth_rate": {
      "value": 2.5,
      "status": "ESTIMATED",
      "source": "gdp_growth",
      "unit": "%"
    },
    "terminal_ebitda_multiple": {
      "value": 12.5,
      "status": "ESTIMATED",
      "source": "industry_average",
      "unit": "x"
    }
  },
  
  "market_data": {
    "current_stock_price": {
      "value": 178.72,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD",
      "confidence_score": 100.0
    },
    "shares_outstanding": {
      "value": 15552752000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "shares"
    },
    "market_cap": {
      "value": 2780000000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "beta": {
      "value": 1.29,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "ratio"
    },
    "total_debt": {
      "value": 111088000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "cash": {
      "value": 29965000000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "currency": {
      "value": "USD",
      "status": "RETRIEVED",
      "source": "yfinance"
    },
    "fifty_two_week_high": {
      "value": 199.62,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "fifty_two_week_low": {
      "value": 143.90,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "average_volume": {
      "value": 57832000,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "shares"
    }
  },
  
  "dupont_metrics": {
    "net_profit_margin": {
      "value": 25.3,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "net_income/revenue",
      "unit": "%"
    },
    "return_on_assets": {
      "value": 27.5,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "net_income/total_assets",
      "unit": "%"
    },
    "return_on_equity": {
      "value": 156.2,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "net_income/shareholders_equity",
      "unit": "%"
    },
    "asset_turnover": {
      "value": 1.09,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "revenue/total_assets",
      "unit": "x"
    },
    "inventory_turnover": {
      "value": 33.8,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "cogs/inventory",
      "unit": "x"
    },
    "receivables_turnover": {
      "value": 13.0,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "revenue/accounts_receivable",
      "unit": "x"
    },
    "equity_multiplier": {
      "value": 5.68,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "total_assets/equity",
      "unit": "x"
    },
    "debt_to_equity": {
      "value": 1.79,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "total_debt/equity",
      "unit": "ratio"
    },
    "interest_coverage": {
      "value": 31.5,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "ebit/interest_expense",
      "unit": "x"
    }
  },
  
  "comps_multiples": {
    "ev_to_ebitda": {
      "value": 23.5,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "enterprise_value/ebitda",
      "unit": "x"
    },
    "ev_to_sales": {
      "value": 7.2,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "enterprise_value/revenue",
      "unit": "x"
    },
    "ev_to_ebit": {
      "value": 25.8,
      "status": "CALCULATED",
      "source": "calculated",
      "unit": "x"
    },
    "p_to_e": {
      "value": 28.7,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "price/eps",
      "unit": "x"
    },
    "p_to_b": {
      "value": 44.8,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "market_cap/equity",
      "unit": "x"
    },
    "p_to_sales": {
      "value": 7.3,
      "status": "CALCULATED",
      "source": "calculated",
      "formula": "market_cap/revenue",
      "unit": "x"
    },
    "companies": [
      {
        "ticker": "MSFT",
        "company_name": "Microsoft Corporation",
        "ev_to_ebitda": 22.5,
        "p_to_e": 35.2,
        "market_cap": 2800000000000
      },
      {
        "ticker": "GOOGL",
        "company_name": "Alphabet Inc.",
        "ev_to_ebitda": 18.2,
        "p_to_e": 25.8,
        "market_cap": 1700000000000
      }
    ]
  },
  
  "data_source": "yfinance",
  "fetch_timestamp": "2024-01-15T10:30:00Z",
  "cache_used": false,
  "periods_covered": ["FY2019", "FY2020", "FY2021", "FY2022", "FY2023"],
  
  "missing_data_summary": {
    "total_fields": 60,
    "retrieved_count": 45,
    "calculated_count": 13,
    "estimated_count": 2,
    "missing_count": 0,
    "manual_override_count": 0,
    "completion_percentage": 100.0,
    "critical_missing": [],
    "optional_missing": [],
    "valuation_ready": true,
    "data_quality_score": 92.5,
    "warnings": [],
    "recommendations": []
  },
  
  "data_quality_flags": [],
  "warnings": [],
  "message": "Successfully fetched all data for DCF valuation"
}
```

---

## Step 7: Historical Data Processing

### Endpoint
- **Frontend Call**: `retrieveHistoricalData(sessionId, method, market)`
- **Backend Route**: `POST /api/step-7-retrieve-historical-data`
- **Service**: `step7_dcf_historical_data.py` | `step7_comps_historical_data.py` | `step7_dupont_historical_data.py`
- **Processor**: `step7_historical_data_processor.py`

### Request Format
```json
{
  "session_id": "uuid-string",
  "method": "DCF",
  "market": "international",
  "adjustments": {
    "one_time_items": ["restructuring_charge_2022"],
    "currency_normalization": true
  }
}
```

### Response Format: `UnifiedStep7Response`
```json
{
  "status": "success",
  "session_id": "uuid-string",
  "method": "DCF",
  "market": "international",
  "processed_periods": [
    {
      "period": "FY2023",
      "year": 2023,
      "metrics": {
        "revenue": {
          "value": 383285000000,
          "status": "RETRIEVED",
          "unit": "USD"
        },
        "ebitda": {
          "value": 125820000000,
          "status": "CALCULATED",
          "unit": "USD"
        },
        "net_income": {
          "value": 96995000000,
          "status": "RETRIEVED",
          "unit": "USD"
        }
      },
      "growth_rates": {
        "revenue_growth": {
          "value": 2.8,
          "unit": "%"
        },
        "ebitda_growth": {
          "value": 5.2,
          "unit": "%"
        }
      },
      "margins": {
        "gross_margin": {
          "value": 44.1,
          "unit": "%"
        },
        "ebitda_margin": {
          "value": 32.8,
          "unit": "%"
        },
        "net_margin": {
          "value": 25.3,
          "unit": "%"
        }
      }
    },
    {
      "period": "FY2022",
      "year": 2022,
      "metrics": {
        "revenue": {
          "value": 394328000000,
          "status": "RETRIEVED",
          "unit": "USD"
        }
      },
      "growth_rates": {
        "revenue_growth": {
          "value": 7.8,
          "unit": "%"
        }
      }
    }
  ],
  "trend_analysis": {
    "revenue_trend": {
      "value": "increasing",
      "cagr_5y": 7.8,
      "volatility": "low"
    },
    "margin_trend": {
      "value": "stable",
      "avg_ebitda_margin": 32.5,
      "volatility": "low"
    }
  },
  "adjustments_applied": [
    "Removed one-time restructuring charge from FY2022",
    "Normalized currency effects"
  ],
  "missing_data_summary": {
    "total_fields": 40,
    "retrieved_count": 38,
    "calculated_count": 2,
    "missing_count": 0,
    "completion_percentage": 100.0,
    "critical_missing": [],
    "valuation_ready": true,
    "data_quality_score": 95.0
  },
  "message": "Historical data processed successfully with 2 adjustments applied"
}
```

---

## Step 8: Assumptions & AI Suggestion Studio

### Endpoints

#### 8.1 Initialize Assumptions
- **Frontend Call**: `initializeStep8Assumptions(sessionId, method, market)`
- **Backend Route**: `POST /api/step-8-initialize`
- **Service**: `step8_manual_overrides.py`

#### 8.2 Generate AI Suggestion
- **Frontend Call**: `generateAISuggestion(sessionId, category, method, market)`
- **Backend Route**: `POST /api/step-8-generate-ai-suggestion`
- **Service**: `ai_engine.py`

#### 8.3 Apply Override
- **Frontend Call**: Internal state management (no direct API call)
- **Backend Route**: Applied during Step 9 confirmation

### Request Formats

#### Initialize Request
```json
{
  "session_id": "uuid-string",
  "method": "DCF",
  "market": "international",
  "include_ai_suggestions": false
}
```

#### Generate AI Suggestion Request
```json
{
  "session_id": "uuid-string",
  "method": "DCF",
  "market": "international",
  "category": "REVENUE_DRIVERS"
}
```

### Response Format: `UnifiedStep8Response`
```json
{
  "status": "success",
  "session_id": "uuid-string",
  "method": "DCF",
  "market": "international",
  "operation_type": "initialize",
  "ticker": "AAPL",
  "valuation_model": "DCF",
  
  "categories": {
    "REVENUE_DRIVERS": {
      "category": "REVENUE_DRIVERS",
      "category_name": "Revenue Drivers",
      "assumptions": [
        {
          "metric": "revenue_growth_rate",
          "category": "REVENUE_DRIVERS",
          "description": "Annual revenue growth rate for forecast period",
          "unit": "%",
          
          "historical_trendline": {
            "metric": "revenue_growth_rate",
            "trend_points": [
              {"year": 2019, "value": 2.0, "label": "FY2019"},
              {"year": 2020, "value": 5.5, "label": "FY2020"},
              {"year": 2021, "value": 33.3, "label": "FY2021"},
              {"year": 2022, "value": 7.8, "label": "FY2022"},
              {"year": 2023, "value": -2.8, "label": "FY2023"}
            ],
            "average": 9.16,
            "cagr": 7.8,
            "trend_direction": "stable",
            "volatility": "high"
          },
          
          "ai_suggestion": {
            "metric": "revenue_growth_rate",
            "suggested_value": 6.5,
            "reasoning": "Based on historical CAGR of 7.8%, analyst consensus of 6.2%, and maturing smartphone market. Conservative estimate accounts for services growth offsetting hardware saturation.",
            "confidence_level": "high",
            "min_range": 4.0,
            "max_range": 9.0,
            "category": "REVENUE_DRIVERS"
          },
          
          "user_value": null,
          "final_value": 6.5,
          "status": "DEFAULT",
          
          "is_valid": true,
          "validation_message": null,
          "warning_message": null,
          
          "is_multi_year": true,
          "year_values": {
            "1": 7.0,
            "2": 6.5,
            "3": 6.0,
            "4": 5.5,
            "5": 5.0
          }
        },
        {
          "metric": "volume_growth",
          "category": "REVENUE_DRIVERS",
          "description": "Unit volume growth component of revenue",
          "unit": "%",
          "historical_trendline": null,
          "ai_suggestion": {
            "metric": "volume_growth",
            "suggested_value": 3.5,
            "reasoning": "Volume growth typically lags revenue growth in mature markets. Services mix shift reduces volume dependency.",
            "confidence_level": "medium",
            "min_range": 2.0,
            "max_range": 5.0,
            "category": "REVENUE_DRIVERS"
          },
          "user_value": null,
          "final_value": 3.5,
          "status": "DEFAULT",
          "is_valid": true,
          "is_multi_year": false
        }
      ],
      "ai_generated": true,
      "generation_timestamp": "2024-01-15T10:35:00Z",
      "message": "AI suggestions generated based on historical trends and analyst consensus"
    },
    
    "COST_MARGINS": {
      "category": "COST_MARGINS",
      "category_name": "Cost & Margins",
      "assumptions": [
        {
          "metric": "ebitda_margin",
          "category": "COST_MARGINS",
          "description": "EBITDA margin as percentage of revenue",
          "unit": "%",
          "historical_trendline": {
            "metric": "ebitda_margin",
            "trend_points": [
              {"year": 2019, "value": 29.5},
              {"year": 2020, "value": 31.2},
              {"year": 2021, "value": 33.8},
              {"year": 2022, "value": 32.5},
              {"year": 2023, "value": 32.8}
            ],
            "average": 31.96,
            "cagr": null,
            "trend_direction": "increasing",
            "volatility": "low"
          },
          "ai_suggestion": {
            "metric": "ebitda_margin",
            "suggested_value": 32.5,
            "reasoning": "Historical average of 32.0% with upward trend. Maintaining at recent levels reflects operational efficiency gains.",
            "confidence_level": "high",
            "min_range": 30.0,
            "max_range": 35.0,
            "category": "COST_MARGINS"
          },
          "user_value": null,
          "final_value": 32.5,
          "status": "DEFAULT",
          "is_valid": true,
          "is_multi_year": true,
          "year_values": {
            "1": 32.5,
            "2": 32.8,
            "3": 33.0,
            "4": 33.0,
            "5": 33.0
          }
        },
        {
          "metric": "tax_rate",
          "category": "COST_MARGINS",
          "description": "Effective corporate tax rate",
          "unit": "%",
          "historical_trendline": null,
          "ai_suggestion": {
            "metric": "tax_rate",
            "suggested_value": 15.8,
            "reasoning": "Based on historical effective tax rate. Lower than statutory rate due to international operations and tax credits.",
            "confidence_level": "high",
            "min_range": 14.0,
            "max_range": 18.0,
            "category": "COST_MARGINS"
          },
          "user_value": null,
          "final_value": 15.8,
          "status": "DEFAULT",
          "is_valid": true,
          "is_multi_year": false
        }
      ],
      "ai_generated": true,
      "generation_timestamp": "2024-01-15T10:35:00Z",
      "message": ""
    },
    
    "WORKING_CAPITAL": {
      "category": "WORKING_CAPITAL",
      "category_name": "Working Capital",
      "assumptions": [
        {
          "metric": "ar_days",
          "category": "WORKING_CAPITAL",
          "description": "Days sales outstanding (Accounts Receivable)",
          "unit": "days",
          "historical_trendline": {
            "metric": "ar_days",
            "trend_points": [
              {"year": 2019, "value": 26},
              {"year": 2020, "value": 27},
              {"year": 2021, "value": 26},
              {"year": 2022, "value": 28},
              {"year": 2023, "value": 28}
            ],
            "average": 27.0,
            "trend_direction": "stable",
            "volatility": "low"
          },
          "ai_suggestion": {
            "metric": "ar_days",
            "suggested_value": 28,
            "reasoning": "Consistent with historical average. No significant changes expected in collection policies.",
            "confidence_level": "high",
            "min_range": 25,
            "max_range": 32,
            "category": "WORKING_CAPITAL"
          },
          "user_value": null,
          "final_value": 28,
          "status": "DEFAULT",
          "is_valid": true,
          "is_multi_year": false
        },
        {
          "metric": "inv_days",
          "category": "WORKING_CAPITAL",
          "description": "Days inventory outstanding",
          "unit": "days",
          "ai_suggestion": {
            "metric": "inv_days",
            "suggested_value": 11,
            "reasoning": "Apple maintains industry-leading inventory turnover. Expect consistency with historical levels.",
            "confidence_level": "high",
            "min_range": 9,
            "max_range": 14,
            "category": "WORKING_CAPITAL"
          },
          "user_value": null,
          "final_value": 11,
          "status": "DEFAULT",
          "is_valid": true,
          "is_multi_year": false
        },
        {
          "metric": "ap_days",
          "category": "WORKING_CAPITAL",
          "description": "Days payable outstanding",
          "unit": "days",
          "ai_suggestion": {
            "metric": "ap_days",
            "suggested_value": 107,
            "reasoning": "Apple's strong supplier relationships allow extended payment terms. Consistent with historical performance.",
            "confidence_level": "high",
            "min_range": 100,
            "max_range": 115,
            "category": "WORKING_CAPITAL"
          },
          "user_value": null,
          "final_value": 107,
          "status": "DEFAULT",
          "is_valid": true,
          "is_multi_year": false
        }
      ],
      "ai_generated": true,
      "generation_timestamp": "2024-01-15T10:35:00Z",
      "message": ""
    },
    
    "WACC_COMPONENTS": {
      "category": "WACC_COMPONENTS",
      "category_name": "WACC Components",
      "assumptions": [
        {
          "metric": "risk_free_rate",
          "category": "WACC_COMPONENTS",
          "description": "10-year US Treasury yield",
          "unit": "%",
          "ai_suggestion": {
            "metric": "risk_free_rate",
            "suggested_value": 4.25,
            "reasoning": "Current 10-year US Treasury yield as of valuation date.",
            "confidence_level": "high",
            "min_range": 3.5,
            "max_range": 5.0,
            "category": "WACC_COMPONENTS"
          },
          "user_value": null,
          "final_value": 4.25,
          "status": "DEFAULT",
          "is_valid": true,
          "is_multi_year": false
        },
        {
          "metric": "equity_risk_premium",
          "category": "WACC_COMPONENTS",
          "description": "Market equity risk premium",
          "unit": "%",
          "ai_suggestion": {
            "metric": "equity_risk_premium",
            "suggested_value": 5.5,
            "reasoning": "Based on Damodaran's current ERP estimate for US market.",
            "confidence_level": "high",
            "min_range": 4.5,
            "max_range": 6.5,
            "category": "WACC_COMPONENTS"
          },
          "user_value": null,
          "final_value": 5.5,
          "status": "DEFAULT",
          "is_valid": true,
          "is_multi_year": false
        },
        {
          "metric": "beta",
          "category": "WACC_COMPONENTS",
          "description": "Levered equity beta",
          "unit": "ratio",
          "ai_suggestion": {
            "metric": "beta",
            "suggested_value": 1.29,
            "reasoning": "5-year monthly regression beta from yfinance. Reflects Apple's systematic risk relative to market.",
            "confidence_level": "high",
            "min_range": 1.1,
            "max_range": 1.5,
            "category": "WACC_COMPONENTS"
          },
          "user_value": null,
          "final_value": 1.29,
          "status": "DEFAULT",
          "is_valid": true,
          "is_multi_year": false
        },
        {
          "metric": "cost_of_debt",
          "category": "WACC_COMPONENTS",
          "description": "Pre-tax cost of debt",
          "unit": "%",
          "ai_suggestion": {
            "metric": "cost_of_debt",
            "suggested_value": 3.8,
            "reasoning": "Based on current yield on Apple's outstanding bonds. Investment grade credit rating supports low cost of debt.",
            "confidence_level": "medium",
            "min_range": 3.0,
            "max_range": 5.0,
            "category": "WACC_COMPONENTS"
          },
          "user_value": null,
          "final_value": 3.8,
          "status": "DEFAULT",
          "is_valid": true,
          "is_multi_year": false
        },
        {
          "metric": "terminal_growth_rate",
          "category": "WACC_COMPONENTS",
          "description": "Perpetual growth rate for terminal value",
          "unit": "%",
          "ai_suggestion": {
            "metric": "terminal_growth_rate",
            "suggested_value": 2.5,
            "reasoning": "Aligned with long-term GDP growth expectations. Conservative estimate for mature company.",
            "confidence_level": "medium",
            "min_range": 2.0,
            "max_range": 3.5,
            "category": "WACC_COMPONENTS"
          },
          "user_value": null,
          "final_value": 2.5,
          "status": "DEFAULT",
          "is_valid": true,
          "is_multi_year": false
        }
      ],
      "ai_generated": true,
      "generation_timestamp": "2024-01-15T10:35:00Z",
      "message": ""
    },
    
    "TERMINAL_VALUE": {
      "category": "TERMINAL_VALUE",
      "category_name": "Terminal Value",
      "assumptions": [
        {
          "metric": "terminal_ebitda_multiple",
          "category": "TERMINAL_VALUE",
          "description": "Exit multiple for terminal value calculation",
          "unit": "x",
          "ai_suggestion": {
            "metric": "terminal_ebitda_multiple",
            "suggested_value": 12.5,
            "reasoning": "Based on average trading multiples of comparable companies. Conservative to current trading levels given maturity.",
            "confidence_level": "medium",
            "min_range": 10.0,
            "max_range": 15.0,
            "category": "TERMINAL_VALUE"
          },
          "user_value": null,
          "final_value": 12.5,
          "status": "DEFAULT",
          "is_valid": true,
          "is_multi_year": false
        }
      ],
      "ai_generated": true,
      "generation_timestamp": "2024-01-15T10:35:00Z",
      "message": ""
    }
  },
  
  "targeted_category": null,
  "all_categories_complete": true,
  "all_validations_passed": true,
  "total_validation_errors": [],
  "ready_for_calculation": true,
  
  "sensitivity_preview": {
    "base_case_fair_value": 195.50,
    "bull_case_fair_value": 225.00,
    "bear_case_fair_value": 165.00,
    "key_sensitivities": ["wacc", "terminal_growth_rate", "revenue_growth"]
  },
  
  "message": "All assumption categories initialized with AI suggestions"
}
```

### AssumptionCategoryType Enum
```json
{
  "category": "REVENUE_DRIVERS" | "COST_MARGINS" | "WORKING_CAPITAL" | "WACC_COMPONENTS" | "TERMINAL_VALUE" | "DUPONT_TARGETS" | "COMPS_MULTIPLES"
}
```

### OverrideStatus Enum
```json
{
  "status": "ACCEPTED_AI" | "MANUAL_OVERRIDE" | "DEFAULT"
}
```

---

## Step 9: Assumptions Confirmation

### Endpoint
- **Frontend Call**: `confirmAssumptions(sessionId, confirmedValues, scenario, method, market)`
- **Backend Route**: `POST /api/step-9-confirm-assumptions`
- **Service**: Validation before Step 10 execution

### Request Format
```json
{
  "session_id": "uuid-string",
  "method": "DCF",
  "market": "international",
  "confirmed_assumptions": {
    "REVENUE_DRIVERS": {
      "revenue_growth_rate": {
        "final_value": 6.5,
        "status": "ACCEPTED_AI",
        "year_values": {"1": 7.0, "2": 6.5, "3": 6.0, "4": 5.5, "5": 5.0}
      }
    },
    "COST_MARGINS": {
      "ebitda_margin": {
        "final_value": 32.5,
        "status": "MANUAL_OVERRIDE",
        "year_values": {"1": 32.5, "2": 32.8, "3": 33.0, "4": 33.0, "5": 33.0}
      }
    }
  }
}
```

### Response Format: `UnifiedStep9Response`
```json
{
  "status": "success",
  "session_id": "uuid-string",
  "method": "DCF",
  "market": "international",
  "all_categories_confirmed": true,
  "confirmed_assumptions": {
    "REVENUE_DRIVERS": {
      "revenue_growth_rate": 6.5,
      "volume_growth": 3.5
    },
    "COST_MARGINS": {
      "ebitda_margin": 32.5,
      "tax_rate": 15.8
    },
    "WORKING_CAPITAL": {
      "ar_days": 28,
      "inv_days": 11,
      "ap_days": 107
    },
    "WACC_COMPONENTS": {
      "risk_free_rate": 4.25,
      "equity_risk_premium": 5.5,
      "beta": 1.29,
      "cost_of_debt": 3.8,
      "terminal_growth_rate": 2.5
    },
    "TERMINAL_VALUE": {
      "terminal_ebitda_multiple": 12.5
    }
  },
  "ready_for_valuation": true,
  "validation_errors": [],
  "message": "All assumptions confirmed. Ready for DCF valuation."
}
```

---

## Step 10: Valuation Execution

### Endpoint
- **Frontend Call**: `runValuation(sessionId, method, scenario, market)`
- **Backend Route**: `POST /api/step-10-valuate`
- **Service**: `dcf_engine.py` | `dupont_engine.py` | `comps_engine.py`
- **Report Generator**: `step10_dcf_report.py` | `step10_dupont_report.py` | `step10_comps_report.py`

### Request Format
```json
{
  "session_id": "uuid-string",
  "method": "DCF",
  "market": "international",
  "run_sensitivity": true,
  "scenario_analysis": true
}
```

### Response Format: `UnifiedStep10Response`
```json
{
  "status": "success",
  "session_id": "uuid-string",
  "method": "DCF",
  "market": "international",
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  
  "valuation_summary": {
    "enterprise_value": {
      "value": 2850000000000,
      "status": "CALCULATED",
      "source": "dcf_model",
      "unit": "USD",
      "formula": "PV(FCF) + PV(Terminal Value)"
    },
    "equity_value": {
      "value": 2768000000000,
      "status": "CALCULATED",
      "source": "dcf_model",
      "unit": "USD",
      "formula": "Enterprise Value - Net Debt"
    },
    "fair_value_per_share": {
      "value": 178.00,
      "status": "CALCULATED",
      "source": "dcf_model",
      "unit": "USD",
      "formula": "Equity Value / Shares Outstanding"
    },
    "current_price": {
      "value": 178.72,
      "status": "RETRIEVED",
      "source": "yfinance",
      "unit": "USD"
    },
    "implied_upside_downside": {
      "value": -0.4,
      "status": "CALCULATED",
      "source": "calculated",
      "unit": "%",
      "formula": "(Fair Value - Current Price) / Current Price"
    },
    "valuation_range_low": {
      "value": 165.00,
      "status": "CALCULATED",
      "source": "sensitivity_analysis",
      "unit": "USD"
    },
    "valuation_range_high": {
      "value": 225.00,
      "status": "CALCULATED",
      "source": "sensitivity_analysis",
      "unit": "USD"
    }
  },
  
  "detailed_outputs": {
    "projected_fcf": [
      {"year": 1, "fcf": 105000000000, "pv_fcf": 96153846154},
      {"year": 2, "fcf": 111500000000, "pv_fcf": 93402777778},
      {"year": 3, "fcf": 117800000000, "pv_fcf": 90512820513},
      {"year": 4, "fcf": 123500000000, "pv_fcf": 87234567901},
      {"year": 5, "fcf": 128900000000, "pv_fcf": 83846153846}
    ],
    "terminal_value": {
      "tv_at_year_5": 2450000000000,
      "pv_terminal_value": 1575000000000,
      "method": "perpetuity_growth",
      "terminal_growth_rate": 2.5,
      "wacc": 9.2
    },
    "wacc_breakdown": {
      "cost_of_equity": 11.32,
      "cost_of_debt": 3.8,
      "tax_rate": 15.8,
      "weight_equity": 0.72,
      "weight_debt": 0.28,
      "wacc": 9.2
    },
    "npv_calculation": {
      "sum_pv_fcf": 451150166192,
      "pv_terminal_value": 1575000000000,
      "enterprise_value": 2850000000000,
      "net_debt": 81123000000,
      "equity_value": 2768000000000
    }
  },
  
  "sensitivity_analysis": {
    "variable_1": "wacc",
    "variable_2": "terminal_growth_rate",
    "ranges": {
      "wacc": [8.2, 8.7, 9.2, 9.7, 10.2],
      "terminal_growth_rate": [2.0, 2.25, 2.5, 2.75, 3.0]
    },
    "results_matrix": [
      [210.00, 205.00, 200.00, 195.00, 190.00],
      [198.00, 193.00, 188.00, 183.00, 178.00],
      [187.00, 182.00, 178.00, 173.00, 168.00],
      [177.00, 172.00, 168.00, 163.00, 158.00],
      [168.00, 163.00, 159.00, 154.00, 150.00]
    ]
  },
  
  "scenario_analysis": {
    "base_case": {
      "enterprise_value": 2850000000000,
      "equity_value": 2768000000000,
      "fair_value_per_share": 178.00,
      "implied_upside_downside": -0.4
    },
    "bull_case": {
      "enterprise_value": 3200000000000,
      "equity_value": 3118000000000,
      "fair_value_per_share": 200.50,
      "implied_upside_downside": 12.2,
      "assumptions": "Higher revenue growth (9%), expanded margins (35%)"
    },
    "bear_case": {
      "enterprise_value": 2400000000000,
      "equity_value": 2318000000000,
      "fair_value_per_share": 149.00,
      "implied_upside_downside": -16.6,
      "assumptions": "Lower revenue growth (3%), compressed margins (28%)"
    }
  },
  
  "confidence_level": "high",
  "key_assumptions_summary": {
    "revenue_cagr": 6.5,
    "avg_ebitda_margin": 32.5,
    "wacc": 9.2,
    "terminal_growth_rate": 2.5,
    "terminal_multiple": 12.5
  },
  "warnings": [],
  "calculation_timestamp": "2024-01-15T10:40:00Z",
  "message": "DCF valuation completed successfully. Fair value: $178.00 per share"
}
```

---

## Utility Responses

### Session Status Check
**Endpoint**: `GET /api/session-status/{session_id}`

```json
{
  "session_id": "uuid-string",
  "current_step": 6,
  "market": "international",
  "method": "DCF",
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "completed_steps": [1, 2, 3, 4, 5],
  "data_completeness": {
    "step_1": 100.0,
    "step_2": 100.0,
    "step_3": 100.0,
    "step_4": 100.0,
    "step_5": 95.0,
    "step_6": 0.0
  },
  "ready_for_next_step": true,
  "errors": [],
  "warnings": ["Some assumptions are estimated"]
}
```

### Error Response (Standardized)
```json
{
  "success": false,
  "error_code": "DATA_NOT_AVAILABLE",
  "error_message": "Historical financial data not available for the requested period",
  "details": {
    "ticker": "AAPL",
    "missing_periods": ["Q1-2019"],
    "available_from": "Q2-2019"
  },
  "suggestions": [
    "Try reducing the historical period to 4 years",
    "Use estimated data with lower confidence score",
    "Manually input missing data points"
  ]
}
```

### Critical Error: 401 Unauthorized (Missing Vendor API Credentials)

**When This Occurs:**
- FMP API key not configured in environment variables
- Request header `x-api-key-fmp` missing or invalid
- API key expired or rate-limited by vendor

**Response Format:**
```json
{
  "success": false,
  "error_code": "MISSING_API_CREDENTIALS",
  "error_message": "Missing API Credentials for Service [Financial Modeling Prep]",
  "details": {
    "service": "Financial Modeling Prep",
    "checked_locations": [
      "request.headers.x-api-key-fmp",
      "process.env.FMP_API_KEY"
    ],
    "fallback_used": false,
    "rate_limit_status": null
  },
  "suggestions": [
    "Configure FMP_API_KEY environment variable on backend",
    "Provide API key via request header: x-api-key-fmp",
    "Contact administrator to configure vendor credentials",
    "Check API key validity at https://financialmodelingprep.com/"
  ],
  "action_required": "Prompt user to provide active API layer token configuration in client panel or infrastructure env variables."
}
```

**Frontend Handling:**
```javascript
// In React component
if (error.response?.data?.error_code === 'MISSING_API_CREDENTIALS') {
  // Show API configuration panel
  setShowApiConfigPanel(true);
  setRequiredService(error.response.data.details.service);
}
```

**Backend Implementation Notes:**
- API keys are retrieved with priority: request header > environment variable > default fallback
- Default fallback key is deprecated and should not be used in production
- Keys are tracked per-request to prevent global rate-limit exhaustion
- See `get_fmp_api_key()` in `institutional_peer_discovery.py`

### Empty Results Diagnostic Response

**When This Occurs:**
- Peer discovery returns zero matches due to strict constraints
- No companies match sector/industry/market cap criteria
- Vendor API timeout or failure

**Response Format (Step 4 Example):**
```json
{
  "status": "success",
  "session_id": "uuid-string",
  "method": "COMPS",
  "market": "international",
  "target_company": "AAPL",
  "suggested_peers": [],
  "selected_peers": [],
  "message": "No peers found matching strict COMPS criteria",
  "mandatory": true,
  "min_peers_recommended": 5,
  "diagnostics": {
    "engine_message": "Zero peers found - constraints too strict",
    "vendor_api_status": "SUCCESS",
    "local_db_fallback_triggered": false,
    "applied_constraints": {
      "initial_market_cap_range": "80% - 120%",
      "relaxed_constraints_applied": false,
      "sector_match_required": true,
      "industry_preference": "strict"
    },
    "critical_missing_metrics": [],
    "search_criteria": {
      "target_ticker": "AAPL",
      "method": "COMPS",
      "max_peers_requested": 10,
      "market": "international"
    },
    "warnings": [
      "No peers found with strict sector/industry matching",
      "Consider relaxing market cap range or industry requirements"
    ],
    "recommendations": [
      "Switch to moderate constraint mode (50%-200% market cap)",
      "Allow cross-industry peers within same sector",
      "Manually specify peer tickers if auto-discovery fails"
    ]
  }
}
```

**Frontend Handling:**
```javascript
// Check diagnostics when suggested_peers is empty
if (response.suggested_peers.length === 0 && response.diagnostics) {
  const { warnings, recommendations } = response.diagnostics;
  // Show user-friendly message with recommendations
  showPeerDiscoveryWarning(warnings, recommendations);
  
  // For mandatory methods (COMPS), block progression
  if (response.mandatory) {
    disableNextButton(true);
    showManualEntryOption();
  }
}
```

---

## Common Error Codes

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `DATA_NOT_AVAILABLE` | Requested data not found in source | Reduce time period or use estimates |
| `INVALID_TICKER` | Ticker symbol not recognized | Verify ticker or search for correct symbol |
| `SESSION_EXPIRED` | Session timeout | Restart workflow from Step 1 |
| `METHOD_NOT_SUPPORTED` | Valuation method not available for market | Check market-method compatibility |
| `ASSUMPTION_INVALID` | User input fails validation | Review assumption ranges |
| `CALCULATION_FAILED` | Valuation calculation error | Check input data quality |
| `API_KEY_MISSING` | Required API key not provided | Add API key in settings |
| `RATE_LIMIT_EXCEEDED` | External API rate limit hit | Wait and retry |

---

## Market-Specific Notes

### International Market (Current Focus)
- **Data Source**: yfinance, FRED, SEC EDGAR, Alpha Vantage, FMP
- **Currency**: USD (primarily), local currencies converted
- **Accounting Standard**: IFRS / US GAAP
- **Risk-Free Rate**: US Treasury 10Y or local government bond

### Vietnamese Market (Version 2 - Future)
- **Data Source**: VietStock, local exchanges
- **Currency**: VND
- **Accounting Standard**: VAS (Vietnamese Accounting Standards) / TT99
- **Risk-Free Rate**: Vietnamese government bond
- **Special Fields**: `vnindex_performance`, `exchange_info`, `market_code`

---

## Frontend Integration Guidelines

### DataField Rendering
```jsx
// Always check status before displaying
<DataFieldDisplay 
  field={data.revenue}
  showSource={true}
  allowOverride={field.can_override}
  unit={field.unit}
/>
```

### Handling Missing Data
```jsx
// Check missing_data_summary before proceeding
if (!response.missing_data_summary.valuation_ready) {
  showWarning("Insufficient data for valuation");
  displayMissingFields(response.missing_data_summary.critical_missing);
}
```

### Multi-Year Assumptions
```jsx
// For multi-year assumptions, render year-by-year inputs
{assumption.is_multi_year ? (
  <YearByYearInput 
    values={assumption.year_values}
    onChange={handleYearChange}
  />
) : (
  <SingleValueInput 
    value={assumption.final_value}
    onChange={handleValueChange}
  />
)}
```

---

## Document Version
- **Version**: 1.0
- **Last Updated**: 2024
- **Architecture**: 3 Valuation Methods × 2 Markets
- **Current Status**: International Market Only (Vietnam = Version 2)
