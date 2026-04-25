# Unified Valuation Model - Complete Reference

## Project Overview
A comprehensive Python-based valuation system supporting **DCF**, **Trading Comps**, and **DuPont Analysis** models with schema-compliant inputs, AI-enhanced data extraction, and full calculation engines.

---

## 📁 File Structure

```
backend/
├── input.py                  # API data retrieval (yfinance + Alpha Vantage)
├── input_ai.py               # AI-extracted footnote & guidance data
├── input_dcf.py              # DCF-specific 3-year historical configuration
├── dcf_engine_full.py        # Full DCF calculation engine
├── dupont_module.py          # DuPont analysis engine (3-step & 5-step)
├── comps_engine.py           # Trading comparables engine
├── main.py                   # FastAPI application (12-step workflow)
└── requirements.txt          # Python dependencies
```

---

## 🔧 INPUT MODULES (Data Retrieval)

### 1. `ValuationInputs` (input.py)
**Purpose:** Fetch all API-retrievable data for DCF, Comps, and DuPont models  
**Schema:** `Unified_Valuation_API_Calculated_Schema`  
**Primary Source:** yfinance | **Fallback:** Alpha Vantage

#### Required Input:
```python
ticker: str  # Stock ticker symbol (e.g., "AAPL", "MSFT")
currency: str = "USD"  # Optional, defaults to USD
```

#### Key Methods:
- `fetch_all()` → Returns complete schema-compliant dictionary
- `to_json()` → JSON export
- `save_to_file(path)` → Save to file

#### Data Sections Retrieved:
| Section | Fields |
|---------|--------|
| `metadata` | ticker, company_name, exchange, currency, fiscal_year_end_month, data_timestamp, data_source, model_usage |
| `market_structure` | current_price, shares_outstanding, market_cap, enterprise_value, total_debt, cash, beta, dividend_yield |
| `macro_indicators` | risk_free_rate_10y, equity_risk_premium, inflation_expectations, gdp_growth, fx_rate |
| `income_statement_raw` | revenue, cogs, gross_profit, sga, r&d, ebitda, depreciation, ebit, interest, net_income, eps |
| `balance_sheet_raw` | accounts_receivable, inventory, accounts_payable, ppe, goodwill, total_assets, total_equity |
| `cash_flow_raw` | operating_cash_flow, capex, free_cash_flow, change_in_wc, dividends_paid |
| `calculated_metrics_common` | gross_margin, ebitda_margin, operating_margin, net_margin, roe, roa, roic, debt_to_equity |
| `wacc_components` | cost_of_debt, cost_of_equity, equity_weight, debt_weight, wacc |
| `comps_specific_calculated` | ev_ebitda, ev_sales, pe, pb, peer arrays & statistics |
| `dupont_specific_components` | tax_burden, interest_burden, roe_3step, roe_5step |

#### Usage Example:
```python
from input import ValuationInputs

inputs = ValuationInputs(ticker="AAPL")
data = inputs.fetch_all()
print(data["market_structure"]["current_price"])
```

---

### 2. `AIValuationInputs` (input_ai.py)
**Purpose:** AI-extracted footnote data, forward guidance, and hybrid adjustments  
**Schema:** `Unified_Valuation_AI_Hybrid_Schema`  
**Primary Source:** LLM parsing of SEC EDGAR filings, earnings transcripts  
**Fallback:** Manual estimates or API-sourced base figures

#### Required Input:
```python
ticker: str  # Stock ticker symbol
sec_filing_urls: List[str] = []  # Optional: specific 10-K/10-Q URLs
openai_api_key: str = None  # Or use ANTHROPIC_API_KEY
```

#### Key Methods:
- `fetch_all()` → Returns AI-extracted data with confidence scores
- `extract_footnotes()` → Parse 10-K/10-Q footnotes
- `parse_forward_guidance()` → Extract MD&A guidance
- `calculate_hybrid_adjustments()` → Combine AI + API data
- `suggest_peers()` → AI-driven peer identification
- `to_json()`, `save_to_file()`

