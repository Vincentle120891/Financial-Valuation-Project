"""
International Services Package

Business logic and data orchestration for international markets:
- Input validation and transformation
- Data fetching from yfinance and international sources
- DCF, Comps, and DuPont input building
"""

from app.services.international.dcf_input_manager import (
    DCFInputManager,
    build_dupont_inputs,
    build_comps_selection_inputs,
    build_comps_valuation_inputs,
    apply_iqr_outlier_filtering,
)

from app.services.international.yfinance_service import (
    YFinanceService,
    fetch_yfinance_data,
)

from app.services.international.international_ticker_service import (
    InternationalTickerService,
)

from app.services.international.metrics_calculator import (
    MetricsCalculator,
    calculate_metrics,
    fetch_and_calculate_all_metrics,
)

__all__ = [
    # Input Manager
    "DCFInputManager",
    "build_dupont_inputs",
    "build_comps_selection_inputs",
    "build_comps_valuation_inputs",
    "apply_iqr_outlier_filtering",
    
    # YFinance Service
    "YFinanceService",
    "fetch_yfinance_data",
    
    # Ticker Service
    "InternationalTickerService",
    
    # Metrics Calculator
    "MetricsCalculator",
    "calculate_metrics",
    "fetch_and_calculate_all_metrics",
]
