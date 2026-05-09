"""
YFinance Service - Step 5A: API Fetch (Primary Source)

Fetches ALL available raw data from yfinance free tier:
    - Income Statement: Revenue, COGS, EBITDA, EBIT, Net Income, Interest Expense*, D&A
        *Note: Interest Expense often missing for recent periods in yfinance
    - Balance Sheet: Debt, Cash, Equity, Working Capital, Shares, AR, Inventory, AP
    - Cash Flow: FCF, Operating CF, Capex, Dividends
    - Key Stats: Market Cap, Enterprise Value
        *Note: Beta and Risk-Free Rate NOT available via yfinance API - must be calculated/fetched elsewhere
    - Analyst Estimates: Revenue estimates, earnings estimates, target prices, recommendations

DATA LIMITATIONS (CANNOT be fetched from yfinance):
    - Equity Risk Premium (ERP) - Macro input, requires external source or AI estimation
    - Country Risk Premium - Macro input, requires external source or AI estimation  
    - Terminal EBITDA Multiples - Forward-looking, requires AI estimation or analyst comps
    - Risk-Free Rate - Not provided by yfinance, requires treasury yield API or manual input
    - Forward-looking Beta - Must be calculated from historical prices or use default
    - Segment Data - Not available in yfinance free tier
    - Management Guidance - Not available, requires SEC filings or company reports

ENHANCED WITH ALPHAVANTAGE FALLBACK:
    This service now integrates with AlphaVantageService for:
    - Fallback when yfinance fails to fetch data
    - Enhanced coverage for international stocks
    - Cross-validation of critical financial metrics
    - Additional analyst ratings data
    
    Cascade: yfinance (primary) -> AlphaVantage (fallback) -> Error

VIETNAM MARKET ENHANCEMENT:
    For Vietnamese stocks, this service now integrates with VietnamDataAggregator
    which provides cascading fallback: vnstock (primary) -> yfinance (fallback).
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class YFinanceService:
    """Service for fetching financial data from yfinance with AlphaVantage fallback."""
    
    def __init__(self, enable_alphavantage_fallback: bool = True):
        self.ticker = None
        self.info = None
        self.financials = None
        self.balance_sheet = None
        self.cashflow = None
        self.estimates = None
        self.enable_alphavantage_fallback = enable_alphavantage_fallback
        self.alphavantage_service = None
    
    def fetch_key_stats(self, ticker_symbol: str) -> Dict[str, Any]:
        """
        Fetch key statistics for a single ticker.
        
        Args:
            ticker_symbol: Stock ticker symbol
            
        Returns:
            Dictionary containing key stats (marketCap, beta, totalDebt, cash, effectiveTaxRate, costOfDebt)
        """
        import yfinance as yf
        
        try:
            logger.info(f"Fetching key stats for ticker='{ticker_symbol}'")
            yf_ticker = yf.Ticker(ticker_symbol)
            info = yf_ticker.info
            
            if not info:
                logger.warning(f"No info returned for {ticker_symbol}")
                return {
                    'marketCap': None,
                    'beta': None,
                    'totalDebt': None,
                    'cash': None,
                    'effectiveTaxRate': None,
                    'costOfDebt': None,
                }
            
            # Helper to sanitize values
            def sanitize_value(val):
                if val is None:
                    return None
                if isinstance(val, float) and (val != val):  # NaN check
                    return None
                return val
            
            # Try to get financials for tax rate and cost of debt calculation
            effective_tax_rate = None
            cost_of_debt = None
            try:
                income_stmt = yf_ticker.financials
                balance_sheet = yf_ticker.balance_sheet
                if income_stmt is not None and not income_stmt.empty:
                    # Get the most recent column
                    latest_col = income_stmt.columns[0]
                    
                    # Calculate effective tax rate
                    tax_provision = income_stmt.loc['Tax Provision', latest_col] if 'Tax Provision' in income_stmt.index else None
                    pretax_income = income_stmt.loc['Pretax Income', latest_col] if 'Pretax Income' in income_stmt.index else None
                    
                    if tax_provision and pretax_income and pretax_income != 0:
                        effective_tax_rate = abs(tax_provision / pretax_income)
                    
                    # Calculate cost of debt (Interest Expense / Total Debt)
                    interest_expense = None
                    total_debt = None
                    
                    # Try to get interest expense from income statement
                    for interest_key in ['Interest Expense', 'Interest Expense Non Operating', 'Net Interest Income']:
                        if interest_key in income_stmt.index:
                            interest_expense = abs(income_stmt.loc[interest_key, latest_col])
                            break
                    
                    # Try to get total debt from balance sheet
                    if balance_sheet is not None and not balance_sheet.empty:
                        bs_latest_col = balance_sheet.columns[0]
                        for debt_key in ['Total Debt', 'Long Term Debt', 'Short Long Term Debt', 'Long-Term Debt', 'Short/Current Long Term Debt']:
                            if debt_key in balance_sheet.index:
                                total_debt = balance_sheet.loc[debt_key, bs_latest_col]
                                break
                        
                        # If total debt not found directly, try to sum long-term and short-term
                        if total_debt is None:
                            long_term = balance_sheet.loc['Long Term Debt', bs_latest_col] if 'Long Term Debt' in balance_sheet.index else 0
                            short_term = balance_sheet.loc['Short/Current Long Term Debt', bs_latest_col] if 'Short/Current Long Term Debt' in balance_sheet.index else 0
                            total_debt = long_term + short_term
                    
                    # Calculate cost of debt if both values available
                    if interest_expense and total_debt and total_debt != 0:
                        cost_of_debt = interest_expense / total_debt
                        logger.debug(f"Calculated cost of debt for {ticker_symbol}: {cost_of_debt:.4f}")
                        
            except Exception as e:
                logger.debug(f"Could not calculate tax rate or cost of debt for {ticker_symbol}: {e}")
            
            return {
                'marketCap': sanitize_value(info.get('marketCap')),
                'beta': sanitize_value(info.get('beta', 1.0)),
                'totalDebt': sanitize_value(info.get('totalDebt') or info.get('TotalDebt')),
                'cash': sanitize_value(info.get('cash') or info.get('CashAndCashEquivalents') or info.get('TotalCash')),
                'effectiveTaxRate': effective_tax_rate,
                'costOfDebt': cost_of_debt,
            }
            
        except Exception as e:
            logger.error(f"Error fetching key stats for '{ticker_symbol}': {str(e)}")
            return {
                'marketCap': None,
                'beta': None,
                'totalDebt': None,
                'cash': None,
                'effectiveTaxRate': None,
                'costOfDebt': None,
                'error': str(e)
            }
    
    def fetch_all_data(self, ticker_symbol: str, market: str = "international") -> Dict[str, Any]:
        """
        Fetch all available financial data from yfinance with AlphaVantage fallback.
        
        Data source cascade:
        1. yfinance (primary) - Most comprehensive free data
        2. AlphaVantage (fallback) - Better for some international stocks
        3. Vietnamese market: vnstock -> yfinance -> AlphaVantage
        
        For Vietnamese markets, uses VietnamDataAggregator with cascading fallback:
        vnstock (primary) -> yfinance (fallback).
        
        Args:
            ticker_symbol: Stock ticker symbol
            market: Market type (vietnamese or international)
            
        Returns:
            Comprehensive dictionary containing all fetched data
        """
        import yfinance as yf
        
        try:
            logger.info(f"Fetching all yfinance data for ticker='{ticker_symbol}', market='{market}'")
            
            # For Vietnamese market, use enhanced aggregator with vnstock integration
            if market == "vietnamese":
                return self._fetch_vietnamese_enhanced(ticker_symbol)
            
            # Try yfinance first (primary source)
            data_package = self._fetch_yfinance_primary(ticker_symbol, market, yf)
            
            if data_package and self._validate_data_quality(data_package):
                # Optionally enhance with AlphaVantage data
                if self.enable_alphavantage_fallback:
                    data_package = self._enhance_with_alphavantage(data_package, ticker_symbol, market)
                
                logger.info(f"Successfully fetched all data for ticker='{ticker_symbol}'")
                return data_package
            else:
                # yfinance returned poor quality data, try AlphaVantage
                if self.enable_alphavantage_fallback:
                    logger.warning(f"yfinance data quality low for {ticker_symbol}, trying AlphaVantage fallback")
                    av_data = self._fetch_alphavantage_fallback(ticker_symbol, market)
                    if av_data:
                        logger.info(f"Successfully fetched fallback data from AlphaVantage for {ticker_symbol}")
                        return av_data
                
                # Return whatever we have, even if incomplete
                return data_package
            
        except Exception as e:
            logger.error(f"Failed to fetch yfinance data for ticker='{ticker_symbol}': {str(e)}")
            # On complete failure, try AlphaVantage as emergency fallback
            if self.enable_alphavantage_fallback:
                logger.info(f"Attempting AlphaVantage emergency fallback for {ticker_symbol}")
                av_data = self._fetch_alphavantage_fallback(ticker_symbol, market)
                if av_data:
                    return av_data
            raise
    
    def _fetch_yfinance_primary(self, ticker_symbol: str, market: str, yf) -> Dict[str, Any]:
        """Fetch data from yfinance as primary source."""
        self.ticker = yf.Ticker(ticker_symbol)
        
        # Fetch all data categories
        self.info = self._fetch_key_stats()
        self.financials = self._fetch_income_statement()
        self.balance_sheet = self._fetch_balance_sheet()
        self.cashflow = self._fetch_cash_flow()
        self.estimates = self._fetch_analyst_estimates()
        
        # Compile comprehensive data package
        data_package = {
            "symbol": ticker_symbol,
            "fetch_timestamp": datetime.now().isoformat(),
            "market": market,
            "data_sources": ["yfinance"],
            "key_stats": self.info,
            "income_statement": self.financials,
            "balance_sheet": self.balance_sheet,
            "cash_flow": self.cashflow,
            "analyst_estimates": self.estimates,
        }
        
        return data_package
    
    def _validate_data_quality(self, data_package: Dict[str, Any]) -> bool:
        """
        Validate minimum data quality requirements.
        
        Returns True if data meets minimum thresholds, False otherwise.
        """
        # Check for critical fields
        key_stats = data_package.get('key_stats', {})
        income_stmt = data_package.get('income_statement', {})
        
        # Must have at least revenue data
        has_revenue = bool(income_stmt.get('total_revenue'))
        
        # Must have some key stats
        has_price = key_stats.get('current_price') is not None
        
        return has_revenue or has_price
    
    def _enhance_with_alphavantage(self, data_package: Dict[str, Any], ticker_symbol: str, market: str) -> Dict[str, Any]:
        """Enhance yfinance data with supplementary AlphaVantage data."""
        try:
            av_data = self._get_alphavantage_service().fetch_all_data(ticker_symbol, market)
            
            if not av_data:
                return data_package
            
            # Use merge function from AlphaVantageService
            merged = self._get_alphavantage_service().merge_with_yfinance(data_package, av_data)
            logger.info(f"Enhanced yfinance data with AlphaVantage for {ticker_symbol}")
            return merged
            
        except Exception as e:
            logger.warning(f"Failed to enhance with AlphaVantage: {e}")
            return data_package
    
    def _fetch_alphavantage_fallback(self, ticker_symbol: str, market: str) -> Optional[Dict[str, Any]]:
        """Fetch data from AlphaVantage as fallback when yfinance fails."""
        try:
            av_service = self._get_alphavantage_service()
            av_data = av_service.fetch_all_data(ticker_symbol, market)
            
            if av_data:
                av_data['data_sources'] = ['alphavantage']
                av_data['fallback_used'] = True
            
            return av_data
            
        except Exception as e:
            logger.error(f"AlphaVantage fallback failed: {e}")
            return None
    
    def _get_alphavantage_service(self):
        """Lazy initialization of AlphaVantage service."""
        if self.alphavantage_service is None:
            from .alphavantage_service import AlphaVantageService
            self.alphavantage_service = AlphaVantageService()
        return self.alphavantage_service
    
    def _fetch_vietnamese_enhanced(self, ticker_symbol: str) -> Dict[str, Any]:
        """
        Enhanced fetch for Vietnamese stocks using VietnamDataAggregator.
        
        Implements cascading fallback:
        1. vnstock (primary - local VAS-compliant data)
        2. yfinance (fallback - international format)
        
        Args:
            ticker_symbol: Vietnamese ticker (without suffix)
            
        Returns:
            Merged data package with quality scoring
        """
        try:
            from .vietnam_data_aggregator import VietnamDataAggregator
            
            logger.info(f"Using VietnamDataAggregator for {ticker_symbol}")
            
            aggregator = VietnamDataAggregator()
            result = aggregator.fetch_comprehensive_data(ticker_symbol, market="VN")
            
            if result['success']:
                # Extract merged data for compatibility with existing code
                merged = result.get('merged_data', {})
                
                # Map to standard yfinance_service structure
                data_package = {
                    "symbol": f"{ticker_symbol}.VN",
                    "fetch_timestamp": result['fetch_timestamp'],
                    "market": "vietnamese",
                    "data_sources_used": result['data_sources_used'],
                    "data_quality_score": result['data_quality_score'],
                    "warnings": result.get('warnings', []),
                    "key_stats": {
                        "company_name": merged.get('company_info', {}).get('company_name'),
                        "sector": merged.get('company_info', {}).get('sector'),
                        "industry": merged.get('company_info', {}).get('industry'),
                        "currency": "VND",
                        "current_price": merged.get('trading_data', {}).get('current_price'),
                        "market_cap": merged.get('ratios', {}).get('market_cap'),
                        "beta": merged.get('ratios', {}).get('beta', 1.0),
                        **merged.get('ratios', {})
                    },
                    "income_statement": merged.get('financials', {}).get('income_statement', {}),
                    "balance_sheet": merged.get('financials', {}).get('balance_sheet', {}),
                    "cash_flow": merged.get('financials', {}).get('cash_flow', {}),
                    "ownership": merged.get('ownership', {}),
                    "analyst_estimates": {},  # Not available for Vietnamese stocks typically
                }
                
                logger.info(f"Vietnamese data aggregated successfully. Quality: {result['data_quality_score']:.2f}, Sources: {result['data_sources_used']}")
                return data_package
            else:
                logger.warning(f"VietnamDataAggregator failed, falling back to direct yfinance: {result.get('warnings', [])}")
                # Fallback to direct yfinance
                return self._fetch_direct_yfinance(ticker_symbol)
                
        except ImportError as e:
            logger.warning(f"VietnamDataAggregator not available, using direct yfinance: {e}")
            return self._fetch_direct_yfinance(ticker_symbol)
        except Exception as e:
            logger.error(f"Error in Vietnamese enhanced fetch: {e}")
            return self._fetch_direct_yfinance(ticker_symbol)
    
    def _fetch_direct_yfinance(self, ticker_symbol: str) -> Dict[str, Any]:
        """Direct yfinance fetch for Vietnamese stocks (fallback method)."""
        import yfinance as yf
        
        # Append .VN suffix
        full_ticker = f"{ticker_symbol}.VN" if not ticker_symbol.endswith(".VN") else ticker_symbol
        self.ticker = yf.Ticker(full_ticker)
        
        info = self._fetch_key_stats()
        financials = self._fetch_income_statement()
        balance_sheet = self._fetch_balance_sheet()
        cashflow = self._fetch_cash_flow()
        estimates = self._fetch_analyst_estimates()
        
        return {
            "symbol": full_ticker,
            "fetch_timestamp": datetime.now().isoformat(),
            "market": "vietnamese",
            "data_sources_used": ["yfinance"],
            "data_quality_score": 0.5,  # Lower score for fallback
            "warnings": ["Using yfinance fallback - vnstock data not available"],
            "key_stats": info,
            "income_statement": financials,
            "balance_sheet": balance_sheet,
            "cash_flow": cashflow,
            "analyst_estimates": estimates,
        }
    
    def _fetch_key_stats(self) -> Dict[str, Any]:
        """Fetch key statistics and company info."""
        try:
            info = self.ticker.info
            
            def sanitize_value(val):
                if val is None:
                    return None
                if isinstance(val, float) and (val != val):  # NaN check
                    return None
                return val
            
            return {
                # Company Info
                "company_name": sanitize_value(info.get('longName')),
                "short_name": sanitize_value(info.get('shortName')),
                "sector": sanitize_value(info.get('sector')),
                "industry": sanitize_value(info.get('industry')),
                "currency": sanitize_value(info.get('currency', 'USD')),
                
                # Market Data
                "current_price": sanitize_value(info.get('currentPrice')),
                "previous_close": sanitize_value(info.get('previousClose')),
                "open": sanitize_value(info.get('open')),
                "day_low": sanitize_value(info.get('dayLow')),
                "day_high": sanitize_value(info.get('dayHigh')),
                "fifty_two_week_low": sanitize_value(info.get('fiftyTwoWeekLow')),
                "fifty_two_week_high": sanitize_value(info.get('fiftyTwoWeekHigh')),
                
                # Market Cap & Enterprise Value
                "market_cap": sanitize_value(info.get('marketCap')),
                "enterprise_value": sanitize_value(info.get('enterpriseValue')),
                
                # Risk Metrics
                "beta": sanitize_value(info.get('beta', 1.0)),
                "beta_3y": sanitize_value(info.get('threeYearBeta')),
                
                # Shares
                "shares_outstanding": sanitize_value(info.get('sharesOutstanding')),
                "float_shares": sanitize_value(info.get('floatShares')),
                "shares_short": sanitize_value(info.get('sharesShort')),
                
                # Valuation Ratios
                "pe_ratio": sanitize_value(info.get('trailingPE')),
                "forward_pe": sanitize_value(info.get('forwardPE')),
                "peg_ratio": sanitize_value(info.get('pegRatio')),
                "price_to_book": sanitize_value(info.get('priceToBook')),
                "price_to_sales": sanitize_value(info.get('priceToSalesTrailing12Months')),
                "ev_to_revenue": sanitize_value(info.get('enterpriseToRevenue')),
                "ev_to_ebitda": sanitize_value(info.get('enterpriseToEbitda')),
                
                # Dividend Info
                "dividend_rate": sanitize_value(info.get('dividendRate')),
                "dividend_yield": sanitize_value(info.get('dividendYield')),
                "payout_ratio": sanitize_value(info.get('payoutRatio')),
                
                # Profitability
                "profit_margin": sanitize_value(info.get('profitMargins')),
                "operating_margin": sanitize_value(info.get('operatingMargins')),
                "return_on_assets": sanitize_value(info.get('returnOnAssets')),
                "return_on_equity": sanitize_value(info.get('returnOnEquity')),
                
                # Financial Health
                "total_debt": sanitize_value(info.get('totalDebt')),
                "total_cash": sanitize_value(info.get('totalCash')),
                "debt_to_equity": sanitize_value(info.get('debtToEquity')),
                "current_ratio": sanitize_value(info.get('currentRatio')),
                "quick_ratio": sanitize_value(info.get('quickRatio')),
                
                # Raw info for fallback
                "raw_info": info
            }
        except Exception as e:
            logger.warning(f"Error fetching key stats: {str(e)}")
            return {}
    
    def _fetch_income_statement(self) -> Dict[str, Any]:
        """Fetch income statement data."""
        try:
            stmt = self.ticker.financials
            if stmt.empty:
                logger.warning("No income statement data available")
                return {}
            
            def get_series_raw(label: str, fallback_labels: List[str] = None) -> Dict[str, Optional[float]]:
                """Get series with fallback options for field name variations."""
                labels_to_try = [label] + (fallback_labels or [])
                for lbl in labels_to_try:
                    if lbl in stmt.index:
                        series = stmt.loc[lbl]
                        return {str(col): self._sanitize_value(val) for col, val in series.items()}
                logger.warning(f"Income statement field '{label}' not found, tried: {labels_to_try}")
                return {}
            
            return {
                # Top Line
                "total_revenue": get_series_raw('Total Revenue', ['Operating Revenue']),
                "revenue": get_series_raw('Total Revenue', ['Operating Revenue']),  # Alias
                
                # Cost of Goods Sold
                "cost_of_revenue": get_series_raw('Cost Of Revenue', ['Reconciled Cost Of Revenue']),
                "cogs": get_series_raw('Cost Of Revenue'),  # Alias
                
                # Gross Profit
                "gross_profit": get_series_raw('Gross Profit'),
                
                # Operating Expenses
                "operating_expense": get_series_raw('Operating Expense', ['Total Expenses']),
                "selling_general_administrative": get_series_raw('Selling General And Administration', ['Selling General And Administrative']),
                "research_development": get_series_raw('Research And Development', ['Research Development']),
                
                # Operating Income
                "operating_income": get_series_raw('Operating Income', ['Total Operating Income As Reported']),
                "ebit": get_series_raw('EBIT', ['Operating Income']),  # Alias
                
                # EBITDA
                "ebitda": get_series_raw('EBITDA', ['Normalized EBITDA']),
                
                # Non-Operating Items
                "interest_expense": get_series_raw('Interest Expense', ['Interest Expense Non Operating']),
                "interest_income": get_series_raw('Interest Income', ['Interest Income Non Operating']),
                "other_income_expense": get_series_raw('Other Income Expense', ['Other Income Expense Net', 'Other Non Operating Income Expenses']),
                
                # Pre-Tax Income
                "pretax_income": get_series_raw('Pretax Income'),
                
                # Tax
                "tax_provision": get_series_raw('Tax Provision'),
                "tax_expense": get_series_raw('Tax Provision'),  # Alias
                
                # Net Income
                "net_income": get_series_raw('Net Income Common Stockholders', ['Net Income', 'Diluted NI Availto Com Stockholders']),
                "net_income_continuing_ops": get_series_raw('Net Income From Continuing And Discontinued Operation', ['Net Income From Continuing Operation Net Minority Interest']),
                "diluted_eps": get_series_raw('Diluted EPS'),
                "basic_eps": get_series_raw('Basic EPS'),
                
                # Depreciation & Amortization (try income statement first, then cash flow)
                "depreciation_amortization": get_series_raw('Reconciled Depreciation', ['Depreciation Amortization Depletion', 'Depreciation And Amortization']),
                "d_and_a": get_series_raw('Reconciled Depreciation', ['Depreciation Amortization Depletion']),  # Alias
            }
        except Exception as e:
            logger.warning(f"Error fetching income statement: {str(e)}")
            return {}
    
    def _fetch_balance_sheet(self) -> Dict[str, Any]:
        """Fetch balance sheet data."""
        try:
            bs = self.ticker.balance_sheet
            if bs.empty:
                logger.warning("No balance sheet data available")
                return {}
            
            def get_series_raw(label: str, fallback_labels: List[str] = None) -> Dict[str, Optional[float]]:
                """Get series with fallback options for field name variations."""
                labels_to_try = [label] + (fallback_labels or [])
                for lbl in labels_to_try:
                    if lbl in bs.index:
                        series = bs.loc[lbl]
                        return {str(col): self._sanitize_value(val) for col, val in series.items()}
                logger.warning(f"Balance sheet field '{label}' not found, tried: {labels_to_try}")
                return {}
            
            return {
                # Assets
                "total_assets": get_series_raw('Total Assets'),
                "current_assets": get_series_raw('Current Assets'),
                "non_current_assets": get_series_raw('Total Non Current Assets'),
                
                # Current Assets Breakdown
                "cash_and_equivalents": get_series_raw('Cash Cash Equivalents And Short Term Investments'),
                "cash": get_series_raw('Cash Cash Equivalents And Short Term Investments'),  # Alias
                "accounts_receivable": get_series_raw('Accounts Receivable', ['Receivables', 'Gross Accounts Receivable']),
                "ar": get_series_raw('Accounts Receivable', ['Receivables']),  # Alias
                "inventory": get_series_raw('Inventory'),
                "other_current_assets": get_series_raw('Other Current Assets'),
                
                # Non-Current Assets
                "property_plant_equipment": get_series_raw('Net PPE'),
                "ppe_net": get_series_raw('Net PPE'),  # Alias
                "goodwill": get_series_raw('Goodwill'),
                "intangible_assets": get_series_raw('Other Intangible Assets', ['Intangible Assets']),
                "long_term_investments": get_series_raw('Investments And Advances', ['Long Term Equity Investment']),
                
                # Liabilities
                "total_liabilities": get_series_raw('Total Liabilities Net Minority Interest'),
                "current_liabilities": get_series_raw('Current Liabilities'),
                "non_current_liabilities": get_series_raw('Total Non Current Liabilities Net Minority Interest'),
                
                # Current Liabilities Breakdown
                "accounts_payable": get_series_raw('Accounts Payable', ['Payables And Accrued Expenses', 'Payables']),
                "ap": get_series_raw('Accounts Payable', ['Payables']),  # Alias
                "short_term_debt": get_series_raw('Current Debt'),
                "other_current_liabilities": get_series_raw('Other Current Liabilities'),
                
                # Non-Current Liabilities
                "long_term_debt": get_series_raw('Long Term Debt'),
                "deferred_tax_liabilities": get_series_raw('Non Current Deferred Taxes Liabilities', ['Non Current Deferred Liabilities']),
                "other_non_current_liabilities": get_series_raw('Other Non Current Liabilities'),
                
                # Total Debt
                "total_debt": get_series_raw('Total Debt'),
                "net_debt": None,  # Will be calculated
                
                # Equity
                "total_equity": get_series_raw('Total Equity Gross Minority Interest'),
                "stockholders_equity": get_series_raw('Stockholders Equity'),
                "retained_earnings": get_series_raw('Retained Earnings'),
                "common_stock": get_series_raw('Common Stock Equity'),
                
                # Working Capital (calculated)
                "working_capital": None,  # Will be calculated
                "shares_outstanding": get_series_raw('Ordinary Shares Number'),
            }
        except Exception as e:
            logger.warning(f"Error fetching balance sheet: {str(e)}")
            return {}
    
    def _fetch_cash_flow(self) -> Dict[str, Any]:
        """Fetch cash flow statement data."""
        try:
            cf = self.ticker.cashflow
            if cf.empty:
                logger.warning("No cash flow data available")
                return {}
            
            def get_series_raw(label: str, fallback_labels: List[str] = None) -> Dict[str, Optional[float]]:
                """Get series with fallback options for field name variations."""
                labels_to_try = [label] + (fallback_labels or [])
                for lbl in labels_to_try:
                    if lbl in cf.index:
                        series = cf.loc[lbl]
                        return {str(col): self._sanitize_value(val) for col, val in series.items()}
                logger.warning(f"Cash flow field '{label}' not found, tried: {labels_to_try}")
                return {}
            
            return {
                # Operating Activities
                "operating_cash_flow": get_series_raw('Operating Cash Flow'),
                "ocf": get_series_raw('Operating Cash Flow'),  # Alias
                "net_income_from_continuing_ops": get_series_raw('Net Income From Continuing Operations'),
                "depreciation_amortization": get_series_raw('Depreciation Amortization Depletion', ['Depreciation And Amortization']),
                "change_in_working_capital": get_series_raw('Change In Working Capital'),
                "change_in_ar": get_series_raw('Change In Receivables', ['Change In Account Receivable', 'Changes In Account Receivables']),
                "change_in_inventory": get_series_raw('Change In Inventory'),
                "change_in_ap": get_series_raw('Change In Payable', ['Change In Account Payable', 'Change In Payables And Accrued Expense']),
                
                # Investing Activities
                "investing_cash_flow": get_series_raw('Investing Cash Flow'),
                "capital_expenditure": get_series_raw('Capital Expenditure', ['Purchase Of PPE', 'Capital Expenditure Reported']),
                "capex": get_series_raw('Capital Expenditure', ['Purchase Of PPE']),  # Alias
                "acquisitions": get_series_raw('Purchase Of Business', ['Net Business Purchase And Sale']),
                "purchase_of_investments": get_series_raw('Purchase Of Investment'),
                "sale_of_investments": get_series_raw('Sale Of Investment'),
                "other_investing_activities": get_series_raw('Other Investing Activities'),
                
                # Financing Activities
                "financing_cash_flow": get_series_raw('Financing Cash Flow'),
                "dividends_paid": get_series_raw('Cash Dividends Paid'),
                "dividends": get_series_raw('Cash Dividends Paid'),  # Alias
                "repurchase_of_stock": get_series_raw('Common Stock Payments', ['Repurchase Of Capital Stock']),
                "issuance_of_stock": get_series_raw('Issuance Of Capital Stock'),
                "repayment_of_debt": get_series_raw('Repayment Of Debt'),
                "issuance_of_debt": get_series_raw('Issuance Of Debt'),
                "other_financing_activities": get_series_raw('Other Financing Activities'),
                
                # Free Cash Flow
                "free_cash_flow": get_series_raw('Free Cash Flow'),
                "fcf": get_series_raw('Free Cash Flow'),  # Alias
                
                # Net Change in Cash
                "end_cash_position": get_series_raw('End Cash Position'),
                "beginning_cash_position": get_series_raw('Beginning Cash Position'),
                "change_in_cash": get_series_raw('Change In Cash And Cash Equivalents'),
            }
        except Exception as e:
            logger.warning(f"Error fetching cash flow: {str(e)}")
            return {}
    
    def _fetch_analyst_estimates(self) -> Dict[str, Any]:
        """Fetch analyst estimates and recommendations."""
        try:
            estimates = {}
            
            # Revenue estimates
            try:
                rev_est = self.ticker.revenue_estimate
                if rev_est is not None and not rev_est.empty:
                    estimates['revenue_estimates'] = {
                        'avg': self._sanitize_value(rev_est.loc['avg', '0q'] if 'avg' in rev_est.index else None),
                        'low': self._sanitize_value(rev_est.loc['low', '0q'] if 'low' in rev_est.index else None),
                        'high': self._sanitize_value(rev_est.loc['high', '0q'] if 'high' in rev_est.index else None),
                        'year_ago': self._sanitize_value(rev_est.loc['yearAgo', '0q'] if 'yearAgo' in rev_est.index else None),
                        'num_analysts': int(rev_est.loc['numberOfAnalysts', '0q']) if 'numberOfAnalysts' in rev_est.index else None,
                        'growth': self._sanitize_value(rev_est.loc['growth', '0q'] if 'growth' in rev_est.index else None),
                    }
            except Exception:
                pass
            
            # Earnings estimates
            try:
                earn_est = self.ticker.earnings_estimate
                if earn_est is not None and not earn_est.empty:
                    estimates['earnings_estimates'] = {
                        'avg': self._sanitize_value(earn_est.loc['avg', '0q'] if 'avg' in earn_est.index else None),
                        'low': self._sanitize_value(earn_est.loc['low', '0q'] if 'low' in earn_est.index else None),
                        'high': self._sanitize_value(earn_est.loc['high', '0q'] if 'high' in earn_est.index else None),
                        'year_ago': self._sanitize_value(earn_est.loc['yearAgo', '0q'] if 'yearAgo' in earn_est.index else None),
                        'num_analysts': int(earn_est.loc['numberOfAnalysts', '0q']) if 'numberOfAnalysts' in earn_est.index else None,
                        'growth': self._sanitize_value(earn_est.loc['growth', '0q'] if 'growth' in earn_est.index else None),
                    }
            except Exception:
                pass
            
            # EPS trends
            try:
                eps_trend = self.ticker.eps_trend
                if eps_trend is not None and not eps_trend.empty:
                    estimates['eps_trend'] = eps_trend.to_dict()
            except Exception:
                pass
            
            # EPS revisions
            try:
                eps_revisions = self.ticker.eps_revisions
                if eps_revisions is not None and not eps_revisions.empty:
                    estimates['eps_revisions'] = eps_revisions.to_dict()
            except Exception:
                pass
            
            # Growth estimates
            try:
                growth_est = self.ticker.growth_estimates
                if growth_est is not None and not growth_est.empty:
                    estimates['growth_estimates'] = growth_est.to_dict()
            except Exception:
                pass
            
            # Recommendation trends
            try:
                rec_trend = self.ticker.recommendations
                if rec_trend is not None and not rec_trend.empty:
                    estimates['recommendation_trend'] = rec_trend.to_dict()
            except Exception:
                pass
            
            # Target price
            try:
                target_prices = self.ticker.analyst_price_targets
                if target_prices:
                    estimates['target_prices'] = {
                        'current': self._sanitize_value(target_prices.get('current')),
                        'mean': self._sanitize_value(target_prices.get('mean')),
                        'median': self._sanitize_value(target_prices.get('median')),
                        'low': self._sanitize_value(target_prices.get('low')),
                        'high': self._sanitize_value(target_prices.get('high')),
                    }
            except Exception:
                pass
            
            return estimates
        except Exception as e:
            logger.warning(f"Error fetching analyst estimates: {str(e)}")
            return {}
    
    def _sanitize_value(self, val):
        """Sanitize a value for JSON serialization."""
        if val is None:
            return None
        if isinstance(val, float):
            if val != val:  # NaN check
                return None
            if val == float('inf') or val == float('-inf'):
                return None
        return val


    def search_tickers(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for tickers by company name or symbol.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching ticker results
        """
        import yfinance as yf
        
        try:
            logger.info(f"Searching tickers for query='{query}'")
            results = yf.Search(query=query, max_results=10)
            
            # Convert to list of dicts
            ticker_list = []
            if hasattr(results, 'quotes'):
                for quote in results.quotes:
                    ticker_list.append({
                        'symbol': quote.get('symbol', ''),
                        'shortname': quote.get('shortname', ''),
                        'longname': quote.get('longname', ''),
                        'exchDisp': quote.get('exchDisp', ''),
                        'typeDisp': quote.get('typeDisp', ''),
                        'exchange': quote.get('exchange', ''),
                        'sector': quote.get('sector'),
                        'industry': quote.get('industry'),
                    })
            
            logger.info(f"Found {len(ticker_list)} tickers for query='{query}'")
            return ticker_list
            
        except Exception as e:
            logger.error(f"Error searching tickers: {str(e)}")
            return []
    
    def get_ticker_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get basic ticker information from yfinance.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with ticker info or None if not found
        """
        import yfinance as yf
        
        try:
            logger.info(f"Getting ticker info for '{ticker}'")
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.info
            
            if not info:
                return None
            
            return {
                'symbol': info.get('symbol', ticker),
                'shortName': info.get('shortName', ''),
                'longName': info.get('longName', ''),
                'currentPrice': info.get('currentPrice'),
                'previousClose': info.get('previousClose'),
                'open': info.get('open'),
                'dayLow': info.get('dayLow'),
                'dayHigh': info.get('dayHigh'),
                'regularMarketVolume': info.get('regularMarketVolume'),
                'marketCap': info.get('marketCap'),
                'beta': info.get('beta'),
                'trailingPE': info.get('trailingPE'),
                'forwardPE': info.get('forwardPE'),
                'dividendYield': info.get('dividendYield'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'exchange': info.get('exchange'),
                'currency': info.get('currency'),
            }
            
        except Exception as e:
            logger.error(f"Error getting ticker info for '{ticker}': {str(e)}")
            return None
    
    def get_financial_statements(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get financial statements (income, balance sheet, cash flow) for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with income_stmt, balance_sheet, cashflow DataFrames or None
        """
        import yfinance as yf
        
        try:
            logger.info(f"Getting financial statements for '{ticker}'")
            yf_ticker = yf.Ticker(ticker)
            
            # Use get_* methods for yfinance v1.3.0+ compatibility
            income_stmt = yf_ticker.get_income_stmt()
            balance_sheet = yf_ticker.get_balance_sheet()
            cashflow = yf_ticker.get_cash_flow()
            
            # Check if we have at least some data
            if (income_stmt is None or income_stmt.empty) and \
               (balance_sheet is None or balance_sheet.empty) and \
               (cashflow is None or cashflow.empty):
                logger.warning(f"No financial statements available for '{ticker}'")
                return None
            
            return {
                'income_stmt': income_stmt if income_stmt is not None and not income_stmt.empty else None,
                'balance_sheet': balance_sheet if balance_sheet is not None and not balance_sheet.empty else None,
                'cashflow': cashflow if cashflow is not None and not cashflow.empty else None,
            }
            
        except Exception as e:
            logger.error(f"Error getting financial statements for '{ticker}': {str(e)}")
            return None


def fetch_yfinance_data(ticker_symbol: str, market: str = "international") -> Dict[str, Any]:
    """
    Convenience function to fetch all yfinance data.
    
    Args:
        ticker_symbol: Stock ticker symbol
        market: Market type (vietnamese or international)
        
    Returns:
        Comprehensive dictionary containing all fetched data
    """
    service = YFinanceService()
    return service.fetch_all_data(ticker_symbol, market)