#### Data Sections:
| Section | Description |
|---------|-------------|
| `ai_footnote_extractions` | Tax basis PP&E, NOL carryforwards, lease liabilities, useful lives, deferred taxes, segment breakdowns |
| `ai_contextual_forward_guidance` | Plant utilization targets, projected interest rates, CapEx forecasts, 5-year revenue growth guidance |
| `ai_api_hybrid_adjustments` | Adjusted EBITDA, lease-adjusted EV, tangible equity multiplier, normalized tax burden |
| `ai_peer_matching_analysis` | AI-suggested peers, similarity scores, geographic match, exclusion reasons |
| `ai_hybrid_valuation_suggestions` | Terminal multiple suggestions, scenario weights, quality adjustments |
| `ai_metadata_and_audit` | Confidence scores, source citations, validation status, override logs |

#### Usage Example:
```python
from input_ai import AIValuationInputs

ai_inputs = AIValuationInputs(ticker="AAPL", openai_api_key="sk-...")
ai_data = ai_inputs.fetch_all()
print(ai_data["ai_footnote_extractions"]["nol_carryforward_amount"])
```

---

### 3. `DCFInputConfiguration` (input_dcf.py)
**Purpose:** DCF-specific 3-year historical data + base period balances  
**Schema:** `dcf_input_configuration`  
**Dynamic Year Mapping:** FY-3, FY-2, FY-1 resolve to the 3 most recent completed fiscal years

#### Required Input:
```python
ticker: str  # Stock ticker symbol
valuation_date: str = None  # ISO date, defaults to latest report date
```

#### Data Classes:
**HistoricalFinancialYear** (per year × 3 years):
```python
revenue, cogs, gross_profit, sga, other_opex, ebitda, depreciation, 
ebit, interest_expense, ebt, current_tax, deferred_tax, total_tax, 
net_income, accounts_receivable, inventory, accounts_payable, 
net_working_capital, capital_expenditure
```

**BasePeriodBalances** (FY-1 ending):
```python
net_debt, ppe_net, tax_basis_pp_e, tax_losses_nol_carryforward,
shares_outstanding_diluted, current_stock_price,
projected_interest_expense_annual, plant_capacity_units_per_day
```

#### Key Methods:
- `from_ticker(ticker)` → Auto-fetch from yfinance
- `to_dict()` → Dictionary export
- `to_json()` → JSON export
- `save_to_file(path)` → Save to file

#### Usage Example:
```python
from input_dcf import DCFInputConfiguration

dcf_config = DCFInputConfiguration.from_ticker("AAPL")
historical = dcf_config.historical_financials_3y
print(historical.fy_minus_1.revenue)
print(dcf_config.base_period.shares_outstanding_diluted)
```

---

## ⚙️ ENGINE MODULES (Calculations)

### 4. `DCFEngine` (dcf_engine_full.py)
**Purpose:** Full DCF valuation with Perpetuity and Multiple terminal value methods  
**Forecast Period:** 6 periods (5 years + Terminal)  
**Scenarios:** Best Case, Base Case, Worst Case

