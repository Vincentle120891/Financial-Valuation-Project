"""
YFinance Service - Step 5A: API Fetch

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

VIETNAM MARKET ENHANCEMENT:
    For Vietnamese stocks, this service now integrates with VietnamDataAggregator
    which provides cascading fallback: vnstock (primary) -> yfinance (fallback).
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class YFinanceService:
    """Service for fetching financial data from yfinance."""
    
    def __init__(self):
        self.ticker = None
        self.info = None
        self.financials = None
        self.balance_sheet = None
        self.cashflow = None
        self.estimates = None
    
    def fetch_all_data(self, ticker_symbol: str, market: str = "international") -> Dict[str, Any]:
        """
        Fetch all available financial data from yfinance.
        
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
            
            # Append .VN for Vietnamese stocks if not already present (legacy support)
            if market == "vietnamese" and not ticker_symbol.endswith(".VN"):
                ticker_symbol += ".VN"
            
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
                "key_stats": self.info,
                "income_statement": self.financials,
                "balance_sheet": self.balance_sheet,
                "cash_flow": self.cashflow,
                "analyst_estimates": self.estimates,
            }
            
            logger.info(f"Successfully fetched all data for ticker='{ticker_symbol}'")
            return data_package
            
        except Exception as e:
            logger.error(f"Failed to fetch yfinance data for ticker='{ticker_symbol}': {str(e)}")
            raise
    
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
            
            def get_series(label: str) -> Dict[str, Optional[float]]:
                if label in stmt.index:
                    series = stmt.loc[label]
                    return {str(year): self._sanitize_value(val) for year, val in series.items()}
                return {}
            
            def get_series_raw(label: str) -> Dict[str, Optional[float]]:
                """Get series with original column names (dates)."""
                if label in stmt.index:
                    series = stmt.loc[label]
                    return {str(col): self._sanitize_value(val) for col, val in series.items()}
                return {}
            
            return {
                # Top Line
                "total_revenue": get_series_raw('Total Revenue'),
                "revenue": get_series_raw('Total Revenue'),  # Alias
                
                # Cost of Goods Sold
                "cost_of_revenue": get_series_raw('Cost Of Revenue'),
                "cogs": get_series_raw('Cost Of Revenue'),  # Alias
                
                # Gross Profit
                "gross_profit": get_series_raw('Gross Profit'),
                
                # Operating Expenses
                "operating_expense": get_series_raw('Operating Expense'),
                "selling_general_administrative": get_series_raw('Selling General And Administrative'),
                "research_development": get_series_raw('Research Development'),
                
                # Operating Income
                "operating_income": get_series_raw('Operating Income'),
                "ebit": get_series_raw('Ebit'),  # Alias
                
                # EBITDA
                "ebitda": get_series_raw('EBITDA'),
                
                # Non-Operating Items
                "interest_expense": get_series_raw('Interest Expense'),
                "interest_income": get_series_raw('Interest Income'),
                "other_income_expense": get_series_raw('Other Income Expense Net'),
                
                # Pre-Tax Income
                "pretax_income": get_series_raw('Pretax Income'),
                
                # Tax
                "tax_provision": get_series_raw('Tax Provision'),
                "tax_expense": get_series_raw('Tax Provision'),  # Alias
                
                # Net Income
                "net_income": get_series_raw('Net Income Common Stockholders'),
                "net_income_continuing_ops": get_series_raw('Net Income Continuing Operations'),
                "diluted_eps": get_series_raw('Diluted EPS'),
                "basic_eps": get_series_raw('Basic EPS'),
                
                # Depreciation & Amortization
                "depreciation_amortization": get_series_raw('Depreciation Amortization Depletion'),
                "d_and_a": get_series_raw('Depreciation Amortization Depletion'),  # Alias
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
            
            def get_series_raw(label: str) -> Dict[str, Optional[float]]:
                if label in bs.index:
                    series = bs.loc[label]
                    return {str(col): self._sanitize_value(val) for col, val in series.items()}
                return {}
            
            return {
                # Assets
                "total_assets": get_series_raw('Total Assets'),
                "current_assets": get_series_raw('Current Assets'),
                "non_current_assets": get_series_raw('Non Current Assets'),
                
                # Current Assets Breakdown
                "cash_and_equivalents": get_series_raw('Cash Cash Equivalents And Short Term Investments'),
                "cash": get_series_raw('Cash Cash Equivalents And Short Term Investments'),  # Alias
                "accounts_receivable": get_series_raw('Receivables'),
                "ar": get_series_raw('Receivables'),  # Alias
                "inventory": get_series_raw('Inventory'),
                "other_current_assets": get_series_raw('Other Current Assets'),
                
                # Non-Current Assets
                "property_plant_equipment": get_series_raw('Net PPE'),
                "ppe_net": get_series_raw('Net PPE'),  # Alias
                "goodwill": get_series_raw('Goodwill'),
                "intangible_assets": get_series_raw('Intangible Assets'),
                "long_term_investments": get_series_raw('Investments And Advances'),
                
                # Liabilities
                "total_liabilities": get_series_raw('Total Liabilities Net Minority Interest'),
                "current_liabilities": get_series_raw('Current Liabilities'),
                "non_current_liabilities": get_series_raw('Non Current Liabilities'),
                
                # Current Liabilities Breakdown
                "accounts_payable": get_series_raw('Payables And Accrued Expenses'),
                "ap": get_series_raw('Payables And Accrued Expenses'),  # Alias
                "short_term_debt": get_series_raw('Current Debt'),
                "other_current_liabilities": get_series_raw('Other Current Liabilities'),
                
                # Non-Current Liabilities
                "long_term_debt": get_series_raw('Long Term Debt'),
                "deferred_tax_liabilities": get_series_raw('Tax Liabilities Net'),
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
            
            def get_series_raw(label: str) -> Dict[str, Optional[float]]:
                if label in cf.index:
                    series = cf.loc[label]
                    return {str(col): self._sanitize_value(val) for col, val in series.items()}
                return {}
            
            return {
                # Operating Activities
                "operating_cash_flow": get_series_raw('Operating Cash Flow'),
                "ocf": get_series_raw('Operating Cash Flow'),  # Alias
                "net_income_from_continuing_ops": get_series_raw('Net Income From Continuing Operations'),
                "depreciation_amortization": get_series_raw('Depreciation Amortization Depletion'),
                "change_in_working_capital": get_series_raw('Change In Working Capital'),
                "change_in_ar": get_series_raw('Change In Receivables'),
                "change_in_inventory": get_series_raw('Change In Inventory'),
                "change_in_ap": get_series_raw('Change In Payables And Accrued Expense'),
                
                # Investing Activities
                "investing_cash_flow": get_series_raw('Investing Cash Flow'),
                "capital_expenditure": get_series_raw('Capital Expenditure'),
                "capex": get_series_raw('Capital Expenditure'),  # Alias
                "acquisitions": get_series_raw('Acquisitions Net'),
                "purchase_of_investments": get_series_raw('Purchase Of Investment'),
                "sale_of_investments": get_series_raw('Sale Of Investment'),
                "other_investing_activities": get_series_raw('Other Investing Activities'),
                
                # Financing Activities
                "financing_cash_flow": get_series_raw('Financing Cash Flow'),
                "dividends_paid": get_series_raw('Cash Dividends Paid'),
                "dividends": get_series_raw('Cash Dividends Paid'),  # Alias
                "repurchase_of_stock": get_series_raw('Repurchase Of Capital Stock'),
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
