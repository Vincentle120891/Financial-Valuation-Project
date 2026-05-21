"""
Step 2: Market Data Processor - UNIFIED SCHEMA VERSION
Handles market data retrieval, beta calculations, and risk metrics.
Outputs unified schema compatible with both International and Vietnamese markets.
"""

import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from app.services.international.yfinance_service import YFinanceService
from app.services.international.peer_discovery_service import PeerDiscoveryService, PeerDiscoveryRequest
from app.api.schemas.unified_step_schemas import (
    UnifiedStep2Response,
    MarketDataPoint,
    MarketRiskMetrics,
    ExchangeInfo,
    DataField,
    DataStatus
)

logger = logging.getLogger(__name__)


class MarketDataPointLegacy(BaseModel):
    """Individual market data point with status (legacy format for internal use)."""
    metric: str
    value: Optional[float] = None
    source: str = "yfinance"
    status: str = "RETRIEVED"  # RETRIEVED, CALCULATED, ESTIMATED, MISSING
    formula: Optional[str] = None
    confidence: float = 1.0


class MarketRiskMetricsLegacy(BaseModel):
    """Market risk metrics (legacy format for internal use)."""
    risk_free_rate: Optional[float] = None
    market_risk_premium: Optional[float] = None
    beta: Optional[float] = None
    levered_beta: Optional[float] = None
    unlevered_beta: Optional[float] = None
    equity_risk_premium: Optional[float] = None
    country_risk_premium: Optional[float] = None


