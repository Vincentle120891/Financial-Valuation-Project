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
    
    # Vietnamese
    "VietnameseInputManager",
    "VNStockDatabase",
    "VNDFinancialParser",
    "VietnameseTickerService",
    "VietnamDataAggregator",
    "VietnameseReportScraper",
]
