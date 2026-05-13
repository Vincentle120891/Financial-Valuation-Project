"""Step 4: Forecast Drivers Processor - Model Selection Point

Refactored to use Unified Schemas with DataField wrappers for consistent API contracts.
"""
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel
from enum import Enum

from app.api.schemas.unified_step_schemas import (
    PeerCompany,
    DataField,
    DataStatus,
    ValuationMethod,
    MarketType,
    UnifiedStep4Response
)

logger = logging.getLogger(__name__)


class Step4ForecastProcessor:
    """
    Processor for Step 4: Peer Company Selection.
    
    Responsibilities:
    - Process peer company selection for COMPS and WACC calculations
    - Support both suggested peers (auto-discovered) and custom peers
    - Return unified schema response with DataField wrappers
    
    Note: This processor is now method-agnostic and focuses on peer selection only.
    Forecast drivers are handled in Step 8 (Assumptions Preparation).
    """
    
    def process_peer_selection(
        self,
        ticker: str,
        session_id: str,
        method: str,
        market: str,
        suggested_peers: Optional[List[str]] = None,
        custom_peers: Optional[List[str]] = None,
        peer_data: Optional[Dict] = None
    ) -> UnifiedStep4Response:
        """
        Process peer company selection and return unified response.
        
        Args:
            ticker: Target company ticker
            session_id: Session identifier
            method: Valuation method (DCF, DUPONT, COMPS)
            market: Market type (international, vietnam)
            suggested_peers: List of auto-suggested peer tickers
            custom_peers: List of manually selected peer tickers
            peer_data: Optional dictionary with peer company information
            
        Returns:
            UnifiedStep4Response with peer selection results
        """
        logger.info(f"Processing peer selection for {ticker} using {method} model")
        
        # Determine which peers to use
        selected_peers = []
        if custom_peers:
            selected_peers = custom_peers
        elif suggested_peers:
            selected_peers = suggested_peers
        else:
            # No peers provided - return empty response
            return UnifiedStep4Response(
                status="no_peers",
                session_id=session_id,
                method=method.upper(),
                market=market.lower(),
                target_company=ticker,
                suggested_peers=[],
                selected_peers=[],
                message="No peers provided. Please select peer companies for comparison."
            )
        
        # Build peer company objects with DataField wrappers
        peer_companies = []
        peer_data = peer_data or {}
        
        for peer_ticker in selected_peers:
            # Get peer info from provided data or create minimal object
            peer_info = peer_data.get(peer_ticker, {})
            
            # Create DataField for market cap if available
            market_cap_field = None
            if peer_info.get('marketCap'):
                market_cap_field = DataField(
                    value=peer_info.get('marketCap'),
                    status=DataStatus.RETRIEVED,
                    source="yfinance",
                    unit="USD",
                    confidence_score=90.0
                )
            
            peer_company = PeerCompany(
                ticker=peer_ticker,
                company_name=peer_info.get('name', peer_ticker),
                sector=peer_info.get('sector', 'Unknown'),
                industry=peer_info.get('industry', 'Unknown'),
                market_cap=market_cap_field,
                selected=True
            )
            peer_companies.append(peer_company)
        
        # Calculate data quality score based on peer data completeness
        peers_with_data = sum(1 for p in peer_companies if p.market_cap and p.market_cap.value)
        data_quality = (peers_with_data / len(peer_companies) * 100) if peer_companies else 0
        
        return UnifiedStep4Response(
            status="success",
            session_id=session_id,
            method=method.upper(),
            market=market.lower(),
            target_company=ticker,
            suggested_peers=peer_companies,
            selected_peers=selected_peers,
            message=f"Selected {len(selected_peers)} peer companies for {method.upper()} valuation"
        )
