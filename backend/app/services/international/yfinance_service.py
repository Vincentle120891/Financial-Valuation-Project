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

STRATEGY PATTERN IMPLEMENTATION:
    Implements Strategy pattern for market-specific data fetching:
    - DataStrategy Interface: Defines standard contract for fetching market data
    - InternationalDataStrategy: Standard yfinance + AlphaVantage for international markets
    - VietnamDataStrategy: Specialized for Vietnam using VietnamDataAggregator
"""

import logging
from typing import Dict, Any, Optional, List, Protocol
from datetime import datetime

logger = logging.getLogger(__name__)


# === Strategy Pattern Interface ===

class DataStrategy(Protocol):
    """Interface for market-specific data fetching strategies."""

    def fetch_data(self, ticker_symbol: str, yf) -> Dict[str, Any]:
        """Fetch data for a specific ticker using market-specific logic."""
        ...

    def get_market_type(self) -> str:
        """Return the market type this strategy handles."""
        ...


# === Concrete Strategies ===

class InternationalDataStrategy:
    """
    International Data Strategy - Standard yfinance + AlphaVantage fallback

    Handles all non-Vietnamese markets:
    - US, UK, EU, Japan, Australia, etc.
    - Primary: yfinance API
    - Fallback: AlphaVantage API
    - Quality validation before returning
    """

    def __init__(self, enable_alphavantage_fallback: bool = True):
        self.enable_alphavantage_fallback = enable_alphavantage_fallback
        self.alphavantage_service = None

    def fetch_data(self, ticker_symbol: str, yf) -> Dict[str, Any]:
        """
        Fetch data using yfinance primary + AlphaVantage fallback.

        Args:
            ticker_symbol: Stock ticker symbol
            yf: yfinance module

        Returns:
            Comprehensive dictionary containing all fetched data
        """
        logger.info(f"[InternationalStrategy] Fetching data for ticker='{ticker_symbol}'")

        # Try yfinance first (primary source)
        data_package = self._fetch_yfinance_primary(ticker_symbol, yf)

        if data_package and self._validate_data_quality(data_package):
            # Optionally enhance with AlphaVantage data
            if self.enable_alphavantage_fallback:
                data_package = self._enhance_with_alphavantage(data_package, ticker_symbol)

            logger.info(f"[InternationalStrategy] Successfully fetched data for ticker='{ticker_symbol}'")
            return data_package
        else:
            # yfinance returned poor quality data, try AlphaVantage
            if self.enable_alphavantage_fallback:
                logger.warning(f"[InternationalStrategy] yfinance data quality low for {ticker_symbol}, trying AlphaVantage fallback")
                av_data = self._fetch_alphavantage_fallback(ticker_symbol)
                if av_data:
                    logger.info(f"[InternationalStrategy] Successfully fetched fallback data from AlphaVantage for {ticker_symbol}")
                    return av_data

            # Return whatever we have, even if incomplete
            return data_package

    def get_market_type(self) -> str:
        """Return market type identifier."""
        return "international"

    def _fetch_yfinance_primary(self, ticker_symbol: str, yf) -> Dict[str, Any]:
        """Fetch data from yfinance as primary source."""
        ticker = yf.Ticker(ticker_symbol)

        # Fetch all data categories
        info = self._fetch_key_stats(ticker)
        financials = self._fetch_income_statement(ticker)
        balance_sheet = self._fetch_balance_sheet(ticker)
        cashflow = self._fetch_cash_flow(ticker)
        estimates = self._fetch_analyst_estimates(ticker)

        # Compile comprehensive data package
        data_package = {
            "symbol": ticker_symbol,
            "fetch_timestamp": datetime.now().isoformat(),
            "market": "international",
            "data_sources": ["yfinance"],
            "key_stats": info,
            "income_statement": financials,
            "balance_sheet": balance_sheet,
            "cash_flow": cashflow,
            "analyst_estimates": estimates,
        }

        return data_package

    def _validate_data_quality(self, data_package: Dict[str, Any]) -> bool:
        """Validate minimum data quality requirements."""
        key_stats = data_package.get('key_stats', {})
        income_stmt = data_package.get('income_statement', {})

        # Must have at least revenue data
        has_revenue = bool(income_stmt.get('total_revenue'))

        # Must have some key stats
        has_price = key_stats.get('current_price') is not None

        return has_revenue or has_price

    def _enhance_with_alphavantage(self, data_package: Dict[str, Any], ticker_symbol: str) -> Dict[str, Any]:
        """Enhance yfinance data with supplementary AlphaVantage data."""
        try:
            av_service = self._get_alphavantage_service()
            av_data = av_service.fetch_all_data(ticker_symbol, "international")

            if not av_data:
                return data_package

            # Use merge function from AlphaVantageService
            merged = av_service.merge_with_yfinance(data_package, av_data)
            logger.info(f"[InternationalStrategy] Enhanced yfinance data with AlphaVantage for {ticker_symbol}")
            return merged

        except Exception as e:
            logger.warning(f"[InternationalStrategy] Failed to enhance with AlphaVantage: {e}")
            return data_package

    def _fetch_alphavantage_fallback(self, ticker_symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch data from AlphaVantage as fallback when yfinance fails."""
        try:
            av_service = self._get_alphavantage_service()
            av_data = av_service.fetch_all_data(ticker_symbol, "international")

            if av_data:
                av_data['data_sources'] = ['alphavantage']
                av_data['fallback_used'] = True

            return av_data

        except Exception as e:
            logger.error(f"[InternationalStrategy] AlphaVantage fallback failed: {e}")
            return None

    def _get_alphavantage_service(self):
        """Lazy initialization of AlphaVantage service."""
        if self.alphavantage_service is None:
            from .alphavantage_service import AlphaVantageService
            self.alphavantage_service = AlphaVantageService()
        return self.alphavantage_service

    def _fetch_key_stats(self, ticker) -> Dict[str, Any]:
        """Fetch key statistics from yfinance ticker."""
        info = ticker.info

        if not info:
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
            # Use get_income_stmt() and get_balance_sheet() for yfinance v1.3.0+ compatibility
            income_stmt = ticker.get_income_stmt()
            balance_sheet = ticker.get_balance_sheet()
            if income_stmt is not None and not income_stmt.empty:
                latest_col = income_stmt.columns[0]

                # Calculate effective tax rate
                tax_provision = income_stmt.loc['Tax Provision', latest_col] if 'Tax Provision' in income_stmt.index else None
                pretax_income = income_stmt.loc['Pretax Income', latest_col] if 'Pretax Income' in income_stmt.index else None

                if tax_provision is not None and pretax_income is not None and pretax_income != 0:
                    # Handle negative pretax income (losses) - tax rate not meaningful
                    if pretax_income > 0:
                        effective_tax_rate = abs(tax_provision / pretax_income)
                        # Cap tax rate at reasonable bounds (0-50%)
                        if effective_tax_rate < 0:
                            effective_tax_rate = None
                        elif effective_tax_rate > 0.50:
                            logger.debug(f"Tax rate {effective_tax_rate:.2%} exceeds 50% cap for {ticker_symbol}, setting to None")
                            effective_tax_rate = None
                    # If pretax_income is negative, leave tax_rate as None

                # Calculate cost of debt
                interest_expense = None
                total_debt = None

                for interest_key in ['Interest Expense', 'Interest Expense Non Operating', 'Net Interest Income']:
                    if interest_key in income_stmt.index:
                        interest_expense = abs(income_stmt.loc[interest_key, latest_col])
                        break

                if balance_sheet is not None and not balance_sheet.empty:
                    bs_latest_col = balance_sheet.columns[0]
                    for debt_key in ['Total Debt', 'Long Term Debt', 'Short Long Term Debt', 'Long-Term Debt', 'Short/Current Long Term Debt']:
                        if debt_key in balance_sheet.index:
                            total_debt = balance_sheet.loc[debt_key, bs_latest_col]
                            break

                    if total_debt is None:
                        long_term = balance_sheet.loc['Long Term Debt', bs_latest_col] if 'Long Term Debt' in balance_sheet.index else 0
                        short_term = balance_sheet.loc['Short/Current Long Term Debt', bs_latest_col] if 'Short/Current Long Term Debt' in balance_sheet.index else 0
                        total_debt = long_term + short_term

                if interest_expense and total_debt and total_debt != 0:
                    cost_of_debt = interest_expense / total_debt
                    # Cap cost of debt at reasonable bounds (0-20%)
                    if cost_of_debt < 0 or cost_of_debt > 0.20:
                        logger.debug(f"Cost of debt {cost_of_debt:.2%} outside 0-20% bounds for {ticker_symbol}, setting to None")
                        cost_of_debt = None

        except Exception as e:
            logger.debug(f"Could not calculate tax rate or cost of debt: {e}")

        # DEBUG: Log all available keys in info for troubleshooting
        logger.debug(f"[YFinance] Available info keys for {ticker.ticker}: {list(info.keys())[:30]}...")
        logger.debug(f"[YFinance] currentPrice={info.get('currentPrice')}, totalCash={info.get('totalCash')}, marketCap={info.get('marketCap')}")

        return {
            'marketCap': sanitize_value(info.get('marketCap')),
            'beta': sanitize_value(info.get('beta', 1.0)),
            'totalDebt': sanitize_value(info.get('totalDebt') or info.get('TotalDebt')),
            'cash': sanitize_value(info.get('totalCash') or info.get('TotalCash') or info.get('cash') or info.get('CashAndCashEquivalents')),
            'currentPrice': sanitize_value(info.get('currentPrice') or info.get('regularMarketPrice')),
            'totalAssets': sanitize_value(info.get('totalAssets')),
            'totalEquity': sanitize_value(info.get('totalEquity') or info.get('StockholdersEquity') or info.get('TotalEquityGrossMinorityInterest')),
            'effectiveTaxRate': effective_tax_rate,
            'costOfDebt': cost_of_debt,
        }

    def _fetch_income_statement(self, ticker) -> Dict[str, Any]:
        """Fetch income statement data."""
        try:
            # Use get_income_stmt() for yfinance v1.3.0+ compatibility
            financials = ticker.get_income_stmt()
            if financials is None or financials.empty:
                return {}

            # Get column names (dates)
            columns = financials.columns.tolist()
            periods = [col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else str(col) for col in columns]
            num_periods = len(periods)

            # Map yfinance fields to standard format (with fallback field names - yfinance v1.3.0+ uses CamelCase without spaces)
            result = {
                'periods': periods,
                'total_revenue': self._get_series_values(financials, 'TotalRevenue', num_periods) or
                                 self._get_series_values(financials, 'OperatingRevenue', num_periods),
                'cost_of_revenue': self._get_series_values(financials, 'CostOfRevenue', num_periods) or
                                   self._get_series_values(financials, 'ReconciledCostOfRevenue', num_periods),
                'gross_profit': self._get_series_values(financials, 'GrossProfit', num_periods),
                'ebitda': self._get_series_values(financials, 'EBITDA', num_periods) or
                          self._get_series_values(financials, 'NormalizedEBITDA', num_periods),
                'ebit': self._get_series_values(financials, 'OperatingIncome', num_periods) or
                        self._get_series_values(financials, 'EBIT', num_periods),
                'net_income': self._get_series_values(financials, 'NetIncome', num_periods) or
                              self._get_series_values(financials, 'NetIncomeCommonStockholders', num_periods),
                'depreciation_amortization': self._get_series_values(financials, 'ReconciledDepreciation', num_periods),
            }

            return result
        except Exception as e:
            logger.error(f"Error fetching income statement: {e}")
            return {}

    def _fetch_balance_sheet(self, ticker) -> Dict[str, Any]:
        """Fetch balance sheet data."""
        try:
            # Use get_balance_sheet() for yfinance v1.3.0+ compatibility
            balance_sheet = ticker.get_balance_sheet()
            if balance_sheet is None or balance_sheet.empty:
                return {}

            columns = balance_sheet.columns.tolist()
            periods = [col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else str(col) for col in columns]
            num_periods = len(periods)

            # DEBUG: Log balance sheet keys for troubleshooting
            logger.debug(f"[YFinance] Balance sheet index: {balance_sheet.index.tolist()[:20]}...")

            result = {
                'periods': periods,
                'total_debt': self._get_series_values(balance_sheet, 'TotalDebt', num_periods),
                'cash_and_equivalents': self._get_series_values(balance_sheet, 'CashAndCashEquivalents', num_periods),
                'total_equity': self._get_series_values(balance_sheet, 'TotalEquityGrossMinorityInterest', num_periods) or
                                self._get_series_values(balance_sheet, 'StockholdersEquity', num_periods),
                'total_assets': self._get_series_values(balance_sheet, 'TotalAssets', num_periods),
                'working_capital': self._get_series_values(balance_sheet, 'WorkingCapital', num_periods),
                'shares_outstanding': self._get_series_values(balance_sheet, 'OrdinarySharesNumber', num_periods),
                'accounts_receivable': self._get_series_values(balance_sheet, 'AccountsReceivable', num_periods),
                'inventory': self._get_series_values(balance_sheet, 'Inventory', num_periods),
                'accounts_payable': self._get_series_values(balance_sheet, 'AccountsPayable', num_periods),
            }

            return result
        except Exception as e:
            logger.error(f"Error fetching balance sheet: {e}")
            return {}

    def _fetch_cash_flow(self, ticker) -> Dict[str, Any]:
        """Fetch cash flow data."""
        try:
            # Use get_cashflow() for yfinance v1.3.0+ compatibility
            cashflow = ticker.get_cashflow()
            if cashflow is None or cashflow.empty:
                return {}

            columns = cashflow.columns.tolist()
            periods = [col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else str(col) for col in columns]
            num_periods = len(periods)

            result = {
                'periods': periods,
                'free_cash_flow': self._get_series_values(cashflow, 'FreeCashFlow', num_periods),
                'operating_cash_flow': self._get_series_values(cashflow, 'OperatingCashFlow', num_periods),
                'capital_expenditure': self._get_series_values(cashflow, 'CapitalExpenditure', num_periods),
                'dividends_paid': self._get_series_values(cashflow, 'DividendsPaid', num_periods),
            }

            return result
        except Exception as e:
            logger.error(f"Error fetching cash flow: {e}")
            return {}

    def _fetch_analyst_estimates(self, ticker) -> Dict[str, Any]:
        """Fetch analyst estimates using compatible yfinance API."""
        try:
            # Try the newer earnings_estimate approach first (yfinance >= 0.2.0)
            estimates = {}

            # Method 1: Try earnings_estimate attribute
            if hasattr(ticker, 'earnings_estimate') and ticker.earnings_estimate is not None:
                try:
                    est_df = ticker.earnings_estimate
                    if est_df is not None and not est_df.empty:
                        estimates['earnings_estimate'] = est_df.to_dict() if hasattr(est_df, 'to_dict') else str(est_df)
                except Exception:
                    pass

            # Method 2: Try revenue_estimate attribute
            if hasattr(ticker, 'revenue_estimate') and ticker.revenue_estimate is not None:
                try:
                    rev_df = ticker.revenue_estimate
                    if rev_df is not None and not rev_df.empty:
                        estimates['revenue_estimate'] = rev_df.to_dict() if hasattr(rev_df, 'to_dict') else str(rev_df)
                except Exception:
                    pass

            # Method 3: Try recommendations as fallback
            if hasattr(ticker, 'recommendations') and ticker.recommendations is not None:
                try:
                    rec_df = ticker.recommendations
                    if rec_df is not None and not rec_df.empty:
                        estimates['recommendations'] = rec_df.head(5).to_dict() if hasattr(rec_df, 'to_dict') else str(rec_df)
                except Exception:
                    pass

            # Method 4: Try analyst_price_targets if available
            if hasattr(ticker, 'analyst_price_targets'):
                try:
                    targets = ticker.analyst_price_targets
                    if targets:
                        estimates['analyst_price_targets'] = targets
                except Exception:
                    pass

            if not estimates:
                logger.debug(f"No analyst estimates available for {ticker}")

            return estimates

        except AttributeError as e:
            # Handle deprecated 'estimates' attribute gracefully
            logger.warning(f"Analyst estimates not available (deprecated API): {e}")
            return {}
        except Exception as e:
            logger.error(f"Error fetching analyst estimates: {e}")
            return {}

    def _get_series_values(self, df, field_name: str, num_periods: int = 0) -> List[Optional[float]]:
        """Extract values from a DataFrame row, handling missing fields.

        Args:
            df: The DataFrame to extract values from
            field_name: The field name to look up in the DataFrame index
            num_periods: If provided, ensures the returned list has this length by padding with None

        Returns:
            List of values, padded with None if num_periods is specified and list is shorter
        """
        try:
            if field_name in df.index:
                series = df.loc[field_name]
                values = [None if (isinstance(v, float) and v != v) else v for v in series.values]
            else:
                values = []

            # Pad with None if num_periods is specified and values list is shorter
            if num_periods > 0 and len(values) < num_periods:
                values.extend([None] * (num_periods - len(values)))

            return values
        except Exception:
            return []


