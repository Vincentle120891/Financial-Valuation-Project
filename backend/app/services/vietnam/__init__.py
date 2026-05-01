"""
__init__.py for Vietnam-specific modules

This package provides comprehensive support for Vietnamese stock market analysis:

1. vn_stock_database.py - Scalable database for 700+ HOSE stocks
2. vnd_financial_parser.py - VND financial statement parser (VAS to IFRS)
3. sector_valuation_models.py - Sector-specific valuation models

Usage:
    from backend.app.services.vietnam import get_vn_stock_database
    from backend.app.engines.vietnam import valuate_vn_stock
    from backend.app.services.vietnam import parse_vn_financials_from_dict
"""

from .vn_stock_database import (
    VNStockDatabase,
    VNStock,
    VNSector,
    VNExchange,
    get_vn_stock_database,
    vn_stock_db
)

from .vnd_financial_parser import (
    VNDFinancialParser,
    ParsedVNFinancials,
    VNFinancialItem,
    VNStatementType,
    VNAccountCode,
    parse_vn_financials_from_dict,
    convert_vnd_to_usd,
    get_vas_account_mapping
)

__all__ = [
    # Database
    'VNStockDatabase',
    'VNStock',
    'VNSector',
    'VNExchange',
    'get_vn_stock_database',
    'vn_stock_db',
    
    # Financial Parser
    'VNDFinancialParser',
    'ParsedVNFinancials',
    'VNFinancialItem',
    'VNStatementType',
    'VNAccountCode',
    'parse_vn_financials_from_dict',
    'convert_vnd_to_usd',
    'get_vas_account_mapping',
]

# Version info
__version__ = '1.0.0'
__author__ = 'Vietnamese Market Team'

# Quick start guide
QUICK_START = """
Vietnamese Stock Analysis Package
==================================

1. Get stock database:
   db = get_vn_stock_database()
   stock = db.get_stock('VNM')
   all_banks = db.get_by_sector(VNSector.BANKING)

2. Parse Vietnamese financials:
   parsed = parse_vn_financials_from_dict(vn_data)
   standard_dict = parsed.to_standard_dict()

3. Sector-specific valuation:
   result = valuate_vn_stock(
       ticker='VCB',
       company_name='Vietcombank',
       sector='Banking',
       inputs={...},
       current_price_vnd=85000
   )

Supported Sectors:
- Banking (DDM + Residual Income + P/BV)
- Real Estate (NAV + RNAV)
- Manufacturing (Commodity-Adjusted DCF)

For more information, see individual module docstrings.
"""
