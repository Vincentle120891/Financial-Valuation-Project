"""
Step 4 Peer Management Service

Handles peer company selection, validation, and market data fetching.
Keeps routes thin by encapsulating all business logic here.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.core.session_service import session_service
from app.services.international.yfinance_service import YFinanceService
from app.services.international.institutional_peer_discovery import InstitutionalPeerDiscoveryService, PeerDiscoveryRequest

logger = logging.getLogger(__name__)


class PeerDataResult:
    """Result of peer data fetching."""
    def __init__(self, ticker: str, data: Dict[str, Any], error: Optional[str] = None):
        self.ticker = ticker
        self.data = data
        self.error = error


class Step4PeerManagementService:
    """
    Service for managing peer companies in Step 4.
    
    Responsibilities:
    - Suggest peer companies based on industry and market cap
    - Save selected peers to session
    - Fetch market data for peers from yfinance
    - Validate peer tickers
    - Store peer information in standardized format
    """
    
    def __init__(self, yfinance_service: Optional[YFinanceService] = None):
        """
        Initialize the service.
        
        Args:
            yfinance_service: YFinance service instance (creates default if not provided)
        """
        self.yfinance_service = yfinance_service or YFinanceService()
        self.peer_discovery_service = InstitutionalPeerDiscoveryService()
    
    def save_peers_and_fetch_data(
        self,
        session_id: str,
        peers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Save selected peers to session with BASIC INFO ONLY for UI display.
        
        CRITICAL CHANGE: Do NOT fetch expensive WACC data (Beta, Cost of Debt, Tax Rate) here.
        WACC data will be fetched in Step 10 when actually running valuation calculations.
        
        Workflow:
        1. Extract peer tickers from peer objects
        2. Validate tickers
        3. Save peer tickers and basic info to session (ticker, name, sector, industry, market_cap)
        4. Return basic peer list for UI display
        
        Args:
            session_id: Session identifier
            peers: List of peer company objects with symbol/ticker
            
        Returns:
            Dictionary with status, message, count of peers saved, and peer_list (basic info only)
            
        Raises:
            HTTPException: If session not found or no valid tickers provided
        """
        from fastapi import HTTPException
        
        # Validate session exists
        session = session_service.get_session_data(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Extract peer tickers from the peer objects
        peer_tickers = [peer.get('symbol') or peer.get('ticker') for peer in peers]
        peer_tickers = [t for t in peer_tickers if t]  # Filter out None values
        
        if not peer_tickers:
            raise HTTPException(status_code=400, detail="No valid peer tickers provided")
        
        # Save peer tickers to session
        session_service.update_session_data(session_id, "peer_tickers", peer_tickers)
        session_service.update_session_data(session_id, "selected_peers", peers)
        
        # Build peer_list with BASIC INFO ONLY for UI display (Step 4-5)
        # DO NOT fetch expensive WACC data here - that happens in Step 10
        peer_list = []
        for peer in peers:
            peer_list.append({
                "ticker": peer.get('symbol') or peer.get('ticker'),
                "name": peer.get('name') or peer.get('company_name'),
                "sector": peer.get('sector'),
                "industry": peer.get('industry'),
                "market_cap": peer.get('market_cap') or peer.get('marketCap'),
                "similarity_score": peer.get('similarity_score') or peer.get('score', 0)
            })
        
        # Store basic peer list in session for Step 5 requirements check
        session_service.update_shared_context(session_id, "peer_list", peer_list)
        
        logger.info(f"Saved {len(peer_tickers)} peers with basic info for UI display: {peer_tickers}")
        
        return {
            "status": "success",
            "message": f"Saved {len(peer_tickers)} peers with basic info",
            "peers_saved": len(peer_tickers),
            "peer_list": peer_list  # Basic info for UI, NOT full WACC data
        }
    
    def _fetch_peer_market_data(self, ticker: str) -> PeerDataResult:
        """
        Fetch market data for a single peer company.
        
        Args:
            ticker: Peer company ticker symbol
            
        Returns:
            PeerDataResult with fetched data or error information
        """
        try:
            # Fetch key stats for each peer (includes 5 WACC metrics + costOfDebt)
            peer_stats = self.yfinance_service.fetch_key_stats(ticker)
            
            # Build standardized peer info dict
            peer_info = {
                'marketCap': peer_stats.get('marketCap'),
                'beta': peer_stats.get('beta'),
                'totalDebt': peer_stats.get('totalDebt'),
                'cash': peer_stats.get('cash'),
                'effectiveTaxRate': peer_stats.get('effectiveTaxRate'),
                'costOfDebt': peer_stats.get('costOfDebt'),  # Pre-tax cost of debt
                'error': None
            }
            
            return PeerDataResult(ticker=ticker, data=peer_info)
            
        except Exception as e:
            # Return error result with None values
            error_info = {
                'marketCap': None,
                'beta': None,
                'totalDebt': None,
                'cash': None,
                'effectiveTaxRate': None,
                'costOfDebt': None,
                'error': str(e)
            }
            return PeerDataResult(ticker=ticker, data=error_info, error=str(e))
    
    def validate_peer_tickers(
        self,
        session_id: str,
        tickers: List[str]
    ) -> Dict[str, Any]:
        """
        Validate a list of peer tickers.
        
        Args:
            session_id: Session identifier
            tickers: List of ticker symbols to validate
            
        Returns:
            Dictionary with validated tickers and any errors
        """
        from fastapi import HTTPException
        
        # Validate session exists
        session = session_service.get_session_data(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not tickers:
            raise HTTPException(status_code=400, detail="No tickers provided")
        
        validated = []
        errors = []
        
        for ticker in tickers:
            try:
                # Try to fetch basic info to validate ticker exists
                ticker_info = self.yfinance_service.get_ticker_info(ticker)
                
                if ticker_info and ticker_info.get('currentPrice'):
                    validated.append({
                        'ticker': ticker,
                        'valid': True,
                        'name': ticker_info.get('shortName', ticker),
                        'exchange': ticker_info.get('exchange', 'Unknown')
                    })
                else:
                    errors.append({
                        'ticker': ticker,
                        'valid': False,
                        'error': 'Ticker not found or no price data available'
                    })
                    
            except Exception as e:
                errors.append({
                    'ticker': ticker,
                    'valid': False,
                    'error': str(e)
                })
        
        return {
            "validated_peers": validated,
            "invalid_peers": errors,
            "total_validated": len(validated),
            "total_invalid": len(errors)
        }

    async def suggest_peers(
        self,
        ticker: str,
        session_id: str,
        max_peers: int = 10,
        market: str = "international",
        method: Optional[str] = None  # NEW: valuation method
    ) -> Dict:
        """
        Suggest peer companies for a given ticker and save to session.

        Args:
            ticker: Target ticker symbol
            session_id: Session identifier for storing suggestions
            max_peers: Maximum number of peers to suggest
            market: Market type
            method: Valuation method (DCF, COMPS, DuPont) - affects peer criteria

        Returns:
            Dictionary with status and peer suggestions
        """
        logger.info(f"Suggesting peers for ticker='{ticker}', method='{method}', session_id='{session_id}'")

        try:
            # Get ticker info first
            ticker_info = self.yfinance_service.get_ticker_info(ticker)

            if not ticker_info:
                return {
                    "status": "failed",
                    "message": f"Could not fetch data for {ticker}"
                }

            # Create peer discovery request with method
            request = PeerDiscoveryRequest(
                target_ticker=ticker,
                method=method,  # NEW: pass method
                max_peers=max_peers,
                market=market
            )

            # Discover peers
            response = await self.peer_discovery_service.discover_peers(request)

            if response.total_found == 0:
                return {
                    "status": "partial",
                    "message": f"No suitable peers found for {ticker}",
                    "warnings": response.warnings,
                    "peers": [],
                    "fallback_options": []
                }

            # Build peer list (auto-discovered peers only)
            peers_list = [
                {
                    "ticker": peer.ticker,
                    "symbol": peer.symbol,
                    "company_name": peer.company_name,
                    "name": peer.name,
                    "sector": peer.sector,
                    "industry": peer.industry,
                    "marketCap": peer.marketCap,
                    "score": peer.match_score,
                    "match_reasons": peer.match_reasons
                }
                for peer in response.peers
            ]

            # No fallback options in new service
            fallback_options_list = []

            # CRUCIAL FIX: Save suggestions to session immediately to prevent re-fetching loop
            if session_id:
                session_service.update_session_data(
                    session_id, 
                    f"peer_suggestions_{ticker}", 
                    peers_list
                )
                logger.info(f"Saved {len(peers_list)} peer suggestions to session for {ticker}")

            return {
                "status": "success",
                "message": f"Found {response.total_found} peer candidates for {ticker}",
                "target_company": {
                    "ticker": ticker,
                    "name": ticker_info.get('longName', ticker),
                    "sector": ticker_info.get('sector'),
                    "industry": ticker_info.get('industry'),
                    "marketCap": ticker_info.get('marketCap')
                },
                "peers": peers_list,
                "fallback_options": fallback_options_list,
                "search_criteria": response.search_criteria,
                "warnings": response.warnings
            }

        except Exception as e:
            logger.error(f"Error suggesting peers for {ticker}: {str(e)}")
            return {
                "status": "failed",
                "message": f"Failed to suggest peers: {str(e)}"
            }