class VietnamDataStrategy:
    """
    Vietnam Data Strategy - Specialized for Vietnamese market

    Uses VietnamDataAggregator with cascading fallback:
    - Primary: vnstock (local VAS-compliant data)
    - Fallback: yfinance (international format)

    Handles VND currency, VAS accounting standards, and HOSE/HNX listings.
    """

    def __init__(self):
        self.aggregator = None

    def fetch_data(self, ticker_symbol: str, yf) -> Dict[str, Any]:
        """
        Fetch data using VietnamDataAggregator.

        Args:
            ticker_symbol: Vietnamese ticker symbol (without suffix)
            yf: yfinance module (not used directly, passed for compatibility)

        Returns:
            Comprehensive dictionary containing all fetched data
        """
        logger.info(f"[VietnamStrategy] Fetching data for ticker='{ticker_symbol}'")

        try:
            from .vietnam_data_aggregator import VietnamDataAggregator

            aggregator = VietnamDataAggregator()
            result = aggregator.fetch_comprehensive_data(ticker_symbol, market="VN")

            if result['success']:
                # Extract merged data for compatibility with existing code
                merged = result.get('merged_data', {})

                # Map to standard structure
                data_package = {
                    "symbol": f"{ticker_symbol}.VN",
                    "fetch_timestamp": result['fetch_timestamp'],
                    "market": "vietnam",
                    "data_sources_used": result['data_sources_used'],
                    "data_quality_score": result['data_quality_score'],
                    "warnings": result.get('warnings', []),
                    "key_stats": {
                        "company_name": merged.get('company_info', {}).get('company_name'),
                        "sector": merged.get('company_info', {}).get('sector'),
                        "industry": merged.get('company_info', {}).get('industry'),
                        "currency": merged.get('company_info', {}).get('currency', 'VND'),
                        "market_cap": merged.get('market_data', {}).get('market_cap'),
                        "current_price": merged.get('market_data', {}).get('current_price'),
                        "beta": merged.get('market_data', {}).get('beta'),
                        "pe_ratio": merged.get('market_data', {}).get('pe_ratio'),
                        "pb_ratio": merged.get('market_data', {}).get('pb_ratio'),
                        "dividend_yield": merged.get('market_data', {}).get('dividend_yield'),
                    },
                    "income_statement": merged.get('financials', {}).get('income_statement', {}),
                    "balance_sheet": merged.get('financials', {}).get('balance_sheet', {}),
                    "cash_flow": merged.get('financials', {}).get('cash_flow', {}),
                    "analyst_estimates": merged.get('analyst_estimates', {}),
                }

                logger.info(f"[VietnamStrategy] Successfully fetched data for {ticker_symbol} from vnstock")
                return data_package
            else:
                logger.error(f"[VietnamStrategy] Failed to fetch data for {ticker_symbol}: {result.get('error')}")
                raise Exception(result.get('error', 'Unknown error from VietnamDataAggregator'))

        except ImportError:
            logger.error("[VietnamStrategy] VietnamDataAggregator not found. Please install vnstock package.")
            raise Exception("vnstock package not installed. Cannot fetch Vietnamese market data.")
        except Exception as e:
            logger.error(f"[VietnamStrategy] Error fetching data for {ticker_symbol}: {str(e)}")
            raise

    def get_market_type(self) -> str:
        """Return market type identifier."""
        return "vietnam"