#### Required Input:
```python
from dcf_engine_full import DCFInputs

inputs = DCFInputs(
    valuation_date="2026-04-22",
    base_year="2022A",
    forecast_years=["2023F", "2024F", "2025F", "2026F", "2027F"],
    
    # Historical (3 years)
    historical_revenue=[100000, 110000, 120000],
    historical_cogs=[60000, 65000, 70000],
    historical_ebitda=[30000, 34000, 38000],
    # ... more historical fields
    
    # Base Period Balances
    net_debt_base=50000,
    ppe_net_base=80000,
    shares_outstanding=10000,
    current_stock_price=150.0,
    
    # Forecast Drivers (6 values each: FY+1 to FY+5 + Terminal)
    forecast_drivers={
        "base_case": ForecastDrivers(
            sales_volume_growth=[0.08, 0.07, 0.06, 0.05, 0.04, 0.025],
            inflation_rate=[0.03, 0.03, 0.025, 0.025, 0.02, 0.02],
            opex_growth=[0.04, 0.04, 0.035, 0.03, 0.025, 0.02],
            capital_expenditure=[15000, 16000, 17000, 18000, 19000, 12000],
            ar_days=[45, 44, 43, 42, 41, 40],
            inv_days=[60, 59, 58, 57, 56, 55],
            ap_days=[50, 50, 49, 48, 47, 46],
            tax_rate=[0.21, 0.21, 0.21, 0.21, 0.21, 0.21],
            terminal_growth_rate=0.025,
            terminal_ebitda_multiple=12.0,
            wacc=0.085
        ),
        "best_case": ForecastDrivers(...),
        "worst_case": ForecastDrivers(...)
    },
    
    # Tax Depreciation
    useful_life_existing=10,
    useful_life_new=8,
    tax_loss_utilization_limit_pct=0.80,
    tax_loss_carryforward=5000
)
```

#### Key Methods:
- `calculate(scenario="base_case")` → Run full DCF calculation
- `to_dict()` → Export results as dictionary

#### Output Structure:
```python
{
    "main_outputs": {
        "enterprise_value_perpetuity": 1500000,
        "enterprise_value_multiple": 1450000,
        "equity_value_perpetuity": 1450000,
        "equity_value_multiple": 1400000,
        "equity_value_per_share_perpetuity": 145.0,
        "equity_value_per_share_multiple": 140.0,
        "upside_downside_perpetuity_pct": -3.3,
        "upside_downside_multiple_pct": -6.7
    },
    "scenario_outputs": {
        "best_case": {"enterprise_value": 1800000, "equity_value": 1750000, "equity_value_per_share": 175.0},
        "base_case": {...},
        "worst_case": {...}
    },
    "sensitivity_tables_output": {
        "perpetuity_method": {
            "enterprise_value_table": {"0.077": {"0.01": 1600000, ...}, ...},
            "equity_value_per_share_table": {...},
            "upside_downside_table": {...}
        },
        "multiple_method": {...}
    },
    "supporting_schedules_output": {
        "income_statement_forecast": {...},
        "working_capital_forecast": {...},
        "depreciation_forecast": {...},
        "ufcf_forecast": [{"year": "2023F", "ufcf": 25000}, ...],
        "discounting_details": {...}
    }
}
```

#### Usage Example:
```python
from dcf_engine_full import DCFEngine, DCFInputs, ForecastDrivers

engine = DCFEngine(inputs)
result = engine.calculate(scenario="base_case")
print(result.main_outputs.equity_value_per_share_perpetuity)
```

---

### 5. `DuPontAnalyzer` (dupont_module.py)
**Purpose:** 3-step and 5-step DuPont decomposition with trend analysis and peer comparison

#### Required Input:
```python
from dupont_module import DuPontInputs

inputs = DuPontInputs(
    ticker="AAPL",
    currency="USD",
    
    # Multi-year arrays (newest first)
    revenue=[394328, 365817, 274515],
    gross_profit=[169148, 152836, 104956],
    ebitda=[125820, 113817, 77344],
    ebit=[114301, 108949, 66288],
    net_income=[99803, 94680, 57411],
    interest_expense=[2931, 2645, 2873],
    tax_provision=[14527, 14527, 9680],
    
    total_assets=[352755, 351002, 323888],
    total_equity=[62146, 63090, 65339],
    total_debt=[120069, 124719, 112000],
    accounts_receivable=[28184, 26278, 16120],
    inventory=[6331, 4946, 4061],
    accounts_payable=[64115, 54763, 42296],
    current_assets=[134836, 135405, 143713],
    current_liabilities=[153982, 153982, 125481],
    goodwill=[0, 0, 0],
    intangible_assets=[0, 0, 0],
    
    # Optional: Peer data for comparison
    peer_roe_median=0.18,
    peer_asset_turnover_median=0.95,
    peer_net_margin_median=0.20
)
```

