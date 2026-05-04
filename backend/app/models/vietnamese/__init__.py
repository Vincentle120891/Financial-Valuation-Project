"""
Vietnamese Financial Models Package

Contains Pydantic models for Vietnamese market (TT99 accounting standards):
- Input validation schemas for DCF, Comps, and DuPont analysis
- Cash flow statement models compliant with Thông Tư 99/2025/TT-BTC
- Balance sheet and income statement models for HOSE/HNX/UPCOM
"""

from app.models.vietnamese_inputs import (
    # Enums
    VNExchange,
    VNSector,
    
    # DCF Models
    VietnameseDCFRequest,
    
    # Comps Models
    VNPeerMultiple,
    VietnameseCompsSelectionRequest,
    VietnameseCompsValuationRequest,
    
    # DuPont Models
    VNDuPontComponents,
    VietnameseDuPontRequest,
    
    # Financial Data
    VNFinancialData,
)

from app.models.vietnamese_inputs_tt99 import (
    VNBalanceSheet_B01_DN,
    VNIncomeStatement_B02_DN,
    VNFinancialInputs_TT99,
    TT99_Calculations,
)

# Note: Cash flow models are in VietnameseCashFlowModel class
# from app.models.vietnamese_cashflow_model import (
#     VietnameseCashFlowModel,
# )

__all__ = [
    # Enums
    "VNExchange",
    "VNSector",
    
    # DCF
    "VietnameseDCFRequest",
    
    # Comps
    "VNPeerMultiple",
    "VietnameseCompsSelectionRequest",
    "VietnameseCompsValuationRequest",
    
    # DuPont
    "VNDuPontComponents",
    "VietnameseDuPontRequest",
    
    # TT99 Financial Statements
    "VNBalanceSheet_B01_DN",
    "VNIncomeStatement_B02_DN",
    "VNFinancialInputs_TT99",
    "TT99_Calculations",
    
    # Financial Data
    "VNFinancialData",
]
