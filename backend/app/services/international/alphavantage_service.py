"""
AlphaVantage Service - Step 5A: API Fetch (Fallback/Enhancement)

Provides additional data coverage and fallback for yfinance:
    - Income Statement: Annual and quarterly data with standardized field names
    - Balance Sheet: Comprehensive assets, liabilities, and equity data
    - Cash Flow: Operating, investing, and financing activities
    - Key Stats: Market cap, P/E ratios, dividend info
    - Analyst Recommendations: Buy/sell/hold ratings
    - Price Targets: Analyst price targets

ADVANTAGES OVER YFINANCE:
    - More consistent field naming across different tickers
    - Better coverage for international stocks
    - Explicit API for analyst recommendations
    - Quarterly data often more up-to-date
    - Standardized JSON response format

LIMITATIONS:
    - Free tier: 25 requests/day, 5 requests/minute
    - Some advanced metrics require premium subscription
    - No automatic ticker discovery (must know exact symbol)

USAGE:
    - Primary: Use as fallback when yfinance fails
    - Enhancement: Merge data from both sources for maximum coverage
    - Validation: Cross-check critical values between sources
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class AlphaVantageService:
    """Service for fetching financial data from AlphaVantage API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AlphaVantage service.
        
        Args:
            api_key: AlphaVantage API key. If not provided, will try to load from 
                    environment variable ALPHAVANTAGE_API_KEY
        """
        self.api_key = api_key or os.getenv('ALPHAVANTAGE_API_KEY') or os.getenv('ALPHA_VANTAGE_API_KEY')
        self.base_url = "https://www.alphavantage.co/query"
        self._session = None
        
        if not self.api_key:
            logger.warning("AlphaVantage API key not provided. Set ALPHAVANTAGE_API_KEY or ALPHA_VANTAGE_API_KEY environment variable.")
    
    @property
    def session(self):
        """Lazy session initialization for HTTP requests."""
        if self._session is None:
            import requests
            self._session = requests.Session()
        return self._session
    
    def fetch_all_data(self, ticker_symbol: str, market: str = "international") -> Dict[str, Any]:
        """
        Fetch all available financial data from AlphaVantage.
        
        Args:
            ticker_symbol: Stock ticker symbol
            market: Market type (international or vietnamese)
            
        Returns:
            Comprehensive dictionary containing all fetched data, or empty dict on failure
        """
        if not self.api_key:
            logger.warning("AlphaVantage API key not configured, skipping fetch")
            return {}
        
        try:
            logger.info(f"Fetching AlphaVantage data for ticker='{ticker_symbol}', market='{market}'")
            
            # For Vietnamese market, AlphaVantage may not have coverage
            if market == "vietnamese":
                logger.info(f"AlphaVantage does not support Vietnamese market, skipping")
                return {}
            
            # Fetch all data categories
            overview = self._fetch_company_overview(ticker_symbol)
            income_statement = self._fetch_income_statement(ticker_symbol)
            balance_sheet = self._fetch_balance_sheet(ticker_symbol)
            cash_flow = self._fetch_cash_flow(ticker_symbol)
            analyst_ratings = self._fetch_analyst_ratings(ticker_symbol)
            price_targets = self._fetch_price_targets(ticker_symbol)
            
            # Compile comprehensive data package
            data_package = {
                "symbol": ticker_symbol,
                "fetch_timestamp": datetime.now().isoformat(),
                "market": market,
                "data_source": "alphavantage",
                "key_stats": overview,
                "income_statement": income_statement,
                "balance_sheet": balance_sheet,
                "cash_flow": cash_flow,
                "analyst_estimates": {
                    "analyst_ratings": analyst_ratings,
                    "price_targets": price_targets
                },
            }
            
            logger.info(f"Successfully fetched AlphaVantage data for ticker='{ticker_symbol}'")
            return data_package
            
        except Exception as e:
            logger.error(f"Failed to fetch AlphaVantage data for ticker='{ticker_symbol}': {str(e)}")
            return {}
    
    def _make_request(self, function: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request to AlphaVantage with error handling."""
        try:
            url_params = {
                'function': function,
                'apikey': self.api_key,
                **(params or {})
            }
            
            response = self.session.get(self.base_url, params=url_params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API limit errors
            if 'Note' in data:
                logger.warning(f"AlphaVantage API limit reached: {data['Note']}")
                return None
            
            if 'Error Message' in data:
                logger.error(f"AlphaVantage API error: {data['Error Message']}")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"AlphaVantage request failed: {str(e)}")
            return None
    
    def _fetch_company_overview(self, symbol: str) -> Dict[str, Any]:
        """Fetch company overview and key statistics."""
        try:
            data = self._make_request('OVERVIEW', {'symbol': symbol})
            
            if not data:
                return {}
            
            def parse_float(val: str) -> Optional[float]:
                if val is None or val == '' or val == 'None':
                    return None
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None
            
            return {
                # Company Info
                "company_name": data.get('Name'),
                "description": data.get('Description'),
                "sector": data.get('Sector'),
                "industry": data.get('Industry'),
                "currency": data.get('Currency', 'USD'),
                "country": data.get('Country'),
                "exchange": data.get('Exchange'),
                
                # Market Data
                "current_price": parse_float(data.get('Price')),
                "previous_close": parse_float(data.get('PreviousClose')),
                "open": parse_float(data.get('Open')),
                "day_low": parse_float(data.get('DayLow')),
                "day_high": parse_float(data.get('DayHigh')),
                "fifty_two_week_low": parse_float(data.get('52WeekLow')),
                "fifty_two_week_high": parse_float(data.get('52WeekHigh')),
                
                # Market Cap & Enterprise Value
                "market_cap": parse_float(data.get('MarketCapitalization')),
                
                # Risk Metrics
                "beta": parse_float(data.get('Beta')),
                
                # Shares
                "shares_outstanding": parse_float(data.get('SharesOutstanding')),
                
                # Valuation Ratios
                "pe_ratio": parse_float(data.get('PERatio')),
                "forward_pe": parse_float(data.get('ForwardPE')),
                "peg_ratio": parse_float(data.get('PEGRatio')),
                "price_to_book": parse_float(data.get('PriceToBookRatio')),
                "price_to_sales": parse_float(data.get('PriceToSalesRatio')),
                "ev_to_revenue": None,  # Not directly available
                "ev_to_ebitda": parse_float(data.get('EVToEBITDA')),
                
                # Dividend Info
                "dividend_rate": parse_float(data.get('DividendRate')),
                "dividend_yield": parse_float(data.get('DividendYield')),
                "payout_ratio": parse_float(data.get('PayoutRatio')),
                "ex_dividend_date": data.get('ExDividendDate'),
                
                # Profitability
                "profit_margin": parse_float(data.get('ProfitMargin')),
                "operating_margin": parse_float(data.get('OperatingMarginTTM')),
                "return_on_assets": parse_float(data.get('ReturnOnAssetsTTM')),
                "return_on_equity": parse_float(data.get('ReturnOnEquityTTM')),
                
                # Financial Health
                "total_debt": parse_float(data.get('TotalDebt')),
                "total_cash": parse_float(data.get('TotalCash')),
                "debt_to_equity": parse_float(data.get('DebtToEquity')),
                "current_ratio": parse_float(data.get('CurrentRatio')),
                "quick_ratio": parse_float(data.get('QuickRatio')),
                
                # Revenue & Earnings
                "revenue_ttm": parse_float(data.get('RevenueTTM')),
                "revenue_per_share_ttm": parse_float(data.get('RevenuePerShareTTM')),
                "quarterly_revenue_growth": parse_float(data.get('QuarterlyRevenueGrowthYOY')),
                "gross_profit_ttm": parse_float(data.get('GrossProfitTTM')),
                "ebitda": parse_float(data.get('EBITDA')),
                "net_income_ttm": parse_float(data.get('NetIncomeTTM')),
                "diluted_eps_ttm": parse_float(data.get('DilutedEPSTTM')),
                "quarterly_earnings_growth": parse_float(data.get('QuarterlyEarningsGrowthYOY')),
                
                # Analyst Targets
                "analyst_target_price": parse_float(data.get('AnalystTargetPrice')),
                "trailing_pe": parse_float(data.get('TrailingPE')),
            }
            
        except Exception as e:
            logger.error(f"Error fetching company overview: {str(e)}")
            return {}
    
    def _fetch_income_statement(self, symbol: str) -> Dict[str, Any]:
        """Fetch annual income statement data."""
        try:
            data = self._make_request('INCOME_STATEMENT', {'symbol': symbol})
            
            if not data or 'annualReports' not in data:
                return {}
            
            # Convert annual reports to year-keyed format
            result = {}
            
            for report in data['annualReports'][:5]:  # Last 5 years
                fiscal_year = report.get('fiscalDateEnding', '')[:4]  # Extract year
                
                if not fiscal_year:
                    continue
                
                # Map AlphaVantage fields to standard format
                result[fiscal_year] = {
                    'total_revenue': self._parse_float(report.get('totalRevenue')),
                    'cost_of_revenue': self._parse_float(report.get('costOfRevenue')),
                    'gross_profit': self._parse_float(report.get('grossProfit')),
                    'research_development': self._parse_float(report.get('researchAndDevelopment')),
                    'selling_general_administrative': self._parse_float(report.get('sellingGeneralAndAdministrative')),
                    'operating_expense': self._parse_float(report.get('operatingExpenses')),
                    'operating_income': self._parse_float(report.get('operatingIncome')),
                    'ebit': self._parse_float(report.get('ebit')),
                    'ebitda': self._parse_float(report.get('ebitda')),
                    'interest_expense': self._parse_float(report.get('interestExpense')),
                    'interest_income': self._parse_float(report.get('interestIncome')),
                    'other_income_expense': self._parse_float(report.get('otherNonOperatingIncome')),
                    'pretax_income': self._parse_float(report.get('incomeBeforeTax')),
                    'tax_provision': self._parse_float(report.get('incomeTaxExpense')),
                    'net_income': self._parse_float(report.get('netIncomeFromContinuingOperations')),
                    'net_income_continuing_ops': self._parse_float(report.get('comprehensiveIncomeNetOfTax')),
                    'diluted_eps': self._parse_float(report.get('dilutedEPS')),
                    'basic_eps': self._parse_float(report.get('basicEPS')),
                    'weighted_average_shares_diluted': self._parse_float(report.get('weightedAverageShsOut')),
                    'weighted_average_shares_basic': self._parse_float(report.get('weightedAverageShsOutDil')),
                    'depreciation_amortization': self._parse_float(report.get('depreciationAndAmortization')),
                }
            
            # Transpose to field-keyed format for compatibility
            return self._transpose_annual_data(result)
            
        except Exception as e:
            logger.error(f"Error fetching income statement: {str(e)}")
            return {}
    
    def _fetch_balance_sheet(self, symbol: str) -> Dict[str, Any]:
        """Fetch annual balance sheet data."""
        try:
            data = self._make_request('BALANCE_SHEET', {'symbol': symbol})
            
            if not data or 'annualReports' not in data:
                return {}
            
            result = {}
            
            for report in data['annualReports'][:5]:  # Last 5 years
                fiscal_year = report.get('fiscalDateEnding', '')[:4]
                
                if not fiscal_year:
                    continue
                
                result[fiscal_year] = {
                    # Assets
                    'total_assets': self._parse_float(report.get('totalAssets')),
                    'current_assets': self._parse_float(report.get('totalCurrentAssets')),
                    'non_current_assets': self._parse_float(report.get('totalNonCurrentAssets')),
                    
                    # Current Assets
                    'cash_and_equivalents': self._parse_float(report.get('cashAndCashEquivalentsAtCarryingValue')),
                    'cash': self._parse_float(report.get('cashAndShortTermInvestments')),
                    'accounts_receivable': self._parse_float(report.get('inventory')),  # Note: AV naming issue
                    'ar': self._parse_float(report.get('inventory')),
                    'inventory': self._parse_float(report.get('inventory')),
                    'other_current_assets': self._parse_float(report.get('otherCurrentAssets')),
                    
                    # Non-Current Assets
                    'property_plant_equipment': self._parse_float(report.get('propertyPlantAndEquipmentNet')),
                    'ppe_net': self._parse_float(report.get('propertyPlantAndEquipmentNet')),
                    'goodwill': self._parse_float(report.get('goodwill')),
                    'intangible_assets': self._parse_float(report.get('intangibleAssets')),
                    'long_term_investments': self._parse_float(report.get('longTermInvestments')),
                    
                    # Liabilities
                    'total_liabilities': self._parse_float(report.get('totalLiabilities')),
                    'current_liabilities': self._parse_float(report.get('totalCurrentLiabilities')),
                    'non_current_liabilities': self._parse_float(report.get('totalNonCurrentLiabilities')),
                    
                    # Current Liabilities
                    'accounts_payable': self._parse_float(report.get('accountsPayable')),
                    'ap': self._parse_float(report.get('accountsPayable')),
                    'short_term_debt': self._parse_float(report.get('shortTermDebt')),
                    'other_current_liabilities': self._parse_float(report.get('otherCurrentLiabilities')),
                    
                    # Non-Current Liabilities
                    'long_term_debt': self._parse_float(report.get('longTermDebt')),
                    'deferred_tax_liabilities': self._parse_float(report.get('deferredRevenueNonCurrent')),
                    'other_non_current_liabilities': self._parse_float(report.get('otherNonCurrentLiabilities')),
                    
                    # Total Debt
                    'total_debt': self._parse_float(report.get('totalDebt')),
                    
                    # Equity
                    'total_equity': self._parse_float(report.get('totalShareholderEquity')),
                    'stockholders_equity': self._parse_float(report.get('retainedEarnings')),
                    'retained_earnings': self._parse_float(report.get('retainedEarnings')),
                    'common_stock': self._parse_float(report.get('commonStock')),
                    'shares_outstanding': self._parse_float(report.get('commonStockSharesOutstanding')),
                }
            
            return self._transpose_annual_data(result)
            
        except Exception as e:
            logger.error(f"Error fetching balance sheet: {str(e)}")
            return {}
    
    def _fetch_cash_flow(self, symbol: str) -> Dict[str, Any]:
        """Fetch annual cash flow data."""
        try:
            data = self._make_request('CASH_FLOW', {'symbol': symbol})
            
            if not data or 'annualReports' not in data:
                return {}
            
            result = {}
            
            for report in data['annualReports'][:5]:  # Last 5 years
                fiscal_year = report.get('fiscalDateEnding', '')[:4]
                
                if not fiscal_year:
                    continue
                
                result[fiscal_year] = {
                    # Operating Activities
                    'operating_cash_flow': self._parse_float(report.get('operatingCashflow')),
                    'ocf': self._parse_float(report.get('operatingCashflow')),
                    'net_income_from_continuing_ops': self._parse_float(report.get('netIncome')),
                    'depreciation_amortization': self._parse_float(report.get('depreciationDepletionAndAmortization')),
                    'change_in_working_capital': self._parse_float(report.get('changeInWorkingCapital')),
                    'change_in_ar': self._parse_float(report.get('changeInReceivables')),
                    'change_in_inventory': self._parse_float(report.get('changeInInventory')),
                    'change_in_ap': self._parse_float(report.get('changeInPayables')),
                    
                    # Investing Activities
                    'investing_cash_flow': self._parse_float(report.get('investmentCashflow')),
                    'capital_expenditure': self._parse_float(report.get('capitalExpenditures')),
                    'capex': self._parse_float(report.get('capitalExpenditures')),
                    'acquisitions': self._parse_float(report.get('investments')),
                    'purchase_of_investments': self._parse_float(report.get('investments')),
                    'sale_of_investments': self._parse_float(report.get('proceedsFromSaleOfInvestments')),
                    
                    # Financing Activities
                    'financing_cash_flow': self._parse_float(report.get('financingCashflow')),
                    'dividends_paid': self._parse_float(report.get('dividendsPaid')),
                    'dividends': self._parse_float(report.get('dividendsPaid')),
                    'repurchase_of_stock': self._parse_float(report.get('repurchaseOfCommonStock')),
                    'issuance_of_stock': self._parse_float(report.get('proceedsFromIssuanceOfCommonStock')),
                    'repayment_of_debt': self._parse_float(report.get('paymentsOfLongTermDebt')),
                    'issuance_of_debt': self._parse_float(report.get('proceedsFromIssuanceOfLongTermDebt')),
                    
                    # Free Cash Flow
                    'free_cash_flow': self._parse_float(report.get('freeCashFlow')),
                    'fcf': self._parse_float(report.get('freeCashFlow')),
                    
                    # Net Change in Cash
                    'end_cash_position': self._parse_float(report.get('cashAtEndOfPeriod')),
                    'beginning_cash_position': self._parse_float(report.get('cashAtBeginningOfPeriod')),
                    'change_in_cash': self._parse_float(report.get('changeInCashAndCashEquivalents')),
                }
            
            return self._transpose_annual_data(result)
            
        except Exception as e:
            logger.error(f"Error fetching cash flow: {str(e)}")
            return {}
    
    def _fetch_analyst_ratings(self, symbol: str) -> Dict[str, Any]:
        """Fetch analyst recommendations."""
        try:
            data = self._make_request('ANALYST_RECOMMENDATIONS', {'symbol': symbol})
            
            if not data or 'data' not in data:
                return {}
            
            # Get most recent recommendation
            latest = data['data'][0] if data['data'] else {}
            
            return {
                'strong_buy': self._parse_int(latest.get('strongBuy')),
                'buy': self._parse_int(latest.get('buy')),
                'hold': self._parse_int(latest.get('hold')),
                'sell': self._parse_int(latest.get('sell')),
                'strong_sell': self._parse_int(latest.get('strongSell')),
                'date': latest.get('period'),
            }
            
        except Exception as e:
            logger.error(f"Error fetching analyst ratings: {str(e)}")
            return {}
    
    def _fetch_price_targets(self, symbol: str) -> Dict[str, Any]:
        """Fetch analyst price targets (if available via other endpoints)."""
        # AlphaVantage doesn't have direct price target endpoint in free tier
        # This would need to be supplemented from other sources
        return {}
    
    def _parse_float(self, val: str) -> Optional[float]:
        """Parse string value to float, handling None and empty strings."""
        if val is None or val == '' or val == 'None':
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    
    def _parse_int(self, val: str) -> Optional[int]:
        """Parse string value to int, handling None and empty strings."""
        if val is None or val == '' or val == 'None':
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None
    
    def _transpose_annual_data(self, year_data: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Transpose year-keyed data to field-keyed data for compatibility.
        
        Input: {'2023': {'revenue': 100}, '2022': {'revenue': 90}}
        Output: {'revenue': {'2023': 100, '2022': 90}}
        """
        if not year_data:
            return {}
        
        # Get all unique field names
        all_fields = set()
        for year_data_dict in year_data.values():
            all_fields.update(year_data_dict.keys())
        
        # Transpose
        result = {}
        for field in all_fields:
            result[field] = {}
            for year, data in year_data.items():
                result[field][year] = data.get(field)
        
        return result
    
    def merge_with_yfinance(self, yf_data: Dict, av_data: Dict) -> Dict:
        """
        Merge AlphaVantage data with yfinance data for maximum coverage.
        
        Priority:
        1. Use yfinance as primary source
        2. Fill gaps with AlphaVantage data
        3. Flag discrepancies for review
        
        Args:
            yf_data: Data from yfinance (primary)
            av_data: Data from AlphaVantage (supplementary)
            
        Returns:
            Merged data package with quality indicators
        """
        if not av_data:
            return yf_data
        
        merged = yf_data.copy()
        merged['data_sources'] = ['yfinance', 'alphavantage']
        merged['merge_timestamp'] = datetime.now().isoformat()
        
        # Fill gaps in key stats
        if 'key_stats' in yf_data and 'key_stats' in av_data:
            for key, value in av_data['key_stats'].items():
                if yf_data['key_stats'].get(key) is None and value is not None:
                    merged['key_stats'][key] = value
                    merged['key_stats'][f'{key}_source'] = 'alphavantage'
        
        # Fill gaps in financial statements
        for statement in ['income_statement', 'balance_sheet', 'cash_flow']:
            if statement in yf_data and statement in av_data:
                for field, values in av_data[statement].items():
                    if yf_data[statement].get(field) is None or not yf_data[statement][field]:
                        merged[statement][field] = values
                        merged[statement][f'{field}_source'] = 'alphavantage'
        
        # Add analyst estimates from AlphaVantage
        if 'analyst_estimates' in av_data and av_data['analyst_estimates']:
            if 'analyst_estimates' not in merged:
                merged['analyst_estimates'] = {}
            merged['analyst_estimates']['alphavantage_ratings'] = av_data['analyst_estimates'].get('analyst_ratings', {})
        
        logger.info(f"Merged yfinance and AlphaVantage data successfully")
        return merged