class Step2MarketDataProcessor:
    """
    Processor for Step 2: Market Data.

    Responsibilities:
    - Fetch current market price
    - Calculate/retrieve beta
    - Get risk-free rate
    - Calculate market risk premium
    - Flag missing market data
    - Discover peer companies based on industry and market cap
    """

    DEFAULT_RISK_FREE_RATE = 4.5  # 10-year US Treasury
    DEFAULT_MARKET_PREMIUM = 7.0  # Historical equity risk premium

    def __init__(self, yfinance_service: Optional[YFinanceService] = None):
        self.yfinance_service = yfinance_service or YFinanceService()
        self.peer_discovery_service = PeerDiscoveryService(self.yfinance_service)

    async def select_company(
        self,
        ticker: str,
        market: str = "international",
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Select a company and fetch its market data.

        Args:
            ticker: Ticker symbol
            market: Market type
            session_id: Optional session ID

        Returns:
            Dictionary with status and message
        """
        logger.info(f"Selecting company ticker='{ticker}', market='{market}'")

        try:
            # Process market data
            response = self.process_market_data(ticker, market)

            # Check if we got valid data
            if response.data_quality_score > 0.5:
                return {
                    "status": "completed",
                    "message": f"Successfully selected {ticker}",
                    "data": response.model_dump()
                }
            else:
                return {
                    "status": "partial",
                    "message": f"Selected {ticker} with limited data",
                    "warnings": response.warnings,
                    "data": response.model_dump()
                }

        except Exception as e:
            logger.error(f"Error selecting company {ticker}: {str(e)}")
            return {
                "status": "failed",
                "message": f"Failed to select {ticker}: {str(e)}"
            }

    def process_market_data(
        self,
        ticker: str,
        market: str = "international",
        session_id: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> UnifiedStep2Response:
        """
        Process market data for a ticker using unified schema.

        Args:
            ticker: Ticker symbol
            market: Market type (international or vietnam)
            session_id: Optional session ID
            company_name: Optional company name

        Returns:
            UnifiedStep2Response with market data and risk metrics
        """
        logger.info(f"Processing market data for ticker='{ticker}', market='{market}'")

        # Fetch ticker info
        ticker_info = self.yfinance_service.get_ticker_info(ticker)

        if not ticker_info:
            return UnifiedStep2Response(
                status="failed",
                session_id=session_id or "",
                ticker=ticker,
                market=market,
                company_name=company_name or ticker,
                confirmed=False,
                market_data=[],
                risk_metrics=None,
                missing_data=["All market data"],
                warnings=[f"Could not fetch any data for {ticker}"],
                data_quality_score=0.0,
                message=f"Failed to fetch data for {ticker}"
            )

        # Build market data points using unified schema
        market_data_points: List[MarketDataPoint] = []
        missing_data: List[str] = []
        warnings: List[str] = []

        # Get currency from ticker info
        currency = ticker_info.get('currency', 'USD')
        if market == "vietnam" or market == "vietnam":
            currency = 'VND'

        # Current Price
        current_price = ticker_info.get('currentPrice')
        if current_price:
            market_data_points.append(MarketDataPoint(
                metric="current_price",
                value=current_price,
                source="yfinance",
                status=DataStatus.RETRIEVED,
                confidence_score=95.0,
                currency=currency,
                unit=currency
            ))
        else:
            missing_data.append("current_price")
            warnings.append("Current price not available")

        # Market Cap
        market_cap = ticker_info.get('marketCap')
        if market_cap:
            market_data_points.append(MarketDataPoint(
                metric="market_cap",
                value=market_cap,
                source="yfinance",
                status=DataStatus.RETRIEVED,
                confidence_score=90.0,
                currency=currency,
                unit=currency
            ))
        else:
            missing_data.append("market_cap")

        # Beta
        beta = ticker_info.get('beta')
        beta_status = DataStatus.RETRIEVED if beta else DataStatus.ESTIMATED
        beta_value = beta if beta else 1.0
        beta_formula = "Beta = Covariance(stock, market) / Variance(market)" if beta else "Default beta = 1.0 (market average)"

        market_data_points.append(MarketDataPoint(
            metric="beta",
            value=beta_value,
            source="yfinance" if beta else "default",
            status=beta_status,
            formula=beta_formula,
            confidence_score=85.0 if beta else 50.0,
            currency=None,
            unit=None
        ))

        if not beta:
            warnings.append("Beta estimated as 1.0 (market average)")

        # Risk-free rate
        risk_free_rate = self._get_risk_free_rate(market)
        market_data_points.append(MarketDataPoint(
            metric="risk_free_rate",
            value=risk_free_rate,
            source="government_bond",
            status=DataStatus.RETRIEVED,
            formula="10-year Government Bond Yield",
            confidence_score=95.0,
            currency=None,
            unit="%"
        ))

        # Market Risk Premium
        market_premium = self._get_market_premium(market)
        market_data_points.append(MarketDataPoint(
            metric="market_risk_premium",
            value=market_premium,
            source="historical_average",
            status=DataStatus.ESTIMATED,
            formula="Historical Equity Risk Premium",
            confidence_score=75.0,
            currency=None,
            unit="%"
        ))

        # Country Risk Premium (if applicable)
        country_risk = self._get_country_risk_premium(market)
        if country_risk:
            market_data_points.append(MarketDataPoint(
                metric="country_risk_premium",
                value=country_risk,
                source="country_risk_model",
                status=DataStatus.ESTIMATED,
                formula="Sovereign Risk Spread",
                confidence_score=65.0,
                currency=None,
                unit="%"
            ))

        # Build risk metrics using DataField wrappers
        unlevered_beta_value = self._unlever_beta(beta_value, ticker_info)

        risk_metrics = MarketRiskMetrics(
            risk_free_rate=DataField(
                value=risk_free_rate,
                status=DataStatus.RETRIEVED,
                source="government_bond",
                formula="10-year Government Bond Yield",
                confidence_score=95.0,
                unit="%",
                currency=None
            ),
            market_risk_premium=DataField(
                value=market_premium,
                status=DataStatus.ESTIMATED,
                source="historical_average",
                formula="Historical Equity Risk Premium",
                confidence_score=75.0,
                unit="%",
                currency=None
            ),
            beta=DataField(
                value=beta_value,
                status=beta_status,
                source="yfinance" if beta else "default",
                formula=beta_formula,
                confidence_score=85.0 if beta else 50.0,
                currency=None,
                unit=None
            ),
            levered_beta=DataField(
                value=beta_value,
                status=beta_status,
                source="yfinance" if beta else "default",
                formula=beta_formula,
                confidence_score=85.0 if beta else 50.0,
                currency=None,
                unit=None
            ),
            unlevered_beta=DataField(
                value=unlevered_beta_value,
                status=DataStatus.CALCULATED,
                source="calculated",
                formula="βu = βl / (1 + (1-t)(D/E))",
                confidence_score=70.0,
                currency=None,
                unit=None
            ),
            equity_risk_premium=DataField(
                value=market_premium + (country_risk or 0),
                status=DataStatus.ESTIMATED,
                source="calculated",
                formula="ERP + CRP",
                confidence_score=70.0,
                unit="%",
                currency=None
            ),
            country_risk_premium=DataField(
                value=country_risk,
                status=DataStatus.ESTIMATED if country_risk else DataStatus.MISSING,
                source="country_risk_model",
                formula="Sovereign Risk Spread",
                confidence_score=65.0 if country_risk else None,
                unit="%",
                currency=None
            ) if country_risk else None
        )

        # Calculate data quality score
        total_metrics = len(market_data_points)
        retrieved_count = sum(1 for md in market_data_points if md.status == DataStatus.RETRIEVED)
        data_quality_score = (retrieved_count / total_metrics * 100) if total_metrics > 0 else 0

        # Determine confirmation status
        confirmed = data_quality_score >= 50

        # Get company name
        final_company_name = company_name or ticker_info.get('longName', ticker_info.get('shortName', ticker))

        return UnifiedStep2Response(
            status="completed" if confirmed else "partial",
            session_id=session_id or "",
            ticker=ticker,
            market=market,
            company_name=final_company_name,
            confirmed=confirmed,
            market_data=market_data_points,
            risk_metrics=risk_metrics,
            missing_data=missing_data,
            warnings=warnings,
            data_quality_score=data_quality_score,
            message=f"Successfully processed market data for {final_company_name}"
        )

    def _get_risk_free_rate(self, market: str) -> float:
        """Get risk-free rate based on market."""
        if market == "vietnam":
            return 6.8  # Vietnam 10-year government bond
        return self.DEFAULT_RISK_FREE_RATE

    def _get_market_premium(self, market: str) -> float:
        """Get market risk premium based on market."""
        if market == "vietnam":
            return 7.5  # Higher premium for emerging market
        return self.DEFAULT_MARKET_PREMIUM

    def _get_country_risk_premium(self, market: str) -> Optional[float]:
        """Get country risk premium."""
        if market == "vietnam":
            return 2.5  # Additional CRP for Vietnam
        return None

    def _unlever_beta(self, beta: float, ticker_info: Dict) -> Optional[float]:
        """Calculate unlevered beta."""
        # Simplified: need debt/equity ratio for proper calculation
        # βu = βl / (1 + (1-t)(D/E))
        return beta * 0.9  # Rough estimate

    async def validate_manual_peers(
        self,
        tickers: List[str],
        market: str = "international"
    ) -> Dict:
        """
        Validate manually entered peer tickers and return their details.

        Args:
            tickers: List of ticker symbols to validate
            market: Market type

        Returns:
            Dictionary with validated peers and any errors
        """
        logger.info(f"Validating {len(tickers)} manual peer tickers for market='{market}'")

        validated_peers = []
        errors = []

        for ticker in tickers:
            try:
                # Get ticker info
                ticker_info = self.yfinance_service.get_ticker_info(ticker)

                if not ticker_info:
                    errors.append({
                        "ticker": ticker,
                        "error": "Could not fetch data for this ticker"
                    })
                    continue

                # Check if ticker has required data
                if not ticker_info.get('currentPrice') or ticker_info.get('currentPrice') <= 0:
                    errors.append({
                        "ticker": ticker,
                        "error": "Invalid or missing current price"
                    })
                    continue

                if not ticker_info.get('marketCap') or ticker_info.get('marketCap') <= 0:
                    errors.append({
                        "ticker": ticker,
                        "error": "Invalid or missing market cap"
                    })
                    continue

                # Check exchange filtering for international market
                exchange = ticker_info.get('exchange', '')
                if market == "international":
                    # Block OTC and problematic exchanges
                    if exchange in ["PNK", "GRE", "BTS", "NCY", "NGM"]:
                        errors.append({
                            "ticker": ticker,
                            "error": f"Exchange {exchange} not allowed for international market (OTC/foreign)"
                        })
                        continue

                # Add to validated peers
                validated_peers.append({
                    "symbol": ticker,
                    "name": ticker_info.get('longName', ticker_info.get('shortName', ticker)),
                    "sector": ticker_info.get('sector'),
                    "industry": ticker_info.get('industry'),
                    "market_cap": ticker_info.get('marketCap'),
                    "current_price": ticker_info.get('currentPrice'),
                    "exchange": exchange,
                    "score": 50,  # Default score for manual entries
                    "match_reasons": ["Manually selected"]
                })

            except Exception as e:
                errors.append({
                    "ticker": ticker,
                    "error": str(e)
                })
                logger.error(f"Error validating ticker {ticker}: {str(e)}")

        return {
            "status": "success" if validated_peers else "partial",
            "validated_peers": validated_peers,
            "errors": errors,
            "total_validated": len(validated_peers),
            "total_errors": len(errors)
        }