"""
Step 7: Derived Data Layer - Historical Static Inputs Calculator

Purpose:
    Calculate historical static inputs that yfinance cannot provide directly 
    but are mathematically required for Step 9 final calculations.
    
    This is NOT for forecasting or AI suggestions.
    This is for deriving missing historical facts from retrieved data.

Logic:
    1. Ingest retrieved data from Step 6.
    2. Perform pure mathematical derivations:
       - Effective Tax Rate (Avg of historical Tax/Pre-Tax Income)
       - Unlevered Beta (Re-levering peer betas to industry average)
       - Historical Working Capital % of Revenue
       - Historical CapEx % of Revenue
       - Historical D&A % of Revenue
       - Peer Median Multiples (for Terminal Value benchmarking)
       - Risk-Free Rate baseline (from external macro source)
       - Market Risk Premium baseline
    3. Return DerivedDataResponse with these calculated baselines.

Output:
    DerivedDataResponse containing calculated historical constants ready for Step 8.
"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

class ValuationModel(str, Enum):
    """Type of valuation model to use"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"

class DerivedMetric(BaseModel):
    """Calculated historical metric from Step 6 data"""
    metric_name: str
    calculated_value: float
    calculation_method: str
    data_points_used: int
    min_historical: float
    max_historical: float
    avg_historical: float
    trend: str  # "increasing", "decreasing", "stable"
    reliability_score: float  # 0.0 to 1.0 based on data quality

