"""
Shared Context Service - Centralized data fetching for common company information

This service provides unified access to shared company context (Steps 1-3) that is
accessible by all valuation methods (DCF, DuPont, Comps) without duplication.

Features:
- Single source of truth for company overview, market data, historical financials
- Method-agnostic data retrieval
- Caching to avoid redundant API calls
- Consistent data format across all valuation methods
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd

from .yfinance_service import YFinanceService
from .alphavantage_service import AlphaVantageService

logger = logging.getLogger(__name__)


class SharedContextData:
    """Container for shared company context data"""

    def __init__(self):
        self.ticker: str = ""
        self.company_name: str = ""
        self.market: str = ""
        self.sector: str = ""
        self.industry: str = ""
        self.description: str = ""

        # Market Data (Step 2)
        self.current_price: Optional[float] = None
        self.market_cap: Optional[float] = None
        self.shares_outstanding: Optional[float] = None
        self.beta: Optional[float] = None
        self.pe_ratio: Optional[float] = None
        self.currency: str = "USD"

        # Historical Financials (Step 3)
        self.income_statement: Optional[pd.DataFrame] = None
        self.balance_sheet: Optional[pd.DataFrame] = None
        self.cash_flow: Optional[pd.DataFrame] = None

        # Peer Selection
        self.peer_tickers: List[str] = []
        self.peer_data: Dict[str, Any] = {}

        # Metadata
        self.last_updated: Optional[datetime] = None
        self.data_sources: Dict[str, str] = {}

    def _update_from_overview(self, overview_data: Dict[str, Any]):
        """Update context from overview data"""
        if not overview_data:
            return
        self.company_name = overview_data.get("company_name", self.company_name)
        self.sector = overview_data.get("sector", self.sector)
        self.industry = overview_data.get("industry", self.industry)
        self.description = overview_data.get("description", self.description)
        self.current_price = overview_data.get("current_price", self.current_price)
        self.market_cap = overview_data.get("market_cap", self.market_cap)
        self.shares_outstanding = overview_data.get("shares_outstanding", self.shares_outstanding)
        self.beta = overview_data.get("beta", self.beta)
        self.pe_ratio = overview_data.get("pe_ratio", self.pe_ratio)
        self.currency = overview_data.get("currency", self.currency)

    def _update_from_financials(self, financials_data: Dict[str, pd.DataFrame]):
        """Update context from financials data"""
        if not financials_data:
            return
        self.income_statement = financials_data.get("income_statement", self.income_statement)
        self.balance_sheet = financials_data.get("balance_sheet", self.balance_sheet)
        self.cash_flow = financials_data.get("cash_flow", self.cash_flow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for session storage"""
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "market": self.market,
            "sector": self.sector,
            "industry": self.industry,
            "description": self.description,
            "market_data": {
                "current_price": self.current_price,
                "market_cap": self.market_cap,
                "shares_outstanding": self.shares_outstanding,
                "beta": self.beta,
                "pe_ratio": self.pe_ratio,
                "currency": self.currency
            },
            "historical_financials": {
                "income_statement": self.income_statement.to_dict() if self.income_statement is not None else None,
                "balance_sheet": self.balance_sheet.to_dict() if self.balance_sheet is not None else None,
                "cash_flow": self.cash_flow.to_dict() if self.cash_flow is not None else None
            },
            "peer_selection": {
                "peer_tickers": self.peer_tickers,
                "peer_data": self.peer_data
            },
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "data_sources": self.data_sources
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SharedContextData':
        """Create from dictionary (for session retrieval)"""
        context = cls()
        context.ticker = data.get("ticker", "")
        context.company_name = data.get("company_name", "")
        context.market = data.get("market", "")
        context.sector = data.get("sector", "")
        context.industry = data.get("industry", "")
        context.description = data.get("description", "")

        market_data = data.get("market_data", {})
        context.current_price = market_data.get("current_price")
        context.market_cap = market_data.get("market_cap")
        context.shares_outstanding = market_data.get("shares_outstanding")
        context.beta = market_data.get("beta")
        context.pe_ratio = market_data.get("pe_ratio")
        context.currency = market_data.get("currency", "USD")

        hist_fin = data.get("historical_financials", {})
        if hist_fin.get("income_statement"):
            context.income_statement = pd.DataFrame.from_dict(hist_fin["income_statement"])
        if hist_fin.get("balance_sheet"):
            context.balance_sheet = pd.DataFrame.from_dict(hist_fin["balance_sheet"])
        if hist_fin.get("cash_flow"):
            context.cash_flow = pd.DataFrame.from_dict(hist_fin["cash_flow"])

        peer_sel = data.get("peer_selection", {})
        context.peer_tickers = peer_sel.get("peer_tickers", [])
        context.peer_data = peer_sel.get("peer_data", {})

        if data.get("last_updated"):
            context.last_updated = datetime.fromisoformat(data["last_updated"])
        context.data_sources = data.get("data_sources", {})

        return context


