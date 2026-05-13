"""
Vietnamese Step 1-4 Unified Transformers

Transforms Vietnamese Step 1-4 processor outputs to unified schema format.
Ensures consistency with International market responses.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import logging

from app.api.schemas.unified_step_schemas import (
    UnifiedStep1Response,
    UnifiedStep2Response,
    UnifiedStep3Response,
    UnifiedStep4Response,
    CompanySearchResult,
    MarketDataPoint,
    MarketRiskMetrics,
    ExchangeInfo,
    PeerCompany,
    DataStatus,
    DataField,
)

logger = logging.getLogger(__name__)


class VNStep1UnifiedTransformer:
    """
    Transforms Vietnamese Step 1 ticker selection output to unified schema.
    """

    def transform(
        self,
        vn_output: Any,
        query: str,
        market: str = "vietnam"
    ) -> UnifiedStep1Response:
        """
        Transform Vietnamese Step 1 output to unified response.

        Args:
            vn_output: Output from vn_Step1TickerProcessor
            query: Original search query
            market: Market type

        Returns:
            UnifiedStep1Response conforming to standard schema
        """
        # Extract results from Vietnamese processor output
        results = []
        if hasattr(vn_output, 'tickers'):
            for ticker_info in vn_output.tickers:
                results.append(CompanySearchResult(
                    ticker=ticker_info.symbol,
                    company_name=ticker_info.name,
                    exchange=ticker_info.exchange,
                    market="vietnam",
                    sector=ticker_info.sector,
                    industry=ticker_info.industry,
                    currency=ticker_info.currency,
                    country="Vietnam"
                ))

        valid_count = getattr(vn_output, 'valid_count', len([r for r in results]))
        invalid_count = getattr(vn_output, 'invalid_count', 0)

        return UnifiedStep1Response(
            status="success" if valid_count > 0 else "no_results",
            query=query,
            market=market,
            results=results,
            total_results=len(results),
            message=f"Found {valid_count} valid Vietnamese tickers"
        )


class VNStep2UnifiedTransformer:
    """
    Transforms Vietnamese Step 2 market data output to unified schema.
    """

    def transform(
        self,
        vn_output: Any,
        session_id: str,
        ticker: str,
        company_name: str,
        market: str = "vietnam"
    ) -> UnifiedStep2Response:
        """
        Transform Vietnamese Step 2 output to unified response.

        Args:
            vn_output: Output from vn_Step2MarketDataProcessor
            session_id: Session identifier
            ticker: Ticker symbol
            company_name: Company name
            market: Market type

        Returns:
            UnifiedStep2Response conforming to standard schema
        """
        # Build market data points from Vietnamese output
        market_data = []
        if hasattr(vn_output, 'market_data'):
            for data_point in vn_output.market_data:
                market_data.append(MarketDataPoint(
                    metric=data_point.metric,
                    value=data_point.value,
                    source=data_point.source,
                    status=DataStatus(data_point.status) if hasattr(data_point, 'status') else DataStatus.RETRIEVED,
                    formula=getattr(data_point, 'formula', None),
                    confidence_score=data_point.confidence,
                    currency=data_point.currency
                ))

        # Build risk metrics
        risk_metrics = None
        if hasattr(vn_output, 'risk_metrics'):
            rm = vn_output.risk_metrics
            risk_metrics = MarketRiskMetrics(
                risk_free_rate=DataField(value=getattr(rm, 'risk_free_rate', None), source="vietnamese_bond", unit="%") if hasattr(rm, 'risk_free_rate') else None,
                market_risk_premium=DataField(value=getattr(rm, 'market_risk_premium', None), source="calculated", unit="%") if hasattr(rm, 'market_risk_premium') else None,
                beta=DataField(value=getattr(rm, 'beta', None), source="calculated") if hasattr(rm, 'beta') else None,
                levered_beta=DataField(value=getattr(rm, 'levered_beta', None), source="calculated") if hasattr(rm, 'levered_beta') else None,
                unlevered_beta=DataField(value=getattr(rm, 'unlevered_beta', None), source="calculated") if hasattr(rm, 'unlevered_beta') else None,
                equity_risk_premium=DataField(value=getattr(rm, 'equity_risk_premium', None), source="calculated", unit="%") if hasattr(rm, 'equity_risk_premium') else None,
                country_risk_premium=DataField(value=getattr(rm, 'country_risk_premium', None), source="estimated", unit="%") if hasattr(rm, 'country_risk_premium') else None,
                vnindex_performance=getattr(rm, 'vnindex_performance', None)
            )

        # Build exchange info for Vietnam
        exchange_info = None
        if hasattr(vn_output, 'exchange_info') and vn_output.exchange_info:
            ei = vn_output.exchange_info
            exchange_info = ExchangeInfo(
                code=getattr(ei, 'code', None),
                name=getattr(ei, 'name', None),
                trading_hours=getattr(ei, 'trading_hours', None),
                settlement=getattr(ei, 'settlement', None),
                price_band=getattr(ei, 'price_band', None),
                currency=getattr(ei, 'currency', "VND")
            )

        missing_data = getattr(vn_output, 'missing_data', [])
        warnings = getattr(vn_output, 'warnings', [])
        data_quality_score = getattr(vn_output, 'data_quality_score', 0.0)

        return UnifiedStep2Response(
            status="completed" if data_quality_score > 70 else "partial",
            session_id=session_id,
            ticker=ticker,
            market=market,
            company_name=company_name,
            confirmed=True,
            market_data=market_data,
            risk_metrics=risk_metrics,
            market_code=getattr(vn_output, 'market_code', None),
            exchange_info=exchange_info,
            missing_data=missing_data,
            warnings=warnings,
            data_quality_score=data_quality_score,
            message=f"Market data retrieved for {ticker} ({company_name})"
        )


class VNStep3UnifiedTransformer:
    """
    Transforms Vietnamese Step 3 peer selection output to unified schema.
    """

    def transform(
        self,
        vn_output: Any,
        session_id: str,
        method: str,
        market: str = "vietnam",
        target_company: str = ""
    ) -> UnifiedStep4Response:
        """
        Transform Vietnamese Step 3 output to unified response.
        Note: Maps to UnifiedStep4Response as it handles peer selection.

        Args:
            vn_output: Output from vn_Step3PeerManagementService
            session_id: Session identifier
            method: Valuation method
            market: Market type
            target_company: Target company name

        Returns:
            UnifiedStep4Response conforming to standard schema
        """
        # Build suggested peers from output
        suggested_peers = []
        selected_peers = []

        if isinstance(vn_output, dict):
            # Handle dictionary output from save_peers_and_fetch_data
            if 'peer_tickers' in vn_output:
                selected_peers = vn_output['peer_tickers']
            if 'errors' in vn_output and vn_output['errors']:
                logger.warning(f"Peer fetch errors: {vn_output['errors']}")
        elif hasattr(vn_output, 'peers'):
            # Handle object output with peers list
            for peer in vn_output.peers:
                peer_company = PeerCompany(
                    ticker=peer.get('symbol') or peer.get('ticker', ''),
                    company_name=peer.get('company_name', ''),
                    sector=peer.get('sector', 'Unknown'),
                    industry=peer.get('industry', 'Unknown'),
                    market_cap=DataField(value=peer.get('market_cap'), currency="VND", unit="billion VND") if peer.get('market_cap') else None,
                    selected=True
                )
                suggested_peers.append(peer_company)
                selected_peers.append(peer_company.ticker)

        status = "success" if len(selected_peers) > 0 else "no_peers"

        return UnifiedStep4Response(
            status=status,
            session_id=session_id,
            method=method,
            market=market,
            target_company=target_company,
            suggested_peers=suggested_peers,
            selected_peers=selected_peers,
            message=f"Selected {len(selected_peers)} Vietnamese peer companies"
        )


class VNStep4UnifiedTransformer:
    """
    Transforms Vietnamese Step 4 model selection output to unified schema.
    """

    def transform(
        self,
        vn_output: Any,
        session_id: str,
        market: str = "vietnam"
    ) -> UnifiedStep4Response:
        """
        Transform Vietnamese Step 4 output to unified response.

        Args:
            vn_output: Output from vn_ModelSelectionProcessor
            session_id: Session identifier
            market: Market type

        Returns:
            UnifiedStep4Response conforming to standard schema
        """
        selected_models = []
        if hasattr(vn_output, 'selected_models'):
            selected_models = vn_output.selected_models
        elif isinstance(vn_output, dict) and 'selected_models' in vn_output:
            selected_models = vn_output['selected_models']

        # Map model selection to peer selection response structure
        # Since Step 4 is about model selection, we adapt the response
        return UnifiedStep4Response(
            status="success" if selected_models else "no_selection",
            session_id=session_id,
            method=selected_models[0] if selected_models else "UNKNOWN",
            market=market,
            target_company=getattr(vn_output, 'target_company', "Unknown"),
            suggested_peers=[],  # Not applicable for model selection
            selected_peers=selected_models,  # Reuse field for selected models
            message=f"Selected {len(selected_models)} valuation model(s): {', '.join(selected_models)}"
        )