"""
Step 4: DCF Peer Discovery Service (International Market)

DCF Analysis requires peer comparison for:
- Beta calculation (levered/unlevered)
- Terminal value benchmarking
- WACC component validation

Market Cap Range for DCF: 50% - 200% of target (tighter range for similar cash flow profiles)
"""
from typing import Dict, Any, List, Optional
import asyncio
from app.services.international.peer_discovery_service import PeerDiscoveryService, PeerDiscoveryRequest
from app.services.international.yfinance_service import YFinanceService


async def process(session_id: str, ticker: str, market: str, max_peers: int = 5) -> Dict[str, Any]:
    """
    For DCF, we discover peers based on sector/industry/market cap.
    Returns 5-10 peers for beta and valuation benchmarking.
    
    DCF-specific criteria:
    - Market cap range: 50% - 200% of target (tighter range)
    - Focus on companies with similar cash flow profiles
    - Bonus for similar growth stage (70%-140% market cap ratio)
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
                "method": "dcf",
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
                "method": "dcf",
                "message": f"Could not determine sector/industry for {ticker}. Manual peer selection required.",
                "peer_count": 0,
                "warning": "Missing sector/industry data"
            }
        
        # Create discovery request with DCF-specific parameters
        discovery_request = PeerDiscoveryRequest(
            target_ticker=ticker,
            target_sector=sector,
            target_industry=industry,
            target_market_cap=market_cap,
            max_peers=max_peers,
            market=market,
            method="DCF"  # Critical: triggers DCF-specific market cap ranges
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
            "method": "dcf",
            "message": f"Found {len(suggested_peers)} DCF peers in {sector} - {industry}",
            "peer_count": len(suggested_peers),
            "mandatory": False,  # DCF can proceed without peers but recommended
            "min_peers_recommended": 3,
            "sector": sector,
            "industry": industry,
            "target_market_cap": market_cap,
            "fallback_options": []  # Could add fallback options if needed
        }
        
    except Exception as e:
        return {
            "suggested_peers": [],
            "method": "dcf",
            "message": f"Error discovering DCF peers: {str(e)}",
            "peer_count": 0,
            "error": str(e)
        }