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
            "yfinance": "TotalRevenue",  # From financials index (CamelCase without spaces for yfinance v1.3.0+)
            "alpha_vantage": "totalRevenue",
            "financial_modeling_prep": "revenue"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF", "COMPS"]
    },
    "cost_of_revenue": {
        "display_name": "Cost of Revenue (COGS)",
        "category": MetricCategory.INCOME_STATEMENT,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "CostOfRevenue",  # From financials index (CamelCase without spaces for yfinance v1.3.0+)
            "alpha_vantage": "costOfRevenue",
            "financial_modeling_prep": "cost_of_revenue"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF", "COMPS"]
    },
    "operating_expenses": {
        "display_name": "Operating Expenses",
        "category": MetricCategory.INCOME_STATEMENT,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "OperatingExpense",  # From financials index (CamelCase without spaces for yfinance v1.3.0+)
            "alpha_vantage": "operatingExpenses",
            "financial_modeling_prep": "operating_expenses"
        },
        "validation": {"min_value": None},  # Can be negative
        "required_for_methods": ["DCF"]
    },
    "interest_expense": {
        "display_name": "Interest Expense",
        "category": MetricCategory.INCOME_STATEMENT,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "InterestExpense",  # From financials index (CamelCase without spaces for yfinance v1.3.0+)
            "alpha_vantage": "interestExpense",
            "financial_modeling_prep": "interest_expense"
        },
        "validation": {"min_value": None},  # Usually positive (expense)
        "required_for_methods": ["DCF"]
    },
    "pretax_income": {
        "display_name": "Pre-Tax Income",
        "category": MetricCategory.INCOME_STATEMENT,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "PretaxIncome",  # From financials index (CamelCase without spaces for yfinance v1.3.0+)
            "alpha_vantage": "pretaxIncome",
            "financial_modeling_prep": "pretax_income"
        },
        "validation": {"min_value": None},  # Can be negative
        "required_for_methods": ["DCF"]
    },
    "tax_provision": {
        "display_name": "Tax Provision",
        "category": MetricCategory.INCOME_STATEMENT,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "IncomeTaxExpense",  # From financials index (CamelCase without spaces for yfinance v1.3.0+)
            "alpha_vantage": "incomeTaxExpense",
            "financial_modeling_prep": "tax_provision"
        },
        "validation": {"min_value": None},  # Can be negative (tax benefit)
        "required_for_methods": ["DCF"]
    },
    "operating_income": {
        "display_name": "Operating Income (EBIT)",
        "category": MetricCategory.INCOME_STATEMENT,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "OperatingIncome",  # From financials index (CamelCase without spaces for yfinance v1.3.0+)
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
            "yfinance": "NetIncomeCommonStockholders",  # From financials index (CamelCase without spaces for yfinance v1.3.0+)
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
            "yfinance": "EBITDA",  # From financials index
            "alpha_vantage": "ebitda",
            "financial_modeling_prep": "ebitda"
        },
        "validation": {"min_value": None},
        "required_for_methods": ["DCF", "COMPS"],
        "calculation_formula": "operating_income + depreciation_amortization"  # Fallback logic
    },
    "depreciation_amortization": {
        "display_name": "Depreciation & Amortization",
        "category": MetricCategory.INCOME_STATEMENT,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "ReconciledDepreciation",  # From financials index (CamelCase without spaces for yfinance v1.3.0+)
            "alpha_vantage": "depreciationAndAmortization",
            "financial_modeling_prep": "depreciation_and_amortization"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF"]
    },
    "gross_profit": {
        "display_name": "Gross Profit",
        "category": MetricCategory.INCOME_STATEMENT,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "GrossProfit",  # From financials index (CamelCase without spaces)
        },
        "validation": {"min_value": None},
        "required_for_methods": ["DCF"],
        "calculation_formula": "revenue - cost_of_revenue"
    },
    "sg_and_a": {
        "display_name": "SG&A Expenses",
        "category": MetricCategory.INCOME_STATEMENT,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "SellingGeneralAndAdministration",  # From financials index
        },
        "validation": {"min_value": None},
        "required_for_methods": ["DCF"]
    },
    "deferred_tax": {
        "display_name": "Deferred Tax",
        "category": MetricCategory.CASH_FLOW,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "DeferredIncomeTax",  # From cashflow index
        },
        "validation": {"min_value": None},
        "required_for_methods": ["DCF"]
    },

    # --- Balance Sheet ---
    "total_assets": {
        "display_name": "Total Assets",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "TotalAssets",  # From balance sheet index (CamelCase without spaces for yfinance v1.3.0+)
            "alpha_vantage": "totalAssets",
            "financial_modeling_prep": "total_assets"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DuPont", "COMPS", "DCF"]
    },
    "accounts_receivable": {
        "display_name": "Accounts Receivable",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "Receivables",  # From balance sheet (CamelCase without spaces for yfinance v1.3.0+)
            "alpha_vantage": "receivables",
            "financial_modeling_prep": "accounts_receivable"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF"]
    },
    "inventory": {
        "display_name": "Inventory",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "Inventories",  # From balance sheet (CamelCase without spaces for yfinance v1.3.0+)
            "alpha_vantage": "inventory",
            "financial_modeling_prep": "inventory"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF"]
    },
    "accounts_payable": {
        "display_name": "Accounts Payable",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "PayablesAndAccruedExpenses",  # From balance sheet (CamelCase without spaces for yfinance v1.3.0+)
            "alpha_vantage": "payables",
            "financial_modeling_prep": "accounts_payable"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF"]
    },
    "shareholders_equity": {
        "display_name": "Shareholders Equity",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "StockholdersEquity",  # From balance sheet (CamelCase without spaces for yfinance v1.3.0+)
            "alpha_vantage": "totalShareholderEquity",
            "financial_modeling_prep": "total_equity"
        },
        "validation": {"min_value": None},
        "required_for_methods": ["DCF"]
    },
    "total_liabilities": {
        "display_name": "Total Liabilities",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "TotalLiabilitiesNetMinorityInterest",  # From balance sheet (CamelCase without spaces for yfinance v1.3.0+)
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
            "yfinance": "StockholdersEquity",  # From balance sheet (CamelCase without spaces for yfinance v1.3.0+)
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
            "yfinance": "CashAndCashEquivalents",  # From balance sheet (CamelCase without spaces for yfinance v1.3.0+)
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
            "yfinance": "TotalDebt",  # From balance sheet (CamelCase without spaces for yfinance v1.3.0+)
            "alpha_vantage": "totalDebt",
            "financial_modeling_prep": "total_debt"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF", "DuPont"],
        "calculation_formula": "short_term_debt + long_term_debt"
    },
    "long_term_debt": {
        "display_name": "Long-Term Debt",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "LongTermDebt",
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF"]
    },
    "net_debt": {
        "display_name": "Net Debt",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "NetDebt",
        },
        "validation": {"min_value": None},
        "required_for_methods": ["DCF"],
        "calculation_formula": "total_debt - cash_and_equivalents"
    },
    "ppe_net": {
        "display_name": "PP&E (Net)",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "NetPPE",
        },
        "validation": {"min_value": None},
        "required_for_methods": ["DCF"]
    },
    "retained_earnings": {
        "display_name": "Retained Earnings",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "RetainedEarnings",
        },
        "validation": {"min_value": None},
        "required_for_methods": ["DCF"]
    },
    "total_current_assets": {
        "display_name": "Total Current Assets",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "CurrentAssets",
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF"]
    },
    "total_current_liabilities": {
        "display_name": "Total Current Liabilities",
        "category": MetricCategory.BALANCE_SHEET,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "CurrentLiabilities",
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF"]
    },

    # --- Cash Flow ---
    "working_capital_change": {
        "display_name": "Change in Working Capital",
        "category": MetricCategory.CASH_FLOW,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "ChangeInWorkingCapital",
        },
        "validation": {"min_value": None},
        "required_for_methods": ["DCF"]
    },
    "dividends_paid": {
        "display_name": "Dividends Paid",
        "category": MetricCategory.CASH_FLOW,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "CashDividendsPaid",
        },
        "validation": {"min_value": None},
        "required_for_methods": ["DCF"]
    },
    "operating_cash_flow": {
        "display_name": "Operating Cash Flow",
        "category": MetricCategory.CASH_FLOW,
        "type": DataType.FLOAT,
        "unit": "currency",
        "sources": {
            "yfinance": "OperatingCashFlow",  # From cash flow (CamelCase without spaces for yfinance v1.3.0+)
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
            "yfinance": "CapitalExpenditure",  # From cash flow (CamelCase without spaces for yfinance v1.3.0+)
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
            "yfinance": "FreeCashFlow",  # From cash flow (CamelCase without spaces for yfinance v1.3.0+)
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
            "yfinance": "marketCap",  # From info dict
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
            "yfinance": "sharesOutstanding",  # From info dict
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
            "yfinance": "currentPrice",  # From info dict
            "alpha_vantage": "price",
            "financial_modeling_prep": "price"
        },
        "validation": {"min_value": 0},
        "required_for_methods": ["DCF", "COMPS"]
    },
    "beta": {
        "display_name": "Beta",
        "category": MetricCategory.MARKET_DATA,
        "type": DataType.FLOAT,
        "unit": "ratio",
        "sources": {
            "yfinance": "beta",  # From info dict
            "alpha_vantage": "beta",
            "financial_modeling_prep": "beta"
        },
        "validation": {"min_value": -2.0, "max_value": 5.0},
        "required_for_methods": ["DCF", "COMPS"]
    },

    # --- Ratios (Often calculated, but can be fetched) ---
    "pe_ratio": {
        "display_name": "P/E Ratio",
        "category": MetricCategory.RATIOS,
        "type": DataType.FLOAT,
        "unit": "ratio",
        "sources": {
            "yfinance": "trailingPE",  # From info dict
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
            "yfinance": "priceToBook",  # From info dict
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
            "yfinance": "returnOnEquity",  # From info dict
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
            "yfinance": "returnOnAssets",  # From info dict
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
            "yfinance": "profitMargins",  # From info dict
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
            "yfinance": "assetTurnover",  # Not always direct
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
        "sources": {
            "yfinance": "effectiveTaxRate",  # From info dict (key_stats)
            "alpha_vantage": "taxRate",
            "financial_modeling_prep": "effectiveTaxRate"
        },
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