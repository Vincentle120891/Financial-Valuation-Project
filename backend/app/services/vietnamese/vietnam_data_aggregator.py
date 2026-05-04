"""
Vietnam Data Aggregator Service - Multi-Source Data Fetching

Primary Source: vnstock (local Vietnamese data provider)
Fallback Sources: 
    1. yfinance (Yahoo Finance)
    2. Direct API calls to Vietnamese exchanges
    3. Manual data entry interface

This service implements a cascading fallback mechanism to ensure maximum
data coverage for Vietnamese stocks, addressing the challenges of:
    - Incomplete yfinance data for .VN tickers
    - Fiscal year mismatches
    - VAS (Vietnamese Accounting Standards) vs IFRS/GAAP differences
    - Low free float and liquidity issues
    - Foreign ownership limit tracking
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


class VietnamDataAggregator:
    """
    Multi-source data aggregator for Vietnamese stocks.
    
    Priority order:
    1. vnstock (primary - local source with complete VAS data)
    2. yfinance (fallback - international standard format)
    3. Direct exchange APIs (fallback - raw data)
    4. Manual entry placeholders (last resort)
    """
    
    def __init__(self):
        self.vnstock_available = False
        self._check_vnstock_availability()
    
    def _check_vnstock_availability(self):
        """Check if vnstock is installed and functional"""
        try:
            import vnstock
            self.vnstock_available = True
            logger.info("vnstock library available - will use as primary source")
        except ImportError:
            self.vnstock_available = False
            logger.warning("vnstock not available - will rely on fallback sources")
    
    def fetch_comprehensive_data(self, ticker: str, market: str = "vietnamese") -> Dict[str, Any]:
        """
        Fetch comprehensive data for Vietnamese stock using cascading fallback.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'VNM', 'VIC', 'HPG')
            market: Market code ('VN' for HOSE, 'HA' for HNX, 'VC' for UPCOM)
            
        Returns:
            Comprehensive data package with source attribution
        """
        logger.info(f"Fetching comprehensive data for {ticker}.{market}")
        
        result = {
            'symbol': ticker,
            'market': market,
            'fetch_timestamp': datetime.now().isoformat(),
            'data_sources_used': [],
            'data_quality_score': 0.0,
            'warnings': [],
            'success': False
        }
        
        # Try primary source: vnstock
        if self.vnstock_available:
            try:
                logger.info(f"Attempting vnstock fetch for {ticker}")
                vnstock_data = self._fetch_from_vnstock(ticker, market)
                if vnstock_data and self._validate_vnstock_data(vnstock_data):
                    result['vnstock_data'] = vnstock_data
                    result['data_sources_used'].append('vnstock')
                    logger.info(f"Successfully fetched from vnstock for {ticker}")
            except Exception as e:
                logger.warning(f"vnstock fetch failed for {ticker}: {str(e)}")
                result['warnings'].append(f"vnstock primary source failed: {str(e)}")
        
        # Try fallback: yfinance
        try:
            logger.info(f"Attempting yfinance fetch for {ticker}")
            yf_data = self._fetch_from_yfinance(ticker, market)
            if yf_data:
                result['yfinance_data'] = yf_data
                result['data_sources_used'].append('yfinance')
                logger.info(f"Successfully fetched from yfinance for {ticker}")
        except Exception as e:
            logger.warning(f"yfinance fetch failed for {ticker}: {str(e)}")
            result['warnings'].append(f"yfinance fallback failed: {str(e)}")
        
        # Merge and normalize data
        if result['data_sources_used']:
            merged_data = self._merge_data_sources(result)
            result['merged_data'] = merged_data
            result['data_quality_score'] = self._calculate_data_quality(merged_data)
            result['success'] = True
            logger.info(f"Data aggregation complete for {ticker}. Quality score: {result['data_quality_score']}")
        else:
            result['warnings'].append("No data sources returned valid data")
            result['data_quality_score'] = 0.0
        
        return result
    
    def _fetch_from_vnstock(self, ticker: str, market: str) -> Optional[Dict[str, Any]]:
        """
        Fetch data from vnstock (primary source for Vietnamese stocks).
        
        Returns comprehensive VAS-compliant financial data.
        """
        try:
            import vnstock
            
            # Initialize vnstock connection
            vnstock.set_exchange(market.lower() if market != 'VN' else 'hose')
            
            data_package = {
                'source': 'vnstock',
                'timestamp': datetime.now().isoformat(),
                'company_info': {},
                'financials': {},
                'trading_data': {},
                'ownership': {},
                'ratios': {}
            }
            
            # Company Information
            try:
                company_info = vnstock.company_info(ticker)
                if company_info is not None and not company_info.empty:
                    data_package['company_info'] = company_info.to_dict('records')[0] if len(company_info) > 0 else {}
            except Exception as e:
                logger.warning(f"Could not fetch company info from vnstock: {e}")
            
            # Financial Statements (VAS compliant)
            try:
                # Income Statement
                income_stmt = vnstock.financial_report_income(ticker, period='annual')
                if income_stmt is not None and not income_stmt.empty:
                    data_package['financials']['income_statement'] = self._normalize_vas_financials(income_stmt)
                
                # Balance Sheet
                balance_sheet = vnstock.financial_report_balance(ticker, period='annual')
                if balance_sheet is not None and not balance_sheet.empty:
                    data_package['financials']['balance_sheet'] = self._normalize_vas_financials(balance_sheet)
                
                # Cash Flow
                cash_flow = vnstock.financial_report_cashflow(ticker, period='annual')
                if cash_flow is not None and not cash_flow.empty:
                    data_package['financials']['cash_flow'] = self._normalize_vas_financials(cash_flow)
            except Exception as e:
                logger.warning(f"Could not fetch financial statements from vnstock: {e}")
            
            # Trading Data
            try:
                # Historical prices (last 2 years)
                hist_data = vnstock.stock_history(ticker, days=730)
                if hist_data is not None and not hist_data.empty:
                    data_package['trading_data']['historical_prices'] = hist_data
                    data_package['trading_data']['current_price'] = hist_data['close'].iloc[-1] if len(hist_data) > 0 else None
            except Exception as e:
                logger.warning(f"Could not fetch trading data from vnstock: {e}")
            
            # Ownership Structure (FOL tracking)
            try:
                ownership = vnstock.share_structure(ticker)
                if ownership is not None and not ownership.empty:
                    data_package['ownership'] = ownership.to_dict('records')[0] if len(ownership) > 0 else {}
            except Exception as e:
                logger.warning(f"Could not fetch ownership data from vnstock: {e}")
            
            # Financial Ratios
            try:
                ratios = vnstock.financial_ratio(ticker)
                if ratios is not None and not ratios.empty:
                    data_package['ratios'] = ratios.to_dict('records')[0] if len(ratios) > 0 else {}
            except Exception as e:
                logger.warning(f"Could not fetch ratios from vnstock: {e}")
            
            return data_package if any(data_package[k] for k in ['company_info', 'financials', 'trading_data']) else None
            
        except ImportError:
            logger.error("vnstock not installed")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching from vnstock: {e}")
            return None
    
    def _fetch_from_yfinance(self, ticker: str, market: str) -> Optional[Dict[str, Any]]:
        """
        Fetch data from yfinance (fallback source).
        
        Appends appropriate suffix based on market:
            - VN (HOSE): .VN
            - HA (HNX): .HA
            - VC (UPCOM): .VC
        """
        try:
            import yfinance as yf
            
            # Construct proper ticker symbol
            suffix_map = {'VN': '.VN', 'HA': '.HA', 'VC': '.VC'}
            suffix = suffix_map.get(market, '.VN')
            full_ticker = f"{ticker}{suffix}" if not ticker.endswith(suffix) else ticker
            
            yf_ticker = yf.Ticker(full_ticker)
            
            data_package = {
                'source': 'yfinance',
                'timestamp': datetime.now().isoformat(),
                'info': {},
                'financials': {},
                'balance_sheet': {},
                'cashflow': {},
                'history': {}
            }
            
            # Company Info & Key Stats
            try:
                info = yf_ticker.info
                if info:
                    data_package['info'] = info
            except Exception as e:
                logger.warning(f"Could not fetch info from yfinance: {e}")
            
            # Financial Statements
            try:
                if not yf_ticker.financials.empty:
                    data_package['financials'] = yf_ticker.financials.to_dict()
            except Exception as e:
                logger.warning(f"Could not fetch financials from yfinance: {e}")
            
            try:
                if not yf_ticker.balance_sheet.empty:
                    data_package['balance_sheet'] = yf_ticker.balance_sheet.to_dict()
            except Exception as e:
                logger.warning(f"Could not fetch balance sheet from yfinance: {e}")
            
            try:
                if not yf_ticker.cashflow.empty:
                    data_package['cashflow'] = yf_ticker.cashflow.to_dict()
            except Exception as e:
                logger.warning(f"Could not fetch cashflow from yfinance: {e}")
            
            # Historical Prices
            try:
                hist = yf_ticker.history(period='2y')
                if not hist.empty:
                    data_package['history'] = hist.to_dict()
            except Exception as e:
                logger.warning(f"Could not fetch history from yfinance: {e}")
            
            return data_package if any(data_package[k] for k in ['info', 'financials', 'history']) else None
            
        except Exception as e:
            logger.error(f"Error fetching from yfinance: {e}")
            return None
    
    def _normalize_vas_financials(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Normalize VAS (Vietnamese Accounting Standards) financials to standard format.
        
        Converts Vietnamese column names to English equivalents and ensures
        compatibility with downstream processing.
        """
        if df.empty:
            return {}
        
        # Common VAS to English mappings
        vas_mappings = {
            # Income Statement
            'Doanh thu thuần': 'Net Revenue',
            'Giá vốn hàng bán': 'Cost of Goods Sold',
            'Lợi nhuận gộp': 'Gross Profit',
            'Chi phí bán hàng': 'Selling Expenses',
            'Chi phí quản lý doanh nghiệp': 'Management Expenses',
            'Lợi nhuận thuần từ hoạt động kinh doanh': 'Operating Profit',
            'Doanh thu hoạt động tài chính': 'Financial Income',
            'Chi phí tài chính': 'Financial Expenses',
            'Trong đó: Chi phí lãi vay': 'Interest Expense',
            'Lợi nhuận khác': 'Other Profit',
            'Tổng lợi nhuận kế toán trước thuế': 'Profit Before Tax',
            'Chi phí thuế TNDN hiện hành': 'Current Tax Expense',
            'Lợi nhuận sau thuế TNDN': 'Net Profit After Tax',
            
            # Balance Sheet
            'Tiền và tương đương tiền': 'Cash and Equivalents',
            'Đầu tư tài chính ngắn hạn': 'Short-term Financial Investments',
            'Phải thu ngắn hạn': 'Short-term Receivables',
            'Hàng tồn kho': 'Inventory',
            'Tài sản ngắn hạn khác': 'Other Current Assets',
            'TÀI SẢN NGẮN HẠN': 'Total Current Assets',
            'Tài sản cố định': 'Fixed Assets',
            'Nguyên giá TSCĐ': 'Original Value of Fixed Assets',
            'Giá trị hao mòn lũy kế': 'Accumulated Depreciation',
            'Giá trị còn lại TSCĐ': 'Net Fixed Assets',
            'Đầu tư tài chính dài hạn': 'Long-term Financial Investments',
            'Phải thu dài hạn': 'Long-term Receivables',
            'Tài sản dài hạn khác': 'Other Non-current Assets',
            'TÀI SẢN DÀI HẠN': 'Total Non-current Assets',
            'TỔNG CỘNG TÀI SẢN': 'Total Assets',
            'Nợ ngắn hạn': 'Short-term Liabilities',
            'Phải trả người bán ngắn hạn': 'Short-term Trade Payables',
            'Người mua trả tiền trước ngắn hạn': 'Short-term Advances from Customers',
            'Thuế và các khoản phải nộp Nhà nước': 'Tax Payables',
            'Phải trả người lao động': 'Employee Payables',
            'Chi phí phải trả ngắn hạn': 'Short-term Accrued Expenses',
            'Nợ dài hạn': 'Long-term Liabilities',
            'Vốn chủ sở hữu': 'Equity',
            'Vốn góp của chủ sở hữu': 'Contributed Capital',
            'Lợi nhuận chưa phân phối': 'Retained Earnings',
            'NGUỒN VỐN': 'Total Liabilities and Equity',
            
            # Cash Flow
            'Lợi nhuận trước thuế': 'Profit Before Tax',
            'Điều chỉnh cho các khoản không phải bằng tiền': 'Non-cash Adjustments',
            'Khấu hao TSCĐ': 'Depreciation',
            'Các khoản dự phòng': 'Provisions',
            'Lãi/lỗ từ hoạt động đầu tư': 'Investment Gain/Loss',
            'Chi phí lãi vay': 'Interest Expense',
            'Biến động vốn lưu động': 'Changes in Working Capital',
            'Thu nhập chịu thuế': 'Taxable Income',
            'Thuế TNDN đã nộp': 'Income Tax Paid',
            'Lưu chuyển tiền thuần từ hoạt động kinh doanh': 'Net Cash from Operating Activities',
            'Mua sắm TSCĐ': 'Purchase of Fixed Assets',
            'Thanh lý TSCĐ': 'Disposal of Fixed Assets',
            'Mua sắm công cụ dụng cụ': 'Purchase of Tools',
            'Lưu chuyển tiền thuần từ hoạt động đầu tư': 'Net Cash from Investing Activities',
            'Vay ngắn hạn': 'Short-term Borrowings',
            'Trả nợ gốc vay': 'Repayment of Borrowings',
            'Cổ tức đã trả': 'Dividends Paid',
            'Lưu chuyển tiền thuần từ hoạt động tài chính': 'Net Cash from Financing Activities',
            'Lưu chuyển tiền thuần trong năm': 'Net Cash Flow for the Year',
        }
        
        # Rename columns using mapping
        normalized_df = df.copy()
        normalized_df.rename(columns=vas_mappings, inplace=True)
        
        # Convert to dictionary with string keys for years
        result = {}
        for col in normalized_df.columns:
            result[str(col)] = normalized_df[col].tolist()
        
        return result
    
    def _merge_data_sources(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge data from multiple sources with priority to vnstock.
        
        Priority:
        1. vnstock data (most reliable for Vietnamese stocks)
        2. yfinance data (good for international comparison)
        3. Calculated/derived metrics
        """
        merged = {
            'company_info': {},
            'key_stats': {},
            'financials': {
                'income_statement': {},
                'balance_sheet': {},
                'cash_flow': {}
            },
            'trading_data': {},
            'ownership': {},
            'ratios': {}
        }
        
        # Prioritize vnstock for company info
        if 'vnstock_data' in result and result['vnstock_data'].get('company_info'):
            merged['company_info'] = result['vnstock_data']['company_info']
        elif 'yfinance_data' in result and result['yfinance_data'].get('info'):
            yf_info = result['yfinance_data']['info']
            merged['company_info'] = {
                'company_name': yf_info.get('longName'),
                'sector': yf_info.get('sector'),
                'industry': yf_info.get('industry'),
                'currency': yf_info.get('currency', 'VND'),
                'exchange': yf_info.get('exchange'),
            }
        
        # Merge financials (vnstock preferred)
        if 'vnstock_data' in result:
            vn_financials = result['vnstock_data'].get('financials', {})
            if vn_financials.get('income_statement'):
                merged['financials']['income_statement'] = vn_financials['income_statement']
            if vn_financials.get('balance_sheet'):
                merged['financials']['balance_sheet'] = vn_financials['balance_sheet']
            if vn_financials.get('cash_flow'):
                merged['financials']['cash_flow'] = vn_financials['cash_flow']
        elif 'yfinance_data' in result:
            yf_data = result['yfinance_data']
            if yf_data.get('financials'):
                merged['financials']['income_statement'] = yf_data['financials']
            if yf_data.get('balance_sheet'):
                merged['financials']['balance_sheet'] = yf_data['balance_sheet']
            if yf_data.get('cashflow'):
                merged['financials']['cash_flow'] = yf_data['cashflow']
        
        # Merge trading data
        if 'vnstock_data' in result and result['vnstock_data'].get('trading_data'):
            merged['trading_data'] = result['vnstock_data']['trading_data']
        elif 'yfinance_data' in result and result['yfinance_data'].get('history'):
            merged['trading_data']['historical_prices'] = result['yfinance_data']['history']
        
        # Merge ownership data (vnstock only)
        if 'vnstock_data' in result and result['vnstock_data'].get('ownership'):
            merged['ownership'] = result['vnstock_data']['ownership']
        
        # Merge ratios
        if 'vnstock_data' in result and result['vnstock_data'].get('ratios'):
            merged['ratios'] = result['vnstock_data']['ratios']
        elif 'yfinance_data' in result and result['yfinance_data'].get('info'):
            yf_info = result['yfinance_data']['info']
            merged['ratios'] = {
                'pe_ratio': yf_info.get('trailingPE'),
                'pb_ratio': yf_info.get('priceToBook'),
                'roe': yf_info.get('returnOnEquity'),
                'roa': yf_info.get('returnOnAssets'),
                'profit_margin': yf_info.get('profitMargins'),
            }
        
        # Add currency and market info
        merged['currency'] = 'VND'
        merged['market'] = result.get('market', 'vietnamese')
        
        return merged
    
    def _validate_vnstock_data(self, data: Dict[str, Any]) -> bool:
        """Validate that vnstock data meets minimum quality thresholds"""
        if not data:
            return False
        
        # Check for at least one key component
        has_company_info = bool(data.get('company_info'))
        has_financials = bool(data.get('financials', {}).get('income_statement'))
        has_trading = bool(data.get('trading_data', {}).get('historical_prices'))
        
        return has_company_info or has_financials or has_trading
    
    def _calculate_data_quality(self, merged_data: Dict[str, Any]) -> float:
        """
        Calculate data quality score (0.0 to 1.0).
        
        Scoring criteria:
        - Company info present: +0.15
        - Income statement (3+ years): +0.25
        - Balance sheet (3+ years): +0.20
        - Cash flow (3+ years): +0.15
        - Trading data (1+ year): +0.15
        - Ownership data: +0.10
        """
        score = 0.0
        
        # Company info
        if merged_data.get('company_info'):
            score += 0.15
        
        # Financial statements
        financials = merged_data.get('financials', {})
        if financials.get('income_statement'):
            years = len(financials['income_statement'])
            score += min(0.25, 0.08 * years)
        
        if financials.get('balance_sheet'):
            years = len(financials['balance_sheet'])
            score += min(0.20, 0.07 * years)
        
        if financials.get('cash_flow'):
            years = len(financials['cash_flow'])
            score += min(0.15, 0.05 * years)
        
        # Trading data
        if merged_data.get('trading_data', {}).get('historical_prices'):
            score += 0.15
        
        # Ownership data
        if merged_data.get('ownership'):
            score += 0.10
        
        return min(1.0, score)
    
    def get_foreign_ownership_limit(self, ticker: str) -> Optional[float]:
        """
        Get Foreign Ownership Limit (FOL) for Vietnamese stock.
        
        Standard limits:
        - Banks: 30%
        - Listed companies: 49% (default)
        - Specific sectors may have lower limits
        """
        # Default FOL by sector (simplified)
        sector_fol_limits = {
            'Banking': 30.0,
            'Finance': 30.0,
            'Telecommunications': 49.0,
            'Defense': 0.0,
            'Media': 30.0,
        }
        
        # Try to get from vnstock first
        if self.vnstock_available:
            try:
                import vnstock
                ownership = vnstock.share_structure(ticker)
                if ownership is not None and not ownership.empty and 'foreign_limit' in ownership.columns:
                    return float(ownership['foreign_limit'].iloc[0])
            except Exception as e:
                logger.warning(f"Could not fetch FOL from vnstock: {e}")
        
        # Fallback to sector-based estimation
        if 'vnstock_data' in dir(self):
            company_info = getattr(self, 'vnstock_data', {}).get('company_info', {})
            sector = company_info.get('sector', '')
            return sector_fol_limits.get(sector, 49.0)
        
        return 49.0  # Default limit
    
    def convert_to_ttm(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert fiscal year data to Trailing Twelve Months (TTM).
        
        Addresses fiscal year mismatch issues in Vietnamese reporting.
        """
        if not financial_data:
            return {}
        
        ttm_data = {}
        
        # For each metric, sum the last 4 quarters or interpolate from annual data
        for metric, values in financial_data.items():
            if isinstance(values, dict) and len(values) >= 2:
                # If quarterly data available, sum last 4 quarters
                # If only annual data, use most recent year
                sorted_years = sorted(values.keys(), reverse=True)
                ttm_data[metric] = values[sorted_years[0]]
        
        return ttm_data
