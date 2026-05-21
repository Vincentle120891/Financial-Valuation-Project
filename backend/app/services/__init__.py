"""
Services Package - Business Logic and Orchestration

Unified services package supporting both:
- International markets (yfinance, IFRS/US GAAP)
- Vietnamese market (VNDirect, CafeF, TT99)

Structure:
├── international/ - International market services
└── vietnam/       - Vietnamese market services
"""

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
