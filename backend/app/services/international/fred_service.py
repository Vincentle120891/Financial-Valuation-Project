"""
FRED (Federal Reserve Economic Data) Service for retrieving US Treasury yields and economic indicators.
Provides risk-free rates, market risk premiums, and other macroeconomic data for valuation models.
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fredapi import Fred
from fastapi import Request

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

    @staticmethod
    def get_api_key(request: Optional[Request] = None) -> Optional[str]:
        """
        Get API key with priority: request header > environment variable.

        Args:
            request: FastAPI request object (optional)

        Returns:
            API key from request header if available, else from environment, else None
        """
        # Priority 1: Check request state (from header)
        if request:
            api_keys = getattr(request.state, 'api_keys', {})
            request_key = api_keys.get('fred')
            if request_key:
                logger.debug("Using FRED API key from request header")
                return request_key

        # Priority 2: Fallback to environment variable
        env_key = os.getenv('FRED_API_KEY')
        if env_key and env_key != 'your_fred_api_key_here':
            logger.debug("Using FRED API key from environment variable")
            return env_key

        # No key available
        logger.warning("FRED API key not configured (neither in request header nor environment)")
        return None

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
        Calculate Equity Risk Premium (ERP) from S&P 500 historical returns vs risk-free rate.
        
        ERP = Average(S&P 500 annual returns over 10 years) - Average(10Y Treasury yield over 10 years)
        
        Uses FRED series:
        - SP500: S&P 500 Index (monthly)
        - DGS10: 10-Year Treasury Constant Maturity Rate
        """
        if not self.fred:
            return None

        try:
            # Fetch S&P 500 monthly index (last 10 years)
            sp500 = self.fred.get_series('SP500')
            treasury = self.fred.get_series('DGS10')

            if sp500 is None or treasury is None:
                return None

            # Use last 10 years of data
            cutoff = datetime.now() - timedelta(days=365 * 10)
            sp500_monthly = sp500[sp500.index >= cutoff].dropna()
            treasury_monthly = treasury[treasury.index >= cutoff].dropna()

            if len(sp500_monthly) < 12 or len(treasury_monthly) < 12:
                return None

            # Calculate annual S&P 500 returns from monthly prices
            sp500_annual_returns = []
            sp500_monthly_values = sp500_monthly.resample('ME').last().dropna()
            for i in range(12, len(sp500_monthly_values)):
                prev = sp500_monthly_values.iloc[i - 12]
                curr = sp500_monthly_values.iloc[i]
                if prev > 0:
                    sp500_annual_returns.append((curr / prev) - 1)

            # Average 10Y Treasury yield
            avg_risk_free = treasury_monthly.mean() / 100  # Convert from % to decimal

            if not sp500_annual_returns or avg_risk_free is None:
                return None

            avg_market_return = sum(sp500_annual_returns) / len(sp500_annual_returns)
            erp = avg_market_return - avg_risk_free

            # Clamp to reasonable range (3% - 12%)
            erp = max(0.03, min(0.12, erp))

            logger.info(f"Calculated ERP from FRED: {erp:.2%} (S&P500 avg return: {avg_market_return:.2%}, avg Rf: {avg_risk_free:.2%})")

            return {
                'value': round(erp * 100, 2),  # Return as percentage
                'unit': '%',
                'source': 'FRED - Calculated from S&P 500 vs 10Y Treasury (10-year history)',
                'series_id': 'SP500 / DGS10',
                'last_updated': sp500_monthly.index[-1].isoformat(),
                'status': 'CALCULATED'
            }
        except Exception as e:
            logger.error(f"Error calculating ERP from FRED: {str(e)}")

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


def get_fred_service(request: Optional[Request] = None) -> FREDService:
    """Get or create FRED service instance with API key from request or environment.
    
    Args:
        request: FastAPI request object (optional). If provided, API key will be
                 extracted from request headers with priority over environment variables.
    
    Returns:
        FREDService instance initialized with appropriate API key
    """
    global _fred_service_instance
    
    # Get API key with priority: request header > environment variable
    api_key = FREDService.get_api_key(request)
    
    # Create new instance with the resolved API key
    # Note: We create a new instance per request to ensure correct API key usage
    # This is necessary because API keys vary per user
    return FREDService(api_key=api_key)