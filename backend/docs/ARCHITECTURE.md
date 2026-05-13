# Backend Architecture Documentation

## ⚠️ CRITICAL DEVELOPMENT GUIDELINES

### 1. Market Separation (DO NOT MERGE MARKETS)
**NEVER create "Generic Displayer" components or services that merge Vietnamese and International markets.**

- **Why?** Fundamental differences exist:
  - **Accounting Standards:** VAS/TT99 (Vietnam) vs IFRS/US GAAP (International)
  - **Currency:** VND vs USD with different formatting rules and magnitudes
  - **Market Mechanics:** Foreign ownership limits, board types (HOSE/HNX/UPCoM), trading mechanisms
  
- **Correct Approach:**
  - **UI Layer:** Keep `VietnameseMarketData.jsx` and `InternationalMarketData.jsx` separate
  - **Service Layer:** Use `UnifiedTransformer` services ONLY for temporary normalization during peer comparison
  - **Never** lose local precision or context by forcing a lowest-common-denominator schema

### 2. Thin Routes, Fat Services
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

### 3. Workflow Step Integrity
**File names MUST match their workflow step purpose.**

| Step | Purpose | Correct File | Mismatched Files (Rename to `mismatch_*.py`) |
|------|---------|--------------|---------------------------------------------|
| **3** | Peer Company Selection | `peer_discovery_service.py` | `step3_historical_processor.py` |
| **4** | Model Selection (DCF/DuPont/Comps) | `step4_selected_models_processor.py` | `step4_forecast_processor.py` |
| **5** | Required Inputs Display | `step5_required_inputs_processor.py` | `step5_assumptions_processor.py` |

- **Rule:** If a file name suggests a different purpose than its step number, rename it with `mismatch_` prefix to prevent accidental usage.

---

## Overview

**⚠️ CURRENT STATUS: INTERNATIONAL MARKET ONLY**  
Vietnamese market support is planned for **Version 2** (future release). All active development focuses on International markets.

This backend provides dual-market stock valuation capabilities with **strict separation** between:
- ✅ **International Markets** (IFRS/US GAAP) - US, EU, Asia ex-Vietnam - **CURRENTLY ACTIVE**
- ⏳ **Vietnamese Market** (TT99 accounting standards) - HOSE, HNX, UPCOM exchanges - **Version 2 (Future)**

## 3×2 Workflow Matrix (Target Architecture)

**Current Focus**: International market implementation complete. Vietnamese market in development for Version 2.

| | **International (Current)** | **Vietnam (Version 2 - Future)** |
|---|---|---|
| **DCF** | ✅ `services/international/dcf_engine.py` + 10 step processors | ⏳ `services/vietnamese/vietnamese_dcf_engine.py` + 10 step processors |
| **DuPont** | ✅ `services/international/dupont_engine.py` + 10 step processors | ⏳ `services/vietnamese/vietnamese_dupont_engine.py` + 10 step processors |
| **Comps** | ✅ `services/international/comps_engine.py` + 10 step processors | ⏳ `services/vietnamese/vietnamese_comps_engine.py` (sector_valuation_models.py) |

### Critical Workflow Principles

1. **Fetch Once, Use Many**: Step 6 fetches ALL data for ANY model into shared cache
2. **Single Model Execution**: Steps 7-9 run sequentially for ONE selected model only
3. **Market Isolation**: No cross-contamination between international and Vietnamese workflows
4. **Model Integrity**: No input/calculation simplification - all fields preserved

