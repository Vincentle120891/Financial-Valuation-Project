"""Step 9: Comps Final Calculation Engine - Specialized Comparable Companies Analysis Processor

This module performs complete Comps analysis using the mathematically verified TradingCompsAnalyzer:
- Peer company multiples extraction and analysis
- Median/mean multiple calculations with outlier detection
- Implied valuation from multiple approaches
- Cross-sectional comparison and normalization

Input: Step 6 aggregated data (target + peer financials) + Step 8 Comps assumptions
Output: Complete Comps analysis with implied valuations and peer comparison
"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime
import statistics

# Import specialized Comps engine for calculations
from app.services.international.comps_engine import (
    TradingCompsAnalyzer,
    TargetCompanyData,
    PeerCompanyData,
    TradingCompsOutputs
)

logger = logging.getLogger(__name__)


class CompsValuationDetails(BaseModel):
    """Detailed Comps analysis results"""
    peer_multiples: Dict[str, List[float]]  # Multiple -> list of peer values
    median_multiples: Dict[str, float]
    mean_multiples: Dict[str, float]
    implied_valuations: Dict[str, float]  # Multiple -> implied share price
    average_implied_value: float
    peer_count: int
    outliers_removed: List[str] = []


class CompsValuationResultResponse(BaseModel):
    """
    Step 9 Comps Response: Final Comps valuation results with peer multiples.
    This is the SOLE calculation hub for Comps model in the international market.
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: str = "COMPS"
    fair_value: Optional[float] = None
    current_price: Optional[float] = None
    upside_downside: Optional[float] = None  # Percentage
    recommendation: str = "HOLD"  # BUY, HOLD, SELL
    confidence_level: str = "MEDIUM"
    comps_details: Optional[CompsValuationDetails] = None
    key_metrics: Dict[str, float] = {}
    warnings: List[str] = []
    calculation_notes: str = ""


