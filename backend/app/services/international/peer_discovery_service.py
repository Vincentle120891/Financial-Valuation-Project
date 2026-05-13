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
    allowed_exchanges: Optional[List[str]] = None  # Explicitly allowed exchanges


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
            'market_cap_range': f"${market_cap_min/1e9:.1f}B - ${market_cap_max/1e9:.1f}B" if market_cap_min else "Any",
            'allowed_exchanges': request.allowed_exchanges
        }
        
        # Determine allowed exchanges for this market
        allowed_exchanges = self._get_allowed_exchanges(request.market, request.allowed_exchanges)
        
        # Search for peers
        peer_candidates = await self._search_peer_candidates(
            sector=target_sector,
            industry=target_industry,
            market_cap_min=market_cap_min,
            market_cap_max=market_cap_max,
            exclude_ticker=request.target_ticker,
            max_results=request.max_peers * 3,  # Get more to filter and rank
            allowed_exchanges=allowed_exchanges
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
        max_results: int = 30,
        allowed_exchanges: Optional[List[str]] = None
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
            allowed_exchanges: List of allowed exchange codes
            
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
        Search for companies by keyword using yfinance.
        
        Args:
            keyword: Search keyword (industry or sector name)
            market_cap_min: Minimum market cap
            market_cap_max: Maximum market cap
            exclude_tickers: Set of tickers to exclude
            allowed_exchanges: List of allowed exchange codes
            
        Returns:
            List of matching company dictionaries
        """
        results = []
        
        # Generate multiple search queries from the keyword
        # yfinance search works better with shorter, simpler queries
        search_queries = self._generate_search_queries(keyword)
        
        seen_symbols = set()
        
        for query in search_queries:
            # Use yfinance search (now filtered in yfinance_service.search_tickers)
            search_results = self.yfinance_service.search_tickers(query)
            
            for result in search_results[:20]:  # Limit search results per query
                ticker = result.get('symbol', '')
                exchange = result.get('exchange', '')
                
                if ticker in exclude_tickers or ticker in seen_symbols:
                    continue
                
                # EXCHANGE FILTERING: Check if exchange is allowed
                if not self._is_exchange_allowed(exchange, allowed_exchanges):
                    logger.debug(f"Excluding {ticker}: exchange '{exchange}' not in allowed list")
                    continue
                
                seen_symbols.add(ticker)
                
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
                    'exchange': exchange,
                    'sector': ticker_info.get('sector'),
                    'industry': ticker_info.get('industry'),
                    'market_cap': market_cap,
                    'current_price': ticker_info.get('currentPrice'),
                    'beta': ticker_info.get('beta')
                })
                
                # Stop if we have enough results
                if len(results) >= 20:
                    break
            
            if len(results) >= 20:
                break
        
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
        industry_mappings = {
            'auto manufacturers': ['Auto', 'Automotive', 'Cars', 'Trucks'],
            'automotive': ['Auto', 'Automotive', 'Cars'],
            'drug manufacturers': ['Pharma', 'Drugs', 'Pharmaceuticals'],
            'software': ['Software', 'Technology'],
            'semiconductors': ['Semiconductor', 'Chips', 'Semis'],
            'biotechnology': ['Biotech', 'Biotechnology'],
            'oil & gas': ['Oil', 'Gas', 'Energy'],
            'banks': ['Bank', 'Banking'],
            'insurance': ['Insurance'],
            'retail': ['Retail', 'Stores'],
            'restaurants': ['Restaurant', 'Food'],
            'aerospace & defense': ['Aerospace', 'Defense', 'Aviation'],
            'telecom services': ['Telecom', 'Communication'],
            'utilities': ['Utilities', 'Electric', 'Power'],
            'real estate': ['Real Estate', 'REIT', 'Property'],
            'consumer electronics': ['Electronics', 'Consumer'],
            'apparel manufacturing': ['Apparel', 'Clothing', 'Fashion'],
            'footwear & accessories': ['Footwear', 'Shoes', 'Apparel'],
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
        
        Args:
            sector: Target sector
            industry: Target industry
            exclude_tickers: Set of tickers to exclude
            allowed_exchanges: List of allowed exchange codes
            
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
                
                # Check exchange filtering
                exchange = ticker_info.get('exchange', '')
                if not self._is_exchange_allowed(exchange, allowed_exchanges):
                    logger.debug(f"Excluding fallback peer {ticker}: exchange '{exchange}' not allowed")
                    continue
                
                results.append({
                    'symbol': ticker,
                    'name': ticker_info.get('longName', ticker),
                    'exchange': exchange,
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
        
        Scoring methodology (enhanced with sub-industry weighting):
        - Sub-industry match (exact): +50 points
        - Industry match (general): +30 points
        - Sector match: +15 points
        - Market cap within range: +25 points
        - Market cap proximity: +10 points (closer = higher)
        - Same country/region: +5 points
        
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
            
            # INDUSTRY MATCHING WITH SUB-INDUSTRY WEIGHTING
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
                    # Check for keyword overlap as fallback (+15 points)
                    if self._has_industry_keyword_overlap(target_industry_lower, cand_industry):
                        score += 15
                        match_reasons.append("Related industry")
            
            # Sector match (+15 points)
            if target_sector and candidate.get('sector'):
                if candidate['sector'].lower() == target_sector.lower():
                    score += 15
                    if not any("industry" in reason.lower() for reason in match_reasons):
                        match_reasons.append("Same sector")
            
            # Market cap range match (+25 points)
            candidate_market_cap = candidate.get('market_cap')
            if target_market_cap and candidate_market_cap:
                ratio = candidate_market_cap / target_market_cap
                if self.MARKET_CAP_RANGE_MIN <= ratio <= self.MARKET_CAP_RANGE_MAX:
                    score += 25
                    match_reasons.append("Similar market cap")
                    
                    # Proximity scoring (+10 points max)
                    # Perfect match = 1.0 ratio gets full 10 points
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
    
    def _industries_are_similar(self, industry1: str, industry2: str) -> bool:
        """
        Check if two industries are similar based on key terms.
        
        Args:
            industry1: First industry string
            industry2: Second industry string
            
        Returns:
            True if industries are similar, False otherwise
        """
        # Define industry term mappings
        industry_groups = {
            'auto': ['auto', 'automotive', 'car', 'truck', 'vehicle', 'motor'],
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