## Directory Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── international_market_data_routes.py    # /international/* endpoints (DCF/DuPont/Comps)
│   │       ├── vietnamese_market_data_routes.py       # /vietnamese/* endpoints (VN-specific)
│   │       ├── pdf_extraction_routes.py               # PDF financial extraction (VN)
│   │       ├── search_routes.py                       # Ticker/company search
│   │       ├── valuation_routes.py                    # Steps 4-10 unified workflow
│   │       └── vietnamese_reports_routes.py           # VN report auto-fetch
│   │
│   ├── models/
│   │   ├── __init__.py                                # Unified exports
│   │   ├── international/                             # International market models
│   │   │   └── __init__.py                            # DuPont, Comps, DCF requests
│   │   └── vietnamese/                                # Vietnamese market models (TT99)
│   │       └── __init__.py                            # VN-specific schemas
│   │
│   ├── services/                                      # Business logic - 70+ files total
│   │   ├── __init__.py                                # Unified exports
│   │   ├── international/                             # International services (40+ files)
│   │   │   ├── dcf_engine.py                          # DCF calculations (IFRS/GAAP)
│   │   │   ├── dupont_engine.py                       # DuPont analysis
│   │   │   ├── comps_engine.py                        # Trading comparables
│   │   │   ├── step1_ticker_processor.py
│   │   │   ├── step2_market_data_processor.py
│   │   │   ├── step3_historical_processor.py
│   │   │   ├── step4_forecast_processor.py
│   │   │   ├── step5_assumptions_processor.py
│   │   │   ├── step6_data_review.py                   # Fetch Once, Use Many
│   │   │   ├── step6_dcf_data_review.py               # Model-specific data review
│   │   │   ├── step6_dupont_data_review.py
│   │   │   ├── step6_comps_data_review.py
│   │   │   ├── step7_historical_data_processor.py
│   │   │   ├── step7_dcf_historical_data.py           # Model-specific historical fetch
│   │   │   ├── step7_dupont_historical_data.py
│   │   │   ├── step7_comps_historical_data.py
│   │   │   ├── step8_dcf_assumptions.py               # AI suggestions (model-specific)
│   │   │   ├── step8_dupont_assumptions.py
│   │   │   ├── step8_comps_assumptions.py
│   │   │   ├── step8_manual_overrides.py              # User manual adjustments
│   │   │   ├── step9_final_calculation.py             # Pre-valuation calculations
│   │   │   ├── step9_dcf_calculation.py               # Model-specific final calc
│   │   │   ├── step9_dupont_calculation.py
│   │   │   ├── step9_comps_calculation.py
│   │   │   ├── step10_valuation_processor.py          # Unified valuation execution
│   │   │   ├── step10_dcf_report.py                   # Model-specific reports
│   │   │   ├── step10_dupont_report.py
│   │   │   ├── step10_comps_report.py
│   │   │   ├── ai_engine.py                           # AI suggestion engine
│   │   │   ├── yfinance_service.py                    # Yahoo Finance integration
│   │   │   ├── alphavantage_service.py                # Alpha Vantage API
│   │   │   ├── peer_discovery_service.py              # Peer company discovery
│   │   │   ├── metrics_calculator.py                  # Financial metrics calculation
│   │   │   ├── dcf_input_manager.py                   # DCF input management
│   │   │   ├── shared_context_service.py              # Cross-step context sharing
│   │   │   └── valuation_orchestrator.py              # Multi-model orchestration
│   │   │
│   │   └── vietnamese/                                # Vietnamese services (30+ files)
│   │       ├── vietnamese_dcf_engine.py               # DCF (TT99, 20% tax, VND)
│   │       ├── vietnamese_dupont_engine.py            # DuPont (TT99 standards)
│   │       ├── vietnamese_comps_engine.py             # Comps (VNINDEX/VN30 filtering)
│   │       ├── sector_valuation_models.py             # VN sector-specific models
│   │       ├── step1_ticker_processor.py
│   │       ├── step2_market_data_processor.py
│   │       ├── step3_historical_processor.py
│   │       ├── step4_model_processor.py               # VN model selection
│   │       ├── step4_forecast_processor.py
│   │       ├── step5_requirements_processor.py        # VN input requirements
│   │       ├── step6_data_fetch_processor.py          # VN data fetching
│   │       ├── step7_historical_processor.py
│   │       ├── step8_assumptions_processor.py
│   │       ├── step8_dcf_assumptions.py               # VN DCF assumptions
│   │       ├── step8_dupont_assumptions.py            # VN DuPont assumptions
│   │       ├── step8_comps_assumptions.py             # VN Comps assumptions
│   │       ├── step9_confirmation_processor.py        # VN assumption confirmation
│   │       ├── step10_valuation_processor.py          # VN valuation execution
│   │       ├── vietnamese_input_manager.py            # VN input management
│   │       ├── vietnamese_ticker_service.py           # VN ticker validation
│   │       ├── vn_stock_database.py                   # VNStockDB integration
│   │       ├── vnd_financial_parser.py                # VNDirect parser
│   │       ├── vn_document_extractor.py               # PDF/document extraction
│   │       ├── vietnamese_report_scraper.py           # Report scraping (CafeF, etc.)
│   │       └── vietnam_data_aggregator.py             # VN data aggregation
│   │
│   └── core/
│       ├── config.py                                  # Application settings
│       ├── logging_config.py                          # Logging setup
│       ├── exceptions.py                              # Custom exceptions
│       └── model_integrity.py                         # Model validation
│
├── main.py                                            # FastAPI application entry
│
└── docs/
    ├── ARCHITECTURE.md                                # This file
    ├── VIETNAMESE_VS_INTERNATIONAL_MODELS.md          # TT99 vs IFRS/GAAP comparison
    └── vietnamese_report_auto_fetch.md                # Auto-fetch VN reports guide
