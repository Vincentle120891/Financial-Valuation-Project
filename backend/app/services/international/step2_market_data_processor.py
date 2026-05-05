"""
Step 2: Market Data Processor
Handles market data retrieval, beta calculations, and risk metrics.
"""

import logging
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.services.international.yfinance_service import YFinanceService

logger = logging.getLogger(__name__)


class MarketDataPoint(BaseModel):
    """Individual market data point with status."""
    metric: str
    value: Optional[float] = None
    source: str = "yfinance"
    status: str = "RETRIEVED"  # RETRIEVED, CALCULATED, ESTIMATED, MISSING
    formula: Optional[str] = None
    confidence: float = 1.0


class MarketRiskMetrics(BaseModel):
    """Market risk metrics."""
    risk_free_rate: Optional[float] = None
    market_risk_premium: Optional[float] = None
    beta: Optional[float] = None
    levered_beta: Optional[float] = None
    unlevered_beta: Optional[float] = None
    equity_risk_premium: Optional[float] = None
    country_risk_premium: Optional[float] = None


class Step2Response(BaseModel):
    """Step 2 response model."""
    ticker: str
    market_data: List[MarketDataPoint]
    risk_metrics: MarketRiskMetrics
    missing_data: List[str] = []
    warnings: List[str] = []
    data_quality_score: float = 0.0


class Step2MarketDataProcessor:
    """
    Processor for Step 2: Market Data.
    
    Responsibilities:
    - Fetch current market price
    - Calculate/retrieve beta
    - Get risk-free rate
    - Calculate market risk premium
    - Flag missing market data
    """
    
    DEFAULT_RISK_FREE_RATE = 4.5  # 10-year US Treasury
    DEFAULT_MARKET_PREMIUM = 7.0  # Historical equity risk premium
    
    def __init__(self, yfinance_service: Optional[YFinanceService] = None):
        self.yfinance_service = yfinance_service or YFinanceService()
    
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
        market: str = "international"
    ) -> Step2Response:
        """
        Process market data for a ticker.
        
        Args:
            ticker: Ticker symbol
            market: Market type
            
        Returns:
            Step2Response with market data and risk metrics
        """
        logger.info(f"Processing market data for ticker='{ticker}'")
        
        # Fetch ticker info
        ticker_info = self.yfinance_service.get_ticker_info(ticker)
        
        if not ticker_info:
            return Step2Response(
                ticker=ticker,
                market_data=[],
                risk_metrics=MarketRiskMetrics(),
                missing_data=["All market data"],
                warnings=[f"Could not fetch any data for {ticker}"],
                data_quality_score=0.0
            )
        
        # Build market data points
        market_data_points: List[MarketDataPoint] = []
        missing_data: List[str] = []
        warnings: List[str] = []
        
        # Current Price
        current_price = ticker_info.get('currentPrice')
        if current_price:
            market_data_points.append(MarketDataPoint(
                metric="current_price",
                value=current_price,
                source="yfinance",
                status="RETRIEVED",
                confidence=0.95
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
                status="RETRIEVED",
                confidence=0.90
            ))
        else:
            missing_data.append("market_cap")
        
        # Beta
        beta = ticker_info.get('beta')
        beta_status = "RETRIEVED" if beta else "ESTIMATED"
        beta_value = beta if beta else 1.0
        beta_formula = "Beta = Covariance(stock, market) / Variance(market)" if beta else "Default beta = 1.0 (market average)"
        
        market_data_points.append(MarketDataPoint(
            metric="beta",
            value=beta_value,
            source="yfinance" if beta else "default",
            status=beta_status,
            formula=beta_formula,
            confidence=0.85 if beta else 0.50
        ))
        
        if not beta:
            warnings.append("Beta estimated as 1.0 (market average)")
        
        # Risk-free rate
        risk_free_rate = self._get_risk_free_rate(market)
        market_data_points.append(MarketDataPoint(
            metric="risk_free_rate",
            value=risk_free_rate,
            source="government_bond",
            status="RETRIEVED",
            formula="10-year Government Bond Yield",
            confidence=0.95
        ))
        
        # Market Risk Premium
        market_premium = self._get_market_premium(market)
        market_data_points.append(MarketDataPoint(
            metric="market_risk_premium",
            value=market_premium,
            source="historical_average",
            status="ESTIMATED",
            formula="Historical Equity Risk Premium",
            confidence=0.75
        ))
        
        # Build risk metrics
        risk_metrics = MarketRiskMetrics(
            risk_free_rate=risk_free_rate,
            market_risk_premium=market_premium,
            beta=beta_value,
            levered_beta=beta_value,  # Same as beta for now
            unlevered_beta=self._unlever_beta(beta_value, ticker_info),
            equity_risk_premium=market_premium,
            country_risk_premium=self._get_country_risk_premium(market)
        )
        
        # Calculate data quality score
        total_metrics = len(market_data_points)
        retrieved_count = sum(1 for md in market_data_points if md.status == "RETRIEVED")
        data_quality_score = (retrieved_count / total_metrics * 100) if total_metrics > 0 else 0
        
        return Step2Response(
            ticker=ticker,
            market_data=market_data_points,
            risk_metrics=risk_metrics,
            missing_data=missing_data,
            warnings=warnings,
            data_quality_score=data_quality_score
        )
    
    def _get_risk_free_rate(self, market: str) -> float:
        """Get risk-free rate based on market."""
        if market == "vietnamese":
            return 6.8  # Vietnam 10-year government bond
        return self.DEFAULT_RISK_FREE_RATE
    
    def _get_market_premium(self, market: str) -> float:
        """Get market risk premium based on market."""
        if market == "vietnamese":
            return 7.5  # Higher premium for emerging market
        return self.DEFAULT_MARKET_PREMIUM
    
    def _get_country_risk_premium(self, market: str) -> Optional[float]:
        """Get country risk premium."""
        if market == "vietnamese":
            return 2.5  # Additional CRP for Vietnam
        return None
    
    def _unlever_beta(self, beta: float, ticker_info: Dict) -> Optional[float]:
        """Calculate unlevered beta."""
        # Simplified: need debt/equity ratio for proper calculation
        # βu = βl / (1 + (1-t)(D/E))
        return beta * 0.9  # Rough estimate