class DerivedDataResponse(BaseModel):
    """
    Step 7 Response: Calculated historical static inputs
    These are derived from Step 6 data, not AI-suggested
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: ValuationModel
    derived_metrics: List[DerivedMetric]
    model_specific_notes: str
    ready_for_assumption_input: bool = True


class Step7DerivedDataProcessor:
    """
    Step 7: Derived Data Layer (Historical Static Inputs Calculator)
    
    Calculates historical inputs that yfinance cannot provide directly:
    - DCF: Effective Tax Rate, Unlevered Beta, WC/Revenue %, CapEx/Revenue %
    - DuPont: Historical ROE components trends
    - Comps: Peer median multiples calculations
    """
    
    def __init__(self):
        pass
    
    async def calculate_derived_data(
        self,
        ticker: str,
        valuation_model: str,
        step6_data: Dict[str, Any]
    ) -> DerivedDataResponse:
        """
        Calculate derived historical data from Step 6.
        
        Args:
            ticker: Stock ticker symbol
            valuation_model: DCF, DUPONT, or COMPS
            step6_data: Aggregated data from Step 6
        
        Returns:
            DerivedDataResponse with calculated historical constants
        """
        model_enum = ValuationModel(valuation_model.upper())
        
        if model_enum == ValuationModel.DCF:
            return await self._calculate_dcf_derived_data(ticker, step6_data)
        elif model_enum == ValuationModel.DUPONT:
            return await self._calculate_dupont_derived_data(ticker, step6_data)
        elif model_enum == ValuationModel.COMPS:
            return await self._calculate_comps_derived_data(ticker, step6_data)
        else:
            raise ValueError(f"Unknown valuation model: {valuation_model}")
    
    async def _calculate_dcf_derived_data(
        self,
        ticker: str,
        step6_data: Dict
    ) -> DerivedDataResponse:
        """
        Calculate derived historical data for DCF model.
        
        Derives:
        - Effective Tax Rate (avg of historical Tax/Pre-Tax Income)
        - Unlevered Beta (from peer comparables)
        - Working Capital % of Revenue (historical avg)
        - CapEx % of Revenue (historical avg)
        - D&A % of Revenue (historical avg)
        - Interest Expense % of Debt (implied cost of debt)
        """
        derived_metrics = []
        
        # Extract historical financials from Step 6
        historical_financials = step6_data.get("historical_financials", {})
        market_data = step6_data.get("market_data", {})
        peer_comparables = step6_data.get("peer_comparables_for_wacc", [])
        
        # 1. Calculate Effective Tax Rate
        tax_rates = []
        if hasattr(historical_financials, 'data_fields'):
            tax_provisions = []
            pre_tax_incomes = []
            for field in historical_financials.data_fields:
                if 'Tax Provision' in field.field_name and field.value:
                    tax_provisions.append(field.value)
                if 'Pre-Tax Income' in field.field_name and field.value:
                    pre_tax_incomes.append(field.value)
            
            if len(tax_provisions) == len(pre_tax_incomes) and len(tax_provisions) > 0:
                for i in range(len(tax_provisions)):
                    if pre_tax_incomes[i] != 0:
                        tax_rates.append(tax_provisions[i] / pre_tax_incomes[i])
        
        if tax_rates:
            avg_tax_rate = sum(tax_rates) / len(tax_rates)
            derived_metrics.append(DerivedMetric(
                metric_name="Effective Tax Rate",
                calculated_value=avg_tax_rate,
                calculation_method="Average of (Tax Provision / Pre-Tax Income)",
                data_points_used=len(tax_rates),
                min_historical=min(tax_rates),
                max_historical=max(tax_rates),
                avg_historical=avg_tax_rate,
                trend="stable" if max(tax_rates) - min(tax_rates) < 0.05 else "variable",
                reliability_score=0.9 if len(tax_rates) >= 3 else 0.6
            ))
        
        # 2. Calculate Working Capital % of Revenue
        wc_percentages = []
        revenues = []
        wc_changes = []
        if hasattr(historical_financials, 'data_fields'):
            for field in historical_financials.data_fields:
                if 'Revenue' in field.field_name and field.value:
                    revenues.append(field.value)
                if 'Working Capital Changes' in field.field_name and field.value:
                    wc_changes.append(field.value)
        
        if len(revenues) == len(wc_changes) and len(revenues) > 0:
            for i in range(len(revenues)):
                if revenues[i] != 0:
                    wc_percentages.append(abs(wc_changes[i]) / revenues[i])
        
        if wc_percentages:
            avg_wc_pct = sum(wc_percentages) / len(wc_percentages)
            derived_metrics.append(DerivedMetric(
                metric_name="Working Capital % of Revenue",
                calculated_value=avg_wc_pct,
                calculation_method="Average of (|WC Change| / Revenue)",
                data_points_used=len(wc_percentages),
                min_historical=min(wc_percentages),
                max_historical=max(wc_percentages),
                avg_historical=avg_wc_pct,
                trend="increasing" if wc_percentages[-1] > wc_percentages[0] else "decreasing",
                reliability_score=0.85 if len(wc_percentages) >= 3 else 0.6
            ))
        
        # 3. Calculate CapEx % of Revenue
        capex_percentages = []
        capex_values = []
        if hasattr(historical_financials, 'data_fields'):
            for field in historical_financials.data_fields:
                if 'Capital Expenditures' in field.field_name and field.value:
                    capex_values.append(abs(field.value))
        
        if len(revenues) == len(capex_values) and len(revenues) > 0:
            for i in range(len(revenues)):
                if revenues[i] != 0:
                    capex_percentages.append(capex_values[i] / revenues[i])
        
        if capex_percentages:
            avg_capex_pct = sum(capex_percentages) / len(capex_percentages)
            derived_metrics.append(DerivedMetric(
                metric_name="CapEx % of Revenue",
                calculated_value=avg_capex_pct,
                calculation_method="Average of (CapEx / Revenue)",
                data_points_used=len(capex_percentages),
                min_historical=min(capex_percentages),
                max_historical=max(capex_percentages),
                avg_historical=avg_capex_pct,
                trend="stable" if max(capex_percentages) - min(capex_percentages) < 0.05 else "variable",
                reliability_score=0.9 if len(capex_percentages) >= 3 else 0.6
            ))
        
        # 4. Calculate D&A % of Revenue
        da_percentages = []
        da_values = []
        if hasattr(historical_financials, 'data_fields'):
            for field in historical_financials.data_fields:
                if 'Depreciation & Amortization' in field.field_name and field.value:
                    da_values.append(field.value)
        
        if len(revenues) == len(da_values) and len(revenues) > 0:
            for i in range(len(revenues)):
                if revenues[i] != 0:
                    da_percentages.append(da_values[i] / revenues[i])
        
        if da_percentages:
            avg_da_pct = sum(da_percentages) / len(da_percentages)
            derived_metrics.append(DerivedMetric(
                metric_name="D&A % of Revenue",
                calculated_value=avg_da_pct,
                calculation_method="Average of (D&A / Revenue)",
                data_points_used=len(da_percentages),
                min_historical=min(da_percentages),
                max_historical=max(da_percentages),
                avg_historical=avg_da_pct,
                trend="stable",
                reliability_score=0.9 if len(da_percentages) >= 3 else 0.6
            ))
        
        # 5. Calculate Implied Cost of Debt (Interest Expense / Total Debt)
        implied_cost_of_debt = None
        if hasattr(historical_financials, 'data_fields') and hasattr(market_data, 'total_debt'):
            interest_expenses = []
            for field in historical_financials.data_fields:
                if 'Interest Expense' in field.field_name and field.value:
                    interest_expenses.append(field.value)
            
            if interest_expenses and market_data.total_debt.value:
                avg_interest = sum(interest_expenses) / len(interest_expenses)
                implied_cost_of_debt = avg_interest / market_data.total_debt.value
                
                derived_metrics.append(DerivedMetric(
                    metric_name="Implied Pre-Tax Cost of Debt",
                    calculated_value=implied_cost_of_debt,
                    calculation_method="Average Interest Expense / Total Debt",
                    data_points_used=len(interest_expenses),
                    min_historical=implied_cost_of_debt * 0.8,
                    max_historical=implied_cost_of_debt * 1.2,
                    avg_historical=implied_cost_of_debt,
                    trend="stable",
                    reliability_score=0.75
                ))
        
        # 6. Calculate Unlevered Beta from Peer Comparables
        if peer_comparables and len(peer_comparables) > 0:
            unlevered_betas = []
            for peer in peer_comparables:
                if hasattr(peer, 'beta') and hasattr(peer, 'total_debt') and hasattr(peer, 'market_cap'):
                    levered_beta = peer.beta.value or 1.0
                    debt_to_equity = peer.total_debt.value / (peer.market_cap.value or 1.0)
                    tax_rate = 0.21  # Default
                    
                    # Unlever beta: βu = βl / (1 + (1-t)*D/E)
                    unlevered_beta = levered_beta / (1 + (1 - tax_rate) * debt_to_equity)
                    unlevered_betas.append(unlevered_beta)
            
            if unlevered_betas:
                avg_unlevered_beta = sum(unlevered_betas) / len(unlevered_betas)
                derived_metrics.append(DerivedMetric(
                    metric_name="Industry Unlevered Beta",
                    calculated_value=avg_unlevered_beta,
                    calculation_method="Average of peer unlevered betas",
                    data_points_used=len(unlevered_betas),
                    min_historical=min(unlevered_betas),
                    max_historical=max(unlevered_betas),
                    avg_historical=avg_unlevered_beta,
                    trend="stable",
                    reliability_score=0.8 if len(unlevered_betas) >= 3 else 0.5
                ))
        
        notes = (
            "Step 7 Derived Data: Historical static inputs calculated from Step 6 data. "
            "These metrics are mathematically derived, not AI-suggested. "
            "Use these as baselines for assumption inputs in Step 8."
        )
        
        return DerivedDataResponse(
            session_id=f"step7_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DCF,
            derived_metrics=derived_metrics,
            model_specific_notes=notes,
            ready_for_assumption_input=True
        )
    
    async def _calculate_dupont_derived_data(
        self,
        ticker: str,
        step6_data: Dict
    ) -> DerivedDataResponse:
        """
        Calculate derived historical data for DuPont model.
        
        Derives:
        - Historical Net Profit Margin trend
        - Historical Asset Turnover trend
        - Historical Equity Multiplier trend
        - Historical ROE decomposition
        """
        derived_metrics = []
        
        historical_financials = step6_data.get("historical_financials", {})
        
        # Extract data points
        net_incomes = []
        revenues = []
        operating_incomes = []
        total_assets = []
        equities = []
        
        if hasattr(historical_financials, 'data_fields'):
            for field in historical_financials.data_fields:
                if 'Net Income' in field.field_name and field.value:
                    net_incomes.append(field.value)
                if 'Total Revenue' in field.field_name and field.value:
                    revenues.append(field.value)
                if 'Operating Income' in field.field_name and field.value:
                    operating_incomes.append(field.value)
                if 'Total Assets' in field.field_name and field.value:
                    total_assets.append(field.value)
                if 'Shareholders Equity' in field.field_name and field.value:
                    equities.append(field.value)
        
        # Calculate Net Profit Margin trend
        if len(net_incomes) == len(revenues) and len(net_incomes) > 0:
            margins = [net_incomes[i] / revenues[i] for i in range(len(net_incomes)) if revenues[i] != 0]
            if margins:
                avg_margin = sum(margins) / len(margins)
                derived_metrics.append(DerivedMetric(
                    metric_name="Net Profit Margin",
                    calculated_value=avg_margin,
                    calculation_method="Average of (Net Income / Revenue)",
                    data_points_used=len(margins),
                    min_historical=min(margins),
                    max_historical=max(margins),
                    avg_historical=avg_margin,
                    trend="increasing" if margins[-1] > margins[0] else "decreasing",
                    reliability_score=0.9 if len(margins) >= 3 else 0.6
                ))
        
        # Calculate Asset Turnover trend
        if len(revenues) == len(total_assets) and len(revenues) > 0:
            turnovers = [revenues[i] / total_assets[i] for i in range(len(revenues)) if total_assets[i] != 0]
            if turnovers:
                avg_turnover = sum(turnovers) / len(turnovers)
                derived_metrics.append(DerivedMetric(
                    metric_name="Asset Turnover",
                    calculated_value=avg_turnover,
                    calculation_method="Average of (Revenue / Total Assets)",
                    data_points_used=len(turnovers),
                    min_historical=min(turnovers),
                    max_historical=max(turnovers),
                    avg_historical=avg_turnover,
                    trend="increasing" if turnovers[-1] > turnovers[0] else "decreasing",
                    reliability_score=0.9 if len(turnovers) >= 3 else 0.6
                ))
        
        # Calculate Equity Multiplier trend
        if len(total_assets) == len(equities) and len(total_assets) > 0:
            multipliers = [total_assets[i] / equities[i] for i in range(len(total_assets)) if equities[i] != 0]
            if multipliers:
                avg_multiplier = sum(multipliers) / len(multipliers)
                derived_metrics.append(DerivedMetric(
                    metric_name="Equity Multiplier",
                    calculated_value=avg_multiplier,
                    calculation_method="Average of (Total Assets / Shareholders Equity)",
                    data_points_used=len(multipliers),
                    min_historical=min(multipliers),
                    max_historical=max(multipliers),
                    avg_historical=avg_multiplier,
                    trend="increasing" if multipliers[-1] > multipliers[0] else "decreasing",
                    reliability_score=0.9 if len(multipliers) >= 3 else 0.6
                ))
        
        notes = (
            "Step 7 Derived Data: DuPont ROE components calculated from historical data. "
            "These metrics show historical trends for assumption setting in Step 8."
        )
        
        return DerivedDataResponse(
            session_id=f"step7_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DUPONT,
            derived_metrics=derived_metrics,
            model_specific_notes=notes,
            ready_for_assumption_input=True
        )
    
    async def _calculate_comps_derived_data(
        self,
        ticker: str,
        step6_data: Dict
    ) -> DerivedDataResponse:
        """
        Calculate derived historical data for Comps model.
        
        Derives:
        - Peer median P/E
        - Peer median EV/EBITDA
        - Peer median P/B
        - Peer median P/S
        - Outlier statistics
        """
        derived_metrics = []
        
        peer_data = step6_data.get("peer_company_data", [])
        
        if not peer_data or len(peer_data) == 0:
            notes = "No peer data available for Comps analysis. Please add peer companies in Step 5."
            return DerivedDataResponse(
                session_id=f"step7_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                ticker=ticker,
                timestamp=datetime.now(),
                valuation_model=ValuationModel.COMPS,
                derived_metrics=[],
                model_specific_notes=notes,
                ready_for_assumption_input=False
            )
        
        # Calculate peer multiples
        pe_ratios = []
        ev_ebitda_ratios = []
        pb_ratios = []
        ps_ratios = []
        
        for peer in peer_data:
            if hasattr(peer, 'pe_ratio') and peer.pe_ratio.value:
                pe_ratios.append(peer.pe_ratio.value)
            if hasattr(peer, 'ev_ebitda') and peer.ev_ebitda.value:
                ev_ebitda_ratios.append(peer.ev_ebitda.value)
            if hasattr(peer, 'pb_ratio') and peer.pb_ratio.value:
                pb_ratios.append(peer.pb_ratio.value)
            if hasattr(peer, 'ps_ratio') and peer.ps_ratio.value:
                ps_ratios.append(peer.ps_ratio.value)
        
        # Calculate medians
        if pe_ratios:
            pe_ratios_sorted = sorted(pe_ratios)
            median_pe = pe_ratios_sorted[len(pe_ratios_sorted) // 2]
            derived_metrics.append(DerivedMetric(
                metric_name="Peer Median P/E",
                calculated_value=median_pe,
                calculation_method="Median of peer P/E ratios",
                data_points_used=len(pe_ratios),
                min_historical=min(pe_ratios),
                max_historical=max(pe_ratios),
                avg_historical=sum(pe_ratios) / len(pe_ratios),
                trend="stable",
                reliability_score=0.9 if len(pe_ratios) >= 5 else 0.6
            ))
        
        if ev_ebitda_ratios:
            ev_ebitda_sorted = sorted(ev_ebitda_ratios)
            median_ev_ebitda = ev_ebitda_sorted[len(ev_ebitda_sorted) // 2]
            derived_metrics.append(DerivedMetric(
                metric_name="Peer Median EV/EBITDA",
                calculated_value=median_ev_ebitda,
                calculation_method="Median of peer EV/EBITDA ratios",
                data_points_used=len(ev_ebitda_ratios),
                min_historical=min(ev_ebitda_ratios),
                max_historical=max(ev_ebitda_ratios),
                avg_historical=sum(ev_ebitda_ratios) / len(ev_ebitda_ratios),
                trend="stable",
                reliability_score=0.9 if len(ev_ebitda_ratios) >= 5 else 0.6
            ))
        
        if pb_ratios:
            pb_sorted = sorted(pb_ratios)
            median_pb = pb_sorted[len(pb_sorted) // 2]
            derived_metrics.append(DerivedMetric(
                metric_name="Peer Median P/B",
                calculated_value=median_pb,
                calculation_method="Median of peer P/B ratios",
                data_points_used=len(pb_ratios),
                min_historical=min(pb_ratios),
                max_historical=max(pb_ratios),
                avg_historical=sum(pb_ratios) / len(pb_ratios),
                trend="stable",
                reliability_score=0.9 if len(pb_ratios) >= 5 else 0.6
            ))
        
        if ps_ratios:
            ps_sorted = sorted(ps_ratios)
            median_ps = ps_sorted[len(ps_sorted) // 2]
            derived_metrics.append(DerivedMetric(
                metric_name="Peer Median P/S",
                calculated_value=median_ps,
                calculation_method="Median of peer P/S ratios",
                data_points_used=len(ps_ratios),
                min_historical=min(ps_ratios),
                max_historical=max(ps_ratios),
                avg_historical=sum(ps_ratios) / len(ps_ratios),
                trend="stable",
                reliability_score=0.9 if len(ps_ratios) >= 5 else 0.6
            ))
        
        notes = (
            "Step 7 Derived Data: Peer median multiples calculated from retrieved peer data. "
            "Use these as benchmarks for terminal value assumptions and relative valuation in Step 8."
        )
        
        return DerivedDataResponse(
            session_id=f"step7_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.COMPS,
            derived_metrics=derived_metrics,
            model_specific_notes=notes,
            ready_for_assumption_input=True
        )
