"""
Peer Discovery Service
Automatically identifies peer companies based on industry, sector, and market cap.
"""

import logging
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel

from app.services.international.yfinance_service import YFinanceService

logger = logging.getLogger(__name__)


class PeerCandidate(BaseModel):
    """Peer candidate company."""
    symbol: str
    name: str
    exchange: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    current_price: Optional[float] = None
    beta: Optional[float] = None
    similarity_score: float = 0.0
    match_reasons: List[str] = []


class PeerDiscoveryRequest(BaseModel):
    """Request for peer discovery."""
    target_ticker: str
    target_sector: Optional[str] = None
    target_industry: Optional[str] = None
    target_market_cap: Optional[float] = None
    max_peers: int = 10
    market: str = "international"


class PeerDiscoveryResponse(BaseModel):
    """Response from peer discovery."""
    target_ticker: str
    peers: List[PeerCandidate]
    total_found: int
    search_criteria: Dict
    warnings: List[str] = []


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
    
    def __init__(self, yfinance_service: Optional[YFinanceService] = None):
        self.yfinance_service = yfinance_service or YFinanceService()
        self._industry_cache: Dict[str, List[Dict]] = {}
        self._sector_cache: Dict[str, List[Dict]] = {}
    
    async def discover_peers(
        self,
        request: PeerDiscoveryRequest
    ) -> PeerDiscoveryResponse:
        """
        Discover peer companies for a target ticker.
        
        Args:
            request: Peer discovery request with target company info
            
        Returns:
            PeerDiscoveryResponse with ranked peer candidates
        """
        logger.info(f"Discovering peers for '{request.target_ticker}'")
        
        warnings = []
        
        # Get target company info if not provided
        target_sector = request.target_sector
        target_industry = request.target_industry
        target_market_cap = request.target_market_cap
        
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
                    'market_cap_range': None
                },
                warnings=warnings
            )
        
        # Determine market cap range
        market_cap_min = None
        market_cap_max = None
        if target_market_cap:
            market_cap_min = target_market_cap * self.MARKET_CAP_RANGE_MIN
            market_cap_max = target_market_cap * self.MARKET_CAP_RANGE_MAX
        
        search_criteria = {
            'sector': target_sector,
            'industry': target_industry,
            'market_cap_range': f"${market_cap_min/1e9:.1f}B - ${market_cap_max/1e9:.1f}B" if market_cap_min else "Any"
        }
        
        # Search for peers
        peer_candidates = await self._search_peer_candidates(
            sector=target_sector,
            industry=target_industry,
            market_cap_min=market_cap_min,
            market_cap_max=market_cap_max,
            exclude_ticker=request.target_ticker,
            max_results=request.max_peers * 3  # Get more to filter and rank
        )
        
        # Score and rank candidates
        scored_peers = self._score_and_rank_peers(
            candidates=peer_candidates,
            target_sector=target_sector,
            target_industry=target_industry,
            target_market_cap=target_market_cap
        )
        
        # Return top N peers
        top_peers = scored_peers[:request.max_peers]
        
        if len(top_peers) < request.max_peers:
            warnings.append(f"Only found {len(top_peers)} suitable peers out of {request.max_peers} requested")
        
        return PeerDiscoveryResponse(
            target_ticker=request.target_ticker,
            peers=top_peers,
            total_found=len(top_peers),
            search_criteria=search_criteria,
            warnings=warnings
        )
    
    async def _search_peer_candidates(
        self,
        sector: Optional[str],
        industry: Optional[str],
        market_cap_min: Optional[float],
        market_cap_max: Optional[float],
        exclude_ticker: str,
        max_results: int = 30
    ) -> List[Dict]:
        """
        Search for peer candidates using multiple strategies.
        
        Args:
            sector: Target sector
            industry: Target industry
            market_cap_min: Minimum market cap
            market_cap_max: Maximum market cap
            exclude_ticker: Ticker to exclude from results
            max_results: Maximum number of results to return
            
        Returns:
            List of candidate company dictionaries
        """
        candidates = []
        seen_tickers = set([exclude_ticker])
        
        # Strategy 1: Search by industry keywords
        if industry:
            industry_candidates = await self._search_by_keyword(
                keyword=industry,
                market_cap_min=market_cap_min,
                market_cap_max=market_cap_max,
                exclude_tickers=seen_tickers
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
                exclude_tickers=seen_tickers
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
                exclude_tickers=seen_tickers
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
        exclude_tickers: set
    ) -> List[Dict]:
        """
        Search for companies by keyword using yfinance.
        
        Args:
            keyword: Search keyword (industry or sector name)
            market_cap_min: Minimum market cap
            market_cap_max: Maximum market cap
            exclude_tickers: Set of tickers to exclude
            
        Returns:
            List of matching company dictionaries
        """
        results = []
        
        # Use yfinance search (now filtered in yfinance_service.search_tickers)
        search_results = self.yfinance_service.search_tickers(keyword)
        
        for result in search_results[:20]:  # Limit search results
            ticker = result.get('symbol', '')
            
            if ticker in exclude_tickers:
                continue
            
            # Get detailed info
            ticker_info = self.yfinance_service.get_ticker_info(ticker)
            if not ticker_info or not ticker_info.get('currentPrice'):
                logger.debug(f"Skipping {ticker}: no current price or info")
                continue
            
            # Additional validation: check if it's a valid equity
            market_cap = ticker_info.get('marketCap')
            if not market_cap or market_cap <= 0:
                logger.debug(f"Skipping {ticker}: invalid market cap")
                continue
            
            # Filter by market cap if range specified
            if market_cap_min and market_cap_max:
                if not (market_cap_min <= market_cap <= market_cap_max):
                    logger.debug(f"Skipping {ticker}: market cap ${market_cap/1e9:.2f}B outside range ${market_cap_min/1e9:.2f}B-${market_cap_max/1e9:.2f}B")
                    continue
            
            results.append({
                'symbol': ticker,
                'name': ticker_info.get('longName', ticker),
                'exchange': ticker_info.get('exchange', 'UNKNOWN'),
                'sector': ticker_info.get('sector'),
                'industry': ticker_info.get('industry'),
                'market_cap': market_cap,
                'current_price': ticker_info.get('currentPrice'),
                'beta': ticker_info.get('beta')
            })
        
        return results
    
    async def _get_fallback_peers(
        self,
        sector: Optional[str],
        industry: Optional[str],
        exclude_tickers: set
    ) -> List[Dict]:
        """
        Get fallback peers from known company lists by sector.
        
        Args:
            sector: Target sector
            industry: Target industry
            exclude_tickers: Set of tickers to exclude
            
        Returns:
            List of fallback peer candidates
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
            for ticker in fallback_companies[sector_key]:
                if ticker in exclude_tickers:
                    continue
                
                ticker_info = self.yfinance_service.get_ticker_info(ticker)
                if not ticker_info or not ticker_info.get('currentPrice'):
                    continue
                
                results.append({
                    'symbol': ticker,
                    'name': ticker_info.get('longName', ticker),
                    'exchange': ticker_info.get('exchange', 'UNKNOWN'),
                    'sector': ticker_info.get('sector'),
                    'industry': ticker_info.get('industry'),
                    'market_cap': ticker_info.get('marketCap'),
                    'current_price': ticker_info.get('currentPrice'),
                    'beta': ticker_info.get('beta')
                })
        
        return results
    
    def _score_and_rank_peers(
        self,
        candidates: List[Dict],
        target_sector: Optional[str],
        target_industry: Optional[str],
        target_market_cap: Optional[float]
    ) -> List[PeerCandidate]:
        """
        Score and rank peer candidates.
        
        Scoring methodology:
        - Industry match: +40 points
        - Sector match: +20 points  
        - Market cap within range: +30 points
        - Market cap proximity: +10 points (closer = higher)
        
        Args:
            candidates: List of candidate companies
            target_sector: Target company sector
            target_industry: Target company industry
            target_market_cap: Target company market cap
            
        Returns:
            List of scored and ranked PeerCandidate objects
        """
        scored_peers = []
        
        for candidate in candidates:
            score = 0.0
            match_reasons = []
            
            # Industry match (+40 points)
            if target_industry and candidate.get('industry'):
                if candidate['industry'].lower() == target_industry.lower():
                    score += 40
                    match_reasons.append("Same industry")
            
            # Sector match (+20 points)
            if target_sector and candidate.get('sector'):
                if candidate['sector'].lower() == target_sector.lower():
                    score += 20
                    if "Same industry" not in match_reasons:
                        match_reasons.append("Same sector")
            
            # Market cap range match (+30 points)
            candidate_market_cap = candidate.get('market_cap')
            if target_market_cap and candidate_market_cap:
                ratio = candidate_market_cap / target_market_cap
                if self.MARKET_CAP_RANGE_MIN <= ratio <= self.MARKET_CAP_RANGE_MAX:
                    score += 30
                    match_reasons.append("Similar market cap")
                    
                    # Proximity scoring (+10 points max)
                    # Perfect match = 1.0 ratio gets full 10 points
                    distance_from_perfect = abs(1.0 - ratio)
                    proximity_score = max(0, 10 - (distance_from_perfect * 10))
                    score += proximity_score
                    
                    if proximity_score > 7:
                        match_reasons.append("Very close market cap")
            
            # Create peer candidate
            peer = PeerCandidate(
                symbol=candidate['symbol'],
                name=candidate['name'],
                exchange=candidate['exchange'],
                sector=candidate.get('sector'),
                industry=candidate.get('industry'),
                market_cap=candidate_market_cap,
                current_price=candidate.get('current_price'),
                beta=candidate.get('beta'),
                similarity_score=score,
                match_reasons=match_reasons
            )
            
            scored_peers.append(peer)
        
        # Sort by score descending
        scored_peers.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return scored_peers
