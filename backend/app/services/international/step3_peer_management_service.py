"""
Step 3 Peer Management Service

Handles peer company selection, validation, and market data fetching.
Keeps routes thin by encapsulating all business logic here.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.core.session_service import session_service
from app.services.international.yfinance_service import YFinanceService
from app.services.international.peer_discovery_service import PeerDiscoveryService

logger = logging.getLogger(__name__)


class PeerDataResult:
    """Result of peer data fetching."""
    def __init__(self, ticker: str, data: Dict[str, Any], error: Optional[str] = None):
        self.ticker = ticker
        self.data = data
        self.error = error


class Step3PeerManagementService:
    """
    Service for managing peer companies in Step 3.
    
    Responsibilities:
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
    
    def save_peers_and_fetch_data(
        self,
        session_id: str,
        peers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Save selected peers to session and fetch their market data.
        
        Workflow:
        1. Extract peer tickers from peer objects
        2. Validate tickers
        3. Save peer tickers and objects to session
        4. Fetch market data for each peer from yfinance
        5. Store peer data in session for Step 6 retrieval
        
        Args:
            session_id: Session identifier
            peers: List of peer company objects with symbol/ticker
            
        Returns:
            Dictionary with status, message, and count of peers saved
            
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
        
        # Fetch market data for each peer
        logger.info(f"Fetching market data for {len(peer_tickers)} peers: {peer_tickers}")
        peer_data = {}
        successful_fetches = 0
        failed_fetches = 0
        
        for ticker in peer_tickers:
            result = self._fetch_peer_market_data(ticker)
            
            if result.error:
                failed_fetches += 1
                logger.warning(f"Failed to fetch data for peer {ticker}: {result.error}")
            else:
                successful_fetches += 1
                logger.info(
                    f"Fetched data for peer {ticker}: "
                    f"marketCap={result.data.get('marketCap')}, "
                    f"beta={result.data.get('beta')}, "
                    f"costOfDebt={result.data.get('costOfDebt')}"
                )
            
            # Store in format expected by step6: peer_{TICKER}_info
            # The 5 key WACC inputs per peer: Beta, Market Cap, Cost of Debt, Tax Rate, Risk-free Rate (global)
            peer_data[f"peer_{ticker}_info"] = result.data
        
        # Also store list of peers for easy access
        peer_data['peers'] = peer_tickers
        
        # Save all peer data to session
        session_service.update_session_data(session_id, "retrieved_assumptions", peer_data)
        
        return {
            "status": "success",
            "message": f"Saved {len(peer_tickers)} peers and fetched market data",
            "peers_saved": len(peer_tickers),
            "successful_fetches": successful_fetches,
            "failed_fetches": failed_fetches
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