#### Key Methods:
- `run_analysis()` → Execute full DuPont analysis
- `calculate_dupont_3step()` → Net Margin × Asset Turnover × Equity Multiplier
- `calculate_dupont_5step()` → Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Equity Multiplier
- `calculate_supporting_ratios()` → Margins, turnover, liquidity ratios
- `calculate_growth_trends()` → Revenue/EBITDA/NI growth, DOL/DFL/DTL
- `calculate_peer_comparison()` → Benchmark vs. peer medians
- `validate_results()` → Check 3-step and 5-step ROE reconciliation

#### Output Structure:
```python
{
    "supporting_ratios": {
        "gross_margin": [0.429, 0.418, 0.382],
        "ebitda_margin": [0.319, 0.311, 0.282],
        "net_profit_margin": [0.253, 0.259, 0.209],
        "asset_turnover": [1.12, 1.04, 0.85],
        "roe": [1.56, 1.47, 0.85],
        # ... more ratios
    },
    "dupont_3step": {
        "net_profit_margin": [0.253, 0.259, 0.209],
        "asset_turnover": [1.12, 1.04, 0.85],
        "equity_multiplier": [5.51, 5.44, 4.80],
        "roe_reconciled": [1.56, 1.47, 0.85]
    },
    "dupont_5step": {
        "tax_burden": [0.873, 0.867, 0.856],
        "interest_burden": [0.975, 0.976, 0.959],
        "ebit_margin": [0.290, 0.298, 0.241],
        "asset_turnover": [1.12, 1.04, 0.85],
        "equity_multiplier": [5.51, 5.44, 4.80],
        "roe_reconciled": [1.56, 1.47, 0.85]
    },
    "growth_trends": {
        "revenue_growth": [None, 0.333, 0.056],
        "net_income_growth": [None, 0.649, -0.134],
        "dol": [None, 2.45, 1.89],
        "dfl": [None, 1.03, 1.04],
        "dtl": [None, 2.52, 1.97]
    },
    "validation": {
        "roe_3step_matches_direct": [True, True, True],
        "roe_5step_matches_direct": [True, True, True]
    },
    "metadata": {
        "years_analyzed": 3,
        "currency": "USD",
        "unit_scaling": "thousands"
    }
}
```

#### Usage Example:
```python
from dupont_module import DuPontAnalyzer, DuPontInputs

analyzer = DuPontAnalyzer(inputs)
results = analyzer.run_analysis()
print(results.dupont_5step.roe_reconciled[0])
```

---

### 6. `TradingCompsAnalyzer` (comps_engine.py)
**Purpose:** Trading comparables analysis with peer selection, multiple calculations, and implied valuations

#### Required Input:
```python
from comps_engine import TargetCompanyData, PeerCompanyData, TradingCompsAnalyzer

# Target company
target = TargetCompanyData(
    ticker="AAPL",
    enterprise_value=2800000,
    equity_value=2750000,
    revenue_ltm=394328,
    ebitda_ltm=125820,
    ebit_ltm=114301,
    net_income_ltm=99803,
    fcf_ltm=95000,
    book_value=62146,
    shares_outstanding=15552,
    current_price=175.0
)

# Peer group (minimum 5 recommended)
peers = [
    PeerCompanyData(ticker="MSFT", enterprise_value=2900000, equity_value=2850000, 
                    revenue_ltm=211915, ebitda_ltm=107500, ebit_ltm=88523, 
                    net_income_ltm=72361, fcf_ltm=65000, book_value=206223, 
                    shares_outstanding=7432, current_price=410.0),
    PeerCompanyData(ticker="GOOGL", enterprise_value=1800000, equity_value=1750000,
                    revenue_ltm=307394, ebitda_ltm=98500, ebit_ltm=84267,
                    net_income_ltm=73795, fcf_ltm=69000, book_value=283893,
                    shares_outstanding=12800, current_price=175.0),
    PeerCompanyData(ticker="AMZN", enterprise_value=1900000, equity_value=1850000,
                    revenue_ltm=574785, ebitda_ltm=95000, ebit_ltm=36852,
                    net_income_ltm=30425, fcf_ltm=35000, book_value=201875,
                    shares_outstanding=10330, current_price=180.0),
    PeerCompanyData(ticker="META", enterprise_value=1200000, equity_value=1150000,
                    revenue_ltm=134902, ebitda_ltm=62500, ebit_ltm=46753,
                    net_income_ltm=39098, fcf_ltm=43000, book_value=186252,
                    shares_outstanding=2550, current_price=490.0),
    PeerCompanyData(ticker="NVDA", enterprise_value=2200000, equity_value=2150000,
                    revenue_ltm=60922, ebitda_ltm=42000, ebit_ltm=32972,
                    net_income_ltm=29760, fcf_ltm=28000, book_value=42978,
                    shares_outstanding=2470, current_price=875.0)
]
```

