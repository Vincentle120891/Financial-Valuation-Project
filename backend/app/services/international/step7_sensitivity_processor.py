"""Step 7: Sensitivity Analysis Processor"""
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

class Step7SensitivityProcessor:
    """
    Performs sensitivity analysis by recalculating the full DCF model
    for each combination of WACC and Terminal Growth Rate.
    """
    
    def process_sensitivity_analysis(
        self, 
        assumptions: Dict[str, float],
        historical_data: Optional[Dict[str, Any]] = None,
        wacc_range_override: Optional[List[float]] = None,
        terminal_growth_range_override: Optional[List[float]] = None
    ) -> Step7Response:
        """
        Generate sensitivity matrices by recalculating DCF for each scenario.
        
        Args:
            assumptions: Complete DCF assumptions from Step 5 including:
                - wacc: Base WACC
                - terminal_growth: Base terminal growth rate
                - revenue_growth: Revenue growth rate
                - latest_revenue: Latest revenue (optional)
                - latest_ebitda: Latest EBITDA (optional)
                - tax_rate: Tax rate (default 0.21)
                - capex_pct: CapEx as % of revenue (default 0.03)
            historical_data: Optional historical financial data
            wacc_range_override: Optional custom WACC range
            terminal_growth_range_override: Optional custom terminal growth range
        """
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
            key_insights=insights
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
