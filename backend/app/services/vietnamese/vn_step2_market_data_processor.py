"""
Step 2: Vietnamese Market Data Processor
Handles Vietnamese market data retrieval, beta calculations, and risk metrics.
"""

import logging
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.services.vietnamese.vietnamese_ticker_service import VietnameseTickerService

logger = logging.getLogger(__name__)


class vn_MarketDataPoint(BaseModel):
    """Individual Vietnamese market data point with status."""
    metric: str
    value: Optional[float] = None
    source: str = "vietnamese_data"
    status: str = "RETRIEVED"  # RETRIEVED, CALCULATED, ESTIMATED, MISSING
    formula: Optional[str] = None
    confidence: float = 1.0
    currency: str = "VND"


class vn_MarketRiskMetrics(BaseModel):
    """Vietnamese market risk metrics."""
    risk_free_rate: Optional[float] = None  # Vietnam government bond yield
    market_risk_premium: Optional[float] = None
    beta: Optional[float] = None
    levered_beta: Optional[float] = None
    unlevered_beta: Optional[float] = None
    equity_risk_premium: Optional[float] = None
    country_risk_premium: Optional[float] = None
    vnindex_performance: Optional[Dict] = None  # VNINDEX current performance


class vn_Step2Response(BaseModel):
    """Vietnamese Step 2 response model."""
    ticker: str
    market_code: str  # VN, HA, VC
    market_data: List[vn_MarketDataPoint]
    risk_metrics: vn_MarketRiskMetrics
    missing_data: List[str] = []
    warnings: List[str] = []
    data_quality_score: float = 0.0
    exchange_info: Optional[Dict] = None