#### Key Methods:
- `run_analysis()` → Execute full comps analysis
- `calculate_peer_multiples()` → Calculate EV/EBITDA, EV/Sales, P/E, P/B for all peers
- `calculate_statistics()` → Mean, median, std dev, percentiles for each multiple
- `filter_peers_by_iqr(multiple_type, k=1.5)` → Remove outliers using IQR method
- `calculate_implied_valuation(multiple_type, statistic="median")` → Implied EV, equity value, share price

#### Output Structure:
```python
{
    "target_multiples": {
        "ev_ebitda_ltm": 22.26,
        "ev_sales_ltm": 7.10,
        "ev_ebit_ltm": 24.52,
        "pe_diluted_ltm": 28.05,
        "pb_ltm": 44.25,
        "p_fcf_ltm": 30.00,
        "ev_fcf_ltm": 29.47
    },
    "peer_multiples": [
        {"ticker": "MSFT", "ev_ebitda_ltm": 26.98, "ev_sales_ltm": 13.68, "pe_diluted_ltm": 40.08, "pb_ltm": 13.83},
        {"ticker": "GOOGL", "ev_ebitda_ltm": 18.27, "ev_sales_ltm": 5.86, "pe_diluted_ltm": 24.33, "pb_ltm": 6.34},
        # ... more peers
    ],
    "peer_statistics": {
        "ev_ebitda_ltm": {"mean": 21.5, "median": 20.8, "std_dev": 4.2, "min": 15.3, "max": 28.5, "p25": 18.1, "p75": 24.9, "count": 5},
        "ev_sales_ltm": {...},
        "pe_diluted_ltm": {...},
        "pb_ltm": {...}
    },
    "implied_valuations": {
        "ev_ebitda_median": {
            "implied_enterprise_value": 2617000,
            "implied_equity_value": 2567000,
            "implied_share_price": 165.0,
            "current_share_price": 175.0,
            "upside_downside_pct": -5.7
        },
        "ev_sales_median": {...},
        "pe_median": {...},
        "pb_median": {...}
    },
    "peer_count": 5,
    "peer_count_after_filtering": 5,
    "metadata": {
        "analysis_date": "2026-04-22",
        "currency": "USD",
        "primary_multiple": "ev_ebitda_ltm",
        "outlier_filtering_applied": False
    }
}
```

#### Usage Example:
```python
from comps_engine import TradingCompsAnalyzer

analyzer = TradingCompsAnalyzer(target, peers)
results = analyzer.run_analysis()
print(results.implied_valuations["ev_ebitda_median"].implied_share_price)
```

---

## 🔗 INTEGRATION WITH main.py (FastAPI)

The `main.py` implements a 12-step workflow:

