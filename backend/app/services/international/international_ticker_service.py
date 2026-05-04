"""
International & Vietnamese Ticker Service
Handles data fetching for non-US tickers with market-specific considerations
"""

import yfinance as yf
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class InternationalTickerService:
    """
    Service for fetching data from international exchanges including Vietnam (HOSE, HNX, UPCOM)
    
    Yahoo Finance ticker suffixes:
    - Vietnam: .VN (HOSE), .HA (HNX), .VC (UPCOM)
    - Thailand: .BK
    - Singapore: .SI
    - Malaysia: .KL
    - Indonesia: .JK
    - Philippines: .PS
    - India: .NS (NSE), .BO (BSE)
    - Japan: .T
    - China: .SS (Shanghai), .SZ (Shenzhen)
    - Hong Kong: .HK
    - UK: .L
    - Germany: .DE
    - France: .PA
    - Canada: .TO
    - Australia: .AX
    - Brazil: .SA
    - Mexico: .MX
    """
    
    # Market suffixes for Yahoo Finance
    MARKET_SUFFIXES = {
        'VN': '.VN',  # Vietnam HOSE
        'HA': '.HA',  # Vietnam HNX
        'VC': '.VC',  # Vietnam UPCOM
        'BK': '.BK',  # Thailand
        'SI': '.SI',  # Singapore
        'KL': '.KL',  # Malaysia
        'JK': '.JK',  # Indonesia
        'PS': '.PS',  # Philippines
        'NS': '.NS',  # India NSE
        'BO': '.BO',  # India BSE
        'T': '.T',    # Japan
        'SS': '.SS',  # China Shanghai
        'SZ': '.SZ',  # China Shenzhen
        'HK': '.HK',  # Hong Kong
        'L': '.L',    # UK London
        'DE': '.DE',  # Germany
        'PA': '.PA',  # France Paris
        'TO': '.TO',  # Canada Toronto
        'AX': '.AX',  # Australia
        'SA': '.SA',  # Brazil
        'MX': '.MX',  # Mexico
    }
    
    # Vietnam-specific market codes
    VIETNAM_MARKETS = ['VN', 'HA', 'VC']
    
    # Currency mappings
    MARKET_CURRENCIES = {
        'VN': 'VND',
        'HA': 'VND',
        'VC': 'VND',
        'BK': 'THB',
        'SI': 'SGD',
        'KL': 'MYR',
        'JK': 'IDR',
        'PS': 'PHP',
        'NS': 'INR',
        'BO': 'INR',
        'T': 'JPY',
        'SS': 'CNY',
        'SZ': 'CNY',
        'HK': 'HKD',
        'L': 'GBP',
        'DE': 'EUR',
        'PA': 'EUR',
        'TO': 'CAD',
        'AX': 'AUD',
        'SA': 'BRL',
        'MX': 'MXN',
        'US': 'USD',
    }
    
    def __init__(self):
        pass  # No session initialization needed for yfinance
    
    def get_ticker_with_suffix(self, ticker: str, market_code: str) -> str:
        """
        Append appropriate suffix to ticker based on market
        
        Args:
            ticker: Base ticker symbol (e.g., "VNM", "VIC")
            market_code: Market code (e.g., "VN", "HA", "US")
            
        Returns:
            Full ticker with suffix (e.g., "VNM.VN", "AAPL")
        """
        if market_code.upper() in ['US', 'USA', 'NASDAQ', 'NYSE']:
            return ticker.upper()
        
        suffix = self.MARKET_SUFFIXES.get(market_code.upper())
        if suffix:
            return f"{ticker.upper()}{suffix}"
        
        # Default to .VN for Vietnam if not specified
        if market_code.upper() == 'VIETNAM':
            return f"{ticker.upper()}.VN"
        
        logger.warning(f"Unknown market code: {market_code}, using no suffix")
        return ticker.upper()
    
    def fetch_international_data(self, ticker: str, market_code: str = "VN") -> Dict[str, Any]:
        """
        Fetch all available data for international ticker
        
        Args:
            ticker: Base ticker symbol
            market_code: Market code (default: "VN" for Vietnam)
            
        Returns:
            Dictionary with all fetched data and metadata
        """
        full_ticker = self.get_ticker_with_suffix(ticker, market_code)
        logger.info(f"Fetching data for {full_ticker} (market: {market_code})")
        
        try:
            stock = yf.Ticker(full_ticker)
            
            # Try to get basic info first to verify ticker exists
            info = stock.info
            if not info or 'symbol' not in info:
                logger.error(f"No data found for {full_ticker}")
                return {
                    'success': False,
                    'error': f'Ticker {full_ticker} not found or no data available',
                    'ticker': full_ticker,
                    'market': market_code
                }
            
            # Fetch all financial data
            financials = self._safe_fetch(stock.financials)
            balance_sheet = self._safe_fetch(stock.balance_sheet)
            cashflow = self._safe_fetch(stock.cashflow)
            
            # Fetch estimates (may not be available for all international stocks)
            estimates = self._fetch_estimates(stock)
            
            # Get key statistics from info
            key_stats = self._extract_key_stats(info, market_code)
            
            # Get historical prices for beta calculation
            historical_prices = self._fetch_historical_prices(stock)
            
            return {
                'success': True,
                'ticker': full_ticker,
                'base_ticker': ticker,
                'market': market_code,
                'currency': self.MARKET_CURRENCIES.get(market_code.upper(), 'USD'),
                'company_info': self._extract_company_info(info),
                'financials': financials,
                'balance_sheet': balance_sheet,
                'cashflow': cashflow,
                'estimates': estimates,
                'key_stats': key_stats,
                'historical_prices': historical_prices,
                'data_availability': self._check_data_availability(
                    financials, balance_sheet, cashflow, estimates
                ),
                'warnings': self._generate_warnings(info, market_code)
            }
            
        except Exception as e:
            logger.error(f"Error fetching {full_ticker}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'ticker': full_ticker,
                'market': market_code
            }
    
    def fetch_vietnamese_data(self, ticker: str, market_code: str = "VN") -> Dict[str, Any]:
        """
        Specialized fetch for Vietnamese tickers with additional validation
        
        Args:
            ticker: Vietnamese ticker (e.g., "VNM", "VIC", "HPG")
            market_code: Vietnamese market (VN=HOSE, HA=HNX, VC=UPCOM)
            
        Returns:
            Comprehensive data package for Vietnamese stock
        """
        logger.info(f"Fetching Vietnamese data for {ticker} ({market_code})")
        
        # Fetch base international data
        data = self.fetch_international_data(ticker, market_code)
        
        if not data['success']:
            # Add Vietnam-specific error handling
            data['vietnam_specific_error'] = self._get_vietnam_error_message(
                ticker, market_code, data.get('error', '')
            )
            return data
        
        # Add Vietnam-specific metadata
        data['vietnam_metadata'] = {
            'exchange': self._get_vietnam_exchange_name(market_code),
            'sector_classification': 'VN-Sector',  # Can be enhanced with VSIC codes
            'listing_date': data['company_info'].get('listing_date'),
            'foreign_ownership_limit': self._get_fol_limit(ticker),
            'trading_status': 'Active'  # Can be enhanced with real-time status
        }
        
        # Validate data quality for Vietnamese stocks
        data['data_quality_checks'] = self._validate_vietnamese_data(data)
        
        return data
    
    def _safe_fetch(self, data_obj) -> Optional[pd.DataFrame]:
        """Safely fetch DataFrame, return None if empty or error"""
        try:
            if data_obj is None or data_obj.empty:
                return None
            return data_obj
        except Exception:
            return None
    
    def _fetch_estimates(self, stock) -> Dict[str, Any]:
        """Fetch analyst estimates (limited availability for international stocks)"""
        try:
            # Try to get earnings estimates
            earnings_est = stock.earnings_estimate
            revenue_est = stock.revenue_estimate
            
            if earnings_est is None and revenue_est is None:
                return {'available': False, 'reason': 'No analyst coverage'}
            
            return {
                'available': True,
                'earnings_estimate': self._safe_fetch(earnings_est),
                'revenue_estimate': self._safe_fetch(revenue_est),
                'note': 'Estimates may be limited for international stocks'
            }
        except Exception as e:
            return {'available': False, 'reason': str(e)}
    
    def _extract_key_stats(self, info: Dict, market_code: str) -> Dict[str, Any]:
        """Extract key statistics from info dict"""
        currency = self.MARKET_CURRENCIES.get(market_code.upper(), 'USD')
        
        return {
            'market_cap': info.get('marketCap'),
            'enterprise_value': info.get('enterpriseValue'),
            'trailing_pe': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'price_to_book': info.get('priceToBook'),
            'price_to_sales': info.get('priceToSalesTrailing12Months'),
            'ev_to_revenue': info.get('enterpriseToRevenue'),
            'ev_to_ebitda': info.get('enterpriseToEbitda'),
            'profit_margin': info.get('profitMargins'),
            'operating_margin': info.get('operatingMargins'),
            'return_on_assets': info.get('returnOnAssets'),
            'return_on_equity': info.get('returnOnEquity'),
            'debt_to_equity': info.get('debtToEquity'),
            'current_ratio': info.get('currentRatio'),
            'quick_ratio': info.get('quickRatio'),
            'dividend_yield': info.get('dividendYield'),
            'payout_ratio': info.get('payoutRatio'),
            'beta': info.get('beta'),
            '52_week_high': info.get('fiftyTwoWeekHigh'),
            '52_week_low': info.get('fiftyTwoWeekLow'),
            'average_volume': info.get('averageVolume'),
            'shares_outstanding': info.get('sharesOutstanding'),
            'float_shares': info.get('floatShares'),
            'currency': currency,
            'exchange': info.get('exchange'),
            'quote_type': info.get('quoteType')
        }
    
    def _fetch_historical_prices(self, stock, period: str = "2y") -> Optional[pd.DataFrame]:
        """Fetch historical prices for beta and volatility calculations"""
        try:
            hist = stock.history(period=period)
            if hist is None or hist.empty:
                return None
            return hist[['Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception:
            return None
    
    def _extract_company_info(self, info: Dict) -> Dict[str, Any]:
        """Extract company information"""
        return {
            'name': info.get('longName', info.get('shortName')),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'country': info.get('country'),
            'city': info.get('city'),
            'website': info.get('website'),
            'description': info.get('longBusinessSummary'),
            'employees': info.get('fullTimeEmployees'),
            'ceo': info.get('ceo'),
            'founded': info.get('foundedYear'),
            'listing_date': info.get('ipoDate'),
            'exchange': info.get('exchange'),
            'currency': info.get('currency'),
            'market': info.get('market')
        }
    
    def _check_data_availability(self, financials, balance_sheet, cashflow, estimates) -> Dict[str, bool]:
        """Check which data categories are available"""
        return {
            'income_statement': financials is not None and not financials.empty,
            'balance_sheet': balance_sheet is not None and not balance_sheet.empty,
            'cash_flow': cashflow is not None and not cashflow.empty,
            'analyst_estimates': estimates.get('available', False) if estimates else False,
            'has_quarterly_data': self._has_quarterly_data(financials),
            'has_annual_data': self._has_annual_data(financials)
        }
    
    def _has_quarterly_data(self, df: Optional[pd.DataFrame]) -> bool:
        """Check if DataFrame has quarterly data"""
        if df is None or df.empty:
            return False
        # Check column names for quarterly indicators
        return any('Q' in str(col) for col in df.columns)
    
    def _has_annual_data(self, df: Optional[pd.DataFrame]) -> bool:
        """Check if DataFrame has annual data"""
        if df is None or df.empty:
            return False
        return len(df.columns) > 0
    
    def _generate_warnings(self, info: Dict, market_code: str) -> List[str]:
        """Generate warnings about data limitations"""
        warnings = []
        
        if not info.get('earnings_estimate'):
            warnings.append("No analyst earnings estimates available")
        
        if not info.get('revenue_estimate'):
            warnings.append("No analyst revenue estimates available")
        
        if info.get('beta') is None:
            warnings.append("Beta not available, will calculate from historical prices")
        
        if market_code in self.VIETNAM_MARKETS:
            warnings.append("Vietnamese market data may have limited analyst coverage")
        
        if info.get('marketCap', 0) < 1e9:  # Less than 1B
            warnings.append("Small-cap stock: data may be less reliable")
        
        return warnings
    
    def _get_vietnam_exchange_name(self, market_code: str) -> str:
        """Get full exchange name for Vietnamese markets"""
        exchange_names = {
            'VN': 'Ho Chi Minh Stock Exchange (HOSE)',
            'HA': 'Hanoi Stock Exchange (HNX)',
            'VC': 'Unlisted Public Company Market (UPCOM)'
        }
        return exchange_names.get(market_code.upper(), 'Unknown Vietnamese Market')
    
    def _get_fol_limit(self, ticker: str) -> Optional[float]:
        """
        Get Foreign Ownership Limit for Vietnamese stocks
        Note: This would ideally come from a separate database
        """
        # Placeholder - in production, this would query a database
        fol_limits = {
            'VNM': 49.0,
            'VIC': 49.0,
            'HPG': 49.0,
            'VCB': 30.0,
            'BID': 30.0,
            'CTG': 30.0,
        }
        return fol_limits.get(ticker.upper())
    
    def _validate_vietnamese_data(self, data: Dict) -> Dict[str, Any]:
        """Validate data quality for Vietnamese stocks"""
        checks = {
            'has_financials': data['financials'] is not None,
            'has_balance_sheet': data['balance_sheet'] is not None,
            'has_cashflow': data['cashflow'] is not None,
            'has_market_cap': data['key_stats'].get('market_cap') is not None,
            'has_price_data': data['historical_prices'] is not None,
            'data_completeness_score': 0.0
        }
        
        # Calculate completeness score
        total_checks = 5
        passed_checks = sum([
            checks['has_financials'],
            checks['has_balance_sheet'],
            checks['has_cashflow'],
            checks['has_market_cap'],
            checks['has_price_data']
        ])
        
        checks['data_completeness_score'] = passed_checks / total_checks
        
        # Add quality flags
        checks['quality_flag'] = 'GOOD' if checks['data_completeness_score'] >= 0.8 else \
                                 'MODERATE' if checks['data_completeness_score'] >= 0.6 else 'POOR'
        
        return checks
    
    def _get_vietnam_error_message(self, ticker: str, market_code: str, error: str) -> str:
        """Provide helpful error messages for Vietnamese tickers"""
        common_issues = {
            'not found': f"Ticker {ticker}.{market_code} not found. Verify the ticker symbol and market code.",
            'no data': f"No data available for {ticker}.{market_code}. The stock may have limited trading history.",
            '404': f"Ticker {ticker}.{market_code} not found on Yahoo Finance. Try alternative data sources."
        }
        
        for key, message in common_issues.items():
            if key in error.lower():
                return message
        
        return f"Error fetching {ticker}.{market_code}: {error}. Consider checking ticker symbol or market connectivity."
    
    def list_available_vietnamese_stocks(self) -> List[Dict[str, str]]:
        """
        Return a list of commonly tracked Vietnamese stocks
        In production, this would come from a database
        """
        return [
            {'ticker': 'VNM', 'name': 'Vinamilk', 'market': 'VN', 'sector': 'Consumer Staples'},
            {'ticker': 'VIC', 'name': 'Vingroup', 'market': 'VN', 'sector': 'Real Estate'},
            {'ticker': 'HPG', 'name': 'Hoa Phat Group', 'market': 'VN', 'sector': 'Materials'},
            {'ticker': 'VCB', 'name': 'Vietcombank', 'market': 'VN', 'sector': 'Financials'},
            {'ticker': 'BID', 'name': 'BIDV', 'market': 'VN', 'sector': 'Financials'},
            {'ticker': 'CTG', 'name': 'VietinBank', 'market': 'VN', 'sector': 'Financials'},
            {'ticker': 'VHM', 'name': 'Vinhomes', 'market': 'VN', 'sector': 'Real Estate'},
            {'ticker': 'MSN', 'name': 'Masan Group', 'market': 'VN', 'sector': 'Consumer Staples'},
            {'ticker': 'TCB', 'name': 'Techcombank', 'market': 'VN', 'sector': 'Financials'},
            {'ticker': 'MBB', 'name': 'MB Bank', 'market': 'VN', 'sector': 'Financials'},
            {'ticker': 'FPT', 'name': 'FPT Corporation', 'market': 'VN', 'sector': 'Technology'},
            {'ticker': 'GAS', 'name': 'PV Gas', 'market': 'VN', 'sector': 'Energy'},
            {'ticker': 'SAB', 'name': 'Sabeco', 'market': 'VN', 'sector': 'Consumer Staples'},
            {'ticker': 'VRE', 'name': 'Vincom Retail', 'market': 'VN', 'sector': 'Real Estate'},
            {'ticker': 'POW', 'name': 'PV Power', 'market': 'VN', 'sector': 'Utilities'},
        ]
    
    def get_market_info(self, market_code: str) -> Dict[str, Any]:
        """Get information about a specific market"""
        market_info = {
            'VN': {
                'name': 'Ho Chi Minh Stock Exchange (HOSE)',
                'currency': 'VND',
                'timezone': 'Asia/Ho_Chi_Minh',
                'trading_hours': '09:00-15:00',
                'settlement': 'T+2',
                'lot_size': 100,
                'price_band': '±7%',
            },
            'HA': {
                'name': 'Hanoi Stock Exchange (HNX)',
                'currency': 'VND',
                'timezone': 'Asia/Ho_Chi_Minh',
                'trading_hours': '09:00-15:00',
                'settlement': 'T+2',
                'lot_size': 100,
                'price_band': '±10%',
            },
            'VC': {
                'name': 'Unlisted Public Company Market (UPCOM)',
                'currency': 'VND',
                'timezone': 'Asia/Ho_Chi_Minh',
                'trading_hours': '09:00-15:00',
                'settlement': 'T+2',
                'lot_size': 100,
                'price_band': '±15%',
            }
        }
        
        return market_info.get(market_code.upper(), {
            'name': 'Unknown Market',
            'currency': 'USD',
            'note': 'Market information not available'
        })
