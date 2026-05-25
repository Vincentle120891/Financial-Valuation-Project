"""
Step 4: Comps Peer Discovery Service (International Market)

Trading Comparables relies ENTIRELY on peer multiples.
Peer discovery is MANDATORY and strict.

Market Cap Range for COMPS: 30% - 300% of target (wider range for M&A comparables)
"""
from typing import Dict, Any, List, Optional
import asyncio
from app.services.international.peer_discovery_service import PeerDiscoveryService, PeerDiscoveryRequest
from app.services.international.yfinance_service import YFinanceService


async def process(session_id: str, ticker: str, market: str, max_peers: int = 5) -> Dict[str, Any]:
    """
    For Comps, we enforce strict sector/industry peer discovery.
    Returns 5-10 high-confidence peers in the same industry.
    
    COMPS-specific criteria:
    - Market cap range: 30% - 300% of target (wider range for M&A analysis)
    - Focus on companies suitable for multiple comparison
    - Bonus for potential acquisition targets (<150% market cap)
    """
    try:
        # Initialize services
        yfinance_service = YFinanceService()
        peer_discovery = PeerDiscoveryService(yfinance_service=yfinance_service)
        
        # Get target company info
        ticker_info = yfinance_service.get_ticker_info(ticker)
        if not ticker_info:
            return {
                "suggested_peers": [],
                "method": "comps",
                "message": f"Could not retrieve information for {ticker}.",
                "peer_count": 0,
                "error": "Failed to fetch target company info"
            }
        
        sector = ticker_info.get('sector', '')
        industry = ticker_info.get('industry', '')
        market_cap = ticker_info.get('marketCap', 0)
        
        if not sector or not industry:
            return {
                "suggested_peers": [],
                "method": "comps",
                "message": f"Could not determine sector/industry for {ticker}. Manual peer selection required.",
                "peer_count": 0,
                "warning": "Missing sector/industry data"
            }
        
        # Create discovery request with COMPS-specific parameters
        discovery_request = PeerDiscoveryRequest(
            target_ticker=ticker,
            target_sector=sector,
            target_industry=industry,
            target_market_cap=market_cap,
            max_peers=max_peers,
            market=market,
            method="COMPS"  # Critical: triggers COMPS-specific market cap ranges
        )
        
        # Run async discovery (no manual loop management needed)
        response = await peer_discovery.discover_peers(discovery_request)
        
        # Convert response to expected format
        suggested_peers = []
        for peer in response.peers:
            suggested_peers.append({
                "symbol": peer.symbol,
                "ticker": peer.ticker,
                "name": peer.name,
                "company_name": peer.company_name,
                "sector": peer.sector,
                "industry": peer.industry,
                "market_cap": peer.market_cap,
                "marketCap": peer.marketCap,
                "similarity_score": peer.similarity_score,
                "score": peer.score,
                "match_reasons": peer.match_reasons
            })
        
        return {
            "suggested_peers": suggested_peers,
            "method": "comps",
            "message": f"Found {len(suggested_peers)} peers in {sector} - {industry}",
            "peer_count": len(suggested_peers),
            "mandatory": True,  # COMPS requires peers
            "min_peers_required": 3,
            "sector": sector,
            "industry": industry,
            "target_market_cap": market_cap,
            "fallback_options": []  # Could add fallback options if needed
        }
        
    except Exception as e:
        return {
            "suggested_peers": [],
            "method": "comps",
            "message": f"Error discovering peers: {str(e)}",
            "peer_count": 0,
            "error": str(e)
        }