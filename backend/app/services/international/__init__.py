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

# Step Processors - Complete 10-Step Workflow
from app.services.international.step1_ticker_processor import Step1TickerProcessor
from app.services.international.step2_market_data_processor import Step2MarketDataProcessor
from app.services.international.step3_historical_processor import Step3HistoricalProcessor
from app.services.international.step4_forecast_processor import Step4ForecastProcessor
from app.services.international.step5_assumptions_processor import Step5AssumptionsProcessor
from app.services.international.step6_data_review import Step6DataReviewProcessor
from app.services.international.step7_ai_suggestions import Step7AISuggestionsProcessor
from app.services.international.step8_manual_overrides import Step8ManualOverridesProcessor
from app.services.international.step9_final_calculation import Step9FinalCalculationProcessor
from app.services.international.step10_valuation_processor import Step10ValuationProcessor

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
    
    # Step Processors - Complete 10-Step Workflow
    "Step1TickerProcessor",
    "Step2MarketDataProcessor",
    "Step3HistoricalProcessor",
    "Step4ForecastProcessor",
    "Step5AssumptionsProcessor",
    "Step6DataReviewProcessor",
    "Step7AISuggestionsProcessor",
    "Step8ManualOverridesProcessor",
    "Step9FinalCalculationProcessor",
    "Step10ValuationProcessor",
]
