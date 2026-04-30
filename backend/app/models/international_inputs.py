"""
International Financial Report Inputs Model
Standard IFRS/US GAAP format for non-Vietnamese markets
Used when market selection is 'international'
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


class InternationalBalanceSheet(BaseModel):
    """
    International Balance Sheet (IFRS/US GAAP format)
    Corresponds to Vietnamese B01-DN but with international terminology
    """
    
    # Assets - Current
    cash_and_cash_equivalents: Optional[float] = Field(None, description="Cash and cash equivalents")
    short_term_investments: Optional[float] = Field(None, description="Short-term investments/marketable securities")
    accounts_receivable: Optional[float] = Field(None, description="Trade and other receivables")
    inventory: Optional[float] = Field(None, description="Inventories")
    prepaid_expenses: Optional[float] = Field(None, description="Prepaid expenses and other current assets")
    other_current_assets: Optional[float] = Field(None, description="Other current assets")
    
    # Assets - Non-Current
    property_plant_equipment: Optional[float] = Field(None, description="Property, plant and equipment (net)")
    investment_property: Optional[float] = Field(None, description="Investment property (net)")
    intangible_assets: Optional[float] = Field(None, description="Intangible assets (net)")
    goodwill: Optional[float] = Field(None, description="Goodwill")
    long_term_investments: Optional[float] = Field(None, description="Long-term investments and associates")
    deferred_tax_assets: Optional[float] = Field(None, description="Deferred tax assets")
    other_non_current_assets: Optional[float] = Field(None, description="Other non-current assets")
    
    # Liabilities - Current
    accounts_payable: Optional[float] = Field(None, description="Trade and other payables")
    short_term_debt: Optional[float] = Field(None, description="Short-term borrowings")
    current_portion_long_term_debt: Optional[float] = Field(None, description="Current portion of long-term debt")
    accrued_expenses: Optional[float] = Field(None, description="Accrued expenses and other liabilities")
    deferred_revenue_current: Optional[float] = Field(None, description="Deferred revenue (current)")
    income_tax_payable: Optional[float] = Field(None, description="Income tax payable")
    other_current_liabilities: Optional[float] = Field(None, description="Other current liabilities")
    
    # Liabilities - Non-Current
    long_term_debt: Optional[float] = Field(None, description="Long-term borrowings")
    deferred_tax_liabilities: Optional[float] = Field(None, description="Deferred tax liabilities")
    deferred_revenue_non_current: Optional[float] = Field(None, description="Deferred revenue (non-current)")
    pension_obligations: Optional[float] = Field(None, description="Pension and post-employment benefits")
    provisions_non_current: Optional[float] = Field(None, description="Non-current provisions")
    other_non_current_liabilities: Optional[float] = Field(None, description="Other non-current liabilities")
    
    # Equity
    share_capital: Optional[float] = Field(None, description="Share capital/issued capital")
    share_premium: Optional[float] = Field(None, description="Share premium/additional paid-in capital")
    retained_earnings: Optional[float] = Field(None, description="Retained earnings")
    other_comprehensive_income: Optional[float] = Field(None, description="Other comprehensive income")
    treasury_shares: Optional[float] = Field(None, description="Treasury shares (negative value)")
    non_controlling_interest: Optional[float] = Field(None, description="Non-controlling interest")
    other_equity: Optional[float] = Field(None, description="Other equity reserves")


class InternationalIncomeStatement(BaseModel):
    """
    International Income Statement (IFRS/US GAAP format)
    Corresponds to Vietnamese B02-DN but with international terminology
    """
    
    # Revenue Section
    gross_revenue: Optional[float] = Field(None, description="Gross revenue/sales")
    sales_returns_allowances: Optional[float] = Field(None, description="Sales returns and allowances")
    revenue_deductions: Optional[float] = Field(None, description="Other revenue deductions")
    
    # Calculated: Net Revenue = Gross Revenue - Deductions
    net_revenue: Optional[float] = Field(None, description="Net revenue")
    
    # Cost of Sales
    cost_of_goods_sold: Optional[float] = Field(None, description="Cost of goods sold/cost of sales")
    
    # Calculated: Gross Profit = Net Revenue - COGS
    gross_profit: Optional[float] = Field(None, description="Gross profit")
    
    # Operating Expenses
    selling_expenses: Optional[float] = Field(None, description="Selling and distribution expenses")
    general_administrative_expenses: Optional[float] = Field(None, description="General and administrative expenses")
    research_development_expenses: Optional[float] = Field(None, description="Research and development expenses")
    depreciation_amortization: Optional[float] = Field(None, description="Depreciation and amortization expense")
    other_operating_expenses: Optional[float] = Field(None, description="Other operating expenses")
    
    # Other Income/Expenses
    investment_property_gain_loss: Optional[float] = Field(None, description="Gain/loss on investment property")
    financial_income: Optional[float] = Field(None, description="Finance income (interest, dividends, FX gains)")
    financial_expenses: Optional[float] = Field(None, description="Finance expenses (interest, FX losses)")
    interest_expense: Optional[float] = Field(None, description="Interest expense (subset of financial expenses)")
    share_of_profit_associates: Optional[float] = Field(None, description="Share of profit/loss of associates")
    other_income: Optional[float] = Field(None, description="Other income")
    other_expenses: Optional[float] = Field(None, description="Other expenses")
    
    # Calculated: Operating Profit
    operating_profit: Optional[float] = Field(None, description="Operating profit (EBIT)")
    
    # Calculated: Other Profit
    other_profit_loss: Optional[float] = Field(None, description="Other profit/loss")
    
    # Calculated: Profit Before Tax
    profit_before_tax: Optional[float] = Field(None, description="Profit before tax")
    
    # Tax
    current_tax_expense: Optional[float] = Field(None, description="Current tax expense")
    deferred_tax_expense: Optional[float] = Field(None, description="Deferred tax expense")
    
    # Calculated: Net Profit
    net_profit: Optional[float] = Field(None, description="Net profit for the period")
    
    # Per Share Data (for joint-stock companies)
    basic_eps: Optional[float] = Field(None, description="Basic earnings per share")
    diluted_eps: Optional[float] = Field(None, description="Diluted earnings per share")
    
    # Additional Metrics
    ebitda: Optional[float] = Field(None, description="EBITDA")
    weighted_average_shares_outstanding: Optional[float] = Field(None, description="Weighted average shares outstanding")


class InternationalCashFlowStatement(BaseModel):
    """
    International Cash Flow Statement (IAS 7 / US GAAP)
    Optional supplementary data
    """
    
    # Operating Activities
    cash_from_operating_activities: Optional[float] = Field(None, description="Net cash from operating activities")
    depreciation_amortization_cashflow: Optional[float] = Field(None, description="Depreciation and amortization (cashflow)")
    changes_working_capital: Optional[float] = Field(None, description="Changes in working capital")
    
    # Investing Activities
    cash_from_investing_activities: Optional[float] = Field(None, description="Net cash from investing activities")
    capital_expenditures: Optional[float] = Field(None, description="Capital expenditures (CAPEX)")
    acquisitions: Optional[float] = Field(None, description="Acquisitions, net of cash acquired")
    proceeds_asset_sales: Optional[float] = Field(None, description="Proceeds from sale of assets")
    investment_purchases: Optional[float] = Field(None, description="Purchase of investments")
    investment_sales: Optional[float] = Field(None, description="Sale of investments")
    
    # Financing Activities
    cash_from_financing_activities: Optional[float] = Field(None, description="Net cash from financing activities")
    proceeds_from_borrowings: Optional[float] = Field(None, description="Proceeds from borrowings")
    repayment_of_borrowings: Optional[float] = Field(None, description="Repayment of borrowings")
    dividends_paid: Optional[float] = Field(None, description="Dividends paid")
    proceeds_share_issue: Optional[float] = Field(None, description="Proceeds from share issues")
    share_buybacks: Optional[float] = Field(None, description="Share buybacks")
    
    # Net Change
    net_change_in_cash: Optional[float] = Field(None, description="Net change in cash and cash equivalents")
    cash_beginning_of_period: Optional[float] = Field(None, description="Cash at beginning of period")
    cash_end_of_period: Optional[float] = Field(None, description="Cash at end of period")


class InternationalFinancialInputs(BaseModel):
    """
    Complete International Financial Inputs Package
    Used for international market valuation models
    Currency: USD (or local currency converted to USD)
    """
    
    company_name: str = Field(..., description="Company name")
    ticker: str = Field(..., description="Stock ticker symbol")
    currency: str = Field("USD", description="Reporting currency (default USD)")
    fiscal_year_end: Optional[date] = Field(None, description="Fiscal year end date")
    reporting_period: Optional[str] = Field(None, description="Reporting period (e.g., 'FY2023', 'Q1 2024')")
    
    balance_sheet: Optional[InternationalBalanceSheet] = Field(None, description="Balance sheet data")
    income_statement: Optional[InternationalIncomeStatement] = Field(None, description="Income statement data")
    cash_flow_statement: Optional[InternationalCashFlowStatement] = Field(None, description="Cash flow statement data")
    
    # Market Data
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    shares_outstanding: Optional[float] = Field(None, description="Shares outstanding")
    current_stock_price: Optional[float] = Field(None, description="Current stock price")
    
    # Metadata
    data_source: Optional[str] = Field(None, description="Source of financial data")
    last_updated: Optional[date] = Field(None, description="Last update date")
    accounting_standard: str = Field("IFRS", description="Accounting standard (IFRS or US GAAP)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Apple Inc.",
                "ticker": "AAPL",
                "currency": "USD",
                "fiscal_year_end": "2023-09-30",
                "reporting_period": "FY2023",
                "accounting_standard": "US GAAP",
                "balance_sheet": {
                    "cash_and_cash_equivalents": 29965000000,
                    "accounts_receivable": 29508000000,
                    "inventory": 6331000000,
                    "property_plant_equipment": 43715000000,
                    "total_assets": 352755000000,
                    "accounts_payable": 62611000000,
                    "short_term_debt": 15807000000,
                    "long_term_debt": 95281000000,
                    "share_capital": 73812000000,
                    "retained_earnings": -214000000
                },
                "income_statement": {
                    "gross_revenue": 383285000000,
                    "net_revenue": 383285000000,
                    "cost_of_goods_sold": 214137000000,
                    "gross_profit": 169148000000,
                    "operating_expenses": 55013000000,
                    "operating_profit": 114301000000,
                    "net_profit": 96995000000,
                    "basic_eps": 6.16,
                    "diluted_eps": 6.13
                }
            }
        }


# Mapping helpers for converting Vietnamese TT99 to International format
class VN_to_International_Mapping:
    """
    Helper class to map Vietnamese TT99 fields to International format
    """
    
    BALANCE_SHEET_MAPPING = {
        # Current Assets
        "110": "cash_and_cash_equivalents",
        "120": "short_term_investments",
        "130": "accounts_receivable",
        "140": "inventory",
        "160": "other_current_assets",
        
        # Non-Current Assets
        "220": "property_plant_equipment",
        "240": "investment_property",
        "227": "intangible_assets",
        "260": "long_term_investments",
        "272": "deferred_tax_assets",
        
        # Current Liabilities
        "310": "accounts_payable",
        "321": "short_term_debt",
        "316": "accrued_expenses",
        "319": "deferred_revenue_current",
        "314": "income_tax_payable",
        
        # Non-Current Liabilities
        "339": "long_term_debt",
        "342": "deferred_tax_liabilities",
        "337": "deferred_revenue_non_current",
        "343": "provisions_non_current",
        
        # Equity
        "411": "share_capital",
        "412": "share_premium",
        "420": "retained_earnings",
        "416": "other_comprehensive_income",
        "415": "treasury_shares",
    }
    
    INCOME_STATEMENT_MAPPING = {
        "01": "gross_revenue",
        "02": "revenue_deductions",
        "10": "net_revenue",
        "11": "cost_of_goods_sold",
        "20": "gross_profit",
        "21": "investment_property_gain_loss",
        "22": "financial_income",
        "23": "financial_expenses",
        "24": "interest_expense",
        "25": "selling_expenses",
        "26": "general_administrative_expenses",
        "30": "operating_profit",
        "31": "other_income",
        "32": "other_expenses",
        "40": "other_profit_loss",
        "50": "profit_before_tax",
        "51": "current_tax_expense",
        "52": "deferred_tax_expense",
        "60": "net_profit",
        "70": "basic_eps",
        "71": "diluted_eps",
    }
    
    @classmethod
    def convert_vn_to_international(cls, vn_data: dict) -> InternationalFinancialInputs:
        """
        Convert Vietnamese TT99 format to International format
        """
        # Implementation would map Vietnamese field codes to international fields
        # This is a placeholder for the conversion logic
        pass
