"""
Centralized Metric Registry for DCF Model
Maps internal metric IDs to external API keys and defines validation rules.
"""
from typing import Dict, List, Any, Optional
from enum import Enum

class DataType(Enum):
    FLOAT = "float"
    INTEGER = "integer"
    PERCENTAGE = "percentage"
    STRING = "string"
    DATE = "date"

class MetricCategory(Enum):
    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"
    MARKET_DATA = "market_data"
    RATIOS = "ratios"
    FORECAST = "forecast"

# Central Registry Definition
METRIC_REGISTRY: Dict[str, Dict[str, Any]] = {
    # --- Income Statement ---
    "revenue": {
        "display_name": "Total Revenue",
        "category": MetricCategory.INCOME_STATEMENT,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "total_revenue",
            "alpha_vantage": "totalRevenue",
            "financial_modeling_prep": "revenue"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF", "COMPS"]
    },
    "operating_income": {
        "display_name": "Operating Income (EBIT)",
        "category": MetricCategory.INCOME_STATEMENT,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "operating_income",
            "alpha_vantage": "operatingIncome",
            "financial_modeling_prep": "operating_income"
        },
        "validation": {"min_value": None}, # Can be negative
        "required_for_methods": ["DCF", "DuPont"]
    },
    "net_income": {
        "display_name": "Net Income",
        "category": MetricCategory.INCOME_STATEMENT,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "net_income",
            "alpha_vantage": "netIncome",
            "financial_modeling_prep": "net_income"
        },
        "validation": {"min_value": None},
        "required_for_methods": ["DCF", "DuPont", "COMPS"]
    },
    "ebitda": {
        "display_name": "EBITDA",
        "category": MetricCategory.INCOME_STATEMENT,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "ebitda",
            "alpha_vantage": "ebitda", # Sometimes not direct
            "financial_modeling_prep": "ebitda"
        },
        "validation": {"min_value": None},
        "required_for_methods": ["DCF", "COMPS"],
        "calculation_formula": "operating_income + depreciation_amortization" # Fallback logic
    },
    "depreciation_amortization": {
        "display_name": "Depreciation & Amortization",
        "category": MetricCategory.INCOME_STATEMENT,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "depreciation_and_amortization",
            "alpha_vantage": "depreciationAndAmortization",
            "financial_modeling_prep": "depreciation_and_amortization"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF"]
    },
    
    # --- Balance Sheet ---
    "total_assets": {
        "display_name": "Total Assets",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "total_assets",
            "alpha_vantage": "totalAssets",
            "financial_modeling_prep": "total_assets"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DuPont", "COMPS"]
    },
    "total_liabilities": {
        "display_name": "Total Liabilities",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "total_liabilities_net_minority_interest",
            "alpha_vantage": "totalLiabilities",
            "financial_modeling_prep": "total_liabilities"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DuPont"]
    },
    "total_equity": {
        "display_name": "Total Shareholders Equity",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "total_stockholder_equity",
            "alpha_vantage": "totalShareholderEquity",
            "financial_modeling_prep": "total_equity"
        },
        "validation": {"min_value": None},
        "required_for_methods": ["DuPont", "COMPS"]
    },
    "cash_and_equivalents": {
        "display_name": "Cash and Cash Equivalents",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "cash_and_cash_equivalents",
            "alpha_vantage": "cashAndCashEquivalents",
            "financial_modeling_prep": "cash_and_short_term_investments"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF"]
    },
    "total_debt": {
        "display_name": "Total Debt",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "total_debt", # Might need sum of short/long term
            "alpha_vantage": "totalDebt",
            "financial_modeling_prep": "total_debt"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF", "DuPont"],
        "calculation_formula": "short_term_debt + long_term_debt"
    },

    # --- Cash Flow ---
    "operating_cash_flow": {
        "display_name": "Operating Cash Flow",
        "category": MetricCategory.CASH_FLOW,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "operating_cash_flow",
            "alpha_vantage": "operatingCashflow",
            "financial_modeling_prep": "operating_cash_flow"
        },
        "validation": {"min_value": None},
        "required_for_methods": ["DCF"]
    },
    "capex": {
        "display_name": "Capital Expenditure",
        "category": MetricCategory.CASH_FLOW,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "capital_expenditure",
            "alpha_vantage": "capitalExpenditure",
            "financial_modeling_prep": "capital_expenditure"
        },
        "validation": {"max_value": 0}, # Usually negative in CF
        "required_for_methods": ["DCF"],
        "normalization": "absolute_value" # Store as positive for calculations
    },
    "free_cash_flow": {
        "display_name": "Free Cash Flow",
        "category": MetricCategory.CASH_FLOW,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "free_cash_flow",
            "alpha_vantage": "freeCashflow",
            "financial_modeling_prep": "free_cash_flow"
        },
        "validation": {"min_value": None},
        "required_for_methods": ["DCF"],
        "calculation_formula": "operating_cash_flow - capex"
    },

    # --- Market Data ---
    "market_cap": {
        "display_name": "Market Capitalization",
        "category": MetricCategory.MARKET_DATA,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "market_cap",
            "alpha_vantage": "marketCapitalization",
            "financial_modeling_prep": "market_cap"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["COMPS", "DCF"]
    },
    "shares_outstanding": {
        "display_name": "Shares Outstanding",
        "category": MetricCategory.MARKET_DATA,
        "type": DataType.FLOAT,
        "unit": "shares",
        "sources": {
            "yfinance": "shares_outstanding",
            "alpha_vantage": "sharesOutstanding",
            "financial_modeling_prep": "shares_outstanding"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF", "COMPS"]
    },
    "current_price": {
        "display_name": "Current Stock Price",
        "category": MetricCategory.MARKET_DATA,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "current_price",
            "alpha_vantage": "price",
            "financial_modeling_prep": "price"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF", "COMPS"]
    },

    # --- Ratios (Often calculated, but can be fetched) ---
    "pe_ratio": {
        "display_name": "P/E Ratio",
        "category": MetricCategory.RATIOS,
        "type": DataType.FLOAT,
        "unit": "ratio",
        "sources": {
            "yfinance": "trailing_pe",
            "alpha_vantage": "pe_ratio",
            "financial_modeling_prep": "price_earnings_ratio"
        },
        "validation": {"min_value": None},
        "required_for_methods": ["COMPS"],
        "calculation_formula": "market_cap / net_income"
    },
    "pb_ratio": {
        "display_name": "P/B Ratio",
        "category": MetricCategory.RATIOS,
        "type": DataType.FLOAT,
        "unit": "ratio",
        "sources": {
            "yfinance": "price_to_book",
            "alpha_vantage": "pb_ratio",
            "financial_modeling_prep": "price_to_book_ratio"
        },
        "validation": {"min_value": None},
        "required_for_methods": ["COMPS", "DuPont"],
        "calculation_formula": "market_cap / total_equity"
    },
    "roe": {
        "display_name": "Return on Equity",
        "category": MetricCategory.RATIOS,
        "type": DataType.PERCENTAGE,
        "unit": "percent",
        "sources": {
            "yfinance": "return_on_equity",
            "alpha_vantage": "roe",
            "financial_modeling_prep": "return_on_equity"
        },
        "validation": {"min_value": -1.0, "max_value": 1.0},
        "required_for_methods": ["DuPont", "COMPS"],
        "calculation_formula": "net_income / total_equity"
    },
    "roa": {
        "display_name": "Return on Assets",
        "category": MetricCategory.RATIOS,
        "type": DataType.PERCENTAGE,
        "unit": "percent",
        "sources": {
            "yfinance": "return_on_assets",
            "alpha_vantage": "roa",
            "financial_modeling_prep": "return_on_assets"
        },
        "validation": {"min_value": -1.0, "max_value": 1.0},
        "required_for_methods": ["DuPont"],
        "calculation_formula": "net_income / total_assets"
    },
    "profit_margin": {
        "display_name": "Net Profit Margin",
        "category": MetricCategory.RATIOS,
        "type": DataType.PERCENTAGE,
        "unit": "percent",
        "sources": {
            "yfinance": "profit_margin",
            "alpha_vantage": "net_profit_margin",
            "financial_modeling_prep": "net_profit_margin"
        },
        "validation": {"min_value": -1.0, "max_value": 1.0},
        "required_for_methods": ["DuPont", "DCF"],
        "calculation_formula": "net_income / revenue"
    },
    "asset_turnover": {
        "display_name": "Asset Turnover",
        "category": MetricCategory.RATIOS,
        "type": DataType.FLOAT,
        "unit": "ratio",
        "sources": {
            "yfinance": "asset_turnover", # Not always direct
            "alpha_vantage": "asset_turnover",
            "financial_modeling_prep": "asset_turnover"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DuPont"],
        "calculation_formula": "revenue / total_assets"
    },
    "equity_multiplier": {
        "display_name": "Equity Multiplier",
        "category": MetricCategory.RATIOS,
        "type": DataType.FLOAT,
        "unit": "ratio",
        "sources": {}, # Usually calculated
        "validation": {"min_value": 0},
        "required_for_methods": ["DuPont"],
        "calculation_formula": "total_assets / total_equity"
    },
    
    # --- Forecast Inputs (Step 8) ---
    "revenue_growth_rate": {
        "display_name": "Revenue Growth Rate",
        "category": MetricCategory.FORECAST,
        "type": DataType.PERCENTAGE,
        "unit": "percent",
        "sources": {}, # User/AI input
        "validation": {"min_value": -0.5, "max_value": 2.0},
        "required_for_methods": ["DCF"]
    },
    "ebitda_margin_forecast": {
        "display_name": "Forecasted EBITDA Margin",
        "category": MetricCategory.FORECAST,
        "type": DataType.PERCENTAGE,
        "unit": "percent",
        "sources": {},
        "validation": {"min_value": -0.5, "max_value": 1.0},
        "required_for_methods": ["DCF"]
    },
    "tax_rate": {
        "display_name": "Effective Tax Rate",
        "category": MetricCategory.FORECAST,
        "type": DataType.PERCENTAGE,
        "unit": "percent",
        "sources": {},
        "validation": {"min_value": 0, "max_value": 1.0},
        "required_for_methods": ["DCF"]
    },
    "capex_percent_revenue": {
        "display_name": "Capex as % of Revenue",
        "category": MetricCategory.FORECAST,
        "type": DataType.PERCENTAGE,
        "unit": "percent",
        "sources": {},
        "validation": {"min_value": 0, "max_value": 1.0},
        "required_for_methods": ["DCF"]
    },
    "nwc_percent_revenue": {
        "display_name": "Net Working Capital as % of Revenue",
        "category": MetricCategory.FORECAST,
        "type": DataType.PERCENTAGE,
        "unit": "percent",
        "sources": {},
        "validation": {"min_value": -0.5, "max_value": 1.0},
        "required_for_methods": ["DCF"]
    },
    "wacc": {
        "display_name": "Weighted Average Cost of Capital",
        "category": MetricCategory.FORECAST,
        "type": DataType.PERCENTAGE,
        "unit": "percent",
        "sources": {},
        "validation": {"min_value": 0, "max_value": 0.5},
        "required_for_methods": ["DCF"]
    },
    "terminal_growth_rate": {
        "display_name": "Terminal Growth Rate",
        "category": MetricCategory.FORECAST,
        "type": DataType.PERCENTAGE,
        "unit": "percent",
        "sources": {},
        "validation": {"min_value": -0.05, "max_value": 0.10},
        "required_for_methods": ["DCF"]
    }
}

def get_metric_definition(metric_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full definition for a metric."""
    return METRIC_REGISTRY.get(metric_id)

def get_source_key(metric_id: str, provider: str) -> Optional[str]:
    """Get the specific API key for a metric from a specific provider."""
    metric = METRIC_REGISTRY.get(metric_id)
    if not metric:
        return None
    return metric["sources"].get(provider)

def get_required_metrics_for_method(method: str) -> List[str]:
    """Get list of metric IDs required for a specific valuation method."""
    return [
        mid for mid, data in METRIC_REGISTRY.items() 
        if method in data.get("required_for_methods", [])
    ]

def get_calculated_metrics() -> List[str]:
    """Get list of metrics that have calculation formulas."""
    return [
        mid for mid, data in METRIC_REGISTRY.items() 
        if "calculation_formula" in data
    ]
