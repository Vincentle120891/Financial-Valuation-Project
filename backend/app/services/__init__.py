"""
Services Package - Business Logic and Orchestration

Unified services package supporting both:
- International markets (yfinance, IFRS/US GAAP)
- Vietnamese market (VNDirect, CafeF, TT99)

Structure:
├── international/ - International market services
└── vietnam/       - Vietnamese market services
"""

# Import step7 functions first to avoid circular imports
from .step7_pdf_extraction import extract_financial_metric_from_text
from .step7_web_search_analysis import (
    analyze_web_search_results,
    validate_and_clean_financial_data
)

# Re-export from subpackages for backward compatibility
from app.services.international import (
    DCFInputManager,
    YFinanceService,
    InternationalTickerService,
    MetricsCalculator,
    # Enhanced Services - Mismatch Prevention Layer
    APIAdapter,
    process_multiple_tickers,
    Step7Resolver,
    AuditLogger,
    get_audit_logger,
    TransformationType,
    DataVersioningService,
    get_versioning_service,
)

from app.services.vietnamese import (
    VietnameseInputManager,
    VNStockDatabase,
    VNDFinancialParser,
    VietnameseTickerService,
    VietnamDataAggregator,
    VietnameseReportScraper,
)

__all__ = [
    # Core Services
    "extract_financial_metric_from_text",
    "analyze_web_search_results",
    "validate_and_clean_financial_data",
    
    # International
    "DCFInputManager",
    "YFinanceService",
    "InternationalTickerService",
    "MetricsCalculator",
    
    # Enhanced Services - Mismatch Prevention Layer
    "APIAdapter",
    "process_multiple_tickers",
    "Step7Resolver",
    "AuditLogger",
    "get_audit_logger",
    "TransformationType",
    "DataVersioningService",
    "get_versioning_service",
    
    # Vietnamese
    "VietnameseInputManager",
    "VNStockDatabase",
    "VNDFinancialParser",
    "VietnameseTickerService",
    "VietnamDataAggregator",
    "VietnameseReportScraper",
]
