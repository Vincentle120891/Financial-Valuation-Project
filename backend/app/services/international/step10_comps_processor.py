"""Step 10: Comps Valuation Processor

Handles Comparable Company Analysis for the international market.
Extracted from step10_valuation_processor.py for single-responsibility clarity.

Flow: Step 9 confirmed outputs → TargetCompanyData + PeerCompanyData → TradingCompsAnalyzer → Results dict
"""
import logging
from typing import Dict, List, Optional, Any
import statistics

from app.services.international.comps_engine import (
    TradingCompsAnalyzer,
    TargetCompanyData,
    PeerCompanyData,
)
from app.services.international.step10_utils import msi_to_dict, build_fallback_result

logger = logging.getLogger(__name__)


class Step10CompsProcessor:
    """Comps analysis processor — builds peer data, runs TradingCompsAnalyzer, returns results."""

    async def run_comps_valuation(
        self, ticker: str, assumptions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform Comps analysis using TradingCompsAnalyzer engine.

        Args:
            ticker: Stock ticker symbol
            assumptions: Confirmed assumptions from Step 9

        Returns:
            Dictionary with valuation_summary, detailed_outputs, sensitivity_analysis,
            scenario_analysis, confidence_level, key_assumptions_summary, warnings
        """
        warnings = list(assumptions.get('warnings', []))

        try:
            msi = msi_to_dict(assumptions.get('model_specific_inputs', {}))
            historical = assumptions.get('historical_financials_summary', {})
            market_ctx = assumptions.get('market_context', {})

            target_data = self._build_target_company(ticker, msi, historical, market_ctx)
            peer_list = self._build_peer_list(assumptions)

            if not peer_list:
                return self._calculate_comps_from_multiples(ticker, msi, historical, warnings)

            analyzer = TradingCompsAnalyzer(target=target_data, peers=peer_list)
            comps_output = analyzer.run_analysis()

            median_multiples = self._extract_median_multiples(comps_output)
            implied_values = [
                comps_output.avg_ev_ebitda_ltm_price,
                comps_output.avg_ev_ebitda_fy23_price,
                comps_output.avg_pe_ltm_price,
                comps_output.avg_pe_fy23_price,
            ]
            implied_values = [v for v in implied_values if v and v > 0]
            average_implied_value = statistics.mean(implied_values) if implied_values else 0

            current_price = target_data.share_price if target_data else 0

            upside_downside = None
            recommendation = "HOLD"
            if current_price and current_price > 0 and average_implied_value > 0:
                upside_downside = (average_implied_value - current_price) / current_price
                if upside_downside > 0.15:
                    recommendation = "BUY"
                elif upside_downside < -0.15:
                    recommendation = "SELL"

            confidence = "high" if comps_output.peer_count_after_filtering >= 5 else "medium"

            peer_scatter = self._build_peer_scatter(comps_output, ticker)

            key_metrics = {
                'Median EV/EBITDA LTM': comps_output.ev_ebitda_ltm_stats.median if comps_output.ev_ebitda_ltm_stats else None,
                'Median P/E LTM': comps_output.pe_ltm_stats.median if comps_output.pe_ltm_stats else None,
                'Peer Count': comps_output.peer_count_after_filtering,
                'Average Implied Value': average_implied_value,
                'Current Price': current_price,
                'Upside/Downside': upside_downside,
            }

            calculation_notes = (
                f"Comps valuation completed using {comps_output.peer_count_after_filtering} peers. "
                f"Median EV/EBITDA LTM: {comps_output.ev_ebitda_ltm_stats.median:.2f}x "
                f"(if available). Average implied value: ${average_implied_value:.2f}"
            )

            return {
                'valuation_summary': {
                    'enterprise_value': None,
                    'equity_value': None,
                    'fair_value_per_share': {'value': average_implied_value, 'status': 'CALCULATED', 'unit': 'USD'} if average_implied_value > 0 else None,
                    'current_price': {'value': current_price, 'status': 'RETRIEVED', 'unit': 'USD'} if current_price else None,
                    'implied_upside_downside': {'value': upside_downside, 'status': 'CALCULATED', 'unit': 'percentage'} if upside_downside is not None else None,
                    'valuation_range_low': {'value': comps_output.min_ev_ebitda_ltm_price if comps_output.min_ev_ebitda_ltm_price > 0 else average_implied_value * 0.9, 'status': 'CALCULATED', 'unit': 'USD'},
                    'valuation_range_high': {'value': comps_output.max_ev_ebitda_ltm_price if comps_output.max_ev_ebitda_ltm_price > 0 else average_implied_value * 1.1, 'status': 'CALCULATED', 'unit': 'USD'},
                },
                'detailed_outputs': {
                    'comps_analysis': {
                        'peer_multiples': comps_output.peer_multiples,
                        'median_multiples': median_multiples,
                        'implied_valuations': {
                            'Average EV/EBITDA LTM': comps_output.avg_ev_ebitda_ltm_price,
                            'Average EV/EBITDA FY23': comps_output.avg_ev_ebitda_fy23_price,
                            'Average P/E LTM': comps_output.avg_pe_ltm_price,
                            'Average P/E FY23': comps_output.avg_pe_fy23_price,
                            'Maximum EV/EBITDA LTM': comps_output.max_ev_ebitda_ltm_price,
                            'Minimum EV/EBITDA LTM': comps_output.min_ev_ebitda_ltm_price,
                        },
                        'average_implied_value': average_implied_value,
                        'peer_count': comps_output.peer_count_after_filtering,
                        'excluded_peers': comps_output.excluded_peers,
                        'peer_scatter': peer_scatter,
                        'chart_data': comps_output.chart_data,
                        'calculation_notes': calculation_notes,
                    }
                },
                'sensitivity_analysis': None,
                'scenario_analysis': None,
                'confidence_level': confidence,
                'key_assumptions_summary': {
                    'peer_multiples': msi.get('peer_multiples', {}),
                    'outlier_threshold': msi.get('outlier_threshold'),
                    'selected_peers': msi.get('selected_peers', []),
                },
                'warnings': warnings,
            }

        except Exception as e:
            logger.error(f"Comps Engine calculation failed: {e}", exc_info=True)
            warnings.append(f"Comps Engine error: {str(e)}")
            return self._build_fallback_result(ticker, warnings)

    # ─── Target Company Builder ────────────────────────────────────────────

    def _build_target_company(
        self, ticker: str, msi: Dict, historical: Dict, market_ctx: Dict
    ) -> TargetCompanyData:
        """Build TargetCompanyData for Comps analysis from Step 9 outputs."""
        share_price = msi.get('current_price', 0) or 0
        shares_outstanding = msi.get('shares_outstanding', 0) or 0
        net_debt = msi.get('net_debt', 0) or 0

        market_cap = share_price * shares_outstanding
        enterprise_value = market_cap + net_debt

        ebitda_ltm = historical.get('latest_ebitda', 0) or 0
        latest_net_income = historical.get('latest_net_income', 0) or 0
        eps_ltm = latest_net_income / shares_outstanding if shares_outstanding and latest_net_income else 0

        return TargetCompanyData(
            ticker=ticker,
            company_name=ticker,
            market_cap=market_cap,
            enterprise_value=enterprise_value,
            ebitda_ltm=ebitda_ltm,
            ebitda_fy2023=ebitda_ltm * 1.05,
            ebitda_fy2024=ebitda_ltm * 1.10,
            eps_ltm=eps_ltm,
            eps_fy2023=eps_ltm * 1.05,
            eps_fy2024=eps_ltm * 1.10,
            net_debt=net_debt,
            shares_outstanding=shares_outstanding,
            share_price=share_price,
            currency=market_ctx.get('currency', 'USD'),
        )

    # ─── Peer List Builder ─────────────────────────────────────────────────

    def _build_peer_list(self, assumptions: Dict[str, Any]) -> List[PeerCompanyData]:
        """Build list of PeerCompanyData from Step 9 outputs."""
        historical = assumptions.get('historical_financials_summary', {})
        msi = msi_to_dict(assumptions.get('model_specific_inputs', {}))

        peers = []
        peer_companies = historical.get('peer_companies', [])
        if peer_companies:
            for pc in peer_companies:
                try:
                    peer = PeerCompanyData(
                        ticker=pc.get('ticker', ''),
                        company_name=pc.get('company_name', pc.get('ticker', '')),
                        market_cap=pc.get('market_cap', 0),
                        enterprise_value=pc.get('enterprise_value', 0),
                        share_price=pc.get('share_price', 0),
                        shares_outstanding=pc.get('shares_outstanding', 0),
                        ebitda_ltm=pc.get('ebitda_ltm', 0),
                        ebitda_fy2023=pc.get('ebitda_fy2023', pc.get('ebitda_ltm', 0) * 1.05),
                        ebitda_fy2024=pc.get('ebitda_fy2024', pc.get('ebitda_ltm', 0) * 1.10),
                        eps_ltm=pc.get('eps_ltm', 0),
                        eps_fy2023=pc.get('eps_fy2023', pc.get('eps_ltm', 0) * 1.05),
                        eps_fy2024=pc.get('eps_fy2024', pc.get('eps_ltm', 0) * 1.10),
                        industry=pc.get('industry', ''),
                        sector=pc.get('sector', ''),
                    )
                    peers.append(peer)
                except Exception as e:
                    logger.warning(f"Failed to build peer data for {pc.get('ticker', '?')}: {e}")

        selected_peers = msi.get('selected_peers', [])
        if selected_peers and peers:
            peers = [p for p in peers if p.ticker in selected_peers]

        return peers

    # ─── Simplified Comps from Median Multiples ────────────────────────────

    def _calculate_comps_from_multiples(
        self, ticker: str, msi: Dict, historical: Dict, warnings: List[str]
    ) -> Dict[str, Any]:
        """Simplified Comps calculation using only median multiples from Step 9."""
        peer_multiples = msi.get('peer_multiples', {})
        current_price = msi.get('current_price', 0) or 0
        shares = msi.get('shares_outstanding', 0) or 0
        net_debt = msi.get('net_debt', 0) or 0

        latest_ebitda = historical.get('latest_ebitda', 0) or 0
        latest_net_income = historical.get('latest_net_income', 0) or 0

        implied_values = {}

        ev_ebitda_multiple = peer_multiples.get('EV/EBITDA', 0)
        if ev_ebitda_multiple and latest_ebitda:
            implied_ev = ev_ebitda_multiple * latest_ebitda
            implied_equity = implied_ev - net_debt
            implied_share_price = implied_equity / shares if shares else 0
            implied_values['EV/EBITDA'] = implied_share_price

        pe_multiple = peer_multiples.get('P/E', 0)
        if pe_multiple and latest_net_income:
            implied_equity = pe_multiple * latest_net_income
            implied_share_price = implied_equity / shares if shares else 0
            implied_values['P/E'] = implied_share_price

        valid_values = [v for v in implied_values.values() if v and v > 0]
        average_implied = statistics.mean(valid_values) if valid_values else 0

        upside = None
        recommendation = "HOLD"
        if current_price and current_price > 0 and average_implied > 0:
            upside = (average_implied - current_price) / current_price
            if upside > 0.15:
                recommendation = "BUY"
            elif upside < -0.15:
                recommendation = "SELL"

        confidence = "low" if not valid_values else "medium"
        warnings.append("Comps calculated using median multiples only (no individual peer data available)")

        return {
            'valuation_summary': {
                'enterprise_value': None,
                'equity_value': None,
                'fair_value_per_share': {'value': average_implied, 'status': 'CALCULATED', 'unit': 'USD'} if average_implied > 0 else None,
                'current_price': {'value': current_price, 'status': 'RETRIEVED', 'unit': 'USD'} if current_price else None,
                'implied_upside_downside': {'value': upside, 'status': 'CALCULATED', 'unit': 'percentage'} if upside is not None else None,
            },
            'detailed_outputs': {
                'comps_analysis': {
                    'peer_multiples_used': peer_multiples,
                    'implied_valuations': implied_values,
                    'average_implied_value': average_implied,
                    'peer_count': 0,
                    'method': 'median_multiples_only',
                }
            },
            'sensitivity_analysis': None,
            'scenario_analysis': None,
            'confidence_level': confidence,
            'key_assumptions_summary': {
                'peer_multiples': peer_multiples,
                'outlier_threshold': msi.get('outlier_threshold'),
            },
            'warnings': warnings,
        }

    # ─── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _extract_median_multiples(comps_output) -> Dict[str, float]:
        median_multiples = {}
        if comps_output.ev_ebitda_ltm_stats:
            median_multiples['EV/EBITDA LTM'] = comps_output.ev_ebitda_ltm_stats.median
        if comps_output.ev_ebitda_fy23_stats:
            median_multiples['EV/EBITDA FY23'] = comps_output.ev_ebitda_fy23_stats.median
        if comps_output.pe_ltm_stats:
            median_multiples['P/E LTM'] = comps_output.pe_ltm_stats.median
        if comps_output.pe_fy23_stats:
            median_multiples['P/E FY23'] = comps_output.pe_fy23_stats.median
        return median_multiples

    @staticmethod
    def _build_peer_scatter(comps_output, ticker: str) -> List[Dict]:
        peer_scatter = []
        for pm in comps_output.peer_multiples:
            if pm.get('ev_ebitda_ltm') and pm.get('ticker'):
                peer_scatter.append({
                    'ticker': pm['ticker'],
                    'ev_to_ebitda': pm.get('ev_ebitda_ltm'),
                    'pe_ratio': pm.get('pe_ltm'),
                    'is_target': pm.get('ticker') == ticker,
                })
        return peer_scatter

    @staticmethod
    def _build_fallback_result(ticker: str, warnings: List[str]) -> Dict[str, Any]:
        return build_fallback_result(ticker, 'COMPS', warnings)
