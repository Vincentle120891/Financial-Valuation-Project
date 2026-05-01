"""
__init__.py for Vietnam-specific valuation engines

This package provides sector-specific valuation models for Vietnamese stocks:

1. sector_valuation_models.py - Specialized models by sector
   - Banking: DDM + Residual Income + P/BV
   - Real Estate: NAV + RNAV
   - Manufacturing: Commodity-Adjusted DCF

Usage:
    from backend.app.engines.vietnam import valuate_vn_stock, VNSectorValuationEngine
"""

from .sector_valuation_models import (
    VNSectorValuationEngine,
    VNSectorValuationType,
    BankingValuationInputs,
    RealEstateValuationInputs,
    ManufacturingValuationInputs,
    SectorValuationResult,
    valuate_vn_stock
)

__all__ = [
    'VNSectorValuationEngine',
    'VNSectorValuationType',
    'BankingValuationInputs',
    'RealEstateValuationInputs',
    'ManufacturingValuationInputs',
    'SectorValuationResult',
    'valuate_vn_stock'
]

# Version info
__version__ = '1.0.0'
__author__ = 'Vietnamese Market Team'