# === Strategy Factory ===

def get_data_strategy(market: str, enable_alphavantage_fallback: bool = True) -> DataStrategy:
    """
    Factory function to select the appropriate data fetching strategy based on market.

    Routing Logic:
    - vietnamese → VietnamDataStrategy (vnstock primary)
    - international/other → InternationalDataStrategy (yfinance + AlphaVantage)
    """
    if market.lower() in ["vietnam", "vietnam", "vn"]:
        return VietnamDataStrategy()
    else:
        return InternationalDataStrategy(enable_alphavantage_fallback=enable_alphavantage_fallback)


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
        self._strategy_cache = {}

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
                # Use get_income_stmt() and get_balance_sheet() for yfinance v1.3.0+ compatibility
                income_stmt = yf_ticker.get_income_stmt()
                balance_sheet = yf_ticker.get_balance_sheet()
                if income_stmt is not None and not income_stmt.empty:
                    # Get the most recent column
                    latest_col = income_stmt.columns[0]

                    # Calculate effective tax rate
                    tax_provision = income_stmt.loc['Tax Provision', latest_col] if 'Tax Provision' in income_stmt.index else None
                    pretax_income = income_stmt.loc['Pretax Income', latest_col] if 'Pretax Income' in income_stmt.index else None

                    if tax_provision is not None and pretax_income is not None and pretax_income != 0:
                        # Handle negative pretax income (losses) - tax rate not meaningful
                        if pretax_income > 0:
                            effective_tax_rate = abs(tax_provision / pretax_income)
                            # Cap tax rate at reasonable bounds (0-50%)
                            if effective_tax_rate < 0:
                                effective_tax_rate = None
                            elif effective_tax_rate > 0.50:
                                logger.debug(f"Tax rate {effective_tax_rate:.2%} exceeds 50% cap for {ticker_symbol}, setting to None")
                                effective_tax_rate = None
                        # If pretax_income is negative, leave tax_rate as None

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
                        # Cap cost of debt at reasonable bounds (0-20%)
                        if cost_of_debt < 0 or cost_of_debt > 0.20:
                            logger.debug(f"Cost of debt {cost_of_debt:.2%} outside 0-20% bounds for {ticker_symbol}, setting to None")
                            cost_of_debt = None
                        else:
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
        Fetch all available financial data using Strategy pattern.

        Data source cascade via Strategy pattern:
        - International markets: InternationalDataStrategy (yfinance -> AlphaVantage)
        - Vietnamese market: VietnamDataStrategy (vnstock -> yfinance)

        Args:
            ticker_symbol: Stock ticker symbol
            market: Market type (vietnamese or international)

        Returns:
            Comprehensive dictionary containing all fetched data
        """
        import yfinance as yf

        try:
            logger.info(f"Fetching all data for ticker='{ticker_symbol}', market='{market}' using Strategy pattern")

            # Get the appropriate strategy for this market
            strategy = get_data_strategy(market, self.enable_alphavantage_fallback)

            # Execute strategy
            data_package = strategy.fetch_data(ticker_symbol, yf)

            logger.info(f"Successfully fetched data for ticker='{ticker_symbol}' using {strategy.__class__.__name__}")
            return data_package

        except Exception as e:
            logger.error(f"Failed to fetch data for ticker='{ticker_symbol}': {str(e)}")
            raise

    # Legacy methods kept for backward compatibility
    # These are now deprecated in favor of Strategy pattern

    def _fetch_yfinance_primary(self, ticker_symbol: str, market: str, yf) -> Dict[str, Any]:
        """
        DEPRECATED: Use InternationalDataStrategy instead.
        Kept for backward compatibility only.
        """
        logger.warning("DEPRECATED: _fetch_yfinance_primary is deprecated. Use InternationalDataStrategy.")
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
        DEPRECATED: Use InternationalDataStrategy._validate_data_quality instead.
        Kept for backward compatibility only.
        """
        logger.warning("DEPRECATED: _validate_data_quality is deprecated. Use InternationalDataStrategy.")
        # Check for critical fields
        key_stats = data_package.get('key_stats', {})
        income_stmt = data_package.get('income_statement', {})

        # Must have at least revenue data
        has_revenue = bool(income_stmt.get('total_revenue'))

        # Must have some key stats
        has_price = key_stats.get('current_price') is not None

        return has_revenue or has_price

    def _enhance_with_alphavantage(self, data_package: Dict[str, Any], ticker_symbol: str, market: str) -> Dict[str, Any]:
        """
        DEPRECATED: Use InternationalDataStrategy._enhance_with_alphavantage instead.
        Kept for backward compatibility only.
        """
        logger.warning("DEPRECATED: _enhance_with_alphavantage is deprecated. Use InternationalDataStrategy.")
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
        """
        DEPRECATED: Use InternationalDataStrategy._fetch_alphavantage_fallback instead.
        Kept for backward compatibility only.
        """
        logger.warning("DEPRECATED: _fetch_alphavantage_fallback is deprecated. Use InternationalDataStrategy.")
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
        DEPRECATED: Use VietnamDataStrategy instead.
        Kept for backward compatibility only.
        """
        logger.warning("DEPRECATED: _fetch_vietnamese_enhanced is deprecated. Use VietnamDataStrategy.")
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
                    "market": "vietnam",
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
            "market": "vietnam",
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
            # Use get_income_stmt() for yfinance v1.3.0+ compatibility
            stmt = self.ticker.get_income_stmt()
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
            # Use get_balance_sheet() for yfinance v1.3.0+ compatibility
            bs = self.ticker.get_balance_sheet()
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
                "total_assets": get_series_raw('TotalAssets', ['Total Assets']),
                "current_assets": get_series_raw('CurrentAssets', ['Current Assets']),
                "non_current_assets": get_series_raw('TotalNonCurrentAssets', ['Total Non Current Assets']),

                # Current Assets Breakdown
                "cash_and_equivalents": get_series_raw('CashCashEquivalentsAndShortTermInvestments', ['Cash Cash Equivalents And Short Term Investments', 'CashAndCashEquivalents']),
                "cash": get_series_raw('CashCashEquivalentsAndShortTermInvestments', ['Cash Cash Equivalents And Short Term Investments']),  # Alias
                "accounts_receivable": get_series_raw('AccountsReceivable', ['Receivables', 'Gross Accounts Receivable']),
                "ar": get_series_raw('Accounts Receivable', ['Receivables']),  # Alias
                "inventory": get_series_raw('Inventory', ['Inventories']),
                "other_current_assets": get_series_raw('OtherCurrentAssets', ['Other Current Assets']),

                # Non-Current Assets
                "property_plant_equipment": get_series_raw('NetPPE', ['Net PPE']),
                "ppe_net": get_series_raw('NetPPE', ['Net PPE']),  # Alias
                "goodwill": get_series_raw('Goodwill'),
                "intangible_assets": get_series_raw('OtherIntangibleAssets', ['Other Intangible Assets', 'IntangibleAssets']),
                "long_term_investments": get_series_raw('InvestmentsAndAdvances', ['Investments And Advances', 'Long Term Equity Investment']),

                # Liabilities
                "total_liabilities": get_series_raw('TotalLiabilitiesNetMinorityInterest', ['Total Liabilities Net Minority Interest']),
                "current_liabilities": get_series_raw('CurrentLiabilities', ['Current Liabilities']),
                "non_current_liabilities": get_series_raw('TotalNonCurrentLiabilitiesNetMinorityInterest', ['Total Non Current Liabilities Net Minority Interest']),

                # Current Liabilities Breakdown
                "accounts_payable": get_series_raw('AccountsPayable', ['PayablesAndAccruedExpenses', 'Payables And Accrued Expenses', 'Payables']),
                "ap": get_series_raw('AccountsPayable', ['Payables']),  # Alias
                "short_term_debt": get_series_raw('CurrentDebt', ['Current Debt']),
                "other_current_liabilities": get_series_raw('OtherCurrentLiabilities', ['Other Current Liabilities']),

                # Non-Current Liabilities
                "long_term_debt": get_series_raw('LongTermDebt', ['Long Term Debt']),
                "deferred_tax_liabilities": get_series_raw('NonCurrentDeferredTaxesLiabilities', ['Non Current Deferred Taxes Liabilities', 'Non Current Deferred Liabilities']),
                "other_non_current_liabilities": get_series_raw('OtherNonCurrentLiabilities', ['Other Non Current Liabilities']),

                # Total Debt
                "total_debt": get_series_raw('TotalDebt', ['Total Debt']),
                "net_debt": None,  # Will be calculated

                # Equity
                "total_equity": get_series_raw('TotalEquityGrossMinorityInterest', ['Total Equity Gross Minority Interest']),
                "stockholders_equity": get_series_raw('StockholdersEquity', ['Stockholders Equity']),
                "retained_earnings": get_series_raw('RetainedEarnings'),
                "common_stock": get_series_raw('CommonStockEquity', ['Common Stock Equity']),

                # Working Capital (calculated)
                "working_capital": None,  # Will be calculated
                "shares_outstanding": get_series_raw('OrdinarySharesNumber', ['Ordinary Shares Number']),
            }
        except Exception as e:
            logger.warning(f"Error fetching balance sheet: {str(e)}")
            return {}

    def _fetch_cash_flow(self) -> Dict[str, Any]:
        """Fetch cash flow statement data."""
        try:
            # Use get_cashflow() for yfinance v1.3.0+ compatibility
            cf = self.ticker.get_cashflow()
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

        Filters out:
        - Market indices (symbols starting with ^)
        - ETFs and mutual funds (typeDisp = 'ETF' or 'Mutual Fund')
        - Currency pairs (symbols ending with =X)
        - Cryptocurrencies (symbols ending with -USD, etc.)
        - Symbols without valid exchange

        Args:
            query: Search query string

        Returns:
            List of matching ticker results (only valid equities)
        """
        import yfinance as yf

        try:
            logger.info(f"Searching tickers for query='{query}'")
            results = yf.Search(query=query, max_results=10)

            # Convert to list of dicts with validation
            ticker_list = []
            if hasattr(results, 'quotes'):
                for quote in results.quotes:
                    symbol = quote.get('symbol', '')
                    type_disp = quote.get('typeDisp', '')
                    exchange = quote.get('exchange', '')

                    # FILTER 1: Exclude market indices (start with ^)
                    if symbol.startswith('^'):
                        logger.debug(f"Excluding index symbol: {symbol}")
                        continue

                    # FILTER 2: Exclude ETFs and Mutual Funds
                    if type_disp in ['ETF', 'Mutual Fund']:
                        logger.debug(f"Excluding {type_disp}: {symbol}")
                        continue

                    # FILTER 3: Exclude currency pairs (end with =X)
                    if symbol.endswith('=X'):
                        logger.debug(f"Excluding currency pair: {symbol}")
                        continue

                    # FILTER 4: Exclude cryptocurrencies
                    if any(symbol.endswith(suffix) for suffix in ['-USD', '-EUR', '-BTC', '-ETH', '-USDT']):
                        logger.debug(f"Excluding cryptocurrency: {symbol}")
                        continue

                    # FILTER 5: Require valid exchange
                    if not exchange or exchange == '':
                        logger.debug(f"Excluding symbol without exchange: {symbol}")
                        continue

                    # FILTER 6: Exclude symbols with known problematic patterns
                    if any(pattern in symbol for pattern in ['INDEX', 'IDX', '^']):
                        logger.debug(f"Excluding symbol with problematic pattern: {symbol}")
                        continue

                    ticker_list.append({
                        'symbol': symbol,
                        'shortname': quote.get('shortname', ''),
                        'longname': quote.get('longname', ''),
                        'exchDisp': quote.get('exchDisp', ''),
                        'typeDisp': type_disp,
                        'exchange': exchange,
                        'sector': quote.get('sector'),
                        'industry': quote.get('industry'),
                    })

            logger.info(f"Found {len(ticker_list)} valid tickers for query='{query}' (filtered from raw results)")
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
                'enterpriseValue': info.get('enterpriseValue'),
                'beta': info.get('beta'),
                'trailingPE': info.get('trailingPE'),
                'forwardPE': info.get('forwardPE'),
                'dividendYield': info.get('dividendYield'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'exchange': info.get('exchange'),
                'currency': info.get('currency'),
                'priceToBook': info.get('priceToBook'),
                'enterpriseToEbitda': info.get('enterpriseToEbitda'),
                'enterpriseToRevenue': info.get('enterpriseToRevenue'),
                'priceToSalesTrailing12Months': info.get('priceToSalesTrailing12Months'),
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