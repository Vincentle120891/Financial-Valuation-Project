import os
import sqlite3
import logging
import requests
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from fastapi import Request

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("MARKET_DATABASE_PATH", "market_universe.db")


def get_fmp_api_key(request: Optional[Request] = None) -> str:
    """
    Get FMP API key with priority: request header > environment variable > default.

    Args:
        request: FastAPI request object (optional)

    Returns:
        API key from request header if available, else from environment, else default
    """
    # Priority 1: Check request state (from header)
    if request:
        api_keys = getattr(request.state, 'api_keys', {})
        request_key = api_keys.get('fmp')
        if request_key:
            logger.debug("Using FMP API key from request header")
            return request_key

    # Priority 2: Fallback to environment variable
    env_key = os.getenv('FMP_API_KEY')
    if env_key:
        logger.debug("Using FMP API key from environment variable")
        return env_key

    # Priority 3: Default fallback (for backward compatibility)
    default_key = "meq65Y3F8YP1LRdtqHQHLu6s0RmHSISL"
    logger.warning(f"FMP API key not configured, using default key")
    return default_key


class PeerDiscoveryRequest(BaseModel):
    """Request for peer discovery."""
    target_ticker: str
    method: Optional[str] = None  # DCF, COMPS, DuPont
    max_peers: int = 10
    market: str = "international"


class PeerCandidate(BaseModel):
    """Peer candidate company."""
    symbol: str
    ticker: str
    name: str
    company_name: str
    exchange: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    marketCap: Optional[float] = None
    match_score: float = 0.0
    segments: Dict[str, Any] = {}
    pe_ratio: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    ps_ratio: Optional[float] = None
    match_reasons: List[str] = []


class PeerDiscoveryResponse(BaseModel):
    """Response from peer discovery."""
    target_ticker: str
    peers: List[PeerCandidate]
    total_found: int
    search_criteria: Dict
    warnings: List[str] = []


def extract_market_context(symbol: str) -> tuple[str, str]:
    """
    Normalizes symbols into a clean ticker and country suffix for fallback alignment.
    e.g., '7203.T' -> ('7203', 'JP'), 'VNM.VN' -> ('VNM', 'VN'), 'F' -> ('F', 'US')
    """
    parts = symbol.upper().split('.')
    if len(parts) == 2:
        # Standard corporate syntax for international tracking
        ticker, ext = parts[0], parts[1]
        country = 'JP' if ext in ['T', 'TYO'] else ('VN' if ext in ['VN', 'HNX', 'HOSE'] else ext)
        return ticker, country
    return parts[0], 'US'


