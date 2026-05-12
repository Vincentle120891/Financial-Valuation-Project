"""
Vietnamese Services Package

Business logic and data orchestration for Vietnamese market:
- Input validation and transformation for TT99 standards
- Data fetching from VNDirect, CafeF, and VNStockDatabase
- DCF, Comps, and DuPont input building for Vietnamese stocks
"""

from app.services.vietnamese.vietnamese_input_manager import (
    VietnameseInputManager,
    get_vietnamese_input_manager,
)

from app.services.vietnamese.vn_stock_database import (
    VNStockDatabase,
    get_vn_stock_database,
)

from app.services.vietnamese.vnd_financial_parser import (
    VNDFinancialParser,
    parse_vn_financials_from_dict,
)

from app.services.vietnamese.vietnamese_ticker_service import (
    VietnameseTickerService,
)

from app.services.vietnamese.vietnam_data_aggregator import (
    VietnamDataAggregator,
)

from app.services.vietnamese.vietnamese_report_scraper import (
    VietnameseReportScraper,
    fetch_vietnamese_report,
)

from app.services.vietnamese.vietnamese_dcf_engine import (
    VietnameseDCFEngine,
    get_vietnamese_dcf_engine,
)

from app.services.vietnamese.vietnamese_comps_engine import (
    VNTradingCompsAnalyzer,
    VNTargetCompanyData,
    VNPeerCompanyData,
    VNTradingCompsOutputs,
)

from app.services.vietnamese.vietnamese_dupont_engine import (
    VNDuPontAnalyzer,
    VNFinancialStatements,
    VNDuPontResult,
)

from app.services.vietnamese.vn_step1_ticker_processor import (
    vn_Step1TickerProcessor,
    vn_TickerInfo,
    vn_Step1Response,
)

from app.services.vietnamese.vn_step2_market_data_processor import (
    vn_Step2MarketDataProcessor,
    vn_MarketDataPoint,
    vn_MarketRiskMetrics,
    vn_Step2Response,
)

from app.services.vietnamese.vn_step3_historical_processor import (
    vn_Step3HistoricalProcessor,
    vn_HistoricalYearData,
    vn_CalculatedMetrics,
    vn_Step3Response,
)

from app.services.vietnamese.vn_step8_dcf_assumptions import (
    vn_DCFStep8Processor,
    vn_DCFAssumptionsOutput,
)

from app.services.vietnamese.vn_step8_dupont_assumptions import (
    vn_DuPontStep8Processor,
    vn_DuPontAssumptionsOutput,
)

from app.services.vietnamese.vn_step8_comps_assumptions import (
    vn_CompsStep8Processor,
    vn_CompsAssumptionsOutput,
)

__all__ = [
    # Input Manager
    "VietnameseInputManager",
    "get_vietnamese_input_manager",

    # VNStock Database
    "VNStockDatabase",
    "get_vn_stock_database",

    # VND Financial Parser
    "VNDFinancialParser",
    "parse_vn_financials_from_dict",

    # Ticker Service
    "VietnameseTickerService",

    # Data Aggregator
    "VietnamDataAggregator",

    # Report Scraper
    "VietnameseReportScraper",
    "fetch_vietnamese_report",

    # DCF Engine
    "VietnameseDCFEngine",
    "get_vietnamese_dcf_engine",

    # Comps Engine
    "VNTradingCompsAnalyzer",
    "VNTargetCompanyData",
    "VNPeerCompanyData",
    "VNTradingCompsOutputs",

    # DuPont Engine
    "VNDuPontAnalyzer",
    "VNFinancialStatements",
    "VNDuPontResult",

    # Step Processors
    "vn_Step1TickerProcessor",
    "vn_TickerInfo",
    "vn_Step1Response",

    "vn_Step2MarketDataProcessor",
    "vn_MarketDataPoint",
    "vn_MarketRiskMetrics",
    "vn_Step2Response",

    "vn_Step3HistoricalProcessor",
    "vn_HistoricalYearData",
    "vn_CalculatedMetrics",
    "vn_Step3Response",

    # Step 8 DCF Assumptions
    "vn_DCFStep8Processor",
    "vn_DCFAssumptionsOutput",

    # Step 8 DuPont Assumptions
    "vn_DuPontStep8Processor",
    "vn_DuPontAssumptionsOutput",

    # Step 8 Comps Assumptions
    "vn_CompsStep8Processor",
    "vn_CompsAssumptionsOutput",
]