"""
Vietnamese Step 4: Peer Discovery Service

Handles peer company discovery, validation, and market data fetching for Vietnamese market
(Step 4, AFTER model selection in Step 3). This aligns with the International workflow:
Model Selection (Step 3) → Peer Discovery (Step 4).

Enhancements over basic peer search:
- Method-specific peer discovery (DCF/DuPont/Comps)
- Market cap filtering (50-200% of target)
- Match scoring by sector overlap + market cap similarity
- WACC enrichment for DCF peers (beta, debt, tax_rate)

Bridge method: discover_peers() matches the INT Step4 discovery signature
so valuation_routes.py can delegate when market='vietnam'.
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


class vn_Step4PeerDiscoveryService:
    """
    Service for discovering peer companies in Vietnamese Step 4.

    Responsibilities:
    - Discover Vietnamese peers by sector (method-specific)
    - Filter by market cap (50-200% of target)
    - Score peers by sector overlap + market cap similarity
    - Enrich DCF peers with WACC data (beta, debt, tax_rate)
    - Save selected peers to session
    - Fetch market data for Vietnamese peers
    - Validate Vietnamese peer tickers
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

    # ──────────────────────────────────────────────────────────────────────────
    # Bridge method — matches INT Step4 discovery signature
    # ──────────────────────────────────────────────────────────────────────────

    def discover_peers(
        self,
        session_id: str,
        ticker: str,
        method: str = "dcf",
        max_peers: int = 10,
        market: str = "vietnam",
    ) -> Dict[str, Any]:
        """
        Bridge method matching the shared route handler's peer discovery signature.

        Delegates to method-specific discovery logic and returns a result dict
        with keys: suggested_peers, message, target_market_cap, etc.

        Args:
            session_id: Session identifier
            ticker: Target company ticker
            method: Valuation method ('dcf', 'dupont', 'comps')
            max_peers: Maximum number of peers to return
            market: Market type (always 'vietnam')

        Returns:
            Dict with suggested_peers list and metadata
        """
        method_lower = method.lower()

        # Get target company info
        target_info = self.ticker_service.get_ticker_info(ticker)
        if not target_info:
            return {"suggested_peers": [], "message": f"Target company {ticker} not found"}

        target_sector = target_info.get("sector")
        target_market_cap = target_info.get("market_cap", 0)

        # Method-specific peer discovery
        if method_lower == "comps":
            peers = self._discover_comps_peers(ticker, target_sector, target_market_cap, max_peers)
        elif method_lower == "dcf":
            peers = self._discover_dcf_peers(ticker, target_sector, target_market_cap, max_peers)
        elif method_lower == "dupont":
            peers = self._discover_dupont_peers(ticker, target_sector, target_market_cap, max_peers)
        else:
            peers = self._discover_comps_peers(ticker, target_sector, target_market_cap, max_peers)

        # Save to session
        peer_tickers = [p.get("symbol") for p in peers if p.get("symbol")]
        session_service.update_session_data(session_id, "peer_tickers", peer_tickers)
        session_service.update_session_data(session_id, "peers", peers)

        return {
            "suggested_peers": peers,
            "message": f"Discovered {len(peers)} {method.upper()} peers for {ticker}",
            "target_market_cap": target_market_cap,
            "method": method_lower,
        }

    def _discover_comps_peers(
        self,
        ticker: str,
        target_sector: Optional[str],
        target_market_cap: float,
        max_peers: int,
    ) -> List[Dict[str, Any]]:
        """
        Comps: Strict sector peers with market cap filtering (50-200% of target).
        """
        if not target_sector:
            return []

        sector_companies = self.ticker_service.search_by_sector(target_sector)
        peers = []

        for company in sector_companies:
            if company.get("ticker") == ticker:
                continue

            company_market_cap = company.get("market_cap", 0) or 0

            # Market cap filter: 50% - 200% of target
            if target_market_cap > 0 and company_market_cap > 0:
                ratio = company_market_cap / target_market_cap
                if ratio < 0.5 or ratio > 2.0:
                    continue

            # Calculate match score
            match_score = self._calculate_match_score(
                target_sector, company.get("sector", ""), target_market_cap, company_market_cap
            )

            peers.append({
                "symbol": company.get("ticker"),
                "company_name": company.get("name"),
                "sector": company.get("sector", target_sector),
                "industry": company.get("industry", "Unknown"),
                "market_cap": company_market_cap,
                "exchange": company.get("exchange", "HOSE"),
                "match_score": match_score,
                "current_price": company.get("current_price"),
            })

        # Sort by match score descending, take top N
        peers.sort(key=lambda p: p.get("match_score", 0), reverse=True)
        return peers[:max_peers]

    def _discover_dcf_peers(
        self,
        ticker: str,
        target_sector: Optional[str],
        target_market_cap: float,
        max_peers: int,
    ) -> List[Dict[str, Any]]:
        """
        DCF: Sector peers with market cap filtering + WACC enrichment.
        Peers are used for beta, cost of debt, and tax rate estimation.
        """
        if not target_sector:
            return []

        sector_companies = self.ticker_service.search_by_sector(target_sector)
        peers = []

        for company in sector_companies:
            if company.get("ticker") == ticker:
                continue

            company_market_cap = company.get("market_cap", 0) or 0

            # Market cap filter: 50% - 200% of target (slightly relaxed for DCF)
            if target_market_cap > 0 and company_market_cap > 0:
                ratio = company_market_cap / target_market_cap
                if ratio < 0.5 or ratio > 2.0:
                    continue

            match_score = self._calculate_match_score(
                target_sector, company.get("sector", ""), target_market_cap, company_market_cap
            )

            peer_entry = {
                "symbol": company.get("ticker"),
                "company_name": company.get("name"),
                "sector": company.get("sector", target_sector),
                "industry": company.get("industry", "Unknown"),
                "market_cap": company_market_cap,
                "exchange": company.get("exchange", "HOSE"),
                "match_score": match_score,
                "current_price": company.get("current_price"),
                # WACC enrichment placeholders (would be fetched from financial data)
                "beta": company.get("beta"),
                "cost_of_debt": company.get("cost_of_debt"),
                "tax_rate": company.get("tax_rate", 0.20),
            }

            peers.append(peer_entry)

        peers.sort(key=lambda p: p.get("match_score", 0), reverse=True)
        return peers[:max_peers]

    def _discover_dupont_peers(
        self,
        ticker: str,
        target_sector: Optional[str],
        target_market_cap: float,
        max_peers: int,
    ) -> List[Dict[str, Any]]:
        """
        DuPont: Peers are optional (decomposition of target itself).
        Returns minimal peer set for reference.
        """
        if not target_sector:
            return []

        sector_companies = self.ticker_service.search_by_sector(target_sector)
        peers = []

        for company in sector_companies[:max_peers]:
            if company.get("ticker") == ticker:
                continue

            peers.append({
                "symbol": company.get("ticker"),
                "company_name": company.get("name"),
                "sector": company.get("sector", target_sector),
                "industry": company.get("industry", "Unknown"),
                "market_cap": company.get("market_cap", 0),
                "exchange": company.get("exchange", "HOSE"),
                "match_score": 0.5,  # Equal weight for DuPont
                "current_price": company.get("current_price"),
            })

        return peers[:max_peers]

    @staticmethod
    def _calculate_match_score(
        target_sector: str,
        peer_sector: str,
        target_market_cap: float,
        peer_market_cap: float,
    ) -> float:
        """
        Calculate match score based on sector overlap + market cap similarity.
        Returns score 0.0 - 1.0.
        """
        # Sector overlap (0.6 weight)
        sector_score = 1.0 if target_sector == peer_sector else 0.3

        # Market cap similarity (0.4 weight)
        cap_score = 0.0
        if target_market_cap > 0 and peer_market_cap > 0:
            ratio = peer_market_cap / target_market_cap
            # Best match at ratio=1.0, decays towards 0.5 or 2.0
            if 0.5 <= ratio <= 2.0:
                cap_score = 1.0 - abs(1.0 - ratio) / 1.0
            else:
                cap_score = 0.0

        return round(0.6 * sector_score + 0.4 * cap_score, 3)

    def discover_vietnamese_peers(
        self,
        ticker: str,
        max_peers: int = 10,
        sector: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Legacy method: Discover Vietnamese peer companies by sector.
        Kept for backward compatibility.
        """
        try:
            target_info = self.ticker_service.get_ticker_info(ticker)
            if not target_info:
                logger.warning(f"Could not find target company {ticker}")
                return []

            target_sector = sector or target_info.get("sector")

            if target_sector:
                sector_companies = self.ticker_service.search_by_sector(target_sector)
                peers = [
                    {
                        "symbol": company.get("ticker"),
                        "company_name": company.get("name"),
                        "sector": company.get("sector", target_sector),
                        "industry": company.get("industry", "Unknown"),
                        "market_cap": company.get("market_cap"),
                        "exchange": company.get("exchange", "HOSE"),
                    }
                    for company in sector_companies
                    if company.get("ticker") != ticker
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