class CompsStep9Processor:
    """
    Step 9: Comps Final Calculation Engine

    Performs complete comparable companies analysis:
    - Peer multiples extraction and statistical analysis
    - Outlier detection and removal
    - Implied valuation from median/mean multiples
    - Cross-sectional comparison

    Input: Step 6 aggregated data (target + peer financials) + Step 8 Comps assumptions
    Output: CompsValuationResultResponse with implied fair value and peer metrics
    """

    def __init__(self):
        pass

    async def calculate_comps_valuation(
        self,
        ticker: str,
        step6_data: Dict[str, Any],
        step8_final_inputs: Dict[str, Any],
        market_data: Optional[Dict] = None
    ) -> CompsValuationResultResponse:
        """
        Main entry point for Comps valuation calculation.

        Args:
            ticker: Stock ticker symbol
            step6_data: Aggregated data from Step 6 (target + peer financials)
            step8_final_inputs: Finalized inputs from Step 8 (validated Comps assumptions)
            market_data: Current market data

        Returns:
            CompsValuationResultResponse with complete Comps valuation results
        """
        warnings = []

        try:
            # Build target and peer data from Step 6
            target_company = self._build_target_company_from_step6(ticker, step6_data, market_data)
            peer_list = self._build_peer_list_from_step6(step6_data)

            # Initialize and run Comps Analyzer
            analyzer = TradingCompsAnalyzer(target_company, peer_list)

            # Execute full Comps analysis
            comps_output = analyzer.calculate()

            # Extract median multiples
            median_multiples = comps_output.median_multiples
            mean_multiples = comps_output.mean_multiples

            # Calculate implied valuations
            implied_valuations = {}

            # Get target metrics
            target_ev = target_company.enterprise_value
            target_equity_value = target_company.equity_value
            target_shares = target_company.shares_outstanding
            target_revenue = target_company.revenue
            target_ebitda = target_company.ebitda
            target_ebit = target_company.ebit
            target_net_income = target_company.net_income
            target_book_value = target_company.book_value

            # Calculate implied equity values from different multiples
            if 'EV/EBITDA' in median_multiples and target_ebitda:
                implied_ev = median_multiples['EV/EBITDA'] * target_ebitda
                implied_equity = implied_ev - target_company.net_debt
                implied_valuations['EV/EBITDA'] = implied_equity / target_shares if target_shares else 0

            if 'P/E' in median_multiples and target_net_income:
                eps = target_net_income / target_shares if target_shares else 0
                implied_valuations['P/E'] = median_multiples['P/E'] * eps

            if 'EV/EBIT' in median_multiples and target_ebit:
                implied_ev = median_multiples['EV/EBIT'] * target_ebit
                implied_equity = implied_ev - target_company.net_debt
                implied_valuations['EV/EBIT'] = implied_equity / target_shares if target_shares else 0

            if 'P/B' in median_multiples and target_book_value:
                bvps = target_book_value / target_shares if target_shares else 0
                implied_valuations['P/B'] = median_multiples['P/B'] * bvps

            if 'P/S' in median_multiples and target_revenue:
                sps = target_revenue / target_shares if target_shares else 0
                implied_valuations['P/S'] = median_multiples['P/S'] * sps

            # Calculate average implied value
            valid_implied = [v for v in implied_valuations.values() if v and v > 0]
            average_implied_value = sum(valid_implied) / len(valid_implied) if valid_implied else 0

            # Get current price
            current_price = market_data.get('current_price', 0) if market_data else 0

            # Calculate upside/downside
            upside_downside = None
            recommendation = "HOLD"
            if current_price and current_price > 0 and average_implied_value > 0:
                upside_downside = (average_implied_value - current_price) / current_price
                if upside_downside > 0.15:
                    recommendation = "BUY"
                elif upside_downside < -0.15:
                    recommendation = "SELL"

            # Determine confidence level
            peer_count = len(peer_list)
            if peer_count >= 5:
                confidence = "HIGH"
            elif peer_count >= 3:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"

            comps_details = CompsValuationDetails(
                peer_multiples=comps_output.peer_multiples,
                median_multiples=median_multiples,
                mean_multiples=mean_multiples,
                implied_valuations=implied_valuations,
                average_implied_value=average_implied_value,
                peer_count=peer_count,
                outliers_removed=comps_output.outliers_removed or []
            )

            key_metrics = {
                'Average Implied Value': average_implied_value,
                'Current Price': current_price,
                'Upside/Downside': upside_downside,
                'Peer Count': peer_count,
                'Median P/E': median_multiples.get('P/E', 0),
                'Median EV/EBITDA': median_multiples.get('EV/EBITDA', 0),
                'Median P/B': median_multiples.get('P/B', 0),
                'Median P/S': median_multiples.get('P/S', 0)
            }

            calculation_notes = f"Comps analysis completed with {peer_count} peers. " \
                              f"Average implied value: ${average_implied_value:.2f}. " \
                              f"Median EV/EBITDA: {median_multiples.get('EV/EBITDA', 0):.2f}x"

        except Exception as e:
            logger.error(f"Comps Engine calculation failed: {e}. Using fallback calculation.")
            warnings.append(f"Comps Engine error: {str(e)}")
            # Fallback to simplified calculation
            return self._calculate_comps_fallback(ticker, step6_data, step8_final_inputs, market_data, warnings)

        return CompsValuationResultResponse(
            session_id=f"step9_comps_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            fair_value=average_implied_value,
            current_price=current_price,
            upside_downside=upside_downside,
            recommendation=recommendation,
            confidence_level=confidence,
            comps_details=comps_details,
            key_metrics=key_metrics,
            warnings=warnings,
            calculation_notes=calculation_notes
        )

    def _build_target_company_from_step6(
        self,
        ticker: str,
        step6_data: Dict,
        market_data: Optional[Dict]
    ) -> TargetCompanyData:
        """Build TargetCompanyData from Step 6 data"""
        historical_data = step6_data.get('historical_financials', {})
        market_info = market_data or {}

        # Extract latest year data (index 7 for Year 8)
        revenue = historical_data.get('revenue', [0] * 8)
        ebitda = historical_data.get('ebitda', [0] * 8)
        ebit = historical_data.get('ebit', historical_data.get('operating_income', [0] * 8))
        net_income = historical_data.get('net_income', [0] * 8)
        total_assets = historical_data.get('total_assets', [0] * 8)
        shareholders_equity = historical_data.get('shareholders_equity', [0] * 8)

        latest_idx = 7
        if latest_idx >= len(revenue):
            latest_idx = len(revenue) - 1 if revenue else 0

        rev = revenue[latest_idx] if latest_idx < len(revenue) else 0
        eb = ebitda[latest_idx] if latest_idx < len(ebitda) else 0
        ebt = ebit[latest_idx] if latest_idx < len(ebit) else 0
        ni = net_income[latest_idx] if latest_idx < len(net_income) else 0
        ta = total_assets[latest_idx] if latest_idx < len(total_assets) else 0
        eq = shareholders_equity[latest_idx] if latest_idx < len(shareholders_equity) else 0

        # Get market data
        current_price = market_info.get('current_price', 0)
        shares_outstanding = market_info.get('shares_outstanding', 0)
        net_debt = market_info.get('net_debt', 0)

        # Calculate derived values
        equity_value = current_price * shares_outstanding if current_price and shares_outstanding else eq
        enterprise_value = equity_value + net_debt
        book_value = eq

        return TargetCompanyData(
            ticker=ticker,
            company_name=ticker,
            equity_value=equity_value,
            enterprise_value=enterprise_value,
            revenue=rev,
            ebitda=eb,
            ebit=ebt,
            net_income=ni,
            shares_outstanding=shares_outstanding,
            net_debt=net_debt,
            book_value=book_value
        )

    def _build_peer_list_from_step6(self, step6_data: Dict) -> List[PeerCompanyData]:
        """Build list of PeerCompanyData from Step 6 data"""
        peers_data = step6_data.get('peer_companies', [])
        peer_list = []

        for peer in peers_data:
            try:
                peer_data = PeerCompanyData(
                    ticker=peer.get('ticker', ''),
                    company_name=peer.get('company_name', peer.get('ticker', '')),
                    equity_value=peer.get('equity_value', 0),
                    enterprise_value=peer.get('enterprise_value', 0),
                    revenue=peer.get('revenue', 0),
                    ebitda=peer.get('ebitda', 0),
                    ebit=peer.get('ebit', 0),
                    net_income=peer.get('net_income', 0),
                    book_value=peer.get('book_value', 0)
                )
                peer_list.append(peer_data)
            except Exception as e:
                logger.warning(f"Failed to build peer data for {peer.get('ticker', 'unknown')}: {e}")
                continue

        return peer_list

    def _calculate_comps_fallback(
        self,
        ticker: str,
        step6_data: Dict,
        step8_final_inputs: Dict,
        market_data: Optional[Dict],
        warnings: List[str]
    ) -> CompsValuationResultResponse:
        """Fallback Comps calculation if engine fails"""
        current_price = market_data.get('current_price', 0) if market_data else 0
        peers_data = step6_data.get('peer_companies', [])

        # Simple fallback: use average of available peer multiples if any
        if peers_data:
            # Simplified logic - just return current price with low confidence
            fair_value = current_price
            recommendation = "HOLD"
            confidence = "LOW"
        else:
            fair_value = 0
            recommendation = "HOLD"
            confidence = "LOW"

        return CompsValuationResultResponse(
            session_id=f"step9_comps_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            fair_value=fair_value,
            current_price=current_price,
            upside_downside=None,
            recommendation=recommendation,
            confidence_level=confidence,
            key_metrics={'Current Price': current_price},
            warnings=warnings,
            calculation_notes="Comps calculation failed. Using fallback with limited data."
        )