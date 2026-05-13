"""
Step 6 View Model Transformer - Flattened UI Response

This module transforms the complex UnifiedStep6Response into a simplified,
flat ViewModel that the frontend can directly consume without navigating
nested DataField wrappers.

Purpose:
- Decouple internal unified schema from UI presentation layer
- Provide raw values ready for direct binding in React components
- Strip away status flags, metadata, and nested complexity for Step 6 display
- Maintain stability: frontend won't break when internal schemas change
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.api.schemas.unified_step_schemas import (
    UnifiedStep6Response,
    HistoricalFinancialsData,
    ForecastDriversData,
    MarketDataBase,
    DuPontMetricsData,
    CompsMultiplesData,
    DataField as UnifiedDataField,
)

logger = logging.getLogger(__name__)


class Step6ViewModel:
    """
    Flattened View Model for Step 6 UI.
    
    This is a simple data class (not a Pydantic model) for maximum performance.
    All values are raw primitives (float, str, list) - no wrappers.
    """
    
    def __init__(self):
        # Company Info
        self.ticker: str = ""
        self.company_name: str = ""
        self.currency: str = "USD"
        self.fiscal_year_end: str = ""
        
        # Market Data (Flattened)
        self.current_stock_price: Optional[float] = None
        self.shares_outstanding: Optional[float] = None
        self.market_cap: Optional[float] = None
        self.enterprise_value: Optional[float] = None
        self.beta: Optional[float] = None
        self.risk_free_rate: Optional[float] = None
        self.market_risk_premium: Optional[float] = None
        
        # Historical Financials (Lists of values by period)
        self.periods: List[str] = []
        self.revenues: List[Optional[float]] = []
        self.ebitdas: List[Optional[float]] = []
        self.ebits: List[Optional[float]] = []
        self.net_incomes: List[Optional[float]] = []
        self.free_cash_flows: List[Optional[float]] = []
        self.operating_cash_flows: List[Optional[float]] = []
        
        # Balance Sheet Items
        self.total_assets: Optional[float] = None
        self.total_liabilities: Optional[float] = None
        self.total_equity: Optional[float] = None
        self.cash_and_equivalents: Optional[float] = None
        self.total_debt: Optional[float] = None
        
        # Working Capital
        self.accounts_receivable: Optional[float] = None
        self.inventory: Optional[float] = None
        self.accounts_payable: Optional[float] = None
        
        # Assumptions / Metrics
        self.tax_rate: Optional[float] = None
        self.cost_of_equity: Optional[float] = None
        self.cost_of_debt: Optional[float] = None
        self.wacc: Optional[float] = None
        self.terminal_growth_rate: Optional[float] = None
        
        # Peer Comparables (List of simple dicts)
        self.peer_comparables: List[Dict[str, Any]] = []
        
        # DuPont Metrics
        self.net_profit_margin: Optional[float] = None
        self.asset_turnover: Optional[float] = None
        self.equity_multiplier: Optional[float] = None
        self.return_on_equity: Optional[float] = None
        
        # Comps Multiples
        self.ev_to_ebitda: Optional[float] = None
        self.pe_ratio: Optional[float] = None
        self.pb_ratio: Optional[float] = None
        self.ev_to_sales: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "ticker": self.ticker,
            "companyName": self.company_name,
            "currency": self.currency,
            "fiscalYearEnd": self.fiscal_year_end,
            
            # Market Data
            "currentStockPrice": self.current_stock_price,
            "sharesOutstanding": self.shares_outstanding,
            "marketCap": self.market_cap,
            "enterpriseValue": self.enterprise_value,
            "beta": self.beta,
            "riskFreeRate": self.risk_free_rate,
            "marketRiskPremium": self.market_risk_premium,
            
            # Historical Financials
            "periods": self.periods,
            "revenues": self.revenues,
            "ebitdas": self.ebitdas,
            "ebits": self.ebits,
            "netIncomes": self.net_incomes,
            "freeCashFlows": self.free_cash_flows,
            "operatingCashFlows": self.operating_cash_flows,
            
            # Balance Sheet
            "totalAssets": self.total_assets,
            "totalLiabilities": self.total_liabilities,
            "totalEquity": self.total_equity,
            "cashAndEquivalents": self.cash_and_equivalents,
            "totalDebt": self.total_debt,
            
            # Working Capital
            "accountsReceivable": self.accounts_receivable,
            "inventory": self.inventory,
            "accountsPayable": self.accounts_payable,
            
            # Assumptions
            "taxRate": self.tax_rate,
            "costOfEquity": self.cost_of_equity,
            "costOfDebt": self.cost_of_debt,
            "wacc": self.wacc,
            "terminalGrowthRate": self.terminal_growth_rate,
            
            # Peer Comparables
            "peerComparables": self.peer_comparables,
            
            # DuPont
            "netProfitMargin": self.net_profit_margin,
            "assetTurnover": self.asset_turnover,
            "equityMultiplier": self.equity_multiplier,
            "returnOnEquity": self.return_on_equity,
            
            # Comps
            "evToEbitda": self.ev_to_ebitda,
            "peRatio": self.pe_ratio,
            "pbRatio": self.pb_ratio,
            "evToSales": self.ev_to_sales,
        }


class Step6ViewModelTransformer:
    """
    Transforms UnifiedStep6Response → Step6ViewModel
    
    This transformer:
    1. Extracts raw values from DataField wrappers
    2. Flattens nested structures into simple lists/dicts
    3. Converts period-based data into parallel arrays
    4. Handles missing data gracefully (None values)
    """
    
    @staticmethod
    def extract_value(data_field: Optional[UnifiedDataField]) -> Any:
        """Extract raw value from DataField wrapper"""
        if not data_field:
            return None
        if hasattr(data_field, 'value'):
            return data_field.value
        return None
    
    @staticmethod
    def extract_period_values(data_field: Optional[UnifiedDataField]) -> tuple[List[str], List[Optional[float]]]:
        """
        Extract period labels and values from DataField.
        Returns (periods, values) tuple for building parallel arrays.
        """
        if not data_field or not data_field.value:
            return [], []
        
        value = data_field.value
        
        # If it's already a list of period values
        if isinstance(value, list) and len(value) > 0:
            periods = []
            values = []
            for item in value:
                if isinstance(item, dict):
                    periods.append(item.get('period', 'Unknown'))
                    values.append(item.get('value'))
                elif hasattr(item, 'period') and hasattr(item, 'value'):
                    periods.append(getattr(item, 'period', 'Unknown'))
                    values.append(getattr(item, 'value', None))
                else:
                    # Fallback for simple values
                    periods.append(f'Period_{len(periods)+1}')
                    values.append(item)
            return periods, values
        
        # Single value case
        return ['Current'], [value]
    
    @classmethod
    def transform(cls, unified_response: UnifiedStep6Response) -> Step6ViewModel:
        """
        Main transformation method: UnifiedStep6Response → Step6ViewModel
        """
        logger.info(f"Transforming Step 6 response to ViewModel for {unified_response.ticker}")
        
        view_model = Step6ViewModel()
        
        # Basic Info
        view_model.ticker = unified_response.ticker
        view_model.currency = "USD"  # Default, could be extracted from market_data
        
        # Extract Market Data
        if unified_response.market_data:
            md = unified_response.market_data
            view_model.current_stock_price = cls.extract_value(md.current_stock_price)
            view_model.shares_outstanding = cls.extract_value(md.shares_outstanding)
            view_model.market_cap = cls.extract_value(md.market_cap)
            view_model.beta = cls.extract_value(md.beta)
            view_model.total_debt = cls.extract_value(md.total_debt)
            view_model.cash_and_equivalents = cls.extract_value(md.cash)
        
        # Extract Historical Financials
        if unified_response.historical_financials:
            hf = unified_response.historical_financials
            
            # Extract revenue periods/values as the reference
            periods, revenues = cls.extract_period_values(hf.revenue)
            view_model.periods = periods
            view_model.revenues = revenues
            
            # Extract other financials using same periods
            _, view_model.ebitdas = cls.extract_period_values(hf.ebitda)
            _, view_model.ebits = cls.extract_period_values(hf.ebit) if hasattr(hf, 'ebit') else ([], [])
            _, view_model.net_incomes = cls.extract_period_values(hf.net_income)
            _, view_model.free_cash_flows = cls.extract_period_values(hf.free_cash_flow)
            _, view_model.operating_cash_flows = cls.extract_period_values(hf.operating_cash_flow)
            
            # Balance Sheet (typically single values, not period-based)
            view_model.total_assets = cls.extract_value(hf.total_assets)
            view_model.total_debt = cls.extract_value(hf.total_debt) or view_model.total_debt
            view_model.cash_and_equivalents = cls.extract_value(hf.cash_and_equivalents) or view_model.cash_and_equivalents
            view_model.accounts_receivable = cls.extract_value(hf.accounts_receivable)
            view_model.inventory = cls.extract_value(hf.inventory)
            view_model.accounts_payable = cls.extract_value(hf.accounts_payable)
            view_model.total_equity = cls.extract_value(hf.shareholders_equity)
        
        # Extract Forecast Drivers / Assumptions
        if unified_response.forecast_drivers:
            fd = unified_response.forecast_drivers
            view_model.tax_rate = cls.extract_value(fd.tax_rate)
            view_model.wacc = cls.extract_value(fd.wacc)
            view_model.terminal_growth_rate = cls.extract_value(fd.terminal_growth_rate)
            view_model.risk_free_rate = cls.extract_value(fd.risk_free_rate)
            view_model.market_risk_premium = cls.extract_value(fd.equity_risk_premium)
            view_model.beta = cls.extract_value(fd.beta) or view_model.beta
            view_model.cost_of_debt = cls.extract_value(fd.cost_of_debt)
        
        # Extract DuPont Metrics
        if unified_response.dupont_metrics:
            dm = unified_response.dupont_metrics
            view_model.net_profit_margin = cls.extract_value(dm.net_profit_margin)
            view_model.asset_turnover = cls.extract_value(dm.asset_turnover)
            view_model.equity_multiplier = cls.extract_value(dm.equity_multiplier)
            view_model.return_on_equity = cls.extract_value(dm.return_on_equity)
        
        # Extract Comps Multiples
        if unified_response.comps_multiples:
            cm = unified_response.comps_multiples
            view_model.ev_to_ebitda = cls.extract_value(cm.ev_to_ebitda)
            view_model.pe_ratio = cls.extract_value(cm.p_to_e)
            view_model.pb_ratio = cls.extract_value(cm.p_to_b)
            view_model.ev_to_sales = cls.extract_value(cm.ev_to_sales)
        
        # Note: Peer comparables would need additional transformation logic
        # For now, leaving empty array - can be populated from session data
        
        return view_model
    
    @classmethod
    def transform_to_dict(cls, unified_response: UnifiedStep6Response) -> Dict[str, Any]:
        """
        Convenience method: Transform directly to dictionary for API response
        """
        view_model = cls.transform(unified_response)
        return view_model.to_dict()
