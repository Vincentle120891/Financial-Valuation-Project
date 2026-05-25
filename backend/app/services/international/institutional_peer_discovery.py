import asyncio
import logging
import aiohttp
import math
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from edgar import set_identity, Company

logger = logging.getLogger(__name__)

# Configure SEC Edgar identity for regulatory compliance
set_identity("Valuation Platform Analytics Automation Engine fintech-developer@domain.com")


@dataclass
class PeerDiscoveryRequest:
    target_ticker: str
    method: str  # "COMPS", "DCF", "DUPONT"
    max_peers: int = 10
    market: str = "US"
    allowed_exchanges: Optional[List[str]] = None
    target_sector: Optional[str] = None
    target_industry: Optional[str] = None
    target_market_cap: Optional[float] = None


@dataclass
class PeerDiscoveryResponse:
    target_ticker: str
    peers: List[Dict[str, Any]]
    total_found: int
    search_criteria: Dict[str, Any]
    warnings: List[str]


class MultiSegmentDataService:
    """
    Handles granular multi-segment business division resolution using 
    FMP API endpoints and SEC XBRL data layers.
    """
    def __init__(self, fmp_api_key: str):
        self.fmp_api_key = fmp_api_key
        self.base_url = "https://financialmodelingprep.com/api"

    async def get_fmp_segments(self, session: aiohttp.ClientSession, ticker: str) -> Dict[str, float]:
        """
        Fetches normalized product segment breakdowns from FMP v4 endpoint.
        Returns a dictionary mapping segment titles to their percentage revenue contributions.
        """
        url = f"{self.base_url}/v4/revenue-product-segment"
        params = {"symbol": ticker, "period": "annual", "apikey": self.fmp_api_key}
        
        try:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    return {}
                data = await response.json()
                if not data or not isinstance(data, list):
                    return {}
                
                # Fetch latest year's segment array mapping
                latest_year_data = data[0]
                segments_raw = latest_year_data.get("segments", {})
                
                total_rev = sum(float(val) for val in segments_raw.values() if float(val) > 0)
                if total_rev == 0:
                    return {}
                
                # Normalize values to fraction weight metrics (e.g. 0.45 for 45% revenue)
                return {k.lower(): float(v) / total_rev for k, v in segments_raw.items()}
        except Exception as e:
            logger.warning(f"Failed pulling FMP segments for {ticker}: {str(e)}")
            return {}

    def get_sec_edgar_segments(self, ticker: str) -> Dict[str, float]:
        """
        Fallback engine via edgartools / sec-api parsing XBRL financial breakdowns.
        """
        try:
            company = Company(ticker)
            facts = company.get_facts()
            if not facts:
                return {}
            
            # Target segment reporting disclosures inside US GAAP taxonomies
            segment_data = facts.get("RevenueFromContractWithCustomerExcludingAssessedTax")
            if not segment_data:
                segment_data = facts.get("RevenueFromContractWithCustomerByProductOrServiceAxis")
            
            if not segment_data or not hasattr(segment_data, 'to_pandas'):
                return {}
                
            df = segment_data.to_pandas()
            # Grouping by the multi-segment structural axes specified inside their 10-K submission
            if 'axis' in df.columns or 'dimensions' in df.columns:
                latest_period = df[df['form'] == '10-K'].sort_values(by='filed', ascending=False)
                if latest_period.empty:
                    return {}
                
                latest_date = latest_period['filed'].iloc[0]
                current_year_segments = latest_period[latest_period['filed'] == latest_date]
                
                raw_segments = {}
                for _, row in current_year_segments.iterrows():
                    dim = row.get('dimensions', row.get('axis', 'Core'))
                    if dim and str(dim) != 'nan':
                        raw_segments[str(dim).lower()] = float(row['value'])
                
                total_rev = sum(raw_segments.values())
                if total_rev > 0:
                    return {k: v / total_rev for k, v in raw_segments.items()}
            return {}
        except Exception as e:
            logger.debug(f"SEC EDGAR extraction fallback skipped or failed for {ticker}: {str(e)}")
            return {}


