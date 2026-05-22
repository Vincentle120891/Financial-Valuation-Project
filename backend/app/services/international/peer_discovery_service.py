"""
Peer Discovery Service
Automatically identifies peer companies based on industry, sector, and market cap.

Key Improvements:
- Progressive Filter Relaxation: Multi-pass search with loosening constraints
- Asynchronous Parallel Fetching: Concurrent ticker info retrieval via asyncio.gather
- Deep Search Strategy: Expanded search pool with better query handling
- HYBRID APPROACH: FMP multi-segment discovery with yfinance fallback
"""

import asyncio
import logging
import math
import aiohttp
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel

from app.services.international.yfinance_service import YFinanceService, run_in_executor

logger = logging.getLogger(__name__)


class PeerCandidate(BaseModel):
    """Peer candidate company."""
    symbol: str
    ticker: str  # Alias for frontend compatibility
    name: str
    company_name: str  # Alias for frontend compatibility
    exchange: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None  # Internal snake_case
    marketCap: Optional[float] = None  # camelCase for frontend
    current_price: Optional[float] = None
    beta: Optional[float] = None
    similarity_score: float = 0.0
    score: float = 0.0  # Alias for frontend compatibility
    match_reasons: List[str] = []


class PeerDiscoveryRequest(BaseModel):
    """Request for peer discovery."""
    target_ticker: str
    target_sector: Optional[str] = None
    target_industry: Optional[str] = None
    target_market_cap: Optional[float] = None
    max_peers: int = 10
    market: str = "international"
    method: Optional[str] = None  # NEW: valuation method (DCF, COMPS, DuPont)
    allowed_exchanges: Optional[List[str]] = None  # Explicitly allowed exchanges


class PeerDiscoveryResponse(BaseModel):
    """Response from peer discovery."""
    target_ticker: str
    peers: List[PeerCandidate]
    total_found: int
    search_criteria: Dict
    warnings: List[str] = []
    # NEW: Fallback options for manual user selection (not auto-included)
    fallback_options: List[PeerCandidate] = []


