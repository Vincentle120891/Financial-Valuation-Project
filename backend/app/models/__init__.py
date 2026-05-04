"""
Financial Models Package

Unified package for financial models supporting both:
- International markets (IFRS/US GAAP)
- Vietnamese market (TT99 accounting standards)

Structure:
├── international/ - International market models
└── vietnamese/  - Vietnamese market models (TT99)
"""

# Re-export from subpackages for backward compatibility
from app.models.international import (
    DuPontRequest,
    DuPontComponents,
    CompsSelectionRequest,
    CompsValuationRequest,
    PeerMultiple,
    InternationalBalanceSheet,
    InternationalIncomeStatement,
    InternationalCashFlowStatement,
    InternationalFinancialInputs,
)

from app.models.vietnamese import (
    VNExchange,
    VNSector,
    VietnameseDCFRequest,
    VNPeerMultiple,
    VietnameseCompsSelectionRequest,
    VietnameseCompsValuationRequest,
    VNDuPontComponents,
    VietnameseDuPontRequest,
    VNFinancialData,
    VNBalanceSheet_B01_DN,
    VNIncomeStatement_B02_DN,
    VNFinancialInputs_TT99,
)

__all__ = [
    # International
    "DuPontRequest",
    "DuPontComponents",
    "CompsSelectionRequest",
    "CompsValuationRequest",
    "PeerMultiple",
    "InternationalBalanceSheet",
    "InternationalIncomeStatement",
    "InternationalCashFlowStatement",
    "InternationalFinancialInputs",
    
    # Vietnamese
    "VNExchange",
    "VNSector",
    "VietnameseDCFRequest",
    "VNPeerMultiple",
    "VietnameseCompsSelectionRequest",
    "VietnameseCompsValuationRequest",
    "VNDuPontComponents",
    "VietnameseDuPontRequest",
    "VNFinancialData",
    "VNBalanceSheet_B01_DN",
    "VNIncomeStatement_B02_DN",
    "VNFinancialInputs_TT99",
]
