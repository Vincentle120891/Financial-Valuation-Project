# Backend Architecture Documentation

## Overview

This backend provides dual-market stock valuation capabilities with **strict separation** between:
- **International Markets** (IFRS/US GAAP) - US, EU, Asia ex-Vietnam
- **Vietnamese Market** (TT99 accounting standards) - HOSE, HNX, UPCOM exchanges

## Directory Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── international_routes.py    # /international/* endpoints
│   │       ├── vietnamese_routes.py       # /vietnamese/* endpoints
│   │       ├── pdf_extraction_routes.py   # PDF financial extraction
│   │       ├── search_routes.py           # Ticker/company search
│   │       └── vietnamese_reports_routes.py
│   │
│   ├── models/
│   │   ├── __init__.py                    # Unified exports
│   │   ├── international/                 # International market models
│   │   │   └── __init__.py                # DuPont, Comps, DCF requests
│   │   ├── vietnamese/                    # Vietnamese market models (TT99)
│   │   │   └── __init__.py                # VN-specific schemas
│   │   ├── international_inputs.py        # Legacy: DuPont, Comps models
│   │   ├── international_cashflow_model.py
│   │   ├── vietnamese_inputs.py           # Legacy: VN request models
│   │   ├── vietnamese_inputs_tt99.py      # Legacy: TT99 financial forms
│   │   └── vietnamese_cashflow_model.py
│   │
│   ├── services/
│   │   ├── __init__.py                    # Unified exports
│   │   ├── international/                 # International services
│   │   │   └── __init__.py                # yfinance, ticker validation
│   │   ├── vietnam/                       # Vietnamese services
│   │   │   ├── __init__.py                # VNDirect, CafeF, VNStockDB
│   │   │   ├── vn_stock_database.py
│   │   │   └── vnd_financial_parser.py
│   │   ├── dcf_input_manager.py           # Legacy: ValuationInputManager
│   │   ├── vietnamese_input_manager.py    # Legacy: VietnameseInputManager
│   │   ├── yfinance_service.py
│   │   ├── international_ticker_service.py
│   │   ├── vietnamese_ticker_service.py
│   │   └── metrics_calculator.py
│   │
│   ├── engines/
│   │   ├── __init__.py                    # Unified exports
│   │   ├── international/                 # International engines
│   │   │   └── __init__.py                # DCF, Comps, DuPont
│   │   ├── vietnam/                       # Vietnamese engines
│   │   │   ├── __init__.py                # VN DCF, sector models
│   │   │   └── sector_valuation_models.py
│   │   ├── dcf_engine.py                  # Legacy: International DCF
│   │   ├── comps_engine.py                # Legacy: Comps analysis
│   │   ├── dupont_engine.py               # Legacy: DuPont analysis
│   │   ├── vietnamese_dcf_engine.py       # Legacy: VN DCF
│   │   └── ai_engine.py                   # AI suggestions & fallbacks
│   │
│   ├── core/
│   │   ├── config.py                      # Application settings
│   │   ├── logging_config.py              # Logging setup
│   │   ├── exceptions.py                  # Custom exceptions
│   │   └── model_integrity.py             # Model validation
│   │
│   └── main.py                            # FastAPI application entry
│
└── docs/
    ├── ARCHITECTURE.md                    # This file
    ├── VIETNAMESE_VS_INTERNATIONAL_MODELS.md
    └── vietnamese_report_auto_fetch.md
```

## Market Isolation Principles

### 1. **No Cross-Contamination**
- Vietnamese tickers (VNM, VIC, VCB) **cannot** use international logic
- International tickers (AAPL, MSFT, GOOGL) **cannot** use Vietnamese logic
- Separate data sources, parameters, and calculation methods

### 2. **Dedicated Data Sources**

| Market | Data Source | Currency | Tax Rate | Risk-Free Rate |
|--------|-------------|----------|----------|----------------|
| International | yfinance | USD/local | Local corporate tax | 10Y Treasury |
| Vietnamese | VNDirect, CafeF, VNStockDatabase | VND | 20% | 6.8% (10Y VN bond) |

### 3. **Accounting Standards**

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
