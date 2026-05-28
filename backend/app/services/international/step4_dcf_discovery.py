"""
Step 4: DCF Peer Discovery Service (International Market)

DCF Analysis requires peer comparison for:
- Beta calculation (levered/unlevered)
- Terminal value benchmarking
- WACC component validation

Market Cap Range for DCF: 50% - 200% of target (tighter range for similar cash flow profiles)
Uses InstitutionalPeerDiscoveryService for advanced multi-segment peer matching
"""
import os
import logging
from typing import Dict, Any, Optional
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
    Discovers peers for DCF valuation using institutional-grade multi-segment analysis.
    
    DCF-specific criteria:
    - Market Cap Range: 50%-200% of target (strict), 25%-400% (moderate), 5%-1000% (broad)
    - Focus on companies with similar risk profiles and operational scale
    - Prioritizes segment overlap for accurate beta estimation
    
    Args:
        session_id: Session identifier
        ticker: Target company ticker
        market: Market type
        max_peers: Maximum number of peers to return
        request: FastAPI Request object (optional, for API key extraction from headers)
    """
    logger.info(f"Starting DCF peer discovery for {ticker} (Session: {session_id})")
    
    # Get FMP API key from request header or environment variable
    fmp_api_key = get_fmp_api_key(request)
    
    if not fmp_api_key:
        logger.warning("FMP_API_KEY not configured. Peer discovery limited to basic matching.")
        return {
            "status": "success",
            "session_id": session_id,
            "method": "dcf",
            "market": market,
            "suggested_peers": [],
            "peer_count": 0,
            "message": "FMP API key not configured. Please set FMP_API_KEY environment variable for advanced peer discovery.",
            "mandatory": False,
            "min_peers_recommended": 3
        }
    
    try:
        # Initialize institutional discovery service with request context
        discovery_service = InstitutionalPeerDiscoveryService(fmp_api_key=fmp_api_key, request=request)
        
        # Create discovery request with DCF-specific parameters
        discovery_request = PeerDiscoveryRequest(
            target_ticker=ticker,
            method="DCF",
            max_peers=max_peers,
            market=market
        )
        
        # Execute discovery
        response = await discovery_service.discover_peers(discovery_request)
        
        # Transform response to expected format - using unified PeerCompany schema fields
        peers = []
        for peer in response.peers:
            peers.append({
                "ticker": peer.ticker,
                "company_name": peer.company_name,
                "sector": peer.sector or "Unknown",
                "industry": peer.industry or "Unknown",
                "market_cap": peer.market_cap,
                "selected": False,
                "match_score": peer.match_score * 100 if peer.match_score <= 1.0 else peer.match_score,  # Convert to 0-100 scale
                "match_reasons": _generate_match_reasons(peer),  # Returns list of strings
                "segments": peer.segments,
                "pe_ratio": peer.pe_ratio,
                "ev_to_ebitda": peer.ev_to_ebitda,
                "ps_ratio": getattr(peer, 'ps_ratio', None)
            })
        
        logger.info(f"Found {len(peers)} DCF peers for {ticker}")
        
        return {
            "status": "success",
            "session_id": session_id,
            "method": "dcf",
            "market": market,
            "suggested_peers": peers,
            "peer_count": len(peers),
            "message": f"Found {len(peers)} DCF peers using multi-segment analysis",
            "search_criteria": response.search_criteria,
            "warnings": response.warnings,
            "mandatory": False,
            "min_peers_recommended": 3
        }
        
    except Exception as e:
        logger.error(f"Error discovering DCF peers: {str(e)}")
        return {
            "status": "success",
            "session_id": session_id,
            "method": "dcf",
            "market": market,
            "suggested_peers": [],
            "peer_count": 0,
            "message": f"Error discovering DCF peers: {str(e)}",
            "mandatory": False,
            "min_peers_recommended": 3
        }


def _generate_match_reasons(peer: PeerCandidate) -> list[str]:
    """Generate human-readable match reasons based on scoring components. Returns a list."""
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
    
    return reasons if reasons else ["Basic industry match"]
