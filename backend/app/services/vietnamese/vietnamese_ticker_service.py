"""
Vietnamese Ticker Service - Specialized for Vietnam Market
Extended functionality for Vietnamese stocks with local data sources
"""

import yfinance as yf
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import logging
from app.services.international.international_ticker_service import InternationalTickerService

logger = logging.getLogger(__name__)


class VietnameseTickerService(InternationalTickerService):
    """
    Specialized service for Vietnamese tickers with enhanced features:
    - Multiple Vietnamese exchanges (HOSE, HNX, UPCOM)
    - Foreign Ownership Limit (FOL) tracking
    - Trading status monitoring
    - Local market holidays
    - VND currency handling
    - Integration with local data sources (future enhancement)
    
    Yahoo Finance suffixes:
    - HOSE: .VN (e.g., VNM.VN, VIC.VN)
    - HNX: .HA (e.g., PVT.HA)
    - UPCOM: .VC (e.g., DC4.VC)
    """
    
    # Vietnamese market holidays (approximate, should be maintained in database)
    VIETNAM_HOLIDAYS_2024 = [
        '2024-01-01',  # New Year
        '2024-02-08',  # Tet Eve
        '2024-02-09',  # Tet
        '2024-02-10',  # Tet
        '2024-02-11',  # Tet
        '2024-02-12',  # Tet
        '2024-02-13',  # Tet
        '2024-02-14',  # Tet
        '2024-02-15',  # Tet
        '2024-03-28',  # Hung Kings Commemoration
        '2024-04-30',  # Reunification Day
        '2024-05-01',  # Labor Day
        '2024-09-02',  # National Day
        '2024-09-03',  # National Day
    ]
    
    # Major Vietnamese stock indices
    VIETNAM_INDICES = {
        'VNINDEX': '^VNINDEX',
        'HNXINDEX': '^HNXINDEX',
        'UPCOMINDEX': '^UPCOMINDEX',
        'VN30': '^VN30',
        'HNX30': '^HNX30',
    }
    
    # Sector classifications for Vietnamese market
    VIETNAM_SECTORS = {
        'Banking': ['VCB', 'BID', 'CTG', 'TCB', 'MBB', 'ACB', 'STB', 'TPB', 'VPB', 'HDB'],
        'Real Estate': ['VIC', 'VHM', 'VRE', 'NVDR', 'KDH', 'NLG', 'DXG', 'DIG'],
        'Consumer Staples': ['VNM', 'MSN', 'SAB', 'QNS', 'GCT'],
        'Materials': ['HPG', 'HSG', 'NKG', 'ASM'],
        'Energy': ['GAS', 'POW', 'PVS', 'PVX'],
        'Technology': ['FPT', 'CMG', 'SAP'],
        'Utilities': ['PC1', 'REE', 'NT2'],
        'Healthcare': ['DHG', 'TRA', 'IMP'],
        'Telecommunications': ['VGI', 'CTR'],
    }
    
    def __init__(self):
        super().__init__()
        self.vietnam_cache = {}
    
    def fetch_vietnamese_data_enhanced(
        self, 
        ticker: str, 
        market_code: str = "VN",
        include_peers: bool = True,
        include_index_data: bool = True
    ) -> Dict[str, Any]:
        """
        Enhanced fetch for Vietnamese tickers with additional local context
        
        Args:
            ticker: Vietnamese ticker symbol
            market_code: VN (HOSE), HA (HNX), VC (UPCOM)
            include_peers: Whether to include peer comparison data
            include_index_data: Whether to include VNINDEX data
            
        Returns:
            Comprehensive data package for Vietnamese stock
        """
        logger.info(f"Enhanced fetch for Vietnamese ticker: {ticker}.{market_code}")
        
        # Base fetch from parent class
        data = self.fetch_vietnamese_data(ticker, market_code)
        
        if not data['success']:
            return data
        
        # Add Vietnamese-specific enhancements
        data['vietnam_enhancements'] = {
            'sector_peers': self._get_vietnam_sector_peers(ticker) if include_peers else [],
            'index_performance': self._fetch_vietnam_index_data() if include_index_data else {},
            'trading_calendar': self._get_trading_calendar_info(),
            'regulatory_notes': self._get_regulatory_notes(ticker),
            'foreign_ownership_status': self._check_foreign_ownership_status(ticker),
        }
        
        # Calculate Vietnam-specific metrics
        data['vietnam_metrics'] = self._calculate_vietnam_metrics(data)
        
        # Add data quality assessment for Vietnamese market
        data['vietnam_data_quality'] = self._assess_vietnam_data_quality(data)
        
        return data
    
    def _get_vietnam_sector_peers(self, ticker: str) -> List[Dict[str, str]]:
        """Get peer companies in the same Vietnamese sector"""
        sector = None
        for sector_name, tickers in self.VIETNAM_SECTORS.items():
            if ticker.upper() in tickers:
                sector = sector_name
                peers = [t for t in tickers if t != ticker.upper()]
                break
        
        if not sector:
            return []
        
        return [
            {'ticker': p, 'market': 'VN', 'sector': sector}
            for p in peers[:5]  # Top 5 peers
        ]
    
    def _fetch_vietnam_index_data(self) -> Dict[str, Any]:
        """Fetch Vietnamese market index data"""
        index_data = {}
        
        for index_name, index_ticker in self.VIETNAM_INDICES.items():
            try:
                idx = yf.Ticker(index_ticker)
                info = idx.info
                
                if info:
                    index_data[index_name] = {
                        'current_value': info.get('regularMarketPrice'),
                        'change': info.get('regularMarketChange'),
                        'change_percent': info.get('regularMarketChangePercent'),
                        'previous_close': info.get('previousClose'),
                        'open': info.get('regularMarketOpen'),
                        'day_high': info.get('dayHigh'),
                        'day_low': info.get('dayLow'),
                        '52_week_high': info.get('fiftyTwoWeekHigh'),
                        '52_week_low': info.get('fiftyTwoWeekLow'),
                        'volume': info.get('regularMarketVolume'),
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                logger.warning(f"Could not fetch {index_name}: {e}")
        
        return index_data
    
    def _get_trading_calendar_info(self) -> Dict[str, Any]:
        """Get Vietnamese trading calendar information"""
        today = datetime.now().date()
        
        # Check if today is a holiday
        is_holiday = today.strftime('%Y-%m-%d') in self.VIETNAM_HOLIDAYS_2024
        
        # Check if weekend
        is_weekend = today.weekday() >= 5
        
        # Next trading day calculation (simplified)
        next_trading_day = today + timedelta(days=1)
        while next_trading_day.weekday() >= 5 or \
              next_trading_day.strftime('%Y-%m-%d') in self.VIETNAM_HOLIDAYS_2024:
            next_trading_day += timedelta(days=1)
        
        return {
            'is_trading_day': not (is_holiday or is_weekend),
            'is_holiday': is_holiday,
            'is_weekend': is_weekend,
            'next_trading_day': next_trading_day.isoformat(),
            'trading_hours': '09:00-15:00 ICT',
            'timezone': 'Asia/Ho_Chi_Minh',
            'settlement_cycle': 'T+2',
            'upcoming_holidays': self._get_upcoming_holidays()
        }
    
    def _get_upcoming_holidays(self, count: int = 5) -> List[str]:
        """Get upcoming Vietnamese market holidays"""
        today = datetime.now().date()
        upcoming = []
        
        for holiday_str in self.VIETNAM_HOLIDAYS_2024:
            holiday_date = datetime.strptime(holiday_str, '%Y-%m-%d').date()
            if holiday_date >= today:
                upcoming.append(holiday_str)
                if len(upcoming) >= count:
                    break
        
        return upcoming
    
    def _get_regulatory_notes(self, ticker: str) -> List[str]:
        """Get regulatory notes for Vietnamese stock"""
        notes = []
        
        fol_limit = self._get_fol_limit(ticker)
        if fol_limit:
            notes.append(f"Foreign Ownership Limit: {fol_limit}%")
        
        # Check if banking sector (stricter regulations)
        for sector, tickers in self.VIETNAM_SECTORS.items():
            if ticker.upper() in tickers and sector == 'Banking':
                notes.append("Banking sector: Subject to State Bank of Vietnam regulations")
                notes.append("Foreign ownership limited to 30% for most banks")
                break
        
        # General notes
        notes.append("Trading band: ±7% (HOSE), ±10% (HNX), ±15% (UPCOM)")
        notes.append("Settlement: T+2")
        notes.append("Lot size: 100 shares")
        
        return notes
    
    def _check_foreign_ownership_status(self, ticker: str) -> Dict[str, Any]:
        """Check foreign ownership status for Vietnamese stock"""
        fol_limit = self._get_fol_limit(ticker)
        
        # In production, this would query real-time FOL data
        # For now, return structure with placeholder
        return {
            'fol_limit': fol_limit,
            'current_fol': None,  # Would come from real-time data
            'room_remaining': None,  # Would calculate from limit - current
            'status': 'Unknown' if fol_limit is None else 'Within Limit',
            'note': 'Real-time FOL data requires integration with VSD/CDC'
        }
    
    def _calculate_vietnam_metrics(self, data: Dict) -> Dict[str, Any]:
        """Calculate Vietnam-specific metrics"""
        metrics = {}
        
        # Currency conversion info
        metrics['currency'] = 'VND'
        metrics['usd_vnd_rate'] = 24500  # Approximate, would use real-time rate
        
        # Convert key metrics to USD for international comparison
        key_stats = data.get('key_stats', {})
        if key_stats.get('market_cap'):
            metrics['market_cap_vnd'] = key_stats['market_cap']
            metrics['market_cap_usd'] = key_stats['market_cap'] / metrics['usd_vnd_rate']
        
        if key_stats.get('enterprise_value'):
            metrics['ev_vnd'] = key_stats['enterprise_value']
            metrics['ev_usd'] = key_stats['enterprise_value'] / metrics['usd_vnd_rate']
        
        # Liquidity metrics specific to Vietnam
        if data.get('historical_prices') is not None:
            prices = data['historical_prices']
            avg_volume_30d = prices['Volume'].tail(30).mean() if len(prices) >= 30 else prices['Volume'].mean()
            metrics['avg_daily_volume_30d'] = avg_volume_30d
            metrics['liquidity_rating'] = self._assess_liquidity(avg_volume_30d, key_stats.get('market_cap', 0))
        
        return metrics
    
    def _assess_liquidity(self, avg_volume: float, market_cap: float) -> str:
        """Assess liquidity rating for Vietnamese stock"""
        if market_cap == 0:
            return 'Unknown'
        
        # Turnover ratio approximation
        turnover_ratio = (avg_volume * 25000) / market_cap  # Assuming 25k VND avg price
        
        if turnover_ratio > 0.05:
            return 'High'
        elif turnover_ratio > 0.02:
            return 'Medium'
        else:
            return 'Low'
    
    def _assess_vietnam_data_quality(self, data: Dict) -> Dict[str, Any]:
        """Comprehensive data quality assessment for Vietnamese stocks"""
        quality_checks = data.get('data_quality_checks', {})
        
        # Additional Vietnam-specific checks
        vietnam_checks = {
            'has_vietnam_metadata': 'vietnam_metadata' in data,
            'has_sector_classification': data.get('company_info', {}).get('sector') is not None,
            'has_exchange_info': data.get('company_info', {}).get('exchange') is not None,
            'has_currency': data.get('currency') == 'VND',
            'financials_in_vnd': self._check_currency_consistency(data.get('financials')),
        }
        
        # Combine with base checks
        all_checks = {**quality_checks, **vietnam_checks}
        
        # Calculate overall score
        total = len(all_checks)
        passed = sum(1 for v in all_checks.values() if v is True)
        
        return {
            'individual_checks': all_checks,
            'score': passed / total,
            'rating': 'EXCELLENT' if passed / total >= 0.9 else \
                      'GOOD' if passed / total >= 0.75 else \
                      'FAIR' if passed / total >= 0.6 else 'POOR',
            'missing_data': [k for k, v in all_checks.items() if v is False],
            'recommendations': self._generate_data_recommendations(all_checks)
        }
    
    def _check_currency_consistency(self, df: Optional[pd.DataFrame]) -> bool:
        """Check if financial data appears to be in VND (large numbers)"""
        if df is None or df.empty:
            return False
        
        # VND values are typically very large (billions/trillions)
        # This is a heuristic check
        try:
            first_col = df.iloc[:, 0]
            numeric_vals = pd.to_numeric(first_col, errors='coerce')
            avg_val = numeric_vals.abs().mean()
            
            # VND values should be in billions at minimum
            return avg_val > 1e9 if not pd.isna(avg_val) else False
        except Exception:
            return False
    
    def _generate_data_recommendations(self, checks: Dict[str, bool]) -> List[str]:
        """Generate recommendations for improving data quality"""
        recommendations = []
        
        if not checks.get('has_financials'):
            recommendations.append("Financial statements not available - consider manual entry")
        
        if not checks.get('has_balance_sheet'):
            recommendations.append("Balance sheet data missing - critical for valuation")
        
        if not checks.get('analyst_estimates'):
            recommendations.append("No analyst estimates - rely on historical trends and management guidance")
        
        if not checks.get('has_price_data'):
            recommendations.append("Historical price data unavailable - beta calculation not possible")
        
        if not checks.get('financials_in_vnd'):
            recommendations.append("Verify currency denomination of financial data")
        
        return recommendations
    
    def get_vietnam_market_overview(self) -> Dict[str, Any]:
        """Get overview of Vietnamese stock market"""
        return {
            'markets': [
                {
                    'code': 'VN',
                    'name': 'Ho Chi Minh Stock Exchange (HOSE)',
                    'established': 2000,
                    'listed_companies': '~750',
                    'market_cap': '~$250B USD',
                    'main_index': 'VNINDEX',
                    'trading_hours': '09:00-15:00 ICT',
                    'settlement': 'T+2',
                    'price_band': '±7%',
                },
                {
                    'code': 'HA',
                    'name': 'Hanoi Stock Exchange (HNX)',
                    'established': 2005,
                    'listed_companies': '~350',
                    'market_cap': '~$30B USD',
                    'main_index': 'HNXINDEX',
                    'trading_hours': '09:00-15:00 ICT',
                    'settlement': 'T+2',
                    'price_band': '±10%',
                },
                {
                    'code': 'VC',
                    'name': 'Unlisted Public Company Market (UPCOM)',
                    'established': 2009,
                    'listed_companies': '~800',
                    'market_cap': '~$20B USD',
                    'main_index': 'UPCOMINDEX',
                    'trading_hours': '09:00-15:00 ICT',
                    'settlement': 'T+2',
                    'price_band': '±15%',
                }
            ],
            'regulator': 'State Securities Commission (SSC)',
            'depository': 'Vietnam Securities Depository (VSD)',
            'currency': 'Vietnamese Dong (VND)',
            'timezone': 'ICT (UTC+7)',
            'foreign_ownership_limits': {
                'banks': '30%',
                'securities_companies': '49%',
                'other_sectors': '49% (default)',
                'conditional_sectors': 'Varies by industry'
            }
        }
    
    def search_vietnamese_stocks(self, query: str) -> List[Dict[str, str]]:
        """
        Search Vietnamese stocks by name or ticker
        
        Args:
            query: Search term (ticker or company name)
            
        Returns:
            List of matching stocks
        """
        all_stocks = self.list_available_vietnamese_stocks()
        query_lower = query.lower()
        
        matches = []
        for stock in all_stocks:
            if (query_lower in stock['ticker'].lower() or 
                query_lower in stock['name'].lower()):
                matches.append(stock)
        
        return matches
