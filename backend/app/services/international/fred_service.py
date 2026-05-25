"""
FRED (Federal Reserve Economic Data) Service for retrieving US Treasury yields and economic indicators.
Provides risk-free rates, market risk premiums, and other macroeconomic data for valuation models.
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fredapi import Fred

logger = logging.getLogger(__name__)


class FREDService:
    """Service for fetching economic data from FRED API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('FRED_API_KEY')
        self.fred = None
        
        if self.api_key and self.api_key != 'your_fred_api_key_here':
            try:
                self.fred = Fred(api_key=self.api_key)
                logger.info("FRED service initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize FRED service: {str(e)}")
        else:
            logger.warning("FRED API key not configured. Risk-free rate data will be unavailable.")
    
    def get_10year_treasury_yield(self) -> Optional[Dict[str, Any]]:
        """
        Fetch current 10-year US Treasury yield (standard risk-free rate proxy).
        Series ID: DGS10
        """
        if not self.fred:
            return None
        
        try:
            # Fetch latest 10-year Treasury constant maturity rate
            data = self.fred.get_series('DGS10')
            
            if data is not None and not data.empty:
                latest_value = data.iloc[-1]
                latest_date = data.index[-1]
                
                # Filter out NaN values
                if not isinstance(latest_value, (int, float)) or latest_value != latest_value:  # NaN check
                    # Try to get last non-NaN value
                    valid_data = data.dropna()
                    if not valid_data.empty:
                        latest_value = valid_data.iloc[-1]
                        latest_date = valid_data.index[-1]
                    else:
                        return None
                
                logger.info(f"Fetched 10Y Treasury Yield: {latest_value}% ({latest_date})")
                
                return {
                    'value': float(latest_value),
                    'unit': '%',
                    'source': 'FRED - Federal Reserve Economic Data',
                    'series_id': 'DGS10',
                    'last_updated': latest_date.isoformat(),
                    'status': 'RETRIEVED'
                }
        except Exception as e:
            logger.error(f"Error fetching 10Y Treasury yield from FRED: {str(e)}")
        
        return None
    
    def get_market_risk_premium(self) -> Optional[Dict[str, Any]]:
        """
        Fetch estimated Equity Risk Premium (ERP).
        Note: FRED doesn't directly provide ERP, so we use historical averages or 
        implied ERP from market data. This is a placeholder for future implementation.
        
        For now, returns None to indicate data must be estimated or user-provided.
        """
        # TODO: Implement implied ERP calculation from S&P 500 data
        # Alternative: Use Damodaran's published ERP data via web scraping
        logger.info("Market Risk Premium estimation requires external data source (e.g., Damodaran)")
        return None
    
    def get_inflation_rate(self) -> Optional[Dict[str, Any]]:
        """
        Fetch current US inflation rate (CPI year-over-year change).
        Series ID: CPIAUCSL (Consumer Price Index)
        """
        if not self.fred:
            return None
        
        try:
            cpi_data = self.fred.get_series('CPIAUCSL')
            
            if cpi_data is not None and len(cpi_data) >= 12:
                # Calculate YoY inflation rate
                latest_cpi = cpi_data.iloc[-1]
                year_ago_cpi = cpi_data.iloc[-12]
                
                if year_ago_cpi > 0:
                    inflation_rate = ((latest_cpi / year_ago_cpi) - 1) * 100
                    
                    return {
                        'value': round(inflation_rate, 2),
                        'unit': '%',
                        'source': 'FRED - CPI Data',
                        'series_id': 'CPIAUCSL',
                        'last_updated': cpi_data.index[-1].isoformat(),
                        'status': 'CALCULATED'
                    }
        except Exception as e:
            logger.error(f"Error calculating inflation rate from FRED: {str(e)}")
        
        return None
    
    def get_gdp_growth_rate(self) -> Optional[Dict[str, Any]]:
        """
        Fetch US GDP growth rate (real GDP, seasonally adjusted annual rate).
        Series ID: GDPC1
        """
        if not self.fred:
            return None
        
        try:
            gdp_data = self.fred.get_series('GDPC1')
            
            if gdp_data is not None and len(gdp_data) >= 4:
                latest_gdp = gdp_data.iloc[-1]
                year_ago_gdp = gdp_data.iloc[-4]
                
                if year_ago_gdp > 0:
                    gdp_growth = ((latest_gdp / year_ago_gdp) - 1) * 100
                    
                    return {
                        'value': round(gdp_growth, 2),
                        'unit': '%',
                        'source': 'FRED - GDP Data',
                        'series_id': 'GDPC1',
                        'last_updated': gdp_data.index[-1].isoformat(),
                        'status': 'CALCULATED'
                    }
        except Exception as e:
            logger.error(f"Error calculating GDP growth from FRED: {str(e)}")
        
        return None
    
    def get_all_macro_indicators(self) -> Dict[str, Optional[Dict[str, Any]]]:
        """Fetch all available macroeconomic indicators in one call."""
        return {
            'risk_free_rate': self.get_10year_treasury_yield(),
            'market_risk_premium': self.get_market_risk_premium(),
            'inflation_rate': self.get_inflation_rate(),
            'gdp_growth_rate': self.get_gdp_growth_rate()
        }


# Singleton instance for reuse
_fred_service_instance: Optional[FREDService] = None


def get_fred_service() -> FREDService:
    """Get or create singleton FRED service instance."""
    global _fred_service_instance
    if _fred_service_instance is None:
        _fred_service_instance = FREDService()
    return _fred_service_instance