```

## Market Isolation Principles

### 1. **No Cross-Contamination**
- Vietnamese tickers (VNM, VIC, VCB) **cannot** use international logic
- International tickers (AAPL, MSFT, GOOGL) **cannot** use Vietnamese logic
- Separate data sources, parameters, and calculation methods

### 2. **Dedicated Data Sources**

| Market | Data Source | Currency | Tax Rate | Risk-Free Rate |
|--------|-------------|----------|----------|----------------|
| International | yfinance, Alpha Vantage | USD/local | Local corporate tax | 10Y Treasury |
| Vietnamese | VNDirect, CafeF, VNStockDatabase | VND | 20% | 6.8% (10Y VN bond) |

### 3. **Accounting Standards**

### 4. **Model-Specific Processors**

Each valuation method (DCF/DuPont/Comps) has dedicated processors for steps 6-10:

| Step | International | Vietnamese |
|------|---------------|------------|
| **Step 6** (Data Review) | `step6_dcf_data_review.py`, `step6_dupont_data_review.py`, `step6_comps_data_review.py` | Unified `step6_data_fetch_processor.py` |
| **Step 7** (Historical) | `step7_dcf_historical_data.py`, `step7_dupont_historical_data.py`, `step7_comps_historical_data.py` | Unified `step7_historical_processor.py` |
| **Step 8** (Assumptions) | `step8_dcf_assumptions.py`, `step8_dupont_assumptions.py`, `step8_comps_assumptions.py` | `step8_dcf_assumptions.py`, `step8_dupont_assumptions.py`, `step8_comps_assumptions.py` |
| **Step 9** (Calculation) | `step9_dcf_calculation.py`, `step9_dupont_calculation.py`, `step9_comps_calculation.py` | Unified `step9_confirmation_processor.py` |
| **Step 10** (Valuation) | `step10_dcf_report.py`, `step10_dupont_report.py`, `step10_comps_report.py` | Unified `step10_valuation_processor.py` |

| Market | Standard | Key Features |
|--------|----------|--------------|
| International | IFRS / US GAAP | Global reporting norms |
| Vietnamese | TT99 (Thông Tư 99/2025/TT-BTC) | Specific form templates B01-DN, B02-DN |

## API Endpoints

### International Routes (`/international`)

```bash
# DCF Valuation
POST /international/valuate
{
  "ticker": "AAPL",
  "projection_years": 5,
  "wacc_override": null
}

# Comparable Company Analysis
POST /international/comps
{
  "target_ticker": "MSFT",
  "peer_list": ["AAPL", "GOOGL"],
  "apply_outlier_filtering": true
}

# DuPont Analysis
POST /international/dupont
{
  "ticker": "NVDA",
  "years": [2021, 2022, 2023]
}
```

### Vietnamese Routes (`/vietnamese`)

```bash
# DCF Valuation (VN-specific WACC, 20% tax)
POST /vietnamese/vn-valuate
{
  "ticker": "VNM",
  "exchange": "HOSE",
  "projection_years": 5
}

# Comparable Company Analysis (VNINDEX/VN30 filtering)
POST /vietnamese/vn-comps
{
  "target_ticker": "VIC",
  "sector": "Real Estate",
  "max_peers": 10
}

# DuPont Analysis (TT99 financial statements)
POST /vietnamese/vn-dupont
{
  "ticker": "VCB",
  "years": [2021, 2022, 2023]
}

# Get Vietnamese company info
GET /vietnamese/vn-info?ticker=VNM
```

## Key Parameters by Market

### Vietnamese-Specific Constants
- **Corporate Tax Rate**: 20%
- **Risk-Free Rate**: 6.8% (10-year government bond)
- **Market Risk Premium**: 7.5%
- **Terminal Growth Cap**: 6% (aligned with GDP growth expectations)
- **Size Premium**: Applied for small/mid-cap VN stocks

### International Parameters
- **Corporate Tax Rate**: Country-specific (21% US, varies by jurisdiction)
- **Risk-Free Rate**: 10Y Treasury or local equivalent
- **Market Risk Premium**: 5-6% typical for developed markets
- **Terminal Growth**: 2-3% for mature companies

## File Organization Rationale

### Why Subpackages?
1. **Clear Separation**: `international/` vs `vietnam/` subdirectories prevent accidental imports
2. **Scalability**: Easy to add new markets (e.g., `thailand/`, `indonesia/`)
3. **Maintainability**: Related files grouped logically
4. **Import Clarity**: `from app.models.vietnamese import ...` is explicit

### Legacy Files
Files at the root of `models/`, `services/`, and `engines/` are maintained for **backward compatibility** during migration. New code should use subpackage imports.

## Migration Guide

### Old Import → New Import

```python
# ❌ Old (still works but deprecated)
from app.models.vietnamese_inputs import VietnameseDCFRequest
from app.services.vietnamese_input_manager import VietnameseInputManager
from app.engines.vietnamese_dcf_engine import VietnameseDCFEngine

# ✅ New (recommended)
from app.models.vietnamese import VietnameseDCFRequest
from app.services.vietnam import VietnameseInputManager
from app.engines.vietnam import VietnameseDCFEngine
```

## Testing Strategy

Each market has isolated test suites:
- `tests/international/` - Tests for international workflows
- `tests/vietnamese/` - Tests for Vietnamese workflows

Tests verify:
1. Ticker format validation rejects cross-market tickers
2. Correct data sources are used
3. Market-specific parameters are applied
4. No circular dependencies between markets

## Security Notes

- **API Keys**: Never commit API keys to version control
- **Environment Variables**: Use `.env` file for sensitive configuration
- **Rate Limiting**: Implement rate limiting on public endpoints
- **Input Validation**: All inputs validated via Pydantic models
