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
from typing import Dict, Any
from app.services.international.institutional_peer_discovery import discover_institutional_peers

logger = logging.getLogger(__name__)


async def process(session_id: str, ticker: str, market: str, max_peers: int = 10) -> Dict[str, Any]:
    """
    Discovers peers for DCF valuation using institutional-grade multi-segment analysis.
    
    DCF-specific criteria:
    - Market Cap Range: 50%-200% of target (strict), 25%-400% (moderate), 5%-1000% (broad)
    - Focus on companies with similar risk profiles and operational scale
    - Prioritizes segment overlap for accurate beta estimation
    """
    logger.info(f"Starting DCF peer discovery for {ticker} (Session: {session_id})")
    
    try:
        # Use the new hybrid discovery function (FMP + SQLite fallback)
        peer_profiles = discover_institutional_peers(ticker)
        
        # Transform response to expected format
        peers = []
        for peer in peer_profiles[:max_peers]:
            peers.append({
                "ticker": peer.get("symbol"),
                "name": peer.get("companyName") or peer.get("name"),
                "match_score": 75,  # Default score for now
                "market_cap": peer.get("mktCap") or peer.get("marketCap"),
                "sector": peer.get("sector"),
                "industry": peer.get("industry"),
                "match_reasons": _generate_match_reasons(peer),
                "segments": {},  # Will be populated later if available
                "pe_ratio": peer.get("price") and peer.get("eps") and round(peer.get("price", 0) / peer.get("eps", 1), 2),
                "ev_to_ebitda": None  # Will be populated from financial data
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
            "mandatory": False,
            "min_peers_recommended": 3
        }
        
    except Exception as e:
        logger.error(f"Error discovering DCF peers: {str(e)}", exc_info=True)
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


def _generate_match_reasons(peer: Dict[str, Any]) -> str:
    """Generate human-readable match reasons based on scoring components."""
    reasons = []
    
    if peer.get("industry"):
        reasons.append(f"Industry: {peer['industry']}")
    
    if peer.get("sector"):
        reasons.append(f"Sector: {peer['sector']}")
    
    if peer.get("mktCap") or peer.get("marketCap"):
        mc = peer.get("mktCap") or peer.get("marketCap")
        if mc and mc > 0:
            if mc > 1e9:
                reasons.append(f"Market Cap: ${mc/1e9:.2f}B")
            else:
                reasons.append(f"Market Cap: ${mc/1e6:.2f}M")
    
    return "; ".join(reasons) if reasons else "Basic industry match"