class SharedContextService:
    """
    Service for fetching and managing shared company context.

    This service eliminates redundant API calls by fetching common data once
    and making it available to all valuation methods.
    """

    def __init__(self):
        self.yfinance_service = YFinanceService()
        self.alphavantage_service = AlphaVantageService()
        self._cache: Dict[str, SharedContextData] = {}

    async def fetch_company_context(
        self,
        ticker: str,
        market: str = "international",
        peer_tickers: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> SharedContextData:
        """
        Fetch complete company context including overview, market data, and historical financials.

        Args:
            ticker: Stock ticker symbol
            market: Market identifier ('international' or 'vietnam')
            peer_tickers: Optional list of peer ticker symbols
            use_cache: Whether to use cached data if available

        Returns:
            SharedContextData object with all company context
        """
        # Check cache
        cache_key = f"{ticker}_{market}"
        if use_cache and cache_key in self._cache:
            logger.info(f"Using cached context for {cache_key}")
            return self._cache[cache_key]

        logger.info(f"Fetching company context for {ticker} ({market})")
        context = SharedContextData()
        context.ticker = ticker
        context.market = market

        try:
            # Fetch company overview and market data from yfinance
            overview_data = await self._fetch_overview_and_market_data(ticker, market)
            context._update_from_overview(overview_data)

            # Fetch historical financials
            financials_data = await self._fetch_historical_financials(ticker, market)
            context._update_from_financials(financials_data)

            # Fetch peer data if provided
            if peer_tickers:
                peer_data = await self._fetch_peer_data(peer_tickers, market)
                context.peer_tickers = peer_tickers
                context.peer_data = peer_data

            context.last_updated = datetime.utcnow()
            context.data_sources = {
                "overview": "yfinance",
                "financials": "yfinance",
                "peers": "yfinance" if peer_tickers else "none"
            }

            # Cache result
            if use_cache:
                self._cache[cache_key] = context

            logger.info(f"Successfully fetched context for {ticker}")
            return context

        except Exception as e:
            logger.error(f"Error fetching context for {ticker}: {e}")
            raise

    async def _fetch_overview_and_market_data(
        self,
        ticker: str,
        market: str
    ) -> Dict[str, Any]:
        """Fetch company overview and market data"""
        try:
            # Use yfinance for international markets
            if market.lower() in ["international", "us", "in"]:
                key_stats = self.yfinance_service.fetch_key_stats(ticker)
                info = self.yfinance_service.get_stock_info(ticker)

                return {
                    "company_name": info.get("longName", ""),
                    "sector": info.get("sector", ""),
                    "industry": info.get("industry", ""),
                    "description": info.get("longBusinessSummary", ""),
                    "current_price": key_stats.get("currentPrice"),
                    "market_cap": key_stats.get("marketCap"),
                    "shares_outstanding": key_stats.get("sharesOutstanding"),
                    "beta": key_stats.get("beta"),
                    "pe_ratio": key_stats.get("forwardPE") or key_stats.get("trailingPE"),
                    "currency": key_stats.get("currency", "USD")
                }
            else:
                # Vietnam or other markets
                # Could use AlphaVantage or other services
                return await self.alphavantage_service.get_company_overview(ticker)

        except Exception as e:
            logger.warning(f"Failed to fetch overview for {ticker}: {e}")
            return {}

    async def _fetch_historical_financials(
        self,
        ticker: str,
        market: str
    ) -> Dict[str, pd.DataFrame]:
        """Fetch historical financial statements"""
        try:
            if market.lower() in ["international", "us", "in"]:
                financials_df = self.yfinance_service.get_financials(ticker)
                balance_sheet_df = self.yfinance_service.get_balance_sheet(ticker)
                cashflow_df = self.yfinance_service.get_cashflow(ticker)

                return {
                    "income_statement": financials_df,
                    "balance_sheet": balance_sheet_df,
                    "cash_flow": cashflow_df
                }
            else:
                # Vietnam or other markets
                return {}

        except Exception as e:
            logger.warning(f"Failed to fetch financials for {ticker}: {e}")
            return {}

    async def _fetch_peer_data(
        self,
        peer_tickers: List[str],
        market: str
    ) -> Dict[str, Any]:
        """Fetch data for peer companies"""
        peer_data = {}

        for peer_ticker in peer_tickers:
            try:
                if market.lower() in ["international", "us", "in"]:
                    # Use get_ticker_info which provides direct access to valuation multiples
                    peer_info_dict = self.yfinance_service.get_ticker_info(peer_ticker)

                    if not peer_info_dict:
                        logger.warning(f"No info available for peer {peer_ticker}")
                        peer_data[f"peer_{peer_ticker}_info"] = {}
                        continue

                    # Extract valuation multiples directly from yfinance info
                    # These are more reliable than calculating from financials
                    market_cap = peer_info_dict.get('marketCap')
                    enterprise_value = peer_info_dict.get('enterpriseValue')

                    # Get multiples directly from yfinance - use correct field names from get_ticker_info
                    ev_ebitda = peer_info_dict.get('enterpriseToEbitda')
                    pe_ratio = peer_info_dict.get('trailingPE') or peer_info_dict.get('forwardPE')
                    ev_revenue = peer_info_dict.get('enterpriseToRevenue')
                    pb_ratio = peer_info_dict.get('priceToBook')

                    # Also get key stats for WACC calculation
                    key_stats = self.yfinance_service.fetch_key_stats(peer_ticker)

                    peer_info = {
                        "ticker": peer_ticker,
                        "name": peer_info_dict.get('longName') or peer_info_dict.get('shortName'),
                        "marketCap": market_cap,
                        "enterpriseValue": enterprise_value,
                        "beta": peer_info_dict.get('beta') or key_stats.get("beta"),
                        "totalDebt": key_stats.get("totalDebt"),
                        "cash": key_stats.get("cash"),
                        "effectiveTaxRate": key_stats.get("effectiveTaxRate"),
                        "costOfDebt": key_stats.get("costOfDebt"),
                        "peRatio": pe_ratio,
                        "evEbitda": ev_ebitda,
                        "evRevenue": ev_revenue,
                        "pbRatio": pb_ratio
                    }
                    peer_data[f"peer_{peer_ticker}_info"] = peer_info
                    logger.info(f"Fetched peer data for {peer_ticker}: EV/EBITDA={ev_ebitda}, P/E={pe_ratio}, EV/Rev={ev_revenue}, P/B={pb_ratio}")
                else:
                    # Vietnam or other markets
                    peer_data[f"peer_{peer_ticker}_info"] = {}

            except Exception as e:
                logger.warning(f"Failed to fetch peer data for {peer_ticker}: {e}")
                peer_data[f"peer_{peer_ticker}_info"] = {"error": str(e)}

        peer_data["peers"] = peer_tickers
        return peer_data

    def get_cached_context(self, ticker: str, market: str = "international") -> Optional[SharedContextData]:
        """Get cached context if available"""
        cache_key = f"{ticker}_{market}"
        return self._cache.get(cache_key)

    def clear_cache(self, ticker: Optional[str] = None, market: Optional[str] = None):
        """Clear cache for specific ticker or all cache"""
        if ticker and market:
            cache_key = f"{ticker}_{market}"
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.info(f"Cleared cache for {cache_key}")
        elif ticker:
            # Clear all caches for this ticker
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{ticker}_")]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info(f"Cleared {len(keys_to_remove)} cache entries for {ticker}")
        else:
            self._cache.clear()
            logger.info("Cleared all cache")

    def invalidate_old_cache(self, max_age_hours: int = 24):
        """Invalidate cache entries older than specified hours"""
        cutoff = datetime.utcnow()
        keys_to_remove = []

        for key, context in self._cache.items():
            if context.last_updated:
                age = (cutoff - context.last_updated).total_seconds() / 3600
                if age > max_age_hours:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

        if keys_to_remove:
            logger.info(f"Invalidated {len(keys_to_remove)} old cache entries")


# Singleton instance
shared_context_service = SharedContextService()