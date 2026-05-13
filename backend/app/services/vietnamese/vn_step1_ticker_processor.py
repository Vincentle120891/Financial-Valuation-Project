"""
Step 1: Vietnamese Ticker Selection Processor
Handles Vietnamese ticker validation, exchange resolution, and company info fetching.
"""

import logging
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel

from app.services.vietnamese.vietnamese_ticker_service import VietnameseTickerService

logger = logging.getLogger(__name__)


class vn_TickerInfo(BaseModel):
    """Detailed Vietnamese ticker information."""
    symbol: str
    name: str
    exchange: str  # HOSE, HNX, UPCOM
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    currency: str = "VND"
    is_valid: bool = True
    error_message: Optional[str] = None
    market_code: Optional[str] = None  # VN, HA, VC
    foreign_ownership_limit: Optional[float] = None
    listing_date: Optional[str] = None


class vn_Step1Response(BaseModel):
    """Vietnamese Step 1 response model."""
    tickers: List[vn_TickerInfo]
    valid_count: int
    invalid_count: int
    warnings: List[str] = []
    market_summary: Optional[Dict] = None


class vn_Step1TickerProcessor:
    """
    Processor for Vietnamese Step 1: Ticker Selection.

    Responsibilities:
    - Validate Vietnamese ticker symbols
    - Resolve exchanges (HOSE, HNX, UPCOM)
    - Fetch basic company information with Vietnam-specific data
    - Flag invalid tickers
    - Handle .VN, .HA, .VC suffixes
    """

    def __init__(self, vn_ticker_service: Optional[VietnameseTickerService] = None):
        self.vn_ticker_service = vn_ticker_service or VietnameseTickerService()

    def process_ticker_selection(
        self,
        tickers: List[str],
        market: str = "vietnam"
    ) -> vn_Step1Response:
        """
        Process multiple Vietnamese tickers for validation and info retrieval.

        Args:
            tickers: List of Vietnamese ticker symbols
            market: Market type (should be 'vietnam')

        Returns:
            vn_Step1Response with validated tickers and warnings
        """
        logger.info(f"Processing {len(tickers)} Vietnamese tickers")

        ticker_infos: List[vn_TickerInfo] = []
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
                logger.error(f"Error processing Vietnamese ticker '{ticker}': {str(e)}")
                invalid_count += 1
                ticker_infos.append(vn_TickerInfo(
                    symbol=ticker,
                    name="Unknown",
                    exchange="UNKNOWN",
                    is_valid=False,
                    error_message=str(e)
                ))
                warnings.append(f"Failed to process '{ticker}': {str(e)}")

        # Get market summary for Vietnamese market
        market_summary = self.vn_ticker_service.get_vietnam_market_overview()

        return vn_Step1Response(
            tickers=ticker_infos,
            valid_count=valid_count,
            invalid_count=invalid_count,
            warnings=warnings,
            market_summary=market_summary
        )

    def _validate_and_fetch_ticker(
        self,
        ticker: str,
        market: str
    ) -> vn_TickerInfo:
        """
        Validate a single Vietnamese ticker and fetch its information.

        Args:
            ticker: Vietnamese ticker symbol
            market: Market type

        Returns:
            vn_TickerInfo with validation results
        """
        # Determine market code and format ticker
        market_code = "VN"  # Default to HOSE

        # Check if ticker already has suffix
        if ".VN" in ticker.upper():
            market_code = "VN"
            ticker_clean = ticker.replace(".VN", "").upper()
        elif ".HA" in ticker.upper():
            market_code = "HA"
            ticker_clean = ticker.replace(".HA", "").upper()
        elif ".VC" in ticker.upper():
            market_code = "VC"
            ticker_clean = ticker.replace(".VC", "").upper()
        else:
            # Auto-detect based on known listings or default to VN
            ticker_clean = ticker.upper()
            market_code = self._detect_market_code(ticker_clean)
            ticker = f"{ticker_clean}.{market_code}"

        # Fetch data using Vietnamese ticker service
        ticker_data = self.vn_ticker_service.fetch_vietnamese_data(ticker_clean, market_code)

        if not ticker_data.get('success'):
            return vn_TickerInfo(
                symbol=ticker,
                name="Unknown",
                exchange="UNKNOWN",
                market_code=market_code,
                is_valid=False,
                error_message=ticker_data.get('error', 'No data returned')
            )

        # Extract company info
        company_info = ticker_data.get('company_info', {})
        key_stats = ticker_data.get('key_stats', {})

        # Validate required fields
        current_price = key_stats.get('current_price') or company_info.get('currentPrice')
        if not current_price:
            return vn_TickerInfo(
                symbol=ticker,
                name=company_info.get('longName', 'Unknown'),
                exchange=self._get_exchange_name(market_code),
                market_code=market_code,
                sector=company_info.get('sector'),
                industry=company_info.get('industry'),
                market_cap=key_stats.get('market_cap'),
                currency='VND',
                is_valid=False,
                error_message="Missing current price data"
            )

        # Get foreign ownership limit if available
        fol_info = ticker_data.get('vietnam_enhancements', {}).get('foreign_ownership_status', {})
        fol_limit = fol_info.get('fol_limit')

        return vn_TickerInfo(
            symbol=ticker_clean,
            name=company_info.get('longName', ticker_clean),
            exchange=self._get_exchange_name(market_code),
            market_code=market_code,
            sector=company_info.get('sector'),
            industry=company_info.get('industry'),
            market_cap=key_stats.get('market_cap'),
            currency='VND',
            foreign_ownership_limit=fol_limit,
            listing_date=company_info.get('listing_date'),
            is_valid=True
        )

    def _detect_market_code(self, ticker: str) -> str:
        """
        Detect market code based on ticker patterns or known listings.

        Args:
            ticker: Clean ticker symbol

        Returns:
            Market code (VN, HA, or VC)
        """
        # Known HNX tickers (typically end with specific patterns or are known)
        hnx_tickers = ['PVT', 'SHS', 'VCS', 'TVC', 'SCI']
        if ticker in hnx_tickers:
            return 'HA'

        # Known UPCOM tickers
        upcom_tickers = ['DC4', 'NBC', 'TVC']
        if ticker in upcom_tickers:
            return 'VC'

        # Default to HOSE for most common tickers
        return 'VN'

    def _get_exchange_name(self, market_code: str) -> str:
        """Get full exchange name from market code."""
        exchange_map = {
            'VN': 'HOSE (Ho Chi Minh)',
            'HA': 'HNX (Hanoi)',
            'VC': 'UPCOM'
        }
        return exchange_map.get(market_code, 'Unknown')

    async def search_tickers(
        self,
        query: str,
        market: str = "vietnam"
    ) -> List[Dict]:
        """
        Search for Vietnamese tickers based on query string.

        Args:
            query: Search query (company name or partial ticker)
            market: Market type (should be 'vietnam')

        Returns:
            List of matching ticker dictionaries with Vietnam-specific fields
            FIX Issue #2: Returns 'ticker' and 'company_name' fields to match CompanySearchResult schema
        """
        logger.info(f"Searching Vietnamese tickers for query='{query}'")

        # Use yfinance search through Vietnamese ticker service
        search_results = self.vn_ticker_service.search_tickers(query)

        results = []
        for result in search_results:
            # Determine market code from symbol
            symbol = result.get('symbol', '')
            market_code = 'VN'
            if '.HA' in symbol:
                market_code = 'HA'
            elif '.VC' in symbol:
                market_code = 'VC'

            results.append({
                'ticker': symbol.replace('.VN', '').replace('.HA', '').replace('.VC', ''),  # FIX Issue #2: Use 'ticker' instead of 'symbol'
                'company_name': result.get('shortname', result.get('symbol', '')),  # FIX Issue #2: Use 'company_name' instead of 'name'
                'exchange': self._get_exchange_name(market_code),
                'sector': result.get('sector'),
                'industry': result.get('industry'),
                'market_cap': result.get('marketCap'),
                'market': 'vietnamese',
                'market_code': market_code
            })

        return results

    def suggest_similar_tickers(
        self,
        query: str,
        limit: int = 5
    ) -> List[vn_TickerInfo]:
        """
        Suggest similar Vietnamese tickers based on search query.

        Args:
            query: Search query (company name or partial ticker)
            limit: Maximum number of suggestions

        Returns:
            List of suggested Vietnamese tickers
        """
        logger.info(f"Suggesting Vietnamese tickers for query='{query}'")

        # Use yfinance search
        search_results = self.vn_ticker_service.search_tickers(query)

        suggestions = []
        for result in search_results[:limit]:
            symbol = result.get('symbol', '')
            market_code = 'VN'
            if '.HA' in symbol:
                market_code = 'HA'
            elif '.VC' in symbol:
                market_code = 'VC'

            clean_symbol = symbol.replace('.VN', '').replace('.HA', '').replace('.VC', '')

            suggestions.append(vn_TickerInfo(
                symbol=clean_symbol,
                name=result.get('shortname', result.get('symbol', '')),
                exchange=self._get_exchange_name(market_code),
                market_code=market_code,
                sector=result.get('sector'),
                industry=result.get('industry'),
                is_valid=True
            ))

        return suggestions

    def get_sector_tickers(self, sector: str) -> List[vn_TickerInfo]:
        """
        Get all tickers in a specific Vietnamese sector.

        Args:
            sector: Sector name (e.g., 'Banking', 'Real Estate')

        Returns:
            List of tickers in that sector
        """
        logger.info(f"Getting tickers for Vietnamese sector: {sector}")

        sector_tickers = self.vn_ticker_service.VIETNAM_SECTORS.get(sector, [])

        results = []
        for ticker in sector_tickers:
            try:
                info = self._validate_and_fetch_ticker(ticker, 'vietnamese')
                if info.is_valid:
                    results.append(info)
            except Exception as e:
                logger.warning(f"Could not fetch info for {ticker}: {e}")

        return results