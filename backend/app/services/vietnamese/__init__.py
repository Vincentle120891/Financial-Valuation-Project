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
]
