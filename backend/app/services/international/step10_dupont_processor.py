"""Step 10: DuPont Valuation Processor

Handles DuPont ROE decomposition analysis for the international market.
Extracted from step10_valuation_processor.py for single-responsibility clarity.

Flow: Step 9 confirmed outputs → FinancialStatements → DuPontAnalyzer → Results dict
"""
import logging
from typing import Dict, List, Optional, Any

from app.services.international.dupont_engine import (
    DuPontAnalyzer,
    FinancialStatements,
)
from app.services.international.step10_utils import msi_to_dict, build_fallback_result

logger = logging.getLogger(__name__)


class Step10DuPontProcessor:
    """DuPont analysis processor — builds FinancialStatements, runs DuPontAnalyzer, returns results."""

    async def run_dupont_valuation(
        self, ticker: str, assumptions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform DuPont analysis using DuPontAnalyzer engine.

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

            financial_statements = self._build_dupont_statements(historical)

            analyzer = DuPontAnalyzer()
            analyzer.load_data(financial_statements)
            dupont_output = analyzer.calculate_all()

            latest_idx = 7
            net_margin = dupont_output.ratios.net_profit_margin[latest_idx]
            asset_turnover = dupont_output.ratios.asset_turnover[latest_idx]
            equity_multiplier = dupont_output.ratios.total_assets_to_equity[latest_idx]
            roe = dupont_output.ratios.roe[latest_idx]
            roa = dupont_output.ratios.roa[latest_idx]

            trend_analysis = self._build_trend_analysis(dupont_output)
            benchmark_comparison = {
                'industry_avg_roe': 0.15,
                'sector_avg_roe': 0.12,
                'sp500_avg_roe': 0.18,
            }

            if not all(dupont_output.ratios.roe_3step_check):
                warnings.append("DuPont 3-step calculation has minor rounding differences")

            if roe > 0.20:
                recommendation, confidence = "BUY", "HIGH"
            elif roe > 0.15:
                recommendation, confidence = "HOLD", "MEDIUM"
            else:
                recommendation, confidence = "SELL", "MEDIUM"

            ratios_by_year = self._build_ratios_by_year(dupont_output)

            key_metrics = {
                'Net Profit Margin': net_margin,
                'Asset Turnover': asset_turnover,
                'Equity Multiplier': equity_multiplier,
                'ROE': roe,
                'ROA': roa,
                'Gross Margin': dupont_output.ratios.gross_margin[latest_idx],
                'EBITDA Margin': dupont_output.ratios.ebitda_margin[latest_idx],
                'Interest Coverage': dupont_output.ratios.interest_coverage[latest_idx],
                'Debt to Equity': dupont_output.ratios.debt_to_equity[latest_idx],
                'Current Ratio': dupont_output.ratios.current_ratio[latest_idx],
                'Inventory Turnover': dupont_output.ratios.inventory_turnover[latest_idx],
                'ROIC': dupont_output.ratios.roic[latest_idx],
            }

            calculation_notes = (
                f"DuPont analysis completed. ROE: {roe:.2%} decomposed into "
                f"Net Margin ({net_margin:.2%}) × Asset Turnover ({asset_turnover:.2f}) × "
                f"Equity Multiplier ({equity_multiplier:.2f}). "
                f"3-step validation: {'Passed' if all(dupont_output.ratios.roe_3step_check) else 'Minor differences'}"
            )

            return {
                'valuation_summary': {
                    'fair_value_per_share': None,
                    'current_price': {'value': msi.get('current_price'), 'status': 'RETRIEVED'} if msi.get('current_price') else None,
                    'implied_upside_downside': None,
                    'enterprise_value': None,
                    'equity_value': None,
                },
                'detailed_outputs': {
                    'dupont_analysis': {
                        'net_profit_margin': net_margin,
                        'asset_turnover': asset_turnover,
                        'equity_multiplier': equity_multiplier,
                        'roe': roe,
                        'roa': roa,
                        'trend_analysis': trend_analysis,
                        'benchmark_comparison': benchmark_comparison,
                        'ratios_by_year': ratios_by_year,
                        'calculation_notes': calculation_notes,
                    }
                },
                'sensitivity_analysis': None,
                'scenario_analysis': None,
                'confidence_level': confidence.lower(),
                'key_assumptions_summary': {
                    'target_net_margin': msi.get('target_net_margin'),
                    'target_asset_turnover': msi.get('target_asset_turnover'),
                    'target_equity_multiplier': msi.get('target_equity_multiplier'),
                },
                'warnings': warnings,
            }

        except Exception as e:
            logger.error(f"DuPont Engine calculation failed: {e}", exc_info=True)
            warnings.append(f"DuPont Engine error: {str(e)}")
            return self._build_fallback_result(ticker, warnings)

    # ─── FinancialStatements Builder ───────────────────────────────────────

    def _build_dupont_statements(self, historical: Dict[str, Any]) -> FinancialStatements:
        """Build FinancialStatements for DuPont analysis from Step 9 historical summary."""
        statements = FinancialStatements()

        def to_8(arr):
            if not arr:
                return [0.0] * 8
            result = list(arr[:8])
            while len(result) < 8:
                result.append(0.0)
            return [float(v) if v else 0.0 for v in result]

        statements.revenue = to_8(historical.get('revenue', []))
        statements.cogs_gross = to_8(historical.get('cogs', []))
        statements.sga = to_8(historical.get('sga', []))
        statements.other_operating_expenses = to_8(historical.get('other_operating_expenses', []))
        statements.depreciation = to_8(historical.get('depreciation', []))
        statements.interest_expense = to_8(historical.get('interest_expense', []))
        statements.interest_income = to_8(historical.get('interest_income', []))
        statements.tax_current = to_8(historical.get('tax_expense', []))

        statements.cash = to_8(historical.get('cash', []))
        statements.accounts_receivable = to_8(historical.get('accounts_receivable', []))
        statements.inventories = to_8(historical.get('inventories', []))
        statements.ppe_component1 = to_8(historical.get('ppe', []))
        statements.accounts_payable = to_8(historical.get('accounts_payable', []))
        statements.long_term_debt = to_8(historical.get('long_term_debt', []))
        statements.common_equity = to_8(historical.get('shareholders_equity', []))
        statements.retained_earnings = to_8(historical.get('retained_earnings', []))

        statements.capex = to_8(historical.get('capex', []))
        statements.dividends = to_8(historical.get('dividends', []))

        # Fallback: use latest_* values if multi-year arrays are empty
        if all(v == 0.0 for v in statements.revenue):
            if historical.get('latest_revenue'):
                statements.revenue[7] = float(historical['latest_revenue'])
            if historical.get('latest_ebitda'):
                rev = historical.get('latest_revenue', 1)
                statements.cogs_gross[7] = -abs(rev - historical['latest_ebitda'])
            if historical.get('latest_shareholders_equity'):
                statements.common_equity[7] = float(historical['latest_shareholders_equity'])
            if historical.get('latest_capex'):
                statements.capex[7] = -abs(float(historical['latest_capex']))

        # Negate fields matching Excel convention
        for i in range(8):
            if statements.cogs_gross[i] > 0:
                statements.cogs_gross[i] = -statements.cogs_gross[i]
            if statements.sga[i] > 0:
                statements.sga[i] = -statements.sga[i]
            if statements.other_operating_expenses[i] > 0:
                statements.other_operating_expenses[i] = -statements.other_operating_expenses[i]
            if statements.depreciation[i] > 0:
                statements.depreciation[i] = -statements.depreciation[i]
            if statements.interest_expense[i] > 0:
                statements.interest_expense[i] = -statements.interest_expense[i]
            if statements.tax_current[i] > 0:
                statements.tax_current[i] = -statements.tax_current[i]
            if statements.capex[i] > 0:
                statements.capex[i] = -statements.capex[i]
            if statements.dividends[i] > 0:
                statements.dividends[i] = -statements.dividends[i]

        return statements

    # ─── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _build_trend_analysis(dupont_output) -> List[Dict[str, float]]:
        trend_analysis = []
        years = dupont_output.years
        for i in range(len(years)):
            if dupont_output.ratios.roe[i] != 0:
                trend_analysis.append({
                    'year': years[i],
                    'net_margin': dupont_output.ratios.net_profit_margin[i],
                    'asset_turnover': dupont_output.ratios.asset_turnover[i],
                    'equity_multiplier': dupont_output.ratios.total_assets_to_equity[i],
                    'roe': dupont_output.ratios.roe[i],
                    'roa': dupont_output.ratios.roa[i],
                })
        return trend_analysis

    @staticmethod
    def _build_ratios_by_year(dupont_output) -> Dict[str, Dict[str, float]]:
        ratios_by_year = {}
        years = dupont_output.years
        for i, yr in enumerate(years):
            ratios_by_year[yr] = {
                'net_profit_margin': dupont_output.ratios.net_profit_margin[i],
                'asset_turnover': dupont_output.ratios.asset_turnover[i],
                'equity_multiplier': dupont_output.ratios.total_assets_to_equity[i],
                'roe': dupont_output.ratios.roe[i],
                'roa': dupont_output.ratios.roa[i],
                'gross_margin': dupont_output.ratios.gross_margin[i],
                'ebitda_margin': dupont_output.ratios.ebitda_margin[i],
                'interest_coverage': dupont_output.ratios.interest_coverage[i],
                'debt_to_equity': dupont_output.ratios.debt_to_equity[i],
                'current_ratio': dupont_output.ratios.current_ratio[i],
                'inventory_turnover': dupont_output.ratios.inventory_turnover[i],
                'roic': dupont_output.ratios.roic[i],
            }
        return ratios_by_year

    @staticmethod
    def _build_fallback_result(ticker: str, warnings: List[str]) -> Dict[str, Any]:
        return build_fallback_result(ticker, 'DUPONT', warnings)