def _get_live_fmp_peers(symbol: str, request: Optional[Request] = None) -> list[dict]:
    """Primary Option B Strategy: Hits the pre-computed relationships engine

    Returns list of dicts with peer data from stable/stock-peers endpoint:
    [{'symbol': 'AZO', 'companyName': 'AutoZone, Inc.', 'price': 3007.08, 'mktCap': 49222892520}, ...]
    """
    api_key = get_fmp_api_key(request)

    # Try multiple FMP endpoints in order of preference
    endpoints = [
        f"https://financialmodelingprep.com/api/v4/stock_peers?symbol={symbol}&apikey={api_key}",  # V4 API (legacy)
        f"https://financialmodelingprep.com/stable/stock-peers?symbol={symbol}&apikey={api_key}",  # Stable API (working)
    ]

    for url in endpoints:
        logger.info(f"Attempting FMP API call: {url[:80]}...")
        try:
            response = requests.get(url, timeout=7)
            logger.info(f"FMP API Response Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.debug(f"FMP API Raw Response: {str(data)[:200]}")

                # Handle different response formats
                if data and isinstance(data, list):
                    # Format 1: Direct list of peer objects [{"symbol": "AZO", "companyName": "...", "price": ..., "mktCap": ...}]
                    if isinstance(data[0], dict) and "symbol" in data[0]:
                        # Return the full peer objects, not just symbols
                        peers = [item for item in data if isinstance(item, dict) and "symbol" in item]
                        if peers:
                            logger.info(f"Option B Succeeded (Format 1): Retrieved {len(peers)} peers for {symbol}")
                            return peers

                    # Format 2: Wrapped in "peers" key [{"peers": [...]}]
                    if isinstance(data[0], dict) and "peers" in data[0]:
                        peers = data[0]["peers"]
                        if peers and isinstance(peers, list):
                            logger.info(f"Option B Succeeded (Format 2): Retrieved {len(peers)} peers for {symbol}")
                            return peers

                    # Format 3: Simple list of strings ["AAPL", "MSFT", ...]
                    if isinstance(data[0], str):
                        # Convert to minimal dict format
                        peers = [{"symbol": item, "companyName": item, "price": None, "mktCap": None} for item in data if isinstance(item, str)]
                        if peers:
                            logger.info(f"Option B Succeeded (Format 3): Retrieved {len(peers)} peers for {symbol}")
                            return peers

                # If we got a valid response but no peers, log it
                logger.warning(f"FMP API returned valid response but no peers for {symbol}. Response: {data}")
            else:
                logger.warning(f"FMP API returned status {response.status_code} for {symbol}. Response: {response.text[:200]}")

        except Exception as e:
            logger.warning(f"FMP API request failed for {symbol} on {url[:50]}...: {str(e)}")
            continue

    logger.warning(f"All FMP API endpoints failed for {symbol}, returning empty list")
    return []


def _get_local_fallback_peers(symbol: str) -> list[str]:
    """Backup Option A Strategy: Scans local cross-market tables if FMP fails"""
    logger.info(f"Triggering Option A Fallback: Querying local market database for {symbol}")

    if not os.path.exists(DB_PATH):
        logger.error(f"Fallback Failed: Local database '{DB_PATH}' does not exist.")
        return []

    _, target_country = extract_market_context(symbol)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. Fetch Target Metadata from Cache
        cursor.execute(
            "SELECT sector, industry, market_cap FROM market_universe WHERE symbol = ?",
            (symbol.upper(),)
        )
        target = cursor.fetchone()

        if not target:
            logger.warning(f"Option A Aborted: Target {symbol} not found in local cache.")
            conn.close()
            return []

        sector, industry, target_cap = target

        # 2. Establish Gatekeeper Hard Ranges
        min_cap = target_cap * 0.5
        max_cap = target_cap * 2.0

        # 3. Query the localized neighborhood table
        query = """
            SELECT symbol FROM market_universe
            WHERE sector = ?
              AND industry = ?
              AND country = ?
              AND market_cap BETWEEN ? AND ?
              AND symbol != ?
        """
        cursor.execute(query, (sector, industry, target_country, min_cap, max_cap, symbol.upper()))
        fallback_peers = [row[0] for row in cursor.fetchall()]

        conn.close()
        logger.info(f"Option A Successful: Located {len(fallback_peers)} matching peers via SQL constraints.")
        return fallback_peers

    except Exception as e:
        logger.error(f"Fallback Execution Failure on Option A: {str(e)}")
        return []


class InstitutionalPeerDiscoveryService:
    """
    Institutional-grade peer discovery service with dual-loop failover.

    Execution Flow:
    1. Try Live Option B: FMP /stable/peers endpoint
    2. If fails/empty: Trigger Fallback Option A: Local SQLite DB
    3. Normalize candidates and fetch profiles
    4. Return verified peer profiles for soft scoring
    """

    def __init__(self, fmp_api_key: Optional[str] = None, request: Optional[Request] = None):
        """Initialize with optional FMP API key or request object."""
        self.request = request
        self.fmp_api_key = fmp_api_key or get_fmp_api_key(request)

    async def discover_peers(self, request_obj: PeerDiscoveryRequest) -> PeerDiscoveryResponse:
        """
        Master discovery method executing Option B with Option A failover.

        Args:
            request_obj: PeerDiscoveryRequest with target ticker and method

        Returns:
            PeerDiscoveryResponse with ranked peer candidates
        """
        target_symbol = request_obj.target_ticker.upper()
        _, target_country = extract_market_context(target_symbol)

        warnings = []
        search_criteria = {
            'method': request_obj.method,
            'market': request_obj.market,
            'target_country': target_country
        }

        # --- STEP 1: Execute Option B Strategy ---
        candidate_symbols = _get_live_fmp_peers(target_symbol, self.request)

        # --- STEP 2: Automated Hybrid Transition ---
        if not candidate_symbols:
            warnings.append("Option B (FMP API) returned no results. Triggering Option A fallback.")
            candidate_symbols = _get_local_fallback_peers(target_symbol)

        if not candidate_symbols:
            logger.error(f"Peer discovery pipeline completely exhausted for {target_symbol}. Returning 0 assets.")
            return PeerDiscoveryResponse(
                target_ticker=target_symbol,
                peers=[],
                total_found=0,
                search_criteria=search_criteria,
                warnings=warnings + ["No peers found via Option B or Option A"]
            )

        # --- STEP 3: Normalize Candidates & Fetch Profiles (Hybrid Best-Effort) ---
        verified_peers = []

        for symbol in candidate_symbols:
            # Prevent cross-contamination: Ensure peers align with target country
            _, peer_country = extract_market_context(symbol)
            if peer_country != target_country:
                continue

            # Hybrid Approach: Try to fetch profile, but accept peer even if it fails
            profile_data = None
            profile_fetch_success = False
            exchange = "UNKNOWN"

            # Use the stable stock-peers endpoint data if available (already fetched)
            # The stock-peers endpoint returns: symbol, companyName, price, mktCap
            # We'll use this as fallback and try to enhance with profile data
            peer_from_list = next((p for p in candidate_symbols if isinstance(p, dict) and p.get('symbol') == symbol), None)

            # Try multiple profile endpoints (legacy -> stable)
            profile_endpoints = [
                f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={self.fmp_api_key}",
                f"https://financialmodelingprep.com/stable/company-profile?symbol={symbol}&apikey={self.fmp_api_key}",
            ]

            for profile_url in profile_endpoints:
                try:
                    p_resp = requests.get(profile_url, timeout=5)
                    if p_resp.status_code == 200:
                        p_resp_json = p_resp.json()
                        if p_resp_json and isinstance(p_resp_json, list) and len(p_resp_json) > 0:
                            profile_data = p_resp_json[0]
                            profile_fetch_success = True
                            exchange = profile_data.get("exchangeShortName", "UNKNOWN")
                            logger.info(f"Profile fetched successfully for {symbol} via {profile_url[:60]}...")
                            break
                        elif p_resp_json and isinstance(p_resp_json, dict) and "companyName" in p_resp_json:
                            # Handle single object response format
                            profile_data = p_resp_json
                            profile_fetch_success = True
                            exchange = profile_data.get("exchangeShortName", "UNKNOWN")
                            logger.info(f"Profile fetched successfully for {symbol} via {profile_url[:60]}...")
                            break
                    else:
                        logger.debug(f"Profile fetch returned status {p_resp.status_code} for {symbol} on {profile_url[:50]}...")
                except Exception as e:
                    logger.debug(f"Profile fetch failed for {symbol} on {profile_url[:50]}...: {e}")
                    continue

            if not profile_fetch_success:
                logger.warning(f"Profile fetch failed for {symbol}, accepting as unverified peer (Hybrid Mode)")
                # Create minimal profile from symbol only, using data from stock-peers endpoint if available
                profile_data = {
                    "companyName": peer_from_list.get('companyName', symbol) if peer_from_list else symbol,
                    "sector": None,
                    "industry": None,
                    "marketCap": peer_from_list.get('mktCap') if peer_from_list else None,
                    "priceEarningsRatio": None,
                    "evToEBITDA": None,
                    "priceToSalesRatio": None,
                    "exchangeShortName": "UNKNOWN"
                }
                exchange = "UNKNOWN"

            # Relaxed exchange validation: Accept all peers, but flag major exchanges
            major_exchanges = ["NYSE", "NASDAQ", "HOSE", "HNX", "TSE", "NYQ", "NMS", "AMEX", "LSE", "EURONEXT"]
            is_major_exchange = exchange in major_exchanges

            # Calculate match score based on data quality
            if profile_fetch_success and is_major_exchange:
                match_score = 0.8  # High confidence: verified + major exchange
                verification_status = "Verified"
            elif profile_fetch_success:
                match_score = 0.6  # Medium confidence: verified but minor exchange
                verification_status = "Verified (Minor Exchange)"
            else:
                match_score = 0.4  # Lower confidence: unverified but accepted
                verification_status = "Unverified (Profile Unavailable)"

            peer = PeerCandidate(
                symbol=symbol,
                ticker=symbol,
                name=profile_data.get("companyName", symbol),
                company_name=profile_data.get("companyName", symbol),
                exchange=exchange,
                sector=profile_data.get("sector"),
                industry=profile_data.get("industry"),
                market_cap=profile_data.get("marketCap"),
                marketCap=profile_data.get("marketCap"),
                match_score=match_score,
                segments={},
                pe_ratio=profile_data.get("priceEarningsRatio"),
                ev_to_ebitda=profile_data.get("evToEBITDA"),
                ps_ratio=profile_data.get("priceToSalesRatio"),
                match_reasons=[
                    f"Peer via {'Option B' if len(warnings) == 0 else 'Option A'}",
                    f"Status: {verification_status}"
                ]
            )
            verified_peers.append(peer)

        logger.info(f"Pipeline complete. {len(verified_peers)} peers returned ({sum(1 for p in verified_peers if p.match_score >= 0.8)} verified, {sum(1 for p in verified_peers if p.match_score < 0.8)} unverified/partial).")

        return PeerDiscoveryResponse(
            target_ticker=target_symbol,
            peers=verified_peers[:request_obj.max_peers],
            total_found=len(verified_peers),
            search_criteria=search_criteria,
            warnings=warnings
        )


def _expand_peer_network(initial_peers: list[str], target_symbol: str, expansion_count: int = 2) -> list[str]:
    """
    Recursive Neighbor Expansion (2-Hop Discovery):
    Fetches peer lists for the top 'expansion_count' candidates to find secondary connections.
    This broadens the universe when the primary list is sparse (< 5 peers).

    Args:
        initial_peers: List of peer symbols from Option B or A
        target_symbol: Original target ticker (to exclude from results)
        expansion_count: Number of top peers to expand (default 2 to limit API calls)

    Returns:
        Expanded list of unique peer symbols
    """
    if not initial_peers:
        return []

    logger.info(f"Starting Network Expansion: Fetching neighbors for top {expansion_count} peers...")
    expanded_set = set(initial_peers)

    # We only expand the top N peers to avoid rate limits and noise
    peers_to_expand = initial_peers[:expansion_count]

    for peer_symbol in peers_to_expand:
        # Fetch neighbors of the neighbor (2nd degree connection)
        second_degree_peers = _get_live_fmp_peers(peer_symbol, None)

        for candidate in second_degree_peers:
            # Filter: Must not be the original target, and must not be already in the list
            if candidate.upper() != target_symbol.upper() and candidate.upper() not in [p.upper() for p in expanded_set]:
                expanded_set.add(candidate)
                logger.debug(f"Network Expansion: Added {candidate} via {peer_symbol}")

    final_list = list(expanded_set)
    logger.info(f"Network Expansion Complete: List grew from {len(initial_peers)} to {len(final_list)} candidates.")
    return final_list


def discover_institutional_peers(target_symbol: str) -> list[dict]:
    """
    Legacy function-based entry point for backward compatibility.

    Execution Flow:
    1. Execute Option B (FMP Live) -> Fallback to Option A (Local SQL)
    2. [NEW] Recursive Network Expansion (2-Hop Discovery) if list is sparse
    3. Profile Enrichment & Local Soft Scoring
    4. Return scored and sorted peer profiles
    """
    target_symbol = target_symbol.upper()
    _, target_country = extract_market_context(target_symbol)

    # --- STEP 1: Execute Primary/Fallback Strategy ---
    candidate_symbols = _get_live_fmp_peers(target_symbol)

    if not candidate_symbols:
        logger.info("Primary API empty. Triggering Option A Fallback (Local DB)...")
        candidate_symbols = _get_local_fallback_peers(target_symbol)

    if not candidate_symbols:
        logger.error(f"Peer discovery pipeline completely exhausted for {target_symbol}.")
        return []

    # --- STEP 2: Recursive Network Expansion (The "Broadening" Step) ---
    # Only expand if we have few peers (< 5) to maximize coverage without spamming API
    if len(candidate_symbols) < 5:
        candidate_symbols = _expand_peer_network(candidate_symbols, target_symbol, expansion_count=2)

    # --- STEP 3: Normalize, Enrich & Score Candidates (Hybrid Best-Effort) ---
    verified_peer_profiles = []

    for symbol in candidate_symbols:
        # 1. Market Boundary Check
        _, peer_country = extract_market_context(symbol)
        if peer_country != target_country:
            continue

        # 2. Hybrid Approach: Try to fetch profile, but accept peer even if it fails
        profile_data = None
        profile_fetch_success = False
        exchange = "UNKNOWN"

        # Try multiple profile endpoints (legacy -> stable)
        api_key = get_fmp_api_key(request)
        profile_endpoints = [
            f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={api_key}",
            f"https://financialmodelingprep.com/stable/company-profile?symbol={symbol}&apikey={api_key}",
        ]

        for profile_url in profile_endpoints:
            try:
                p_resp = requests.get(profile_url, timeout=5).json()
                if p_resp and isinstance(p_resp, list) and len(p_resp) > 0:
                    profile_data = p_resp[0]
                    profile_fetch_success = True
                    exchange = profile_data.get("exchangeShortName", "UNKNOWN")
                    logger.info(f"Profile fetched successfully for {symbol} via {profile_url[:60]}...")
                    break
                elif p_resp and isinstance(p_resp, dict) and "companyName" in p_resp:
                    # Handle single object response format
                    profile_data = p_resp
                    profile_fetch_success = True
                    exchange = profile_data.get("exchangeShortName", "UNKNOWN")
                    logger.info(f"Profile fetched successfully for {symbol} via {profile_url[:60]}...")
                    break
            except Exception as e:
                logger.debug(f"Profile fetch failed for {symbol} on {profile_url[:50]}...: {e}")
                continue

        if not profile_fetch_success:
            logger.warning(f"Profile fetch failed for {symbol}, accepting as unverified peer (Hybrid Mode)")
            # Create minimal profile from symbol only
            profile_data = {
                "companyName": symbol,
                "sector": None,
                "industry": None,
                "marketCap": None,
                "priceEarningsRatio": None,
                "evToEBITDA": None,
                "priceToSalesRatio": None,
                "exchangeShortName": "UNKNOWN"
            }
            exchange = "UNKNOWN"

        # Relaxed exchange validation: Accept all peers, but flag major exchanges
        major_exchanges = ["NYSE", "NASDAQ", "HOSE", "HNX", "TSE", "NYQ", "NMS", "AMEX", "LSE", "EURONEXT"]
        is_major_exchange = exchange in major_exchanges

        # Calculate match score based on data quality
        if profile_fetch_success and is_major_exchange:
            base_score = 0.85  # High confidence: verified + major exchange
            verification_status = "Verified"
        elif profile_fetch_success:
            base_score = 0.65  # Medium confidence: verified but minor exchange
            verification_status = "Verified (Minor Exchange)"
        else:
            base_score = 0.45  # Lower confidence: unverified but accepted
            verification_status = "Unverified (Profile Unavailable)"

        # Adjust score for expanded peers
        is_expanded = symbol not in candidate_symbols[:max(1, len(candidate_symbols) - 2)]
        score = base_score - (0.05 if is_expanded else 0.0)

        # Inject score and discovery path into the payload
        profile_data['match_score'] = score
        profile_data['discovery_path'] = "expanded" if is_expanded else "direct"
        profile_data['verification_status'] = verification_status
        profile_data['exchange'] = exchange

        verified_peer_profiles.append(profile_data)

    # Sort by score descending (highest quality peers first)
    verified_peer_profiles.sort(key=lambda x: x.get('match_score', 0), reverse=True)

    verified_count = sum(1 for p in verified_peer_profiles if p.get('match_score', 0) >= 0.8)
    partial_count = sum(1 for p in verified_peer_profiles if p.get('match_score', 0) < 0.8)
    logger.info(f"Pipeline complete. {len(verified_peer_profiles)} peers ready ({verified_count} verified, {partial_count} unverified/partial).")
    return verified_peer_profiles