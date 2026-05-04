"""
International Services Package

Business logic and data orchestration for international markets:
- Input validation and transformation
- Data fetching from yfinance and international sources
- DCF, Comps, and DuPont input building
"""

from app.services.international.dcf_input_manager import (
    ValuationInputManager,
    build_dupont_inputs,
    build_comps_selection_inputs,
    build_comps_valuation_inputs,
    apply_iqr_outlier_filtering,
)

from app.services.yfinance_service import (
    YFinanceService,
    fetch_financials,
    fetch_historical_prices,
    fetch_company_info,
)

from app.services.international_ticker_service import (
    InternationalTickerService,
    validate_ticker_format,
    get_ticker_exchange,
)

from app.services.metrics_calculator import (
    MetricsCalculator,
    calculate_financial_ratios,
    calculate_growth_rates,
)

__all__ = [
    # Input Manager
    "ValuationInputManager",
    "build_dupont_inputs",
    "build_comps_selection_inputs",
    "build_comps_valuation_inputs",
    "apply_iqr_outlier_filtering",
    
    # YFinance Service
    "YFinanceService",
    "fetch_financials",
    "fetch_historical_prices",
    "fetch_company_info",
    
    # Ticker Service
    "InternationalTickerService",
    "validate_ticker_format",
    "get_ticker_exchange",
    
    # Metrics Calculator
    "MetricsCalculator",
    "calculate_financial_ratios",
    "calculate_growth_rates",
]
