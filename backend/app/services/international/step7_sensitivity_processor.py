"""Step 7: Sensitivity Analysis Processor

Supports sensitivity analysis for all three valuation models:
- DCF: WACC vs Terminal Growth Rate
- COMPS: P/E Multiple vs EV/EBITDA Multiple  
- DUPONT: Net Margin vs Asset Turnover
"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class SensitivityMatrix(BaseModel):
    variable_x: str
    variable_y: str
    x_values: List[float]
    y_values: List[float]
    results: List[List[float]]

class Step7Response(BaseModel):
    base_case_value: float
    sensitivity_matrices: List[SensitivityMatrix]
    tornado_data: List[Dict]
    key_insights: List[str]
    model_type: str = "DCF"  # DCF, COMPS, or DUPONT

class Step7SensitivityProcessor:
    """
    Performs sensitivity analysis by recalculating the full valuation model
    for each combination of key variables based on the selected model type.
    
    Model-specific variables:
    - DCF: WACC vs Terminal Growth Rate
    - COMPS: P/E Multiple vs EV/EBITDA Multiple
    - DUPONT: Net Margin vs Asset Turnover
    """
    
    def process_sensitivity_analysis(
        self, 
        assumptions: Dict[str, float],
        historical_data: Optional[Dict[str, Any]] = None,
        model_type: str = "DCF",
        wacc_range_override: Optional[List[float]] = None,
        terminal_growth_range_override: Optional[List[float]] = None,
        pe_range_override: Optional[List[float]] = None,
        ev_ebitda_range_override: Optional[List[float]] = None,
        margin_range_override: Optional[List[float]] = None,
        turnover_range_override: Optional[List[float]] = None
    ) -> Step7Response:
        """
        Generate sensitivity matrices by recalculating valuation for each scenario.
        
        Args:
            assumptions: Complete assumptions from Step 5 including model-specific parameters:
                For DCF:
                    - wacc: Base WACC
                    - terminal_growth: Base terminal growth rate
                    - revenue_growth: Revenue growth rate
                    - latest_revenue: Latest revenue
                    - latest_ebitda: Latest EBITDA
                    - tax_rate: Tax rate (default 0.21)
                    - capex_pct: CapEx as % of revenue (default 0.03)
                For COMPS:
                    - base_pe: Base P/E multiple
                    - base_ev_ebitda: Base EV/EBITDA multiple
                    - target_earnings: Target company earnings
                    - target_ebitda: Target company EBITDA
                For DUPONT:
                    - net_margin: Base net profit margin
                    - asset_turnover: Base asset turnover
                    - equity_multiplier: Base equity multiplier
                    - total_assets: Total assets
            historical_data: Optional historical financial data
            model_type: One of "DCF", "COMPS", or "DUPONT"
            wacc_range_override: Optional custom WACC range (DCF only)
            terminal_growth_range_override: Optional custom terminal growth range (DCF only)
            pe_range_override: Optional custom P/E range (COMPS only)
            ev_ebitda_range_override: Optional custom EV/EBITDA range (COMPS only)
            margin_range_override: Optional custom margin range (DUPONT only)
            turnover_range_override: Optional custom turnover range (DUPONT only)
        """
        # Route to appropriate model-specific analysis
        if model_type.upper() == "COMPS":
            return self._process_comps_sensitivity(
                assumptions=assumptions,
                pe_range_override=pe_range_override,
                ev_ebitda_range_override=ev_ebitda_range_override
            )
        elif model_type.upper() == "DUPONT":
            return self._process_dupont_sensitivity(
                assumptions=assumptions,
                margin_range_override=margin_range_override,
                turnover_range_override=turnover_range_override
            )
        else:  # Default to DCF
            return self._process_dcf_sensitivity(
                assumptions=assumptions,
                historical_data=historical_data,
                wacc_range_override=wacc_range_override,
                terminal_growth_range_override=terminal_growth_range_override
            )
    
    def _process_dcf_sensitivity(
        self,
        assumptions: Dict[str, float],
        historical_data: Optional[Dict[str, Any]] = None,
        wacc_range_override: Optional[List[float]] = None,
        terminal_growth_range_override: Optional[List[float]] = None
    ) -> Step7Response:
        """Process DCF sensitivity analysis (WACC vs Terminal Growth)."""
        # Extract base assumptions
        base_wacc = assumptions.get("wacc", 0.10)
        base_terminal_growth = assumptions.get("terminal_growth", 0.025)
        base_revenue_growth = assumptions.get("revenue_growth", 0.05)
        latest_revenue = assumptions.get("latest_revenue", 10000)  # Default $10B
        latest_ebitda = assumptions.get("latest_ebitda", 2000)     # Default $2B
        tax_rate = assumptions.get("tax_rate", 0.21)
        capex_pct = assumptions.get("capex_pct", 0.03)
        net_debt = assumptions.get("net_debt", 0)
        shares_outstanding = assumptions.get("shares_outstanding", 100)
        
        # Calculate base case fair value
        base_fair_value = self._calculate_fair_value(
            wacc=base_wacc,
            terminal_growth=base_terminal_growth,
            revenue_growth=base_revenue_growth,
            latest_revenue=latest_revenue,
            latest_ebitda=latest_ebitda,
            tax_rate=tax_rate,
            capex_pct=capex_pct,
            net_debt=net_debt,
            shares_outstanding=shares_outstanding
        )
        
        # Generate WACC and Terminal Growth ranges
        if wacc_range_override:
            wacc_range = wacc_range_override
        else:
            wacc_range = [
                round(base_wacc - 0.02, 4),
                round(base_wacc - 0.01, 4),
                round(base_wacc, 4),
                round(base_wacc + 0.01, 4),
                round(base_wacc + 0.02, 4)
            ]
        
        if terminal_growth_range_override:
            term_range = terminal_growth_range_override
        else:
            term_range = [
                round(base_terminal_growth - 0.01, 4),
                round(base_terminal_growth, 4),
                round(base_terminal_growth + 0.01, 4)
            ]
        
        # Calculate sensitivity matrix by recalculating DCF for each combination
        matrix = []
        for wacc in wacc_range:
            row = []
            for term_growth in term_range:
                fair_value = self._calculate_fair_value(
                    wacc=wacc,
                    terminal_growth=term_growth,
                    revenue_growth=base_revenue_growth,
                    latest_revenue=latest_revenue,
                    latest_ebitda=latest_ebitda,
                    tax_rate=tax_rate,
                    capex_pct=capex_pct,
                    net_debt=net_debt,
                    shares_outstanding=shares_outstanding
                )
                row.append(round(fair_value, 2))
            matrix.append(row)
        
        # Generate Tornado data with actual impacts
        tornado = self._generate_tornado_data(
            base_fair_value=base_fair_value,
            base_wacc=base_wacc,
            base_terminal_growth=base_terminal_growth,
            base_revenue_growth=base_revenue_growth,
            latest_revenue=latest_revenue,
            latest_ebitda=latest_ebitda,
            tax_rate=tax_rate,
            capex_pct=capex_pct,
            net_debt=net_debt,
            shares_outstanding=shares_outstanding
        )
        
        # Generate key insights based on actual sensitivity analysis
        insights = self._generate_insights(
            base_fair_value=base_fair_value,
            wacc_range=wacc_range,
            term_range=term_range,
            matrix=matrix
        )
        
        return Step7Response(
            base_case_value=round(base_fair_value, 2),
            sensitivity_matrices=[
                SensitivityMatrix(
                    variable_x="WACC",
                    variable_y="Terminal Growth Rate",
                    x_values=wacc_range,
                    y_values=term_range,
                    results=matrix
                )
            ],
            tornado_data=tornado,
            key_insights=insights,
            model_type="DCF"
        )
    
    def _process_comps_sensitivity(
        self,
        assumptions: Dict[str, float],
        pe_range_override: Optional[List[float]] = None,
        ev_ebitda_range_override: Optional[List[float]] = None
    ) -> Step7Response:
        """Process COMPS sensitivity analysis (P/E vs EV/EBITDA)."""
        # Extract base assumptions
        base_pe = assumptions.get("base_pe", 15.0)
        base_ev_ebitda = assumptions.get("base_ev_ebitda", 10.0)
        target_earnings = assumptions.get("target_earnings", 1000)  # $1B
        target_ebitda = assumptions.get("target_ebitda", 2000)      # $2B
        
        # Calculate base case implied valuation
        base_implied_value = target_earnings * base_pe
        
        # Generate P/E range
        if pe_range_override:
            pe_range = pe_range_override
        else:
            pe_range = [
                round(base_pe - 4, 2),
                round(base_pe - 2, 2),
                round(base_pe, 2),
                round(base_pe + 2, 2),
                round(base_pe + 4, 2)
            ]
        
        # Generate EV/EBITDA range
        if ev_ebitda_range_override:
            ev_ebitda_range = ev_ebitda_range_override
        else:
            ev_ebitda_range = [
                round(base_ev_ebitda - 3, 2),
                round(base_ev_ebitda - 1.5, 2),
                round(base_ev_ebitda, 2),
                round(base_ev_ebitda + 1.5, 2),
                round(base_ev_ebitda + 3, 2)
            ]
        
        # Calculate sensitivity matrix
        matrix = []
        for pe in pe_range:
            row = []
            for ev_eb in ev_ebitda_range:
                # Implied valuation using P/E multiple
                implied_by_pe = target_earnings * pe
                # Implied valuation using EV/EBITDA (simplified, assuming net debt = 0)
                implied_by_ev_ebitda = target_ebitda * ev_eb
                # Average of both methods
                avg_value = (implied_by_pe + implied_by_ev_ebitda) / 2
                row.append(round(avg_value, 2))
            matrix.append(row)
        
        # Generate Tornado data
        tornado = [
            {"variable": "P/E Multiple", "low_value": round(target_earnings * pe_range[0], 2), "high_value": round(target_earnings * pe_range[-1], 2)},
            {"variable": "EV/EBITDA Multiple", "low_value": round(target_ebitda * ev_ebitda_range[0], 2), "high_value": round(target_ebitda * ev_ebitda_range[-1], 2)}
        ]
        
        # Generate insights
        insights = [
            f"Base case implied valuation: ${base_implied_value:,.2f}M using P/E of {base_pe:.1f}x",
            f"P/E sensitivity: Valuation ranges from ${target_earnings * pe_range[0]:,.2f}M to ${target_earnings * pe_range[-1]:,.2f}M",
            f"EV/EBITDA sensitivity: Valuation ranges from ${target_ebitda * ev_ebitda_range[0]:,.2f}M to ${target_ebitda * ev_ebitda_range[-1]:,.2f}M",
            "COMPS valuation is highly sensitive to peer group selection and market conditions"
        ]
        
        return Step7Response(
            base_case_value=round(base_implied_value, 2),
            sensitivity_matrices=[
                SensitivityMatrix(
                    variable_x="P/E Multiple",
                    variable_y="EV/EBITDA Multiple",
                    x_values=pe_range,
                    y_values=ev_ebitda_range,
                    results=matrix
                )
            ],
            tornado_data=tornado,
            key_insights=insights,
            model_type="COMPS"
        )
    
    def _process_dupont_sensitivity(
        self,
        assumptions: Dict[str, float],
        margin_range_override: Optional[List[float]] = None,
        turnover_range_override: Optional[List[float]] = None
    ) -> Step7Response:
        """Process DUPONT sensitivity analysis (Net Margin vs Asset Turnover)."""
        # Extract base assumptions
        base_margin = assumptions.get("net_margin", 0.15)  # 15%
        base_turnover = assumptions.get("asset_turnover", 1.2)
        base_multiplier = assumptions.get("equity_multiplier", 2.0)
        total_assets = assumptions.get("total_assets", 10000)  # $10B
        
        # Calculate base case ROE
        base_roe = base_margin * base_turnover * base_multiplier
        
        # Generate Net Margin range
        if margin_range_override:
            margin_range = margin_range_override
        else:
            margin_range = [
                round(base_margin - 0.06, 4),
                round(base_margin - 0.03, 4),
                round(base_margin, 4),
                round(base_margin + 0.03, 4),
                round(base_margin + 0.06, 4)
            ]
        
        # Generate Asset Turnover range
        if turnover_range_override:
            turnover_range = turnover_range_override
        else:
            turnover_range = [
                round(base_turnover - 0.4, 2),
                round(base_turnover - 0.2, 2),
                round(base_turnover, 2),
                round(base_turnover + 0.2, 2),
                round(base_turnover + 0.4, 2)
            ]
        
        # Calculate sensitivity matrix (ROE for each combination)
        matrix = []
        for margin in margin_range:
            row = []
            for turnover in turnover_range:
                roe = margin * turnover * base_multiplier
                row.append(round(roe, 4))
            matrix.append(row)
        
        # Generate Tornado data
        tornado = [
            {"variable": "Net Profit Margin", "low_value": round(margin_range[0] * base_turnover * base_multiplier, 4), "high_value": round(margin_range[-1] * base_turnover * base_multiplier, 4)},
            {"variable": "Asset Turnover", "low_value": round(base_margin * turnover_range[0] * base_multiplier, 4), "high_value": round(base_margin * turnover_range[-1] * base_multiplier, 4)},
            {"variable": "Equity Multiplier", "low_value": round(base_margin * base_turnover * (base_multiplier - 0.5), 4), "high_value": round(base_margin * base_turnover * (base_multiplier + 0.5), 4)}
        ]
        
        # Generate insights
        insights = [
            f"Base case ROE: {base_roe:.2%} driven by {base_margin:.2%} margin, {base_turnover:.2f} turnover, {base_multiplier:.2f} multiplier",
            f"Margin sensitivity: ROE ranges from {margin_range[0] * base_turnover * base_multiplier:.2%} to {margin_range[-1] * base_turnover * base_multiplier:.2%}",
            f"Turnover sensitivity: ROE ranges from {base_margin * turnover_range[0] * base_multiplier:.2%} to {base_margin * turnover_range[-1] * base_multiplier:.2%}",
            "DuPont analysis reveals the primary drivers of ROE changes"
        ]
        
        return Step7Response(
            base_case_value=round(base_roe, 4),
            sensitivity_matrices=[
                SensitivityMatrix(
                    variable_x="Net Profit Margin",
                    variable_y="Asset Turnover",
                    x_values=margin_range,
                    y_values=turnover_range,
                    results=matrix
                )
            ],
            tornado_data=tornado,
            key_insights=insights,
            model_type="DUPONT"
        )
    
    def _calculate_fair_value(
        self,
        wacc: float,
        terminal_growth: float,
        revenue_growth: float,
        latest_revenue: float,
        latest_ebitda: float,
        tax_rate: float,
        capex_pct: float,
        net_debt: float,
        shares_outstanding: float,
        projection_years: int = 5
    ) -> float:
        """
        Recalculate the full DCF model for given assumptions.
        
        Returns:
            Fair value per share
        """
        # Validate inputs
        if wacc <= terminal_growth:
            # If WACC <= terminal growth, use a conservative fallback
            terminal_growth = wacc - 0.01
        
        # Calculate base FCF
        base_fcf = latest_ebitda * (1 - tax_rate) - (latest_revenue * capex_pct)
        
        # Project FCF for projection years
        fcf_projections = []
        for year in range(1, projection_years + 1):
            fcf = base_fcf * ((1 + revenue_growth) ** year)
            fcf_projections.append(fcf)
        
        # Calculate Present Value of FCF Projections
        pv_fcf = 0
        for i, fcf in enumerate(fcf_projections, 1):
            pv_fcf += fcf / ((1 + wacc) ** i)
        
        # Calculate Terminal Value (Perpetuity Growth Method)
        final_fcf = fcf_projections[-1] if fcf_projections else 0
        terminal_value = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
        
        # Calculate Present Value of Terminal Value
        pv_terminal = terminal_value / ((1 + wacc) ** projection_years)
        
        # Calculate Enterprise Value
        enterprise_value = pv_fcf + pv_terminal
        
        # Calculate Equity Value
        equity_value = enterprise_value - net_debt
        
        # Calculate Fair Value per Share
        if shares_outstanding > 0:
            fair_value_per_share = equity_value / shares_outstanding
        else:
            fair_value_per_share = 0
        
        return fair_value_per_share
    
    def _generate_tornado_data(
        self,
        base_fair_value: float,
        base_wacc: float,
        base_terminal_growth: float,
        base_revenue_growth: float,
        latest_revenue: float,
        latest_ebitda: float,
        tax_rate: float,
        capex_pct: float,
        net_debt: float,
        shares_outstanding: float
    ) -> List[Dict]:
        """Generate tornado chart data by calculating actual impacts."""
        tornado = []
        
        # WACC ±1% impact
        wacc_high = base_wacc + 0.01
        wacc_low = base_wacc - 0.01
        fv_wacc_high = self._calculate_fair_value(
            wacc=wacc_high, terminal_growth=base_terminal_growth,
            revenue_growth=base_revenue_growth, latest_revenue=latest_revenue,
            latest_ebitda=latest_ebitda, tax_rate=tax_rate, capex_pct=capex_pct,
            net_debt=net_debt, shares_outstanding=shares_outstanding
        )
        fv_wacc_low = self._calculate_fair_value(
            wacc=wacc_low, terminal_growth=base_terminal_growth,
            revenue_growth=base_revenue_growth, latest_revenue=latest_revenue,
            latest_ebitda=latest_ebitda, tax_rate=tax_rate, capex_pct=capex_pct,
            net_debt=net_debt, shares_outstanding=shares_outstanding
        )
        tornado.append({
            "variable": "WACC ±1%",
            "impact_high": round(fv_wacc_low, 2),  # Lower WACC = Higher valuation
            "impact_low": round(fv_wacc_high, 2)   # Higher WACC = Lower valuation
        })
        
        # Terminal Growth ±1% impact
        term_high = base_terminal_growth + 0.01
        term_low = base_terminal_growth - 0.01
        fv_term_high = self._calculate_fair_value(
            wacc=base_wacc, terminal_growth=term_high,
            revenue_growth=base_revenue_growth, latest_revenue=latest_revenue,
            latest_ebitda=latest_ebitda, tax_rate=tax_rate, capex_pct=capex_pct,
            net_debt=net_debt, shares_outstanding=shares_outstanding
        )
        fv_term_low = self._calculate_fair_value(
            wacc=base_wacc, terminal_growth=term_low,
            revenue_growth=base_revenue_growth, latest_revenue=latest_revenue,
            latest_ebitda=latest_ebitda, tax_rate=tax_rate, capex_pct=capex_pct,
            net_debt=net_debt, shares_outstanding=shares_outstanding
        )
        tornado.append({
            "variable": "Terminal Growth ±1%",
            "impact_high": round(fv_term_high, 2),
            "impact_low": round(fv_term_low, 2)
        })
        
        # Revenue Growth ±2% impact
        rev_high = base_revenue_growth + 0.02
        rev_low = base_revenue_growth - 0.02
        fv_rev_high = self._calculate_fair_value(
            wacc=base_wacc, terminal_growth=base_terminal_growth,
            revenue_growth=rev_high, latest_revenue=latest_revenue,
            latest_ebitda=latest_ebitda, tax_rate=tax_rate, capex_pct=capex_pct,
            net_debt=net_debt, shares_outstanding=shares_outstanding
        )
        fv_rev_low = self._calculate_fair_value(
            wacc=base_wacc, terminal_growth=base_terminal_growth,
            revenue_growth=rev_low, latest_revenue=latest_revenue,
            latest_ebitda=latest_ebitda, tax_rate=tax_rate, capex_pct=capex_pct,
            net_debt=net_debt, shares_outstanding=shares_outstanding
        )
        tornado.append({
            "variable": "Revenue Growth ±2%",
            "impact_high": round(fv_rev_high, 2),
            "impact_low": round(fv_rev_low, 2)
        })
        
        return tornado
    
    def _generate_insights(
        self,
        base_fair_value: float,
        wacc_range: List[float],
        term_range: List[float],
        matrix: List[List[float]]
    ) -> List[str]:
        """Generate key insights from sensitivity analysis."""
        insights = []
        
        # Find max and min values in matrix
        all_values = [val for row in matrix for val in row]
        max_value = max(all_values)
        min_value = min(all_values)
        value_range = max_value - min_value
        pct_range = (value_range / base_fair_value) * 100 if base_fair_value > 0 else 0
        
        insights.append(f"Valuation range: ${min_value:.2f} - ${max_value:.2f} ({pct_range:.1f}% spread)")
        
        # Determine most sensitive variable
        wacc_impact = abs(matrix[0][1] - matrix[-1][1])  # Impact across WACC range
        term_impact = abs(matrix[1][0] - matrix[1][-1])  # Impact across terminal growth range
        
        if wacc_impact > term_impact:
            insights.append("WACC is the primary value driver - small changes significantly impact valuation")
        else:
            insights.append("Terminal growth rate has substantial impact on long-term valuation")
        
        # Add caution about extreme scenarios
        if pct_range > 50:
            insights.append("High sensitivity suggests significant uncertainty - consider additional scenario analysis")
        
        return insights