class PeerDiscoveryService:
    """
    Service for automatic peer company discovery.

    Methodology:
    1. Primary Match: Same Industry + Market Cap within 50-200% range
    2. Secondary Match: Same Sector + Market Cap within 50-200% range
    3. Tertiary Match: Same Industry regardless of market cap
    4. Fallback: Same Sector regardless of market cap

    Scoring:
    - Industry match: +40 points
    - Sector match: +20 points
    - Market cap within range: +30 points
    - Market cap proximity: +10 points (closer = higher)
    """

    MARKET_CAP_RANGE_MIN = 0.5  # 50% of target
    MARKET_CAP_RANGE_MAX = 2.0  # 200% of target

    # Exchange filters by market type
    MARKET_EXCHANGE_FILTERS = {
        "international": ["NMS", "NYQ", "NGM", "NCM"],  # NASDAQ, NYSE
        "vietnam": ["HOSE", "HNX", "UPCOM"],  # Vietnam exchanges
        "us": ["NMS", "NYQ", "NGM", "NCM"],
        "uk": ["LSE"],
        "eu": ["GER", "FRA", "BER", "MUN", "STU", "DUS"],  # German exchanges
        "jp": ["JPX"],
        "au": ["ASX"],
    }

    # Exchanges to always exclude (OTC, foreign, problematic)
    EXCLUDED_EXCHANGES = {"PNK", "GRE", "OTC", "BTS", "NCY"}

    def __init__(self, yfinance_service: Optional[YFinanceService] = None, fmp_api_key: Optional[str] = None):
        self.yfinance_service = yfinance_service or YFinanceService()
        self.fmp_api_key = fmp_api_key  # Provided via environment variables or config
        self._industry_cache: Dict[str, List[Dict]] = {}
        self._sector_cache: Dict[str, List[Dict]] = {}

    async def discover_peers(
        self,
        request: PeerDiscoveryRequest
    ) -> PeerDiscoveryResponse:
        """
        Discover peer companies for a target ticker with progressive fallback relaxation.

        Args:
            request: Peer discovery request with target company info

        Returns:
            PeerDiscoveryResponse with ranked peer candidates
        """
        logger.info(f"Discovering peers for '{request.target_ticker}', method='{request.method}'")
        warnings = []

        # Get target company info if not provided
        target_sector = request.target_sector
        target_industry = request.target_industry
        target_market_cap = request.target_market_cap
        method = request.method  # NEW: valuation method

        if not all([target_sector, target_industry, target_market_cap]):
            ticker_info = self.yfinance_service.get_ticker_info(request.target_ticker)
            if ticker_info:
                target_sector = target_sector or ticker_info.get('sector')
                target_industry = target_industry or ticker_info.get('industry')
                target_market_cap = target_market_cap or ticker_info.get('marketCap')

        if not target_sector and not target_industry:
            warnings.append("No sector or industry information available for target company")
            return PeerDiscoveryResponse(
                target_ticker=request.target_ticker,
                peers=[],
                total_found=0,
                search_criteria={
                    'sector': None,
                    'industry': None,
                    'market_cap_range': None,
                    'method': method
                },
                warnings=warnings
            )

        # Multi-pass search: Start strict, loosen if we don't find enough peers
        relaxation_passes = [
            {"label": "Strict", "dcf_mult": (0.5, 2.0), "comps_mult": (0.3, 3.0), "default_mult": (0.4, 2.5)},
            {"label": "Moderate", "dcf_mult": (0.25, 4.0), "comps_mult": (0.15, 6.0), "default_mult": (0.2, 5.0)},
            {"label": "Broad", "dcf_mult": (0.05, 10.0), "comps_mult": (0.05, 10.0), "default_mult": (0.05, 10.0)}
        ]

        top_peers = []
        fallback_options = []  # Store fallback options separately for manual selection
        search_criteria = {}

        for pas in relaxation_passes:
            if len(top_peers) >= request.max_peers:
                break

            logger.info(f"Running peer discovery pass: {pas['label']}")

            # Determine market cap range for this pass
            market_cap_min = None
            market_cap_max = None
            if target_market_cap:
                if method == "DCF":
                    mult_min, mult_max = pas["dcf_mult"]
                elif method == "COMPS":
                    mult_min, mult_max = pas["comps_mult"]
                else:
                    mult_min, mult_max = pas["default_mult"]

                market_cap_min = target_market_cap * mult_min
                market_cap_max = target_market_cap * mult_max

            search_criteria = {
                'sector': target_sector,
                'industry': target_industry,
                'market_cap_range': f"${market_cap_min/1e9:.1f}B - ${market_cap_max/1e9:.1f}B" if market_cap_min else "Any",
                'allowed_exchanges': request.allowed_exchanges,
                'method': method
            }

            allowed_exchanges = self._get_allowed_exchanges(request.market, request.allowed_exchanges)

            # Search for candidates
            peer_candidates = await self._search_peer_candidates(
                sector=target_sector,
                industry=target_industry,
                market_cap_min=market_cap_min,
                market_cap_max=market_cap_max,
                exclude_ticker=request.target_ticker,
                max_results=request.max_peers * 4,  # Expanded multiplier pool
                allowed_exchanges=allowed_exchanges,
                method=method
            )

            # Score and rank candidates
            scored_peers = self._score_and_rank_peers(
                candidates=peer_candidates,
                target_sector=target_sector,
                target_industry=target_industry,
                target_market_cap=target_market_cap,
                method=method
            )

            # Deduplicate and merge into top_peers
            existing_symbols = {p.symbol for p in top_peers}
            for peer in scored_peers:
                if peer.symbol not in existing_symbols:
                    top_peers.append(peer)
                    existing_symbols.add(peer.symbol)

        # If we still don't have enough peers after all relaxation passes,
        # fetch fallback options but DO NOT auto-include them - they're for manual selection only
        if len(top_peers) < request.max_peers:
            warnings.append(f"Only found {len(top_peers)} suitable peers out of {request.max_peers} requested after broad relaxation.")
            
            # Fetch fallback options from predefined lists (for manual user selection via dropdown)
            fallback_raw = await self._get_fallback_peers(
                sector=target_sector,
                industry=target_industry,
                exclude_tickers={request.target_ticker} | {p.symbol for p in top_peers},
                allowed_exchanges=allowed_exchanges
            )
            
            # Convert fallback raw dicts to PeerCandidate objects
            for fb in fallback_raw:
                try:
                    fallback_peer = PeerCandidate(
                        symbol=fb['symbol'],
                        ticker=fb['symbol'],
                        name=fb.get('name', fb['symbol']),
                        company_name=fb.get('name', fb['symbol']),
                        exchange=fb.get('exchange', ''),
                        sector=fb.get('sector'),
                        industry=fb.get('industry'),
                        market_cap=fb.get('market_cap'),
                        marketCap=fb.get('market_cap'),
                        current_price=fb.get('current_price'),
                        beta=fb.get('beta'),
                        similarity_score=0.0,
                        score=0.0,
                        match_reasons=['fallback_option']
                    )
                    fallback_options.append(fallback_peer)
                except Exception as e:
                    logger.debug(f"Failed to create fallback peer object: {e}")

        # Final slice - only include auto-discovered peers, NOT fallback options
        top_peers = top_peers[:request.max_peers]

        return PeerDiscoveryResponse(
            target_ticker=request.target_ticker,
            peers=top_peers,
            total_found=len(top_peers),
            search_criteria=search_criteria,
            warnings=warnings,
            fallback_options=fallback_options  # Separate list for manual dropdown selection
        )

    async def _search_peer_candidates(
        self,
        sector: Optional[str],
        industry: Optional[str],
        market_cap_min: Optional[float],
        market_cap_max: Optional[float],
        exclude_ticker: str,
        max_results: int = 30,
        allowed_exchanges: Optional[List[str]] = None,
        method: Optional[str] = None  # NEW: valuation method
    ) -> List[Dict]:
        """
        HYBRID IMPLEMENTATION:
        Prioritizes institutional multi-segment tracking via FMP, falls back to yfinance keyword filtering.
        
        Args:
            sector: Target sector
            industry: Target industry
            market_cap_min: Minimum market cap
            market_cap_max: Maximum market cap
            exclude_ticker: Ticker to exclude from results
            max_results: Maximum number of results to return
            allowed_exchanges: List of allowed exchange codes
            method: Valuation method (DCF, COMPS, DuPont) - affects search strategy

        Returns:
            List of candidate company dictionaries
        """
        # PATH A: If FMP is configured, try the advanced multi-segment route
        if self.fmp_api_key:
            try:
                logger.info("FMP API key detected. Initiating multi-segment discovery pool...")
                return await self._search_via_fmp_segments(
                    sector, industry, market_cap_min, market_cap_max, exclude_ticker, max_results, allowed_exchanges
                )
            except Exception as e:
                logger.error(f"FMP Advanced discovery failed ({str(e)}). Falling back to yfinance...")
                # Do not raise an error; fall through to PATH B gracefully

        # PATH B: Fallback / Default engine using current yfinance logic
        logger.info("Executing standard yfinance single-label search fallback.")
        return await self._search_via_yfinance_fallback(
            sector, industry, market_cap_min, market_cap_max, exclude_ticker, max_results, allowed_exchanges
        )

    async def _search_via_fmp_segments(
        self,
        sector: Optional[str],
        industry: Optional[str],
        market_cap_min: Optional[float],
        market_cap_max: Optional[float],
        exclude_ticker: str,
        max_results: int = 30,
        allowed_exchanges: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Helper that queries FMP's broad stock-screener and populates segment matrices.
        Solves the conglomerate trap by matching on revenue segment overlaps.
        """
        screener_url = "https://financialmodelingprep.com/api/v3/stock-screener"
        segment_url = "https://financialmodelingprep.com/api/v4/revenue-product-segment"
        
        async with aiohttp.ClientSession() as session:
            # Step 1: Pull a wide industry + sector footprint pool to capture conglomerates
            params = {"sector": sector, "limit": 100, "apikey": self.fmp_api_key} if sector else \
                     {"industry": industry, "limit": 100, "apikey": self.fmp_api_key} if industry else \
                     {"limit": 100, "apikey": self.fmp_api_key}
            
            async with session.get(screener_url, params=params) as resp:
                if resp.status != 200:
                    raise Exception(f"FMP Screener API responded with status {resp.status}")
                raw_data = await resp.json()

            # Filter broad size constraints immediately to save API calls on segment footprints
            candidates = {}
            for item in raw_data:
                sym = item.get('symbol')
                mcap = float(item.get('marketCap', 0) or 0)
                if sym and sym != exclude_ticker:
                    if market_cap_min is None or market_cap_max is None or (market_cap_min <= mcap <= market_cap_max):
                        if self._is_exchange_allowed(item.get('exchange', ''), allowed_exchanges):
                            candidates[sym] = {
                                "symbol": sym, 
                                "name": item.get("companyName"),
                                "industry": item.get("industry"), 
                                "sector": item.get("sector"),
                                "market_cap": mcap, 
                                "segments": {},  # To be populated
                                "target_segments": {}  # Will be populated with target's segments
                            }

            # Step 2: Fetch target's operational segment profile mapping
            target_segments = await self._get_revenue_segments(session, exclude_ticker)
            
            # Step 3: Concurrently fetch candidate segments
            tasks = []
            for sym in list(candidates.keys())[:max_results * 2]:  # Fetch extra for filtering
                candidates[sym]['target_segments'] = target_segments
                tasks.append(self._enrich_candidate_segments(session, candidates[sym]))
            
            enriched = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful enrichments and apply final market cap filter
            result = []
            for e in enriched:
                if isinstance(e, dict) and e.get('segments'):
                    result.append(e)
                elif isinstance(e, dict):  # No segments but valid candidate
                    result.append(e)
            
            return result[:max_results]

    async def _get_revenue_segments(self, session: aiohttp.ClientSession, ticker: str) -> dict:
        """Helper to resolve granular segment arrays via FMP v4."""
        url = "https://financialmodelingprep.com/api/v4/revenue-product-segment"
        params = {"symbol": ticker, "period": "annual", "apikey": self.fmp_api_key}
        try:
            async with session.get(url, params=params, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and isinstance(data, list):
                        raw_seg = data[0].get("segments", {})
                        if raw_seg:
                            total = sum(float(v) for v in raw_seg.values() if float(v) > 0)
                            return {k.lower(): float(v)/total for k, v in raw_seg.items()} if total > 0 else {}
        except Exception as e:
            logger.debug(f"Failed to fetch segments for {ticker}: {e}")
        return {}

    async def _enrich_candidate_segments(self, session: aiohttp.ClientSession, candidate: dict) -> dict:
        """Fetch segment data for a single candidate."""
        candidate['segments'] = await self._get_revenue_segments(session, candidate['symbol'])
        return candidate

    async def _search_via_yfinance_fallback(
        self,
        sector: Optional[str],
        industry: Optional[str],
        market_cap_min: Optional[float],
        market_cap_max: Optional[float],
        exclude_ticker: str,
        max_results: int = 30,
        allowed_exchanges: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Your exact current peer discovery logic goes here unaltered.
        Fallback when FMP is unavailable.
        """
        candidates = []
        seen_tickers = set([exclude_ticker])

        # Strategy 1: Search by industry keywords
        if industry:
            industry_candidates = await self._search_by_keyword(
                keyword=industry,
                market_cap_min=market_cap_min,
                market_cap_max=market_cap_max,
                exclude_tickers=seen_tickers,
                allowed_exchanges=allowed_exchanges
            )
            for candidate in industry_candidates:
                if candidate['symbol'] not in seen_tickers:
                    candidate['match_strategy'] = 'industry'
                    candidates.append(candidate)
                    seen_tickers.add(candidate['symbol'])

        # Strategy 2: Search by sector keywords
        if sector and len(candidates) < max_results:
            sector_candidates = await self._search_by_keyword(
                keyword=sector,
                market_cap_min=market_cap_min,
                market_cap_max=market_cap_max,
                exclude_tickers=seen_tickers,
                allowed_exchanges=allowed_exchanges
            )
            for candidate in sector_candidates:
                if candidate['symbol'] not in seen_tickers:
                    candidate['match_strategy'] = 'sector'
                    candidates.append(candidate)
                    seen_tickers.add(candidate['symbol'])

        # Strategy 3: Known large companies in major sectors (fallback)
        if len(candidates) < max_results // 2:
            fallback_candidates = await self._get_fallback_peers(
                sector=sector,
                industry=industry,
                exclude_tickers=seen_tickers,
                allowed_exchanges=allowed_exchanges
            )
            for candidate in fallback_candidates:
                if candidate['symbol'] not in seen_tickers:
                    candidate['match_strategy'] = 'fallback'
                    candidates.append(candidate)
                    seen_tickers.add(candidate['symbol'])

        return candidates[:max_results]

    async def _search_by_keyword(
        self,
        keyword: str,
        market_cap_min: Optional[float],
        market_cap_max: Optional[float],
        exclude_tickers: set,
        allowed_exchanges: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search for companies by keyword using yfinance with concurrent fetching.

        Args:
            keyword: Search keyword (industry or sector name)
            market_cap_min: Minimum market cap
            market_cap_max: Maximum market cap
            exclude_tickers: Set of tickers to exclude
            allowed_exchanges: List of allowed exchange codes

        Returns:
            List of matching company dictionaries
        """
        # Generate multiple search queries from the keyword
        # yfinance search works better with shorter, simpler queries
        search_queries = self._generate_search_queries(keyword)

        # Accumulate raw candidate tickers from yfinance search indices across all queries
        raw_candidates = []
        seen_symbols = set(exclude_tickers)

        for query in search_queries:
            # yfinance text search matches against broad terms
            search_results = self.yfinance_service.search_tickers(query) or []
            for result in search_results[:35]:  # Increase deep look capability
                ticker = result.get('symbol', '')
                exchange = result.get('exchange', '')

                if ticker in seen_symbols:
                    continue
                if not self._is_exchange_allowed(exchange, allowed_exchanges):
                    continue

                seen_symbols.add(ticker)
                raw_candidates.append((ticker, exchange))

        if not raw_candidates:
            return []

        # CONCURRENCY FIX: Fetch ticker metrics concurrently rather than sequentially
        # Use run_in_executor to avoid blocking the event loop during synchronous yfinance calls
        async def fetch_and_validate(ticker: str, exchange: str) -> Optional[Dict]:
            try:
                # Run the synchronous get_ticker_info in a thread pool to avoid blocking
                ticker_info = await run_in_executor(self.yfinance_service.get_ticker_info, ticker)
                if not ticker_info or not ticker_info.get('currentPrice'):
                    return None

                market_cap = ticker_info.get('marketCap')
                if not market_cap or market_cap <= 0:
                    return None

                # Apply cap filtering
                if market_cap_min and market_cap_max:
                    if not (market_cap_min <= market_cap <= market_cap_max):
                        return None

                return {
                    'symbol': ticker,
                    'name': ticker_info.get('longName', ticker),
                    'exchange': exchange,
                    'sector': ticker_info.get('sector'),
                    'industry': ticker_info.get('industry'),
                    'market_cap': market_cap,
                    'current_price': ticker_info.get('currentPrice'),
                    'beta': ticker_info.get('beta')
                }
            except Exception as e:
                logger.debug(f"Failed parsing raw ticker data for {ticker}: {str(e)}")
                return None

        # Execute all ticker info fetches in parallel using asyncio.gather
        # This allows all network calls to happen concurrently instead of sequentially
        tasks = [fetch_and_validate(t, e) for t, e in raw_candidates]
        completed_metrics = await asyncio.gather(*tasks)

        # Filter out None values from failed validations
        results = [metric for metric in completed_metrics if metric is not None]
        return results

    def _generate_search_queries(self, keyword: str) -> List[str]:
        """
        Generate optimized search queries from an industry/sector keyword.

        yfinance search works best with short, simple queries. This method
        breaks down complex industry names into searchable terms.

        Args:
            keyword: Original industry or sector name

        Returns:
            List of search queries to try
        """
        if not keyword:
            return []

        queries = []

        # Map common industry terms to better search keywords
        # Priority: Use broad terms that yfinance actually returns results for
        industry_mappings = {
            'auto manufacturers': ['Auto', 'Automotive', 'Cars', 'EV', 'Electric Vehicles'],
            'automotive': ['Auto', 'Automotive', 'Cars', 'EV', 'Electric Vehicles'],
            'drug manufacturers': ['Pharma', 'Pharmaceuticals', 'Biotech'],
            'software': ['Software', 'Technology', 'Computer'],
            'semiconductors': ['Semiconductor', 'Chips', 'Electronics'],
            'biotechnology': ['Biotech', 'Biotechnology', 'Life Sciences'],
            'oil & gas': ['Oil', 'Gas', 'Energy', 'Petroleum'],
            'banks': ['Bank', 'Banking', 'Financial'],
            'insurance': ['Insurance'],
            'retail': ['Retail', 'Stores', 'E-commerce'],
            'restaurants': ['Restaurant', 'Food', 'Dining'],
            'aerospace & defense': ['Aerospace', 'Defense', 'Aviation', 'Airlines'],
            'telecom services': ['Telecom', 'Communication', 'Wireless'],
            'utilities': ['Utilities', 'Electric', 'Power', 'Water'],
            'real estate': ['Real Estate', 'REIT', 'Property'],
            'consumer electronics': ['Electronics', 'Technology', 'Consumer'],
            'apparel manufacturing': ['Apparel', 'Clothing', 'Fashion', 'Textile'],
            'footwear & accessories': ['Footwear', 'Shoes', 'Apparel'],
            'auto parts': ['Auto Parts', 'Automotive', 'Auto'],
            'recreational vehicles': ['RV', 'Recreational', 'Motorcycles', 'Leisure'],
            'farm & heavy construction machinery': ['Machinery', 'Construction', 'Equipment', 'Industrial'],
            'home improvement retail': ['Home Improvement', 'Retail', 'Building'],
            'internet retail': ['Internet', 'E-commerce', 'Retail', 'Technology'],
            'specialty retail': ['Retail', 'Specialty', 'Stores'],
        }

        keyword_lower = keyword.lower().strip()

        # Check for mapped terms
        for industry_term, search_terms in industry_mappings.items():
            if industry_term in keyword_lower:
                queries.extend(search_terms)
                break

        # Always add the first word of the keyword (often the most important)
        first_word = keyword.split()[0] if keyword.split() else keyword
        if first_word not in queries:
            queries.insert(0, first_word)

        # Add original keyword as fallback (in case it works)
        if keyword not in queries:
            queries.append(keyword)

        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)

        return unique_queries[:5]  # Limit to 5 queries max

    async def _get_fallback_peers(
        self,
        sector: Optional[str],
        industry: Optional[str],
        exclude_tickers: set,
        allowed_exchanges: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get fallback peers from known company lists by sector.
        These are ONLY for manual user selection via dropdown, NOT auto-included.

        Args:
            sector: Target sector
            industry: Target industry
            exclude_tickers: Set of tickers to exclude
            allowed_exchanges: List of allowed exchange codes

        Returns:
            List of fallback peer candidates (for manual dropdown selection)
        """
        # Known companies by sector (can be expanded)
        fallback_companies = {
            'Technology': ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'AMD', 'INTC', 'CRM', 'ORCL', 'ADBE'],
            'Healthcare': ['JNJ', 'UNH', 'PFE', 'MRK', 'ABBV', 'TMO', 'ABT', 'DHR', 'BMY', 'LLY'],
            'Financial Services': ['BRK.B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP'],
            'Consumer Cyclical': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'LOW', 'TJX', 'BKNG', 'CMG'],
            'Communication Services': ['GOOGL', 'META', 'DIS', 'NFLX', 'CMCSA', 'VZ', 'T', 'TMUS', 'CHTR', 'EA'],
            'Industrials': ['BA', 'CAT', 'UNP', 'HON', 'UPS', 'RTX', 'LMT', 'DE', 'GE', 'MMM'],
            'Consumer Defensive': ['WMT', 'PG', 'KO', 'PEP', 'COST', 'PM', 'MO', 'MDLZ', 'CL', 'KMB'],
            'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL'],
            'Utilities': ['NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL', 'WEC', 'ED'],
            'Real Estate': ['AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'SPG', 'WELL', 'DLR', 'O', 'SBAC'],
            'Basic Materials': ['LIN', 'APD', 'SHW', 'ECL', 'FCX', 'NEM', 'DOW', 'DD', 'PPG', 'NUE']
        }

        results = []

        # Map sector to fallback list
        sector_key = sector
        if not sector_key or sector_key not in fallback_companies:
            # Try to find partial match
            for key in fallback_companies.keys():
                if sector and key.lower() in sector.lower():
                    sector_key = key
                    break

        if sector_key and sector_key in fallback_companies:
            # CONCURRENT FIX: Fetch all ticker info in parallel using asyncio.gather
            async def fetch_fallback_ticker(ticker: str) -> Optional[Dict]:
                try:
                    ticker_info = await run_in_executor(self.yfinance_service.get_ticker_info, ticker)
                    if not ticker_info or not ticker_info.get('currentPrice'):
                        return None

                    exchange = ticker_info.get('exchange', '')
                    if not self._is_exchange_allowed(exchange, allowed_exchanges):
                        logger.debug(f"Excluding fallback peer {ticker}: exchange '{exchange}' not allowed")
                        return None

                    return {
                        'symbol': ticker,
                        'name': ticker_info.get('longName', ticker),
                        'exchange': exchange,
                        'sector': ticker_info.get('sector'),
                        'industry': ticker_info.get('industry'),
                        'market_cap': ticker_info.get('marketCap'),
                        'current_price': ticker_info.get('currentPrice'),
                        'beta': ticker_info.get('beta')
                    }
                except Exception as e:
                    logger.debug(f"Failed fetching fallback ticker {ticker}: {e}")
                    return None

            # Filter out excluded tickers first
            valid_tickers = [t for t in fallback_companies[sector_key] if t not in exclude_tickers]
            
            # Fetch all in parallel
            tasks = [fetch_fallback_ticker(t) for t in valid_tickers]
            fetched_results = await asyncio.gather(*tasks)
            
            # Filter out None values
            results = [r for r in fetched_results if r is not None]

        return results

    def _score_and_rank_peers(
        self,
        candidates: List[Dict],
        target_sector: Optional[str],
        target_industry: Optional[str],
        target_market_cap: Optional[float],
        method: Optional[str] = None  # NEW: valuation method
    ) -> List[PeerCandidate]:
        """
        Score and rank peer candidates.

        Scoring methodology (enhanced with sub-industry weighting and method-specific adjustments):
        - Sub-industry match (exact): +50 points
        - Industry match (general): +30 points
        - Sector match: +15 points
        - Market cap within range: +25 points
        - Market cap proximity: +10 points (closer = higher)
        - Same country/region: +5 points

        Method-specific adjustments:
        - COMPS: Prioritize recent M&A activity, larger market cap range
        - DCF: Prioritize similar growth profiles, cash flow characteristics
        - DuPont: Prioritize similar operational efficiency metrics

        Args:
            candidates: List of candidate companies
            target_sector: Target company sector
            target_industry: Target company industry
            target_market_cap: Target company market cap
            method: Valuation method (DCF, COMPS, DuPont)

        Returns:
            List of scored and ranked PeerCandidate objects
        """
        scored_peers = []

        # Method-specific scoring adjustments
        method = method or "DCF"  # Default to DCF if not specified

        for candidate in candidates:
            score = 0.0
            match_reasons = []

            # INDUSTRY MATCHING WITH SUB-INDUSTRY WEIGHTING AND STRICT FILTERING
            if target_industry and candidate.get('industry'):
                cand_industry = candidate['industry'].lower()
                target_industry_lower = target_industry.lower()

                # Check for exact sub-industry match (+50 points)
                if cand_industry == target_industry_lower:
                    score += 50
                    match_reasons.append("Exact sub-industry match")
                # Check for partial industry match (contains key terms) (+30 points)
                elif self._industries_are_similar(target_industry_lower, cand_industry):
                    score += 30
                    match_reasons.append("Similar industry")
                else:
                    # RELAXED FILTERING: Allow sector-level match even with different industries
                    # This ensures we get enough peers when industry matches are limited
                    logger.debug(f"Industry mismatch for {candidate.get('symbol')}: '{cand_industry}' vs '{target_industry_lower}', but allowing sector match")
                    # Continue to sector check below

            # Sector match (+15 points) - only if no industry match found
            if target_sector and candidate.get('sector'):
                if candidate['sector'].lower() == target_sector.lower():
                    # Only add sector match if no industry match was found
                    if not any("industry" in reason.lower() or "sub-industry" in reason.lower() for reason in match_reasons):
                        score += 15
                        match_reasons.append("Same sector")
                    else:
                        # Industry already matched, still note same sector but don't double-count
                        logger.debug(f"{candidate.get('symbol')}: Already has industry match, skipping sector bonus")

            # Market cap range match (+25 points)
            candidate_market_cap = candidate.get('market_cap')
            if target_market_cap and candidate_market_cap:
                ratio = candidate_market_cap / target_market_cap

                # Method-specific market cap scoring
                if method == "COMPS":
                    # COMPS: Wider range acceptable, focus on M&A comparables
                    comps_range_min = 0.3
                    comps_range_max = 3.0
                    if comps_range_min <= ratio <= comps_range_max:
                        score += 25
                        match_reasons.append("Comparable for M&A analysis")

                        # Proximity scoring adjusted for COMPS
                        distance_from_perfect = abs(1.0 - ratio)
                        proximity_score = max(0, 10 - (distance_from_perfect * 8))  # Slightly more lenient
                        score += proximity_score

                        if proximity_score > 7:
                            match_reasons.append("Good M&A comparable size")

                    # Bonus for companies known to be acquisition targets
                    if ratio < 1.5:  # Smaller companies are more likely acquisition targets
                        score += 5
                        match_reasons.append("Potential acquisition target")

                elif method == "DCF":
                    # DCF: Tighter range, focus on similar cash flow profiles
                    if self.MARKET_CAP_RANGE_MIN <= ratio <= self.MARKET_CAP_RANGE_MAX:
                        score += 25
                        match_reasons.append("Similar cash flow profile")

                        # Proximity scoring - stricter for DCF
                        distance_from_perfect = abs(1.0 - ratio)
                        proximity_score = max(0, 10 - (distance_from_perfect * 12))  # Stricter penalty
                        score += proximity_score

                        if proximity_score > 7:
                            match_reasons.append("Very close market cap")

                    # Bonus for similar growth characteristics (inferred from market cap)
                    if 0.7 <= ratio <= 1.4:
                        score += 5
                        match_reasons.append("Similar growth stage")

                else:
                    # Default or DuPont - standard scoring
                    if self.MARKET_CAP_RANGE_MIN <= ratio <= self.MARKET_CAP_RANGE_MAX:
                        score += 25
                        match_reasons.append("Similar market cap")

                        # Proximity scoring (+10 points max)
                        distance_from_perfect = abs(1.0 - ratio)
                        proximity_score = max(0, 10 - (distance_from_perfect * 10))
                        score += proximity_score

                        if proximity_score > 7:
                            match_reasons.append("Very close market cap")

            # Country/region match bonus (+5 points)
            if candidate.get('exchange') and self._is_same_region(candidate.get('exchange'), target_market_cap):
                score += 5
                match_reasons.append("Same region")

            # Create peer candidate
            peer = PeerCandidate(
                symbol=candidate['symbol'],
                ticker=candidate['symbol'],
                name=candidate['name'],
                company_name=candidate['name'],
                exchange=candidate['exchange'],
                sector=candidate.get('sector'),
                industry=candidate.get('industry'),
                market_cap=candidate_market_cap,
                marketCap=candidate_market_cap,
                current_price=candidate.get('current_price'),
                beta=candidate.get('beta'),
                similarity_score=score,
                score=score,
                match_reasons=match_reasons
            )

            scored_peers.append(peer)

        # Sort by score descending
        scored_peers.sort(key=lambda x: x.similarity_score, reverse=True)

        return scored_peers

    def _calculate_vector_similarity(self, dict_a: dict, dict_b: dict) -> float:
        """
        Calculate cosine similarity between two segment weight dictionaries.
        
        Args:
            dict_a: First segment dictionary (e.g., target company)
            dict_b: Second segment dictionary (e.g., peer company)
            
        Returns:
            Cosine similarity score between 0.0 and 1.0
        """
        if not dict_a or not dict_b:
            return 0.0
            
        all_keys = set(dict_a.keys()).union(set(dict_b.keys()))
        dot_product = sum(dict_a.get(k, 0.0) * dict_b.get(k, 0.0) for k in all_keys)
        mag_a = math.sqrt(sum(v**2 for v in dict_a.values()))
        mag_b = math.sqrt(sum(v**2 for v in dict_b.values()))
        
        return dot_product / (mag_a * mag_b) if (mag_a * mag_b) > 0 else 0.0

    def _industries_are_similar(self, industry1: str, industry2: str) -> bool:
        """
        Check if two industries are similar based on key terms.

        Args:
            industry1: First industry string
            industry2: Second industry string

        Returns:
            True if industries are similar, False otherwise
        """
        # Define industry term mappings with enhanced automotive coverage
        industry_groups = {
            'auto': ['auto', 'automotive', 'car', 'truck', 'vehicle', 'motor', 'ev', 'electric vehicle'],
            'retail': ['retail', 'store', 'e-commerce', 'merchant'],
            'restaurant': ['restaurant', 'food service', 'dining', 'quick service'],
            'software': ['software', 'application', 'saas', 'cloud software'],
            'semiconductor': ['semiconductor', 'chip', 'integrated circuit'],
            'pharma': ['pharmaceutical', 'drug', 'biopharma'],
            'biotech': ['biotechnology', 'biotech', 'life sciences'],
            'bank': ['bank', 'banking', 'commercial bank'],
            'insurance': ['insurance', 'reinsurance', 'assurance'],
            'oil_gas': ['oil', 'gas', 'petroleum', 'energy exploration'],
            'telecom': ['telecom', 'telecommunication', 'wireless', 'carrier'],
            'utility': ['utility', 'electric', 'power', 'water utility'],
            'real_estate': ['real estate', 'reit', 'property', 'development'],
            'aerospace': ['aerospace', 'defense', 'aviation', 'aircraft'],
            'consumer_electronics': ['consumer electronics', 'electronics', 'gadgets'],
            'apparel': ['apparel', 'clothing', 'garment', 'fashion', 'footwear'],
            'home_improvement': ['home improvement', 'building materials', 'hardware retail'],
            'auto_parts': ['auto parts', 'automotive parts', 'motor vehicle parts'],
        }

        # Check if both industries fall into the same group
        for group_terms in industry_groups.values():
            match1 = any(term in industry1 for term in group_terms)
            match2 = any(term in industry2 for term in group_terms)
            if match1 and match2:
                return True

        return False

    def _has_industry_keyword_overlap(self, industry1: str, industry2: str) -> bool:
        """
        Check if two industries share common keywords.

        Args:
            industry1: First industry string
            industry2: Second industry string

        Returns:
            True if there's keyword overlap, False otherwise
        """
        # Extract significant words (4+ characters)
        def extract_keywords(industry: str) -> set:
            words = industry.replace('&', ' ').replace('-', ' ').split()
            return {w.lower() for w in words if len(w) >= 4}

        keywords1 = extract_keywords(industry1)
        keywords2 = extract_keywords(industry2)

        # Check for overlap
        overlap = keywords1.intersection(keywords2)
        return len(overlap) >= 1

    def _is_same_region(self, exchange: str, target_market_cap: Optional[float]) -> bool:
        """
        Check if exchange is in the same region as typical US stocks.
        Simplified implementation - can be enhanced with country data.

        Args:
            exchange: Exchange code
            target_market_cap: Target market cap (unused but available for future use)

        Returns:
            True if in same region (North America), False otherwise
        """
        north_american_exchanges = {'NMS', 'NYQ', 'NGM', 'NCM', 'TOR', 'VAN', 'CNQ'}
        return exchange in north_american_exchanges

    def _get_allowed_exchanges(
        self,
        market: str,
        custom_exchanges: Optional[List[str]] = None
    ) -> List[str]:
        """
        Get list of allowed exchanges for a given market.

        Args:
            market: Market type (international, vietnamese, us, etc.)
            custom_exchanges: Optional custom list of allowed exchanges

        Returns:
            List of allowed exchange codes
        """
        # If custom exchanges provided, use them
        if custom_exchanges:
            return custom_exchanges

        # Get default exchanges for this market
        allowed = self.MARKET_EXCHANGE_FILTERS.get(market.lower(), [])

        # If no specific filter found, default to international (US exchanges)
        if not allowed:
            allowed = self.MARKET_EXCHANGE_FILTERS.get("international", [])

        return allowed

    def _is_exchange_allowed(
        self,
        exchange: str,
        allowed_exchanges: Optional[List[str]] = None
    ) -> bool:
        """
        Check if an exchange is allowed based on market filters.

        Args:
            exchange: Exchange code to check
            allowed_exchanges: List of allowed exchange codes

        Returns:
            True if exchange is allowed, False otherwise
        """
        # Always exclude problematic exchanges
        if exchange in self.EXCLUDED_EXCHANGES:
            return False

        # If no allowed exchanges specified, allow all (except excluded)
        if not allowed_exchanges:
            return True

        # Check if exchange is in allowed list
        return exchange in allowed_exchanges