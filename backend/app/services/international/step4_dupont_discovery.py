"""
Step 4: DuPont Peer Discovery Service (International Market)

DuPont Analysis requires peer comparison for:
- ROE decomposition benchmarking
- Profit margin, asset turnover, and equity multiplier comparisons
- Operational efficiency analysis

Market Cap Range for DuPont: 20% - 500% of target (widest range for operational analysis)
Uses InstitutionalPeerDiscoveryService for advanced multi-segment peer matching
"""
import os
import logging
from typing import Dict, Any, Optional
from fastapi import Request
from app.services.international.institutional_peer_discovery import (
    InstitutionalPeerDiscoveryService,
    PeerDiscoveryRequest,
    get_fmp_api_key
)

logger = logging.getLogger(__name__)


async def process(session_id: str, ticker: str, market: str, max_peers: int = 10, request: Optional[Request] = None) -> Dict[str, Any]:
    """
    Discovers peers for DuPont valuation using institutional-grade multi-segment analysis.
    
    DuPont-specific criteria:
    - Market Cap Range: 20%-500% of target (widest range for operational comparison)
    - Focus on companies with similar operational metrics and capital structures
    - Optional for DuPont analysis (can work without peers)
    
    Args:
        session_id: Session identifier
        ticker: Target company ticker
        market: Market type
        max_peers: Maximum number of peers to return
        request: FastAPI Request object (optional, for API key extraction from headers)
    """
    logger.info(f"Starting DuPont peer discovery for {ticker} (Session: {session_id})")
    
    # Get FMP API key from request header or environment variable
    fmp_api_key = get_fmp_api_key(request)
    
    if not fmp_api_key:
        logger.warning("FMP_API_KEY not configured. Peer discovery limited to basic matching.")
        return {
            "status": "success",
            "session_id": session_id,
            "method": "dupont",
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
        
        # Create discovery request with DuPont-specific parameters
        request = PeerDiscoveryRequest(
            target_ticker=ticker,
            method="DUPONT",
            max_peers=max_peers,
            market=market
        )
        
        # Execute discovery
        response = await discovery_service.discover_peers(request)
        
        # Transform response to expected format
        peers = []
        for peer in response.peers:
            peers.append({
                "ticker": peer.get("symbol"),
                "name": peer.get("name"),
                "match_score": peer.get("match_score", 0),
                "market_cap": peer.get("market_cap"),
                "sector": peer.get("sector"),
                "industry": peer.get("industry"),
                "match_reasons": _generate_match_reasons(peer),
                "segments": peer.get("segments", {}),
                "pe_ratio": peer.get("pe_ratio"),
                "ev_to_ebitda": peer.get("ev_to_ebitda")
            })
        
        logger.info(f"Found {len(peers)} DuPont peers for {ticker}")
        
        return {
            "status": "success",
            "session_id": session_id,
            "method": "dupont",
            "market": market,
            "suggested_peers": peers,
            "peer_count": len(peers),
            "message": f"Found {len(peers)} DuPont peers using multi-segment analysis",
            "search_criteria": response.search_criteria,
            "warnings": response.warnings,
            "mandatory": False,
            "min_peers_recommended": 3
        }
        
    except Exception as e:
        logger.error(f"Error discovering DuPont peers: {str(e)}")
        return {
            "status": "success",
            "session_id": session_id,
            "method": "dupont",
            "market": market,
            "suggested_peers": [],
            "peer_count": 0,
            "message": f"Error discovering DuPont peers: {str(e)}",
            "mandatory": False,
            "min_peers_recommended": 3
        }


def _generate_match_reasons(peer: Dict[str, Any]) -> str:
    """Generate human-readable match reasons based on scoring components."""
    reasons = []
    
    if peer.get("segments"):
        reasons.append("Segment overlap detected")
    
    if peer.get("industry"):
        reasons.append(f"Industry: {peer['industry']}")
    
    if peer.get("market_cap"):
        mc = peer["market_cap"]
        if mc > 1e9:
            reasons.append(f"Market Cap: ${mc/1e9:.2f}B")
        else:
            reasons.append(f"Market Cap: ${mc/1e6:.2f}M")
    
    return "; ".join(reasons) if reasons else "Basic industry match"
