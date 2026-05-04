"""
Step 1: Ticker Selection Processor
Handles ticker validation, exchange resolution, and company info fetching.
"""

import logging
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel

from app.services.international.yfinance_service import YFinanceService

logger = logging.getLogger(__name__)


class TickerInfo(BaseModel):
    """Detailed ticker information."""
    symbol: str
    name: str
    exchange: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    currency: str = "USD"
    is_valid: bool = True
    error_message: Optional[str] = None


class Step1Response(BaseModel):
    """Step 1 response model."""
    tickers: List[TickerInfo]
    valid_count: int
    invalid_count: int
    warnings: List[str] = []


class Step1TickerProcessor:
    """
    Processor for Step 1: Ticker Selection.
    
    Responsibilities:
    - Validate ticker symbols
    - Resolve exchanges
    - Fetch basic company information
    - Flag invalid tickers
    """
    
    def __init__(self, yfinance_service: Optional[YFinanceService] = None):
        self.yfinance_service = yfinance_service or YFinanceService()
    
    def process_ticker_selection(
        self,
        tickers: List[str],
        market: str = "international"
    ) -> Step1Response:
        """
        Process multiple tickers for validation and info retrieval.
        
        Args:
            tickers: List of ticker symbols
            market: Market type (international or vietnamese)
            
        Returns:
            Step1Response with validated tickers and warnings
        """
        logger.info(f"Processing {len(tickers)} tickers for market='{market}'")
        
        ticker_infos: List[TickerInfo] = []
        warnings: List[str] = []
        valid_count = 0
        invalid_count = 0
        
        for ticker in tickers:
            try:
                info = self._validate_and_fetch_ticker(ticker, market)
                ticker_infos.append(info)
                
                if info.is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1
                    warnings.append(f"Invalid ticker '{ticker}': {info.error_message}")
                    
            except Exception as e:
                logger.error(f"Error processing ticker '{ticker}': {str(e)}")
                invalid_count += 1
                ticker_infos.append(TickerInfo(
                    symbol=ticker,
                    name="Unknown",
                    exchange="UNKNOWN",
                    is_valid=False,
                    error_message=str(e)
                ))
                warnings.append(f"Failed to process '{ticker}': {str(e)}")
        
        return Step1Response(
            tickers=ticker_infos,
            valid_count=valid_count,
            invalid_count=invalid_count,
            warnings=warnings
        )
    
    def _validate_and_fetch_ticker(
        self,
        ticker: str,
        market: str
    ) -> TickerInfo:
        """
        Validate a single ticker and fetch its information.
        
        Args:
            ticker: Ticker symbol
            market: Market type
            
        Returns:
            TickerInfo with validation results
        """
        # Format ticker for Vietnamese market
        if market == "vietnamese":
            if not ticker.endswith(".VN"):
                ticker = f"{ticker}.VN"
        
        # Fetch data from yfinance
        ticker_data = self.yfinance_service.get_ticker_info(ticker)
        
        if not ticker_data:
            return TickerInfo(
                symbol=ticker,
                name="Unknown",
                exchange="UNKNOWN",
                is_valid=False,
                error_message="No data returned from yfinance"
            )
        
        # Validate required fields
        if not ticker_data.get('currentPrice'):
            return TickerInfo(
                symbol=ticker,
                name=ticker_data.get('longName', 'Unknown'),
                exchange=ticker_data.get('exchange', 'UNKNOWN'),
                sector=ticker_data.get('sector'),
                industry=ticker_data.get('industry'),
                market_cap=ticker_data.get('marketCap'),
                currency=ticker_data.get('currency', 'USD'),
                is_valid=False,
                error_message="Missing current price data"
            )
        
        return TickerInfo(
            symbol=ticker,
            name=ticker_data.get('longName', ticker),
            exchange=ticker_data.get('exchange', 'UNKNOWN'),
            sector=ticker_data.get('sector'),
            industry=ticker_data.get('industry'),
            market_cap=ticker_data.get('marketCap'),
            currency=ticker_data.get('currency', 'USD'),
            is_valid=True
        )
    
    def suggest_similar_tickers(
        self,
        query: str,
        limit: int = 5
    ) -> List[TickerInfo]:
        """
        Suggest similar tickers based on search query.
        
        Args:
            query: Search query (company name or partial ticker)
            limit: Maximum number of suggestions
            
        Returns:
            List of suggested tickers
        """
        logger.info(f"Suggesting tickers for query='{query}'")
        
        # Use yfinance search
        search_results = self.yfinance_service.search_tickers(query)
        
        suggestions = []
        for result in search_results[:limit]:
            suggestions.append(TickerInfo(
                symbol=result.get('symbol', ''),
                name=result.get('shortname', result.get('symbol', '')),
                exchange=result.get('exchDisp', 'UNKNOWN'),
                sector=result.get('sector'),
                industry=result.get('industry'),
                is_valid=True
            ))
        
        return suggestions