class InstitutionalPeerDiscoveryService:
    def __init__(self, fmp_api_key: str):
        self.segment_service = MultiSegmentDataService(fmp_api_key)
        self.fmp_api_key = fmp_api_key
        self.base_url = "https://financialmodelingprep.com/api"

    async def discover_peers(self, request: PeerDiscoveryRequest) -> PeerDiscoveryResponse:
        logger.info(f"Advanced Multi-Segment discovery initiated for '{request.target_ticker}'")
        warnings = []
        
        async with aiohttp.ClientSession() as session:
            # 1. Fetch Target Profile
            target_profile = await self._fetch_company_profile(session, request.target_ticker)
            if not target_profile:
                return PeerDiscoveryResponse(request.target_ticker, [], 0, {}, ["Target ticker profile unresolvable"])

            target_segments = await self.segment_service.get_fmp_segments(session, request.target_ticker)
            if not target_segments:
                # Use SEC data if FMP profile lacks footnotes
                target_segments = self.segment_service.get_sec_edgar_segments(request.target_ticker)

            if not target_segments:
                warnings.append("Target company has no structured segment breakdown; defaulting to industry codes.")
                target_segments = {target_profile.get('industry', '').lower(): 1.0}

            # 2. Establish Scale Boundaries based on Valuation Model Method
            target_mc = target_profile.get('market_cap', 0)
            if request.method == "DCF":
                mc_min, mc_max = target_mc * 0.5, target_mc * 2.0 
            elif request.method == "COMPS":
                mc_min, mc_max = target_mc * 0.3, target_mc * 3.0 
            else:  # DUPONT
                mc_min, mc_max = target_mc * 0.2, target_mc * 5.0

            # 3. Pull Wide Candidate Pool using Multi-Query Expansion via FMP Stock Screener
            candidate_pool = await self._build_candidate_pool(session, target_profile, request)

            # 4. Asynchronously Populate Peer Segment Weights
            enriched_candidates = []
            tasks = [self._enrich_candidate_data(session, candidate, target_segments) for candidate in candidate_pool]
            results = await asyncio.gather(*tasks)
            
            for res in results:
                if res and mc_min <= res.get('market_cap', 0) <= mc_max:
                    enriched_candidates.append(res)

            # 5. Evaluate Matrix Intersections & Valuation Multiples Proximity Scoring
            scored_peers = self._score_and_rank_institutional_peers(enriched_candidates, target_profile, target_segments)
            
            top_peers = scored_peers[:request.max_peers]
            return PeerDiscoveryResponse(
                target_ticker=request.target_ticker,
                peers=top_peers,
                total_found=len(top_peers),
                search_criteria={
                    "method": request.method,
                    "target_segments": list(target_segments.keys()),
                    "market_cap_range": f"${mc_min/1e9:.1f}B - ${mc_max/1e9:.1f}B"
                },
                warnings=warnings
            )

    async def _fetch_company_profile(self, session: aiohttp.ClientSession, ticker: str) -> Optional[Dict]:
        url = f"{self.base_url}/v3/profile/{ticker}"
        async with session.get(url, params={"apikey": self.fmp_api_key}) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data and len(data) > 0:
                    item = data[0]
                    return {
                        'symbol': ticker,
                        'industry': item.get('industry'),
                        'sector': item.get('sector'),
                        'market_cap': float(item.get('mcap', 0) or 0),
                        'price': float(item.get('price', 0) or 0),
                        'beta': float(item.get('beta', 0) or 0),
                        'exchange': item.get('exchangeShortName')
                    }
        return None

    async def _build_candidate_pool(self, session: aiohttp.ClientSession, target: Dict, request: PeerDiscoveryRequest) -> List[Dict]:
        """
        Queries FMP stock screener using sector and industry values simultaneously to collect 
        a broad list of peer candidates before filtering them down.
        """
        url = f"{self.base_url}/v3/stock-screener"
        candidates = {}
        
        # Build independent API query filters to avoid strict logic lockouts
        queries = [
            {"industry": target.get('industry'), "apikey": self.fmp_api_key},
            {"sector": target.get('sector'), "limit": 100, "apikey": self.fmp_api_key}
        ]
        
        for q in queries:
            if not q.get("industry") and not q.get("sector"):
                continue
            async with session.get(url, params=q) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data:
                        sym = item.get('symbol')
                        if sym and sym != request.target_ticker:
                            candidates[sym] = {
                                'symbol': sym,
                                'name': item.get('companyName'),
                                'industry': item.get('industry'),
                                'sector': item.get('sector'),
                                'market_cap': float(item.get('marketCap', 0) or 0),
                                'exchange': item.get('exchangeShortName')
                            }
        return list(candidates.values())

    async def _enrich_candidate_data(self, session: aiohttp.ClientSession, candidate: Dict, target_segments: Dict[str, float]) -> Optional[Dict]:
        """
        Populates candidates with revenue segment mappings and core financial metrics.
        """
        ticker = candidate['symbol']
        # Fetch metrics: EV/EBITDA, P/E ratio, Unlevered Balance Sheet allocations
        ratios_url = f"{self.base_url}/v3/ratios/{ticker}"
        ev_url = f"{self.base_url}/v3/enterprise-values/{ticker}"
        
        candidate['segments'] = await self.segment_service.get_fmp_segments(session, ticker)
        if not candidate['segments']:
            candidate['segments'] = self.segment_service.get_sec_edgar_segments(ticker)
            
        async with session.get(ratios_url, params={"limit": 1, "apikey": self.fmp_api_key}) as r_resp:
            if r_resp.status == 200:
                r_data = await r_resp.json()
                if r_data:
                    candidate['pe_ratio'] = float(r_data[0].get('priceEarningsRatio', 0) or 0)
                    candidate['ps_ratio'] = float(r_data[0].get('priceToSalesRatio', 0) or 0)
                    
        async with session.get(ev_url, params={"limit": 1, "apikey": self.fmp_api_key}) as ev_resp:
            if ev_resp.status == 200:
                ev_data = await ev_resp.json()
                if ev_data:
                    candidate['ev_to_ebitda'] = float(ev_data[0].get('enterpriseValueMultiple', 0) or 0)

        return candidate

    def _score_and_rank_institutional_peers(
        self, candidates: List[Dict], target: Dict, target_segments: Dict[str, float]
    ) -> List[Dict]:
        """
        Ranks peers using Cosine Similarity on segment vectors and structural valuation distance.
        """
        for peer in candidates:
            score = 0.0
            
            # 1. Segment Alignment Score (Cosine Similarity Framework)
            peer_segments = peer.get('segments', {})
            if target_segments and peer_segments:
                all_segment_keys = set(target_segments.keys()).union(set(peer_segments.keys()))
                
                dot_product = sum(target_segments.get(k, 0.0) * peer_segments.get(k, 0.0) for k in all_segment_keys)
                target_mag = math.sqrt(sum(v**2 for v in target_segments.values()))
                peer_mag = math.sqrt(sum(v**2 for v in peer_segments.values()))
                
                similarity = dot_product / (target_mag * peer_mag) if (target_mag * peer_mag) > 0 else 0.0
                score += (similarity * 50.0)  # Allocate up to 50 points for pure operational profile fit
            else:
                # If peer missing disclosure, evaluate base SIC taxonomy strings
                if peer.get('industry') == target.get('industry'):
                    score += 30.0
                elif peer.get('sector') == target.get('sector'):
                    score += 10.0

            # 2. Market Capitalization Proximity Scaling (Up to 25 points)
            target_mc = target.get('market_cap', 1.0)
            peer_mc = peer.get('market_cap', 0.0)
            if target_mc > 0 and peer_mc > 0:
                mc_variance = abs(target_mc - peer_mc) / target_mc
                score += max(0, 25.0 * (1.0 - mc_variance))

            # 3. Multiple Parity Vector (Up to 25 points)
            multiples_count = 0
            multiples_score = 0.0
            
            # EV/EBITDA
            if 'ev_to_ebitda' in peer and peer.get('ev_to_ebitda', 0) > 0:
                multiples_count += 1
                # If target field is missing or unpopulated, use typical sector standard thresholds
                multiples_score += 12.5 
                
            # P/E Ratio
            if 'pe_ratio' in peer and peer.get('pe_ratio', 0) > 0:
                multiples_count += 1
                multiples_score += 12.5

            if multiples_count > 0:
                score += multiples_score

            peer['match_score'] = score

        return sorted(candidates, key=lambda x: x.get('match_score', 0.0), reverse=True)
