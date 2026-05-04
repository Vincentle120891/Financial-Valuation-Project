"""
International Financial Models Package

Contains Pydantic models for international markets (IFRS/US GAAP):
- Input validation schemas for DCF, Comps, and DuPont analysis
- Cash flow statement models
- Balance sheet and income statement models
"""

from app.models.international_inputs import (
    # DuPont Models
    DuPontRequest,
    DuPontComponents,
    
    # Comps Models
    CompsSelectionRequest,
    CompsValuationRequest,
    PeerMultiple,
    
    # Financial Statement Models
    InternationalBalanceSheet,
    InternationalIncomeStatement,
    InternationalCashFlowStatement,
    InternationalFinancialInputs,
)

# Note: Cash flow models are in InternationalCashFlowModel class
# from app.models.international_cashflow_model import (
#     InternationalCashFlowModel,
# )

__all__ = [
    # DuPont
    "DuPontRequest",
    "DuPontComponents",
    
    # Comps
    "CompsSelectionRequest",
    "CompsValuationRequest",
    "PeerMultiple",
    
    # Financial Statements
    "InternationalBalanceSheet",
    "InternationalIncomeStatement",
    "InternationalCashFlowStatement",
    "InternationalFinancialInputs",
]
