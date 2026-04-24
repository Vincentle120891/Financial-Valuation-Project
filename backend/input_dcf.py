"""
DCF Input Configuration Module
Retrieves 3 nearest historical fiscal years data + base period balances for DCF modeling.
Dynamic year mapping: FY-3, FY-2, FY-1 resolve to the 3 most recently completed fiscal years.
"""

from datetime import datetime, date
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
import yfinance as yf
import pandas as pd


@dataclass
class HistoricalFinancialYear:
    """Single fiscal year historical financials."""
    revenue: Optional[float] = None
    cogs: Optional[float] = None
    gross_profit: Optional[float] = None
    sga: Optional[float] = None
    other_opex: Optional[float] = None
    ebitda: Optional[float] = None
    depreciation: Optional[float] = None
    ebit: Optional[float] = None
    interest_expense: Optional[float] = None
    ebt: Optional[float] = None
    current_tax: Optional[float] = None
    deferred_tax: Optional[float] = None
    total_tax: Optional[float] = None
    net_income: Optional[float] = None
    accounts_receivable: Optional[float] = None
    inventory: Optional[float] = None
    accounts_payable: Optional[float] = None
    net_working_capital: Optional[float] = None
    capital_expenditure: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BasePeriodBalances:
    """Base period (FY-1 end) balance sheet and market data for DCF."""
    net_debt: Optional[float] = None
    ppe_net: Optional[float] = None
    tax_basis_pp_e: Optional[float] = None
    tax_losses_nol_carryforward: Optional[float] = None
    shares_outstanding_diluted: Optional[float] = None
    current_stock_price: Optional[float] = None
    projected_interest_expense_annual: Optional[float] = None
    plant_capacity_units_per_day: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DCFInputConfiguration:
    """
    Complete DCF input configuration with 3-year historicals and base period balances.
    
    Historical years dynamically map to the 3 most recently completed fiscal years
    relative to valuation_date.
    """
    _metadata: Dict[str, Any] = field(default_factory=dict)
    historical_financials_3y: Dict[str, HistoricalFinancialYear] = field(default_factory=dict)
    base_period_balances_fy_minus_1: BasePeriodBalances = field(default_factory=BasePeriodBalances)

    def __post_init__(self):
        if not self._metadata:
            self._metadata = {
                "valuation_date": date.today().isoformat(),
                "currency": "USD",
                "historical_years_instruction": "FY-3, FY-2, FY-1 dynamically map to the 3 most recently completed fiscal years relative to valuation_date",
                "forecast_years_instruction": "Arrays contain 6 values: [FY+1, FY+2, FY+3, FY+4, FY+5, Terminal]"
            }
        # Initialize historical years structure
        if not self.historical_financials_3y:
            self.historical_financials_3y = {
                "fy_minus_3": HistoricalFinancialYear(),
                "fy_minus_2": HistoricalFinancialYear(),
                "fy_minus_1": HistoricalFinancialYear()
            }

    @classmethod
    def from_ticker(cls, ticker: str, valuation_date: Optional[date] = None) -> "DCFInputConfiguration":
        """
        Fetch DCF inputs from yfinance for a given ticker.
        
        Args:
            ticker: Stock ticker symbol
            valuation_date: Valuation date (defaults to today)
            
        Returns:
            DCFInputConfiguration with populated historical data
        """
        if valuation_date is None:
            valuation_date = date.today()
            
        instance = cls()
        instance._metadata["valuation_date"] = valuation_date.isoformat()
        
        # Fetch ticker data
        stock = yf.Ticker(ticker)
        
        # Get financial statements
        income_stmt = stock.financials
        balance_sheet = stock.balance_sheet
        cash_flow = stock.cashflow
        
        if income_stmt.empty or balance_sheet.empty or cash_flow.empty:
            raise ValueError(f"No financial data available for {ticker}")
        
        # Determine fiscal year end and map to FY-1, FY-2, FY-3
        # Get the column dates (yfinance returns columns as dates)
        income_dates = income_stmt.columns.tolist()
        balance_dates = balance_sheet.columns.tolist()
        cashflow_dates = cash_flow.columns.tolist()
        
        # Filter to only past dates relative to valuation_date
        past_income_dates = [d for d in income_dates if d.date() < valuation_date]
        past_balance_dates = [d for d in balance_dates if d.date() < valuation_date]
        past_cashflow_dates = [d for d in cashflow_dates if d.date() < valuation_date]
        
        if len(past_income_dates) < 3:
            raise ValueError(f"Insufficient historical data for {ticker}. Need at least 3 completed fiscal years.")
        
        # Sort dates descending (most recent first)
        past_income_dates.sort(reverse=True)
        past_balance_dates.sort(reverse=True)
        past_cashflow_dates.sort(reverse=True)
        
        # Map to FY-1 (most recent), FY-2, FY-3
        fy_dates = {
            "fy_minus_1": past_income_dates[0],
            "fy_minus_2": past_income_dates[1],
            "fy_minus_3": past_income_dates[2]
        }
        
        # Populate historical financials for each year
        for fy_key, fy_date in fy_dates.items():
            hist_year = HistoricalFinancialYear()
            
            # Income Statement
            try:
                col = fy_date
                if col in income_stmt.columns:
                    row = income_stmt[col]
                    
                    # Revenue
                    rev_keys = ["Total Revenue", "Net Income", "Operating Revenue"]
                    for key in rev_keys:
                        if key in row:
                            hist_year.revenue = float(row[key]) if pd.notna(row[key]) else None
                            break
                    
                    # COGS
                    cogs_keys = ["Cost Of Revenue", "Cost of Goods Sold", "COGS"]
                    for key in cogs_keys:
                        if key in row:
                            hist_year.cogs = float(row[key]) if pd.notna(row[key]) else None
                            break
                    
                    # Gross Profit
                    gp_keys = ["Gross Profit"]
                    for key in gp_keys:
                        if key in row:
                            hist_year.gross_profit = float(row[key]) if pd.notna(row[key]) else None
                            break
                    
                    # SG&A
                    sga_keys = ["Selling General Administrative", "SGA", "Selling & Marketing Expense"]
                    for key in sga_keys:
                        if key in row:
                            hist_year.sga = float(row[key]) if pd.notna(row[key]) else None
                            break
                    
                    # Other OpEx
                    other_opex_keys = ["Other Operating Expenses", "Other Income Expense"]
                    for key in other_opex_keys:
                        if key in row:
                            val = float(row[key]) if pd.notna(row[key]) else 0
                            hist_year.other_opex = abs(val) if val < 0 else val
                            break
                    
                    # EBITDA
                    ebitda_keys = ["EBITDA", "Ebitda"]
                    for key in ebitda_keys:
                        if key in row:
                            hist_year.ebitda = float(row[key]) if pd.notna(row[key]) else None
                            break
                    
                    # Depreciation
                    dep_keys = ["Depreciation Amortization Depletion", "Depreciation", "D&A"]
                    for key in dep_keys:
                        if key in row:
                            hist_year.depreciation = float(row[key]) if pd.notna(row[key]) else None
                            break
                    
                    # EBIT / Operating Income
                    ebit_keys = ["Operating Income", "EBIT", "Operating Income Loss"]
                    for key in ebit_keys:
                        if key in row:
                            hist_year.ebit = float(row[key]) if pd.notna(row[key]) else None
                            break
                    
                    # Interest Expense
                    int_keys = ["Interest Expense", "Net Interest Income"]
                    for key in int_keys:
                        if key in row:
                            val = float(row[key]) if pd.notna(row[key]) else None
                            hist_year.interest_expense = abs(val) if val and val < 0 else val
                            break
                    
                    # EBT (Pre-Tax Income)
                    ebt_keys = ["Pretax Income", "Pre-Tax Income", "Income Before Tax"]
                    for key in ebt_keys:
                        if key in row:
                            hist_year.ebt = float(row[key]) if pd.notna(row[key]) else None
                            break
                    
                    # Tax Provision
                    tax_keys = ["Tax Provision", "Income Tax Expense", "Provision For Income Taxes"]
                    for key in tax_keys:
                        if key in row:
                            hist_year.total_tax = float(row[key]) if pd.notna(row[key]) else None
                            break
                    
                    # Net Income
                    ni_keys = ["Net Income Common Stockholders", "Net Income", "Net Income Continuous Operations"]
                    for key in ni_keys:
                        if key in row:
                            hist_year.net_income = float(row[key]) if pd.notna(row[key]) else None
                            break
                            
            except Exception as e:
                print(f"Warning: Error parsing income statement for {fy_key}: {e}")
            
            # Balance Sheet
            try:
                col = fy_date
                # Find closest balance sheet date
                bs_col = min(past_balance_dates, key=lambda x: abs((x - col).days)) if past_balance_dates else col
                
                if bs_col in balance_sheet.columns:
                    row = balance_sheet[bs_col]
                    
                    # Accounts Receivable
                    ar_keys = ["Accounts Receivable", "Receivables", "Net Pledges Receivable"]
                    for key in ar_keys:
                        if key in row:
                            hist_year.accounts_receivable = float(row[key]) if pd.notna(row[key]) else None
                            break
                    
                    # Inventory
                    inv_keys = ["Inventory", "Inventories", "Raw Materials & Work In Process"]
                    for key in inv_keys:
                        if key in row:
                            hist_year.inventory = float(row[key]) if pd.notna(row[key]) else None
                            break
                    
                    # Accounts Payable
                    ap_keys = ["Accounts Payable", "Payables And Accrued Income", "Accounts Payable Trade"]
                    for key in ap_keys:
                        if key in row:
                            hist_year.accounts_payable = float(row[key]) if pd.notna(row[key]) else None
                            break
                            
            except Exception as e:
                print(f"Warning: Error parsing balance sheet for {fy_key}: {e}")
            
            # Cash Flow - CapEx
            try:
                col = fy_date
                cf_col = min(past_cashflow_dates, key=lambda x: abs((x - col).days)) if past_cashflow_dates else col
                
                if cf_col in cash_flow.columns:
                    row = cash_flow[cf_col]
                    
                    # Capital Expenditure
                    capex_keys = ["Capital Expenditure", "Capex", "Purchase Of Property Plant Equipment"]
                    for key in capex_keys:
                        if key in row:
                            val = float(row[key]) if pd.notna(row[key]) else None
                            hist_year.capital_expenditure = abs(val) if val and val < 0 else val
                            break
                            
            except Exception as e:
                print(f"Warning: Error parsing cash flow for {fy_key}: {e}")
            
            # Calculate derived fields if possible
            if hist_year.revenue and hist_year.cogs and hist_year.gross_profit is None:
                hist_year.gross_profit = hist_year.revenue - hist_year.cogs
            
            if hist_year.accounts_receivable and hist_year.inventory and hist_year.accounts_payable:
                hist_year.net_working_capital = (
                    hist_year.accounts_receivable + 
                    hist_year.inventory - 
                    hist_year.accounts_payable
                )
            
            instance.historical_financials_3y[fy_key] = hist_year
        
        # Populate base period balances (FY-1 end)
        fy1_date = fy_dates["fy_minus_1"]
        bs_col = min(past_balance_dates, key=lambda x: abs((x - fy1_date).days)) if past_balance_dates else fy1_date
        
        try:
            if bs_col in balance_sheet.columns:
                row = balance_sheet[bs_col]
                
                # Net Debt = Total Debt - Cash
                debt_keys = ["Total Debt", "Long Term Debt", "Short Term Debt"]
                total_debt = 0
                for key in debt_keys:
                    if key in row and pd.notna(row[key]):
                        total_debt += abs(float(row[key]))
                
                cash_keys = ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments", "Cash"]
                cash = 0
                for key in cash_keys:
                    if key in row and pd.notna(row[key]):
                        cash += float(row[key])
                
                instance.base_period_balances_fy_minus_1.net_debt = total_debt - cash if total_debt > 0 else None
                
                # PPE Net
                ppe_keys = ["Net PPE", "Property Plant Equipment Net", "Fixed Assets Net"]
                for key in ppe_keys:
                    if key in row and pd.notna(row[key]):
                        instance.base_period_balances_fy_minus_1.ppe_net = float(row[key])
                        break
                        
        except Exception as e:
            print(f"Warning: Error parsing base period balances: {e}")
        
        # Market data
        try:
            info = stock.info
            instance.base_period_balances_fy_minus_1.shares_outstanding_diluted = info.get("sharesOutstanding")
            instance.base_period_balances_fy_minus_1.current_stock_price = info.get("currentPrice") or info.get("regularMarketPrice")
        except Exception as e:
            print(f"Warning: Error fetching market data: {e}")
        
        return instance

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format matching the JSON schema."""
        return {
            "_metadata": self._metadata,
            "historical_financials_3y": {
                fy_key: fy.to_dict() 
                for fy_key, fy in self.historical_financials_3y.items()
            },
            "base_period_balances_fy_minus_1": self.base_period_balances_fy_minus_1.to_dict()
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.to_dict(), indent=indent)

    def save_to_file(self, filepath: str) -> None:
        """Save to JSON file."""
        import json
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


def fetch_dcf_inputs(ticker: str, valuation_date: Optional[date] = None) -> DCFInputConfiguration:
    """
    Convenience function to fetch DCF inputs for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        valuation_date: Valuation date (defaults to today)
        
    Returns:
        DCFInputConfiguration object
    """
    return DCFInputConfiguration.from_ticker(ticker, valuation_date)


if __name__ == "__main__":
    # Example usage
    ticker = "AAPL"
    print(f"Fetching DCF inputs for {ticker}...")
    
    try:
        dcf_inputs = fetch_dcf_inputs(ticker)
        print(dcf_inputs.to_json())
    except Exception as e:
        print(f"Error: {e}")