1. **Search Tickers** (`POST /api/step-1-search`)
2. **Select Ticker** (`POST /api/step-3-select-ticker`) → Creates session
3. **Select Models** (`POST /api/step-4-select-models`) → DCF, DuPont, COMPS
4. **Prepare Inputs** (`POST /api/step-5-6-prepare-inputs`) → Show required inputs
5. **Fetch Data** (`POST /api/step-7-8-fetch-data`) → Call `ValuationInputs.fetch_all()`
6. **Generate AI Assumptions** (`POST /api/step-9-generate-ai`) → Call `AIValuationInputs`
7. **Confirm Assumptions** (`POST /api/step-10-confirm-assumptions`)
8. **Run Valuation** (`POST /api/step-11-run-valuation`) → Call appropriate engines
9. **Return Results** → Schema-compliant JSON output

---

## 📋 REQUIRED INPUTS SUMMARY

| Module | Minimum Required Inputs | Optional Inputs |
|--------|------------------------|-----------------|
| **ValuationInputs** | `ticker` | `currency` |
| **AIValuationInputs** | `ticker` | `sec_filing_urls`, `openai_api_key` |
| **DCFInputConfiguration** | `ticker` | `valuation_date` |
| **DCFEngine** | `DCFInputs` object with all historical arrays (3 years), base balances, forecast drivers (6 periods each) | Alternative scenarios |
| **DuPontAnalyzer** | `DuPontInputs` with 3+ years of income statement and balance sheet arrays | Peer comparison data |
| **TradingCompsAnalyzer** | `TargetCompanyData` + List of 5+ `PeerCompanyData` objects | Custom peer filters |

---

## 🚀 QUICK START EXAMPLE

```python
# 1. Fetch all API data
from input import ValuationInputs
inputs = ValuationInputs(ticker="AAPL")
data = inputs.fetch_all()

# 2. Fetch AI enhancements (optional)
from input_ai import AIValuationInputs
ai_inputs = AIValuationInputs(ticker="AAPL")
ai_data = ai_inputs.fetch_all()

# 3. Get DCF-specific configuration
from input_dcf import DCFInputConfiguration
dcf_config = DCFInputConfiguration.from_ticker("AAPL")

# 4. Run DCF
from dcf_engine_full import DCFEngine, DCFInputs, ForecastDrivers
# ... construct DCFInputs from data above
dcf_engine = DCFEngine(dcf_inputs)
dcf_result = dcf_engine.calculate(scenario="base_case")

# 5. Run DuPont
from dupont_module import DuPontAnalyzer, DuPontInputs
# ... construct DuPontInputs from data above
dupont_analyzer = DuPontAnalyzer(dupont_inputs)
dupont_result = dupont_analyzer.run_analysis()

# 6. Run Comps
from comps_engine import TradingCompsAnalyzer, TargetCompanyData, PeerCompanyData
# ... construct target and peers from data above
comps_analyzer = TradingCompsAnalyzer(target, peers)
comps_result = comps_analyzer.run_analysis()
```

---

## 📊 SCHEMA COMPLIANCE

All modules produce outputs compliant with their respective schemas:
- `Unified_Valuation_API_Calculated_Schema` → `ValuationInputs`
- `Unified_Valuation_AI_Hybrid_Schema` → `AIValuationInputs`
- `dcf_input_configuration` → `DCFInputConfiguration`
- `dcf_calculation_and_output_schema` → `DCFEngine`
- `DuPont_Analysis_Outputs` → `DuPontAnalyzer`
- `Trading_Comps_Outputs` → `TradingCompsAnalyzer`

---

## ⚠️ IMPORTANT NOTES

1. **API Keys Required:** Set in `.env` file:
   ```
   ALPHA_VANTAGE_API_KEY=your_key
   OPENAI_API_KEY=your_key  # For AI features
   GOOGLE_GEMINI_API_KEY=your_key  # Alternative AI
   GROQ_API_KEY=your_key  # Alternative AI
   ```

2. **Data Availability:** Some fields may be `null` if not available from yfinance (especially for non-US tickers).

3. **Peer Selection:** For Comps, ensure peers are in the same industry/sector for meaningful comparisons.

4. **Forecast Arrays:** All DCF forecast driver arrays must have exactly 6 values (5 years + Terminal).

5. **Validation:** All engines include built-in validation (e.g., terminal growth < WACC, positive revenues).