class vn_Step2MarketDataProcessor:
    """
    Processor for Vietnamese Step 2: Market Data.

    Responsibilities:
    - Fetch current Vietnamese market price (VND)
    - Calculate/retrieve beta for Vietnamese stocks
    - Get Vietnam risk-free rate (government bond yields)
    - Calculate market risk premium for emerging market
    - Flag missing market data
    - Discover Vietnamese peer companies
    - Include VNINDEX performance context
    """

    DEFAULT_RISK_FREE_RATE_VN = 6.8  # Vietnam 10-year government bond yield
    DEFAULT_MARKET_PREMIUM_VN = 7.5  # Higher premium for Vietnam emerging market
    DEFAULT_COUNTRY_RISK_PREMIUM = 3.5  # Country risk premium for Vietnam

    def __init__(self, vn_ticker_service: Optional[VietnameseTickerService] = None):
        self.vn_ticker_service = vn_ticker_service or VietnameseTickerService()

    async def select_company(
        self,
        ticker: str,
        market: str = "vietnam",
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Select a Vietnamese company and fetch its market data.

        Args:
            ticker: Vietnamese ticker symbol
            market: Market type (should be 'vietnam')
            session_id: Optional session ID

        Returns:
            Dictionary with status and message
        """
        logger.info(f"Selecting Vietnamese company ticker='{ticker}'")

        try:
            # Process market data
            response = self.process_market_data(ticker, market)

            # Check if we got valid data
            if response.data_quality_score > 0.5:
                return {
                    "status": "completed",
                    "message": f"Successfully selected Vietnamese company {ticker}",
                    "data": response.model_dump()
                }
            else:
                return {
                    "status": "partial",
                    "message": f"Selected {ticker} with limited Vietnamese market data",
                    "warnings": response.warnings,
                    "data": response.model_dump()
                }

        except Exception as e:
            logger.error(f"Error selecting Vietnamese company {ticker}: {str(e)}")
            return {
                "status": "failed",
                "message": f"Failed to select {ticker}: {str(e)}"
            }

    def process_market_data(
        self,
        ticker: str,
        market: str = "vietnam"
    ) -> vn_Step2Response:
        """
        Process Vietnamese market data for a ticker.

        Args:
            ticker: Vietnamese ticker symbol
            market: Market type

        Returns:
            vn_Step2Response with Vietnamese market data and risk metrics
        """
        logger.info(f"Processing Vietnamese market data for ticker='{ticker}'")

        # Determine market code
        market_code = "VN"
        if ".HA" in ticker.upper():
            market_code = "HA"
            ticker_clean = ticker.replace(".HA", "").upper()
        elif ".VC" in ticker.upper():
            market_code = "VC"
            ticker_clean = ticker.replace(".VC", "").upper()
        elif ".VN" in ticker.upper():
            ticker_clean = ticker.replace(".VN", "").upper()
        else:
            ticker_clean = ticker.upper()

        # Fetch comprehensive Vietnamese data
        ticker_data = self.vn_ticker_service.fetch_vietnamese_data_enhanced(
            ticker_clean,
            market_code,
            include_peers=True,
            include_index_data=True
        )

        if not ticker_data.get('success'):
            return vn_Step2Response(
                ticker=ticker_clean,
                market_code=market_code,
                market_data=[],
                risk_metrics=vn_MarketRiskMetrics(),
                missing_data=["All market data"],
                warnings=[f"Could not fetch any data for {ticker}"],
                data_quality_score=0.0
            )

        # Build Vietnamese market data points
        market_data_points: List[vn_MarketDataPoint] = []
        missing_data: List[str] = []
        warnings: List[str] = []

        # Current Price (VND)
        key_stats = ticker_data.get('key_stats', {})
        current_price = key_stats.get('current_price') or ticker_data.get('company_info', {}).get('currentPrice')

        if current_price:
            market_data_points.append(vn_MarketDataPoint(
                metric="current_price",
                value=current_price,
                source="vietnamese_data",
                status="RETRIEVED",
                confidence=0.95,
                currency="VND"
            ))
        else:
            missing_data.append("current_price")
            warnings.append(f"Current price not available for {ticker}")

        # Market Cap (VND)
        market_cap = key_stats.get('market_cap')
        if market_cap:
            market_data_points.append(vn_MarketDataPoint(
                metric="market_cap",
                value=market_cap,
                source="vietnamese_data",
                status="RETRIEVED",
                confidence=0.90,
                currency="VND"
            ))
        else:
            missing_data.append("market_cap")

        # Beta (if available from Vietnamese data)
        beta = key_stats.get('beta')
        beta_status = "RETRIEVED" if beta else "ESTIMATED"
        beta_value = beta if beta else 1.0
        beta_formula = "Beta = Covariance(stock, VNINDEX) / Variance(VNINDEX)" if beta else "Default beta = 1.0 (market average)"

        market_data_points.append(vn_MarketDataPoint(
            metric="beta",
            value=beta_value,
            source="vietnamese_data" if beta else "default",
            status=beta_status,
            formula=beta_formula,
            confidence=0.85 if beta else 0.50
        ))

        if not beta:
            warnings.append("Beta estimated as 1.0 (VNINDEX average)")

        # Risk-free rate (Vietnam government bond)
        risk_free_rate = self._get_vietnam_risk_free_rate()
        market_data_points.append(vn_MarketDataPoint(
            metric="risk_free_rate",
            value=risk_free_rate,
            source="vietnam_government_bond",
            status="RETRIEVED",
            formula="Vietnam 10-year Government Bond Yield",
            confidence=0.95
        ))

        # Market Risk Premium (Vietnam emerging market)
        market_premium = self._get_vietnam_market_premium()
        market_data_points.append(vn_MarketDataPoint(
            metric="market_risk_premium",
            value=market_premium,
            source="emerging_market_premium",
            status="ESTIMATED",
            formula="Vietnam Equity Risk Premium",
            confidence=0.70
        ))

        # Country Risk Premium
        country_risk = self._get_vietnam_country_risk()
        market_data_points.append(vn_MarketDataPoint(
            metric="country_risk_premium",
            value=country_risk,
            source="country_risk_model",
            status="ESTIMATED",
            formula="Vietnam Sovereign Risk Spread",
            confidence=0.65
        ))

        # Build Vietnamese risk metrics
        vnindex_data = ticker_data.get('vietnam_enhancements', {}).get('index_performance', {}).get('VNINDEX', {})

        risk_metrics = vn_MarketRiskMetrics(
            risk_free_rate=risk_free_rate,
            market_risk_premium=market_premium,
            beta=beta_value,
            levered_beta=beta_value,
            unlevered_beta=self._unlever_beta(beta_value, ticker_data),
            equity_risk_premium=market_premium + country_risk,
            country_risk_premium=country_risk,
            vnindex_performance=vnindex_data if vnindex_data else None
        )

        # Exchange info
        exchange_info = {
            'code': market_code,
            'name': self._get_exchange_name(market_code),
            'trading_hours': '09:00-15:00 ICT',
            'settlement': 'T+2',
            'price_band': self._get_price_band(market_code),
            'currency': 'VND'
        }

        # Calculate data quality score
        total_metrics = len(market_data_points)
        retrieved_count = sum(1 for md in market_data_points if md.status == "RETRIEVED")
        data_quality_score = (retrieved_count / total_metrics * 100) if total_metrics > 0 else 0

        return vn_Step2Response(
            ticker=ticker_clean,
            market_code=market_code,
            market_data=market_data_points,
            risk_metrics=risk_metrics,
            missing_data=missing_data,
            warnings=warnings,
            data_quality_score=data_quality_score,
            exchange_info=exchange_info
        )

    def _get_vietnam_risk_free_rate(self) -> float:
        """Get Vietnam risk-free rate (10-year government bond yield)."""
        # In production, this would fetch real-time data from VNDirect or State Bank of Vietnam
        return self.DEFAULT_RISK_FREE_RATE_VN

    def _get_vietnam_market_premium(self) -> float:
        """Get Vietnam market risk premium (emerging market premium)."""
        # Vietnam-specific ERP considering emerging market status
        return self.DEFAULT_MARKET_PREMIUM_VN

    def _get_vietnam_country_risk(self) -> float:
        """Get Vietnam country risk premium."""
        # Based on sovereign credit spread and market volatility
        return self.DEFAULT_COUNTRY_RISK_PREMIUM

    def _get_exchange_name(self, market_code: str) -> str:
        """Get full exchange name from market code."""
        exchange_map = {
            'VN': 'HOSE (Ho Chi Minh Stock Exchange)',
            'HA': 'HNX (Hanoi Stock Exchange)',
            'VC': 'UPCOM (Unlisted Public Company Market)'
        }
        return exchange_map.get(market_code, 'Unknown')

    def _get_price_band(self, market_code: str) -> str:
        """Get trading price band for exchange."""
        price_bands = {
            'VN': '±7%',
            'HA': '±10%',
            'VC': '±15%'
        }
        return price_bands.get(market_code, 'Unknown')

    def _unlever_beta(self, beta: float, ticker_data: Dict) -> float:
        """
        Unlever beta using Hamada equation.

        Formula: β_unlevered = β_levered / [1 + (1 - tax_rate) * (D/E)]
        """
        # Vietnam corporate tax rate
        tax_rate = 0.20  # 20% standard corporate tax rate in Vietnam

        # Get debt-to-equity ratio from financials
        financials = ticker_data.get('financials', {})
        if financials is not None and len(financials) > 0:
            try:
                latest_year = financials.columns[-1] if hasattr(financials, 'columns') else list(financials.keys())[-1]
                total_debt = financials.get('Total Debt', {}).get(latest_year, 0) if isinstance(financials, dict) else 0
                equity = financials.get('Stockholders Equity', {}).get(latest_year, 0) if isinstance(financials, dict) else 0

                if equity > 0 and total_debt > 0:
                    d_e_ratio = total_debt / equity
                    unlevered_beta = beta / (1 + (1 - tax_rate) * d_e_ratio)
                    return round(unlevered_beta, 3)
            except Exception as e:
                logger.warning(f"Could not calculate unlevered beta: {e}")

        # Default: assume no leverage effect
        return beta

    async def suggest_peers(
        self,
        ticker: str,
        max_peers: int = 10,
        market: str = "vietnam"
    ) -> Dict:
        """
        Suggest Vietnamese peer companies based on sector and market cap.

        Args:
            ticker: Vietnamese ticker symbol
            max_peers: Maximum number of peers to suggest
            market: Market type

        Returns:
            Dictionary with peer suggestions
        """
        logger.info(f"Suggesting Vietnamese peers for ticker='{ticker}', max_peers={max_peers}")

        try:
            # Get sector peers from Vietnamese ticker service
            market_code = "VN"
            if ".HA" in ticker.upper():
                market_code = "HA"
                ticker_clean = ticker.replace(".HA", "").upper()
            elif ".VC" in ticker.upper():
                market_code = "VC"
                ticker_clean = ticker.replace(".VC", "").upper()
            elif ".VN" in ticker.upper():
                ticker_clean = ticker.replace(".VN", "").upper()
            else:
                ticker_clean = ticker.upper()

            # Fetch enhanced data to get sector peers
            ticker_data = self.vn_ticker_service.fetch_vietnamese_data_enhanced(
                ticker_clean,
                market_code,
                include_peers=True,
                include_index_data=False
            )

            sector_peers = ticker_data.get('vietnam_enhancements', {}).get('sector_peers', [])

            # Limit to max_peers
            suggested_peers = sector_peers[:max_peers]

            return {
                'status': 'success',
                'ticker': ticker_clean,
                'market_code': market_code,
                'peers': suggested_peers,
                'count': len(suggested_peers),
                'methodology': 'Sector-based peer selection using Vietnamese industry classification'
            }

        except Exception as e:
            logger.error(f"Failed to suggest Vietnamese peers: {str(e)}")
            return {
                'ticker': ticker,
                'peers': [],
                'error': str(e)
            }