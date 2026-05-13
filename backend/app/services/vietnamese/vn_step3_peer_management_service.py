"""
Vietnamese Step 3: Peer Management Service

Handles peer company selection, validation, and market data fetching for Vietnamese market.
Keeps routes thin by encapsulating all business logic here.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.core.session_service import session_service
from app.services.vietnamese.vietnamese_ticker_service import VietnameseTickerService

logger = logging.getLogger(__name__)


class vn_PeerDataResult:
    """Result of peer data fetching."""
    def __init__(self, ticker: str, data: Dict[str, Any], error: Optional[str] = None):
        self.ticker = ticker
        self.data = data
        self.error = error


class vn_Step3PeerManagementService:
    """
    Service for managing peer companies in Vietnamese Step 3.

    Responsibilities:
    - Save selected peers to session
    - Fetch market data for Vietnamese peers
    - Validate Vietnamese peer tickers
    - Store peer information in standardized format
    - Discover Vietnamese peers by sector
    """

    def __init__(self, ticker_service: Optional[VietnameseTickerService] = None):
        """
        Initialize the service.

        Args:
            ticker_service: Vietnamese ticker service instance (creates default if not provided)
        """
        self.ticker_service = ticker_service or VietnameseTickerService()

    def save_peers_and_fetch_data(
        self,
        session_id: str,
        peers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Save selected peers to session and fetch their market data.

        Workflow:
        1. Extract peer tickers from peer objects
        2. Validate Vietnamese tickers
        3. Save peer tickers and objects to session
        4. Fetch market data for each peer from Vietnamese data sources
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
        peer_tickers = [t for t in peer_tickers if t]  # Filter out None/empty

        if not peer_tickers:
            raise HTTPException(
                status_code=400,
                detail="No valid peer tickers provided"
            )

        # Save peer tickers to session
        session_service.update_session_data(session_id, "peer_tickers", peer_tickers)

        # Save full peer objects to session
        session_service.update_session_data(session_id, "peers", peers)

        # Fetch market data for each peer
        peer_data_results = []
        for peer_ticker in peer_tickers:
            try:
                # Fetch Vietnamese market data for peer
                peer_info = self.ticker_service.get_ticker_info(peer_ticker)
                if peer_info:
                    peer_data = {
                        "ticker": peer_ticker,
                        "company_name": peer_info.get('name', peer_ticker),
                        "exchange": peer_info.get('exchange', 'HOSE'),
                        "sector": peer_info.get('sector', 'Unknown'),
                        "market_cap": peer_info.get('market_cap'),
                        "current_price": peer_info.get('current_price'),
                        "currency": "VND"
                    }
                    peer_data_results.append({
                        "ticker": peer_ticker,
                        "data": peer_data,
                        "error": None
                    })
                else:
                    peer_data_results.append({
                        "ticker": peer_ticker,
                        "data": None,
                        "error": "Ticker not found"
                    })
            except Exception as e:
                logger.error(f"Error fetching data for peer {peer_ticker}: {e}")
                peer_data_results.append({
                    "ticker": peer_ticker,
                    "data": None,
                    "error": str(e)
                })

        # Store peer data in session for Step 6
        session_service.update_session_data(
            session_id,
            "peer_market_data",
            {result['ticker']: result['data'] for result in peer_data_results if result['data']}
        )

        successful_count = sum(1 for r in peer_data_results if r['error'] is None)
        failed_count = len(peer_data_results) - successful_count

        return {
            "status": "success" if failed_count == 0 else "partial",
            "message": f"Saved {successful_count} peers successfully. {failed_count} failed.",
            "peers_saved": successful_count,
            "peer_tickers": peer_tickers,
            "errors": [r for r in peer_data_results if r['error']]
        }

    def discover_vietnamese_peers(
        self,
        ticker: str,
        max_peers: int = 10,
        sector: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Discover Vietnamese peer companies by sector.

        Args:
            ticker: Target company ticker
            max_peers: Maximum number of peers to return
            sector: Optional sector filter

        Returns:
            List of peer company dictionaries
        """
        try:
            # Get target company info to determine sector
            target_info = self.ticker_service.get_ticker_info(ticker)
            if not target_info:
                logger.warning(f"Could not find target company {ticker}")
                return []

            target_sector = sector or target_info.get('sector')

            # Search for companies in same sector
            if target_sector:
                sector_companies = self.ticker_service.search_by_sector(target_sector)
                # Exclude target company and limit results
                peers = [
                    {
                        "symbol": company.get('ticker'),
                        "company_name": company.get('name'),
                        "sector": company.get('sector', target_sector),
                        "industry": company.get('industry', 'Unknown'),
                        "market_cap": company.get('market_cap'),
                        "exchange": company.get('exchange', 'HOSE')
                    }
                    for company in sector_companies
                    if company.get('ticker') != ticker
                ][:max_peers]

                logger.info(f"Discovered {len(peers)} Vietnamese peers for {ticker} in sector {target_sector}")
                return peers
            else:
                logger.warning(f"No sector information available for {ticker}")
                return []

        except Exception as e:
            logger.error(f"Error discovering Vietnamese peers: {e}")
            return []

    def validate_vietnamese_peer_tickers(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Validate a list of Vietnamese peer tickers.

        Args:
            tickers: List of ticker symbols to validate

        Returns:
            Dictionary with valid and invalid tickers
        """
        valid_tickers = []
        invalid_tickers = []

        for ticker in tickers:
            try:
                info = self.ticker_service.get_ticker_info(ticker)
                if info and info.get('is_valid', True):
                    valid_tickers.append({
                        "ticker": ticker,
                        "company_name": info.get('name', ticker),
                        "exchange": info.get('exchange', 'Unknown'),
                        "sector": info.get('sector', 'Unknown')
                    })
                else:
                    invalid_tickers.append({
                        "ticker": ticker,
                        "reason": "Invalid or delisted ticker"
                    })
            except Exception as e:
                invalid_tickers.append({
                    "ticker": ticker,
                    "reason": str(e)
                })

        return {
            "valid_tickers": valid_tickers,
            "invalid_tickers": invalid_tickers,
            "total_valid": len(valid_tickers),
            "total_invalid": len(invalid_tickers)
        }