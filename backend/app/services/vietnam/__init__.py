"""
Vietnamese Services Package

Business logic and data orchestration for Vietnamese market:
- Input validation and transformation for TT99 standards
- Data fetching from VNDirect, CafeF, and VNStockDatabase
- DCF, Comps, and DuPont input building for Vietnamese stocks
"""

from app.services.vietnamese_input_manager import (
    VietnameseInputManager,
    build_vn_dcf_request,
    build_vn_comps_selection_request,
    build_vn_comps_valuation_request,
    build_vn_dupont_request,
)

from app.services.vietnam.vn_stock_database import (
    VNStockDatabase,
    fetch_vn_financials,
    get_vn_company_info,
    query_vnindex_constituents,
)

from app.services.vietnam.vnd_financial_parser import (
    VNDFinancialParser,
    parse_tt99_balance_sheet,
    parse_tt99_income_statement,
)

from app.services.vietnamese_ticker_service import (
    VietnameseTickerService,
    validate_vn_ticker_format,
    get_vn_exchange,
    parse_ticker_suffix,
)

from app.services.vietnam_data_aggregator import (
    VietnamDataAggregator,
    aggregate_vn_financials,
    fetch_vn_market_data,
)

from app.services.vietnamese_report_scraper import (
    VietnameseReportScraper,
    fetch_vn_annual_report,
    scrape_cafef_data,
)

__all__ = [
    # Input Manager
    "VietnameseInputManager",
    "build_vn_dcf_request",
    "build_vn_comps_selection_request",
    "build_vn_comps_valuation_request",
    "build_vn_dupont_request",
    
    # VNStock Database
    "VNStockDatabase",
    "fetch_vn_financials",
    "get_vn_company_info",
    "query_vnindex_constituents",
    
    # VND Financial Parser
    "VNDFinancialParser",
    "parse_tt99_balance_sheet",
    "parse_tt99_income_statement",
    
    # Ticker Service
    "VietnameseTickerService",
    "validate_vn_ticker_format",
    "get_vn_exchange",
    "parse_ticker_suffix",
    
    # Data Aggregator
    "VietnamDataAggregator",
    "aggregate_vn_financials",
    "fetch_vn_market_data",
    
    # Report Scraper
    "VietnameseReportScraper",
    "fetch_vn_annual_report",
    "scrape_cafef_data",
]
