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
    vn_Step1TickerProcessor as VNStep1TickerProcessor,
    vn_TickerInfo as VNTickerInfo,
    vn_Step1Response as VNStep1Response,
)

from app.services.vietnamese.vn_step2_market_data_processor import (
    vn_Step2MarketDataProcessor as VNStep2MarketDataProcessor,
    vn_MarketDataPoint as VNMarketDataPoint,
    vn_MarketRiskMetrics as VNMarketRiskMetrics,
    vn_Step2Response as VNStep2Response,
)

from app.services.vietnamese.vn_mismatch_historical_processor import (
    vn_Step3HistoricalProcessor as VNStep3HistoricalProcessor,
    vn_HistoricalYearData as VNHistoricalYearData,
    vn_CalculatedMetrics as VNCalculatedMetrics,
    vn_Step3Response as VNStep3Response,
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
    "VNStep1TickerProcessor",
    "VNTickerInfo",
    "VNStep1Response",
    
    "VNStep2MarketDataProcessor",
    "VNMarketDataPoint",
    "VNMarketRiskMetrics",
    "VNStep2Response",
    
    "VNStep3HistoricalProcessor",
    "VNHistoricalYearData",
    "VNCalculatedMetrics",
    "VNStep3Response",
]
