"""
Engines Package - Valuation Calculation Engines

Unified engines package supporting both:
- International markets (IFRS/US GAAP)
- Vietnamese market (TT99 accounting standards)

Structure:
├── international/ - International market engines
└── vietnam/       - Vietnamese market engines
"""

# Re-export from subpackages for backward compatibility
from app.engines.international import (
    DCFEngine,
    TradingCompsAnalyzer,
    DuPontAnalyzer,
    ai_engine,
    AIFallbackEngine,
)

from app.engines.vietnam import (
    VietnameseDCFEngine,
    VNSectorValuationEngine,
    SectorValuationResult,
)

__all__ = [
    # International Engines
    "DCFEngine",
    "TradingCompsAnalyzer",
    "DuPontAnalyzer",
    "ai_engine",
    "AIFallbackEngine",
    
    # Vietnamese Engines
    "VietnameseDCFEngine",
    "VNSectorValuationEngine",
    "SectorValuationResult",
]
