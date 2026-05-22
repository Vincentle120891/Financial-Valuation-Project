"""
Step 4: DuPont Peer Discovery Service (International Market)

DuPont Analysis focuses on internal efficiency decomposition (ROE drivers).
Peer comparison is OPTIONAL and secondary.

Market Cap Range for DuPont: 40% - 250% of target (standard range)
"""
from typing import Dict, Any, List, Optional
import asyncio
from app.services.international.peer_discovery_service import PeerDiscoveryService, PeerDiscoveryRequest
from app.services.international.yfinance_service import YFinanceService


def process(session_id: str, ticker: str, market: str, max_peers: int = 5) -> Dict[str, Any]:
    """
    For DuPont, we do not enforce strict peer discovery.
    Returns a minimal/empty peer list as peers are optional for this method.
    
    DuPont-specific criteria:
    - Peers are optional (focus is on internal ROE decomposition)
    - Standard market cap range if peers are requested
    - Useful for benchmarking ROE drivers but not required
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
                "method": "dupont",
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
                "method": "dupont",
                "message": f"Could not determine sector/industry for {ticker}. Manual peer selection optional.",
                "peer_count": 0,
                "warning": "Missing sector/industry data"
            }
        
        # Create discovery request with DuPont-specific parameters
        # Note: DuPont doesn't strictly require peers, so we use standard ranges
        discovery_request = PeerDiscoveryRequest(
            target_ticker=ticker,
            target_sector=sector,
            target_industry=industry,
            target_market_cap=market_cap,
            max_peers=max_peers,
            market=market,
            method="DUPONT"  # Uses standard/default market cap ranges
        )
        
        # Run async discovery
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(peer_discovery.discover_peers(discovery_request))
        finally:
            loop.close()
        
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
            "method": "dupont",
            "message": f"Found {len(suggested_peers)} optional peers for DuPont benchmarking in {sector} - {industry}",
            "peer_count": len(suggested_peers),
            "mandatory": False,  # DuPont does not require peers
            "min_peers_recommended": 0,
            "sector": sector,
            "industry": industry,
            "target_market_cap": market_cap,
            "fallback_options": []  # Could add fallback options if needed
        }
        
    except Exception as e:
        return {
            "suggested_peers": [],
            "method": "dupont",
            "message": f"Error discovering peers: {str(e)}",
            "peer_count": 0,
            "error": str(e)
        }