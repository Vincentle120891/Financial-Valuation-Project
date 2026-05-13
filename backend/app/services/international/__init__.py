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

# Shared Context Service - Centralized data fetching for common company information
from app.services.international.shared_context_service import (
    SharedContextService,
    SharedContextData,
    shared_context_service,
)

# Step Processors - Complete 10-Step Workflow
from app.services.international.step1_ticker_processor import Step1TickerProcessor
from app.services.international.step2_market_data_processor import Step2MarketDataProcessor
from app.services.international.step3_peer_management_service import Step3PeerManagementService
from app.services.international.step4_selected_models_processor import Step4SelectedModelsProcessor
from app.services.international.step5_required_inputs_processor import Step5RequiredInputsProcessor
from app.services.international.step6_data_review import Step6DataReviewProcessor
# Step 6 Specialized Processors - Individual Valuation Method Processors
from app.services.international.step6_dcf_data_review import DCFStep6Processor as DCFDataReviewProcessor
from app.services.international.step6_dupont_data_review import DuPontStep6Processor as DuPontDataReviewProcessor
from app.services.international.step6_comps_data_review import CompsStep6Processor as CompsDataReviewProcessor
from app.services.international.step7_historical_data_processor import Step7HistoricalDataProcessor
# Step 7 Specialized Processors - Individual Valuation Method Processors
from app.services.international.step7_dcf_historical_data import DCFStep7Processor as DCFHistoricalDataProcessor
from app.services.international.step7_dupont_historical_data import DuPontStep7Processor as DuPontHistoricalDataProcessor
from app.services.international.step7_comps_historical_data import CompsStep7Processor as CompsHistoricalDataProcessor
# Step 8 Specialized Processors - Individual Valuation Method Assumption Processors
from app.services.international.step8_dcf_assumptions import DCFStep8Processor as DCFAssumptionsProcessor
from app.services.international.step8_dupont_assumptions import DuPontStep8Processor as DuPontAssumptionsProcessor
from app.services.international.step8_comps_assumptions import CompsStep8Processor as CompsAssumptionsProcessor
from app.services.international.step8_manual_overrides import Step8ManualOverridesProcessor
from app.services.international.step9_confirmation_processor import Step9ConfirmationProcessor as Step9FinalCalculationProcessor
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
    
    # Shared Context Service
    "SharedContextService",
    "SharedContextData",
    "shared_context_service",
    
    # Step Processors - Complete 10-Step Workflow
    "Step1TickerProcessor",
    "Step2MarketDataProcessor",
    "Step3PeerManagementService",
    "Step4SelectedModelsProcessor",
    "Step5RequiredInputsProcessor",
    "Step6DataReviewProcessor",
    "DCFDataReviewProcessor",  # Step 6 DCF-specific processor alias
    "DuPontDataReviewProcessor",  # Step 6 DuPont-specific processor alias
    "CompsDataReviewProcessor",  # Step 6 Comps-specific processor alias
    "Step7HistoricalDataProcessor",
    "DCFHistoricalDataProcessor",  # Step 7 DCF-specific processor alias
    "DuPontHistoricalDataProcessor",  # Step 7 DuPont-specific processor alias
    "CompsHistoricalDataProcessor",  # Step 7 Comps-specific processor alias
    "Step8ManualOverridesProcessor",
    "DCFAssumptionsProcessor",  # Step 8 DCF-specific assumption processor alias
    "DuPontAssumptionsProcessor",  # Step 8 DuPont-specific assumption processor alias
    "CompsAssumptionsProcessor",  # Step 8 Comps-specific assumption processor alias
    "Step9FinalCalculationProcessor",
    "Step10ValuationProcessor",
]
