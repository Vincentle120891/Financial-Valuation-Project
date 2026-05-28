"""
Step 4: COMPS Peer Discovery Service (International Market)

Trading Comps Analysis requires peer comparison for:
- Trading multiples (P/E, EV/EBITDA, P/S, etc.)
- Relative valuation benchmarking
- Sector/industry comparables

Market Cap Range for COMPS: 30% - 300% of target (wider range for trading comps)
Uses InstitutionalPeerDiscoveryService for advanced multi-segment peer matching
"""
import os
import logging
from typing import Dict, Any, Optional, List
from fastapi import Request
from app.services.international.institutional_peer_discovery import (
    InstitutionalPeerDiscoveryService,
    PeerDiscoveryRequest,
    get_fmp_api_key,
    PeerCandidate
)

logger = logging.getLogger(__name__)


async def process(session_id: str, ticker: str, market: str, max_peers: int = 10, request: Optional[Request] = None) -> Dict[str, Any]:
    """
    Discovers peers for Trading Comps valuation using institutional-grade multi-segment analysis.
    
    COMPS-specific criteria:
    - Market Cap Range: 30%-300% of target (strict), 15%-600% (moderate), 5%-1000% (broad)
    - Focus on companies with similar trading multiples and operational profiles
    - Prioritizes segment overlap and multiple availability
    
    Args:
        session_id: Session identifier
        ticker: Target company ticker
        market: Market type
        max_peers: Maximum number of peers to return
        request: FastAPI Request object (optional, for API key extraction from headers)
    """
    logger.info(f"Starting COMPS peer discovery for {ticker} (Session: {session_id})")
    
    # Get FMP API key from request header or environment variable
    fmp_api_key = get_fmp_api_key(request)
    
    if not fmp_api_key:
        logger.warning("FMP_API_KEY not configured. Peer discovery limited to basic matching.")
        return {
            "status": "success",
            "session_id": session_id,
            "method": "comps",
            "market": market,
            "suggested_peers": [],
            "peer_count": 0,
            "message": "FMP API key not configured. Please set FMP_API_KEY environment variable for advanced peer discovery.",
            "mandatory": True,
            "min_peers_recommended": 5
        }
    
    try:
        # Initialize institutional discovery service with request context
        discovery_service = InstitutionalPeerDiscoveryService(fmp_api_key=fmp_api_key, request=request)
        
        # Create discovery request with COMPS-specific parameters
        request = PeerDiscoveryRequest(
            target_ticker=ticker,
            method="COMPS",
            max_peers=max_peers,
            market=market
        )
        
        # Execute discovery
        response = await discovery_service.discover_peers(request)
        
        # Transform response to expected format
        peers = []
        for peer in response.peers:
            peers.append({
                "ticker": peer.ticker,
                "name": peer.name,
                "match_score": peer.match_score,
                "market_cap": peer.market_cap,
                "sector": peer.sector,
                "industry": peer.industry,
                "match_reasons": _generate_match_reasons(peer),
                "segments": peer.segments,
                "pe_ratio": peer.pe_ratio,
                "ev_to_ebitda": peer.ev_to_ebitda,
                "ps_ratio": peer.ps_ratio
            })
        
        logger.info(f"Found {len(peers)} COMPS peers for {ticker}")
        
        return {
            "status": "success",
            "session_id": session_id,
            "method": "comps",
            "market": market,
            "suggested_peers": peers,
            "peer_count": len(peers),
            "message": f"Found {len(peers)} COMPS peers using multi-segment analysis",
            "search_criteria": response.search_criteria,
            "warnings": response.warnings,
            "mandatory": True,
            "min_peers_recommended": 5
        }
        
    except Exception as e:
        logger.error(f"Error discovering COMPS peers: {str(e)}")
        return {
            "status": "success",
            "session_id": session_id,
            "method": "comps",
            "market": market,
            "suggested_peers": [],
            "peer_count": 0,
            "message": f"Error discovering COMPS peers: {str(e)}",
            "mandatory": True,
            "min_peers_recommended": 5
        }


def _generate_match_reasons(peer: PeerCandidate) -> List[str]:
    """Generate human-readable match reasons based on scoring components."""
    reasons = []
    
    if peer.segments:
        reasons.append("Segment overlap detected")
    
    if peer.industry:
        reasons.append(f"Industry: {peer.industry}")
    
    if peer.market_cap:
        mc = peer.market_cap
        if mc > 1e9:
            reasons.append(f"Market Cap: ${mc/1e9:.2f}B")
        else:
            reasons.append(f"Market Cap: ${mc/1e6:.2f}M")
    
    if peer.pe_ratio:
        reasons.append(f"P/E: {peer.pe_ratio:.2f}x")
    
    if peer.ev_to_ebitda:
        reasons.append(f"EV/EBITDA: {peer.ev_to_ebitda:.2f}x")
    
    return reasons if reasons else ["Basic industry match"]
