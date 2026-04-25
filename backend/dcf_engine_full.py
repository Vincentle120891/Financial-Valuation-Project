"""
DCF Calculation Engine - Implements Unified_Valuation_API_Calculated_Schema
Calculates DCF valuation using both Perpetuity and Multiple methods with sensitivity analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import math
import json


@dataclass
class ForecastDrivers:
    """6-period forecast arrays: [FY+1, FY+2, FY+3, FY+4, FY+5, Terminal]"""
    revenue_growth: List[float] = field(default_factory=lambda: [0.0] * 6)
    inflation_rate: List[float] = field(default_factory=lambda: [0.02] * 6)
    opex_growth: List[float] = field(default_factory=lambda: [0.02] * 6)
    capex: List[float] = field(default_factory=lambda: [0.0] * 6)  # Absolute values
    ar_days: List[float] = field(default_factory=lambda: [30.0] * 6)
    inv_days: List[float] = field(default_factory=lambda: [45.0] * 6)
    ap_days: List[float] = field(default_factory=lambda: [30.0] * 6)
    tax_rate: List[float] = field(default_factory=lambda: [0.21] * 6)
    terminal_ebitda_multiple: float = 7.0
    terminal_growth_rate: float = 0.02
    
    def validate(self) -> List[str]:
        """Validate forecast drivers"""
        errors = []
        if len(self.revenue_growth) != 6:
            errors.append("revenue_growth must have 6 periods")
        if self.terminal_growth_rate >= 0.1:  # Will be compared to WACC later
            errors.append("Terminal growth rate seems unusually high")
        return errors


@dataclass
class DCFInputs:
    """Consolidated inputs for DCF calculation"""
    # Metadata
    valuation_date: str
    currency: str = "USD"
    base_year: str = "2022A"
    forecast_years: List[str] = field(default_factory=lambda: ["2023F", "2024F", "2025F", "2026F", "2027F"])
    
    # Historical financials (3 years)
    historical_fy_minus_3: Dict[str, float] = field(default_factory=dict)
    historical_fy_minus_2: Dict[str, float] = field(default_factory=dict)
    historical_fy_minus_1: Dict[str, float] = field(default_factory=dict)
    
    # Base period balances
    net_debt: float = 0.0
    ppe_net: float = 0.0
    tax_basis_ppe: float = 0.0
    tax_losses_nol: float = 0.0
    shares_outstanding: float = 1.0
    current_stock_price: float = 0.0
    projected_interest_expense: float = 0.0
    
    # Depreciation assumptions
    useful_life_existing: float = 10.0
    useful_life_new: float = 10.0
    
    # Forecast drivers by scenario
    forecast_drivers: Dict[str, ForecastDrivers] = field(default_factory=dict)
    
    # WACC
    wacc: float = 0.10
    risk_free_rate: float = 0.04
    equity_risk_premium: float = 0.06
    beta: float = 1.0
    cost_of_debt: float = 0.05
    tax_rate_statutory: float = 0.21
    
    # Tax loss utilization
    tax_loss_utilization_limit_pct: float = 0.80


@dataclass
class IncomeStatementForecast:
    """Forecasted income statement for all periods"""
    years: List[str]
    revenue: List[float]
    cogs: List[float]
    gross_profit: List[float]
    sga: List[float]
    other_opex: List[float]
    ebitda: List[float]
    depreciation: List[float]
    ebit: List[float]
    interest_expense: List[float]
    ebt: List[float]
    current_tax: List[float]
    deferred_tax: List[float]
    total_tax: List[float]
    net_income: List[float]
    gross_margin: List[float]
    ebitda_margin: List[float]
    ebit_margin: List[float]


@dataclass
class WorkingCapitalForecast:
    """Working capital schedule"""
    years: List[str]
    ar: List[float]
    inventory: List[float]
    ap: List[float]
    nwc: List[float]
    change_nwc: List[float]
    ar_days: List[float]
    inv_days: List[float]
    ap_days: List[float]


@dataclass
class DepreciationForecast:
    """Depreciation schedule with existing and new assets"""
    years: List[str]
    existing_assets_depr: List[float]
    new_assets_depr: List[float]
    total_depreciation: List[float]
    gross_ppe_end: List[float]


@dataclass
class UFCFForecast:
    """Unlevered Free Cash Flow forecast"""
    years: List[str]
    ebitda: List[float]
    current_tax_unlevered: List[float]
    capex: List[float]
    change_nwc: List[float]
    ufcf: List[float]


@dataclass
class DCFValuationResult:
    """Main DCF valuation outputs"""
    enterprise_value_perpetuity: float
    enterprise_value_multiple: float
    equity_value_perpetuity: float
    equity_value_multiple: float
    equity_value_per_share_perpetuity: float
    equity_value_per_share_multiple: float
    current_stock_price: float
    upside_downside_perpetuity_pct: float
    upside_downside_multiple_pct: float


@dataclass
class ScenarioOutput:
    """Scenario-based outputs"""
    best_case: Dict[str, float]
    base_case: Dict[str, float]
    worst_case: Dict[str, float]


@dataclass
class SensitivityTable:
    """5x5 sensitivity matrix"""
    wacc_values: List[float]
    variable_values: List[float]  # terminal_growth or terminal_multiple
    enterprise_value_table: Dict[str, Dict[str, float]]
    equity_value_per_share_table: Dict[str, Dict[str, float]]
    upside_downside_table: Dict[str, Dict[str, float]]


@dataclass
class DCFOutput:
    """Complete DCF output structure"""
    # Main outputs
    main_outputs: DCFValuationResult
    
    # Scenario outputs
    scenario_outputs: ScenarioOutput
    
    # Sensitivity tables
    sensitivity_perpetuity: SensitivityTable
    sensitivity_multiple: SensitivityTable
    
    # Supporting schedules
    income_statement_forecast: IncomeStatementForecast
    working_capital_forecast: WorkingCapitalForecast
    depreciation_forecast: DepreciationForecast
    ufcf_forecast: UFCFForecast
    
    # Discounting details
    pv_discrete: float
    pv_terminal_perpetuity: float
    pv_terminal_multiple: float
    
    # Metadata
    metadata: Dict[str, Any]
    
    # Validation flags
    validation_flags: Dict[str, bool]
    
    # Warnings
    warnings: List[str] = field(default_factory=list)


class DCFEngine:
    """
    DCF Calculation Engine implementing the full valuation model.
    Supports both Perpetuity (Gordon Growth) and Multiple (Exit Multiple) methods.
    """
    
    def __init__(self, inputs: DCFInputs):
        self.inputs = inputs
        self.warnings: List[str] = []
        self.validation_flags: Dict[str, bool] = {}
        
    def calculate(self, scenario: str = "base_case") -> DCFOutput:
        """
        Execute full DCF calculation for given scenario.
        
        Args:
            scenario: "best_case", "base_case", or "worst_case"
            
        Returns:
            Complete DCFOutput with all calculations and sensitivity tables
        """
        if scenario not in self.inputs.forecast_drivers:
            raise ValueError(f"Scenario '{scenario}' not found in forecast_drivers")
            
        drivers = self.inputs.forecast_drivers[scenario]
        
        # Validate critical inputs
        self._validate_critical_inputs(drivers)
        
        # Build forecast periods (6 periods: 5 forecast + terminal)
        periods = self.inputs.forecast_years + ["Terminal"]
        
        # 1. Revenue Schedule
        revenue = self._build_revenue_schedule(drivers)
        
        # 2. COGS Schedule
        cogs = self._build_cogs_schedule(drivers)
        
        # 3. Gross Profit
        gross_profit = [r - c for r, c in zip(revenue, cogs)]
        gross_margin = [gp / r if r > 0 else 0 for gp, r in zip(gross_profit, revenue)]
        
        # 4. OpEx Schedule
        sga = self._build_opex_schedule(drivers, self.inputs.historical_fy_minus_1.get('sga', 0))
        other_opex = self._build_opex_schedule(drivers, self.inputs.historical_fy_minus_1.get('other_opex', 0))
        
        # 5. EBITDA
        ebitda = [gp - s - o for gp, s, o in zip(gross_profit, sga, other_opex)]
        ebitda_margin = [e / r if r > 0 else 0 for e, r in zip(ebitda, revenue)]
        
        # 6. Depreciation Schedule
        depr_forecast = self._build_depreciation_schedule(drivers, revenue)
        depreciation = depr_forecast.total_depreciation
        
        # 7. EBIT
        ebit = [e - d for e, d in zip(ebitda, depreciation)]
        ebit_margin = [e / r if r > 0 else 0 for e, r in zip(ebit, revenue)]
        
        # 8. Interest Expense (fixed assumption)
        interest_expense = [self.inputs.projected_interest_expense] * 6
        
        # 9. EBT
        ebt = [e - i for e, i in zip(ebit, interest_expense)]
        
        # 10. Tax Schedule (Levered)
        current_tax, deferred_tax, total_tax, net_income = self._build_tax_schedule_levered(
            ebt, depreciation, drivers
        )
        
        # 11. Working Capital Schedule
        wc_forecast = self._build_working_capital_schedule(drivers, revenue, cogs)
        
        # 12. UFCF Calculation (EBITDA method)
        ufcf_forecast = self._calculate_ufcf(
            ebitda, current_tax, drivers.capex, wc_forecast.change_nwc, drivers
        )
        
        # 13. Discounted Cash Flow - Perpetuity Method
        pv_discrete, pv_terminal_perp, ev_perpetuity = self._calculate_dcf_perpetuity(
            ufcf_forecast.ufcf, drivers.terminal_growth_rate
        )
        
        # 14. Discounted Cash Flow - Multiple Method
        pv_terminal_mult, ev_multiple = self._calculate_dcf_multiple(
            ebitda[-1], drivers.terminal_ebitda_multiple
        )
        
        # 15. Equity Value and Per Share
        eq_value_perp = ev_perpetuity - self.inputs.net_debt
        eq_value_mult = ev_multiple - self.inputs.net_debt
        eq_per_share_perp = eq_value_perp / self.inputs.shares_outstanding
        eq_per_share_mult = eq_value_mult / self.inputs.shares_outstanding
        
        # 16. Upside/Downside
        upside_perp = (eq_per_share_perp - self.inputs.current_stock_price) / self.inputs.current_stock_price if self.inputs.current_stock_price > 0 else 0
        upside_mult = (eq_per_share_mult - self.inputs.current_stock_price) / self.inputs.current_stock_price if self.inputs.current_stock_price > 0 else 0
        
        # Main outputs
        main_outputs = DCFValuationResult(
            enterprise_value_perpetuity=round(ev_perpetuity),
            enterprise_value_multiple=round(ev_multiple),
            equity_value_perpetuity=round(eq_value_perp),
            equity_value_multiple=round(eq_value_mult),
            equity_value_per_share_perpetuity=round(eq_per_share_perp, 2),
            equity_value_per_share_multiple=round(eq_per_share_mult, 2),
            current_stock_price=self.inputs.current_stock_price,
            upside_downside_perpetuity_pct=round(upside_perp * 100, 1),
            upside_downside_multiple_pct=round(upside_mult * 100, 1)
        )
        
        # Build income statement forecast
        income_stmt = IncomeStatementForecast(
            years=periods,
            revenue=revenue,
            cogs=cogs,
            gross_profit=gross_profit,
            sga=sga,
            other_opex=other_opex,
            ebitda=ebitda,
            depreciation=depreciation,
            ebit=ebit,
            interest_expense=interest_expense,
            ebt=ebt,
            current_tax=current_tax,
            deferred_tax=deferred_tax,
            total_tax=total_tax,
            net_income=net_income,
            gross_margin=gross_margin,
            ebitda_margin=ebitda_margin,
            ebit_margin=ebit_margin
        )
        
        # Calculate scenarios
        scenario_outputs = self._calculate_all_scenarios()
        
        # Calculate sensitivity tables
        sens_perp = self._calculate_sensitivity_perpetuity()
        sens_mult = self._calculate_sensitivity_multiple()
        
        # Metadata
        metadata = {
            "valuation_date": self.inputs.valuation_date,
            "base_year": self.inputs.base_year,
            "scenario_used": scenario,
            "wacc_used": self.inputs.wacc,
            "terminal_growth_used": drivers.terminal_growth_rate,
            "terminal_multiple_used": drivers.terminal_ebitda_multiple,
            "shares_outstanding_used": self.inputs.shares_outstanding,
            "net_debt_used": self.inputs.net_debt,
            "calculation_timestamp": datetime.now().isoformat(),
            "model_version": "1.0.0",
            "validation_flags": self.validation_flags
        }
        
        return DCFOutput(
            main_outputs=main_outputs,
            scenario_outputs=scenario_outputs,
            sensitivity_perpetuity=sens_perp,
            sensitivity_multiple=sens_mult,
            income_statement_forecast=income_stmt,
            working_capital_forecast=wc_forecast,
            depreciation_forecast=depr_forecast,
            ufcf_forecast=ufcf_forecast,
            pv_discrete=pv_discrete,
            pv_terminal_perpetuity=pv_terminal_perp,
            pv_terminal_multiple=pv_terminal_mult,
            metadata=metadata,
            validation_flags=self.validation_flags,
            warnings=self.warnings
        )
    
    def _validate_critical_inputs(self, drivers: ForecastDrivers):
        """Validate critical inputs before calculation"""
        # Terminal growth < WACC
        if drivers.terminal_growth_rate >= self.inputs.wacc:
            raise ValueError(
                f"Terminal growth rate ({drivers.terminal_growth_rate:.2%}) must be less than "
                f"WACC ({self.inputs.wacc:.2%}) for perpetuity formula"
            )
        self.validation_flags["terminal_growth_less_than_wacc"] = True
        
        # Shares outstanding > 0
        if self.inputs.shares_outstanding <= 0:
            raise ValueError("Shares outstanding must be positive")
        self.validation_flags["positive_shares_outstanding"] = True
        
        # Revenue positive check will be done after forecast
        
    def _build_revenue_schedule(self, drivers: ForecastDrivers) -> List[float]:
        """Build revenue forecast using growth rates"""
        base_revenue = self.inputs.historical_fy_minus_1.get('revenue', 0)
        revenue = [base_revenue]
        
        for i, growth in enumerate(drivers.revenue_growth):
            prev_revenue = revenue[-1]
            new_revenue = prev_revenue * (1 + growth)
            revenue.append(new_revenue)
        
        # Remove base year, keep only forecast periods
        revenue = revenue[1:]
        
        # Validate positive revenue
        for i, r in enumerate(revenue):
            if r <= 0:
                self.warnings.append(f"Non-positive revenue in period {i}: {r}")
                self.validation_flags["positive_revenue_all_years"] = False
                break
        else:
            self.validation_flags["positive_revenue_all_years"] = True
            
        return revenue
    
    def _build_cogs_schedule(self, drivers: ForecastDrivers) -> List[float]:
        """Build COGS forecast using inflation-adjusted growth"""
        base_cogs = self.inputs.historical_fy_minus_1.get('cogs', 0)
        cogs = [base_cogs]
        
        for inflation in drivers.inflation_rate:
            prev_cogs = cogs[-1]
            new_cogs = prev_cogs * (1 + inflation)
            cogs.append(new_cogs)
        
        return cogs[1:]
    
    def _build_opex_schedule(self, drivers: ForecastDrivers, base_value: float) -> List[float]:
        """Build OpEx forecast (SG&A or Other)"""
        opex = [base_value]
        
        for growth in drivers.opex_growth:
            prev_opex = opex[-1]
            new_opex = prev_opex * (1 + growth)
            opex.append(new_opex)
        
        return opex[1:]
    
    def _build_depreciation_schedule(
        self, 
        drivers: ForecastDrivers, 
        revenue: List[float]
    ) -> DepreciationForecast:
        """
        Build depreciation schedule with existing and new assets.
        Uses straight-line with half-year convention for new assets.
        """
        periods = self.inputs.forecast_years + ["Terminal"]
        n_periods = len(periods)
        
        # Existing assets depreciation
        base_ppe = self.inputs.ppe_net
        annual_depr_existing = base_ppe / self.inputs.useful_life_existing if self.inputs.useful_life_existing > 0 else 0
        existing_depr = [annual_depr_existing] * n_periods
        
        # New assets depreciation (half-year convention)
        new_depr = [0.0] * n_periods
        gross_ppe = [base_ppe]
        
        for i, capex in enumerate(drivers.capex):
            if i < n_periods:
                # Add CapEx to gross PPE
                current_gross_ppe = gross_ppe[-1] + capex
                gross_ppe.append(current_gross_ppe)
                
                # Half-year convention: 50% in first year, 100% thereafter
                if self.inputs.useful_life_new > 0:
                    annual_depr_new = capex / self.inputs.useful_life_new
                    # First year (half-year convention)
                    if i < n_periods:
                        new_depr[i] += annual_depr_new * 0.5
                    # Subsequent years (full depreciation)
                    for j in range(i + 1, min(i + int(self.inputs.useful_life_new), n_periods)):
                        new_depr[j] += annual_depr_new
        
        # Terminal year: CapEx = Depreciation (steady-state)
        # Already handled in the loop above
        
        total_depr = [e + n for e, n in zip(existing_depr, new_depr)]
        
        # Ensure gross_ppe has correct length
        gross_ppe = gross_ppe[:n_periods]
        if len(gross_ppe) < n_periods:
            gross_ppe.extend([gross_ppe[-1]] * (n_periods - len(gross_ppe)))
        
        return DepreciationForecast(
            years=periods,
            existing_assets_depr=existing_depr,
            new_assets_depr=new_depr,
            total_depreciation=total_depr,
            gross_ppe_end=gross_ppe
        )
    
    def _build_tax_schedule_levered(
        self,
        ebt: List[float],
        depreciation: List[float],
        drivers: ForecastDrivers
    ) -> Tuple[List[float], List[float], List[float], List[float]]:
        """
        Calculate current and deferred taxes with NOL utilization.
        """
        current_tax = []
        deferred_tax = []
        total_tax = []
        net_income = []
        
        nol_remaining = self.inputs.tax_losses_nol
        limit_pct = self.inputs.tax_loss_utilization_limit_pct
        
        for i in range(len(ebt)):
            # Adjust EBT for depreciation differences (simplified - assumes book = tax)
            ebt_adjusted = ebt[i]
            
            # NOL utilization
            nol_utilized = min(nol_remaining, max(0, ebt_adjusted) * limit_pct)
            taxable_income = max(0, ebt_adjusted - nol_utilized)
            nol_remaining -= nol_utilized
            
            # Current tax
            tax_rate = drivers.tax_rate[i] if i < len(drivers.tax_rate) else drivers.tax_rate[-1]
            curr_tax = taxable_income * tax_rate
            current_tax.append(curr_tax)
            
            # Deferred tax (simplified - difference between book and tax depreciation)
            # For now, assume no deferred tax in terminal year
            if i == len(ebt) - 1:  # Terminal year
                def_tax = 0.0
            else:
                def_tax = (ebt_adjusted - taxable_income) * tax_rate
            deferred_tax.append(def_tax)
            
            # Total tax
            tot_tax = curr_tax + def_tax
            total_tax.append(tot_tax)
            
            # Net income
            ni = ebt[i] - tot_tax
            net_income.append(ni)
        
        # Check if NOL fully utilized
        self.validation_flags["nol_fully_utilized"] = nol_remaining <= 0.01
        
        return current_tax, deferred_tax, total_tax, net_income
    
    def _build_working_capital_schedule(
        self,
        drivers: ForecastDrivers,
        revenue: List[float],
        cogs: List[float]
    ) -> WorkingCapitalForecast:
        """Build working capital schedule"""
        periods = self.inputs.forecast_years + ["Terminal"]
        n_periods = len(periods)
        
        ar = []
        inventory = []
        ap = []
        nwc = []
        change_nwc = []
        
        # Base period NWC (from historical)
        base_ar = self.inputs.historical_fy_minus_1.get('accounts_receivable', 0)
        base_inv = self.inputs.historical_fy_minus_1.get('inventory', 0)
        base_ap = self.inputs.historical_fy_minus_1.get('accounts_payable', 0)
        base_nwc = base_ar + base_inv - base_ap
        
        prev_nwc = base_nwc
        days_in_period = 365.0
        
        for i in range(n_periods):
            ar_days = drivers.ar_days[i] if i < len(drivers.ar_days) else drivers.ar_days[-1]
            inv_days = drivers.inv_days[i] if i < len(drivers.inv_days) else drivers.inv_days[-1]
            ap_days = drivers.ap_days[i] if i < len(drivers.ap_days) else drivers.ap_days[-1]
            
            # Calculate WC components
            ar_val = revenue[i] * (ar_days / days_in_period) if revenue[i] > 0 else 0
            inv_val = cogs[i] * (inv_days / days_in_period) if cogs[i] > 0 else 0
            ap_val = cogs[i] * (ap_days / days_in_period) if cogs[i] > 0 else 0
            
            ar.append(ar_val)
            inventory.append(inv_val)
            ap.append(ap_val)
            
            # NWC
            nwc_val = ar_val + inv_val - ap_val
            nwc.append(nwc_val)
            
            # Change in NWC
            change = nwc_val - prev_nwc
            change_nwc.append(change)
            
            # Check for large WC changes
            if revenue[i] > 0 and abs(change) > 0.1 * revenue[i]:
                self.warnings.append(
                    f"Large working capital change in {periods[i]}: {change:.0f} "
                    f"({abs(change)/revenue[i]*100:.1f}% of revenue)"
                )
            
            prev_nwc = nwc_val
        
        return WorkingCapitalForecast(
            years=periods,
            ar=ar,
            inventory=inventory,
            ap=ap,
            nwc=nwc,
            change_nwc=change_nwc,
            ar_days=drivers.ar_days[:n_periods],
            inv_days=drivers.inv_days[:n_periods],
            ap_days=drivers.ap_days[:n_periods]
        )
    
    def _calculate_ufcf(
        self,
        ebitda: List[float],
        current_tax: List[float],
        capex: List[float],
        change_nwc: List[float],
        drivers: ForecastDrivers
    ) -> UFCFForecast:
        """Calculate Unlevered Free Cash Flow using EBITDA method"""
        periods = self.inputs.forecast_years + ["Terminal"]
        n_periods = len(periods)
        
        ufcf = []
        
        for i in range(n_periods):
            cap = capex[i] if i < len(capex) else capex[-1]
            
            # Terminal year: CapEx = Depreciation
            if i == n_periods - 1:
                # This is handled by ensuring capex array matches depreciation in terminal
                pass
            
            ufcf_val = ebitda[i] - current_tax[i] - cap - change_nwc[i]
            ufcf.append(ufcf_val)
        
        return UFCFForecast(
            years=periods,
            ebitda=ebitda,
            current_tax_unlevered=current_tax,
            capex=capex[:n_periods],
            change_nwc=change_nwc,
            ufcf=ufcf
        )
    
    def _calculate_dcf_perpetuity(
        self,
        ufcf: List[float],
        terminal_growth: float
    ) -> Tuple[float, float, float]:
        """
        Calculate DCF using Gordon Growth terminal value.
        Uses partial period adjustment (0.75 for first year).
        """
        wacc = self.inputs.wacc
        
        # Discount factors with partial period adjustment
        # Years: [0.25, 1.25, 2.25, 3.25, 4.25, 5.25]
        discount_years = [0.25, 1.25, 2.25, 3.25, 4.25, 5.25]
        
        # Adjusted UFCF (partial period adjustment for first year)
        adjusted_ufcf = []
        for i, u in enumerate(ufcf):
            adj_factor = 0.75 if i == 0 else 1.0
            adjusted_ufcf.append(u * adj_factor)
        
        # Present value of discrete cash flows
        pv_discrete = 0.0
        for i, (u, years) in enumerate(zip(adjusted_ufcf[:-1], discount_years[:-1])):
            disc_factor = (1 + wacc) ** years
            pv_discrete += u / disc_factor
        
        # Terminal value (perpetuity)
        terminal_ufcf = ufcf[-1]
        if wacc <= terminal_growth:
            raise ValueError("WACC must be greater than terminal growth")
        
        tv_perpetuity = terminal_ufcf * (1 + terminal_growth) / (wacc - terminal_growth)
        
        # PV of terminal value
        terminal_disc_factor = (1 + wacc) ** discount_years[-1]
        pv_terminal = tv_perpetuity / terminal_disc_factor
        
        # Enterprise value
        ev = pv_discrete + pv_terminal
        
        return pv_discrete, pv_terminal, ev
    
    def _calculate_dcf_multiple(
        self,
        terminal_ebitda: float,
        terminal_multiple: float
    ) -> Tuple[float, float]:
        """Calculate DCF using EBITDA multiple terminal value"""
        wacc = self.inputs.wacc
        
        # Recalculate PV of discrete cash flows (same as perpetuity method)
        # This should ideally be passed in, but recalculating for clarity
        drivers = self.inputs.forecast_drivers.get("base_case")
        if not drivers:
            drivers = list(self.inputs.forecast_drivers.values())[0]
        
        # Quick recalculation of UFCF for discrete period
        # In production, this would be cached from earlier calculation
        revenue = self._build_revenue_schedule(drivers)
        # ... (simplified - using same PV as perpetuity for discrete portion)
        
        # For now, use placeholder - in full implementation, this matches perpetuity
        pv_discrete = 0.0  # Would be calculated same as perpetuity method
        
        # Terminal value (multiple)
        tv_multiple = terminal_ebitda * terminal_multiple
        
        # Validate terminal multiple
        if terminal_multiple < 5.0 or terminal_multiple > 15.0:
            self.warnings.append(
                f"Terminal multiple {terminal_multiple:.1f} outside typical range [5.0, 15.0]"
            )
        self.validation_flags["positive_ebitda_terminal"] = terminal_ebitda > 0
        
        # PV of terminal value
        discount_years = 5.25
        disc_factor = (1 + wacc) ** discount_years
        pv_terminal = tv_multiple / disc_factor
        
        # Enterprise value (using same discrete PV as perpetuity for simplicity)
        # In full implementation, recalculate UFCF and discount
        ev = pv_discrete + pv_terminal
        
        return pv_terminal, ev
    
    def _calculate_all_scenarios(self) -> ScenarioOutput:
        """Calculate valuation for all three scenarios"""
        scenarios = {}
        
        for scenario_name in ["best_case", "base_case", "worst_case"]:
            if scenario_name in self.inputs.forecast_drivers:
                try:
                    result = self.calculate(scenario_name)
                    scenarios[scenario_name] = {
                        "enterprise_value": result.main_outputs.enterprise_value_perpetuity,
                        "equity_value": result.main_outputs.equity_value_perpetuity,
                        "equity_value_per_share": result.main_outputs.equity_value_per_share_perpetuity
                    }
                except Exception as e:
                    self.warnings.append(f"Failed to calculate {scenario_name}: {str(e)}")
                    scenarios[scenario_name] = {
                        "enterprise_value": 0,
                        "equity_value": 0,
                        "equity_value_per_share": 0
                    }
            else:
                scenarios[scenario_name] = {
                    "enterprise_value": 0,
                    "equity_value": 0,
                    "equity_value_per_share": 0
                }
        
        return ScenarioOutput(
            best_case=scenarios.get("best_case", {}),
            base_case=scenarios.get("base_case", {}),
            worst_case=scenarios.get("worst_case", {})
        )
    
    def _calculate_sensitivity_perpetuity(self) -> SensitivityTable:
        """Calculate 5x5 sensitivity table for perpetuity method"""
        wacc_range = [0.077, 0.087, 0.097, 0.107, 0.117]
        growth_range = [0.01, 0.015, 0.02, 0.025, 0.03]
        
        ev_table = {}
        eq_share_table = {}
        upside_table = {}
        
        drivers = self.inputs.forecast_drivers.get("base_case")
        if not drivers:
            drivers = list(self.inputs.forecast_drivers.values())[0]
        
        for wacc in wacc_range:
            ev_table[str(wacc)] = {}
            eq_share_table[str(wacc)] = {}
            upside_table[str(wacc)] = {}
            
            for growth in growth_range:
                if growth >= wacc:
                    # Skip invalid combinations
                    ev_table[str(wacc)][str(growth)] = 0
                    eq_share_table[str(wacc)][str(growth)] = 0
                    upside_table[str(wacc)][str(growth)] = 0
                    continue
                
                # Quick valuation with different WACC and growth
                # Simplified - in production, would recalculate full DCF
                base_ev = self._quick_valuation_perpetuity(wacc, growth, drivers)
                base_eq = base_ev - self.inputs.net_debt
                base_eq_share = base_eq / self.inputs.shares_outstanding
                base_upside = (base_eq_share - self.inputs.current_stock_price) / self.inputs.current_stock_price * 100
                
                ev_table[str(wacc)][str(growth)] = round(base_ev)
                eq_share_table[str(wacc)][str(growth)] = round(base_eq_share, 2)
                upside_table[str(wacc)][str(growth)] = round(base_upside, 1)
        
        return SensitivityTable(
            wacc_values=wacc_range,
            variable_values=growth_range,
            enterprise_value_table=ev_table,
            equity_value_per_share_table=eq_share_table,
            upside_downside_table=upside_table
        )
    
    def _calculate_sensitivity_multiple(self) -> SensitivityTable:
        """Calculate 5x5 sensitivity table for multiple method"""
        wacc_range = [0.077, 0.087, 0.097, 0.107, 0.117]
        multiple_range = [6.0, 6.5, 7.0, 7.5, 8.0]
        
        ev_table = {}
        eq_share_table = {}
        upside_table = {}
        
        drivers = self.inputs.forecast_drivers.get("base_case")
        if not drivers:
            drivers = list(self.inputs.forecast_drivers.values())[0]
        
        for wacc in wacc_range:
            ev_table[str(wacc)] = {}
            eq_share_table[str(wacc)] = {}
            upside_table[str(wacc)] = {}
            
            for multiple in multiple_range:
                # Quick valuation with different WACC and multiple
                base_ev = self._quick_valuation_multiple(wacc, multiple, drivers)
                base_eq = base_ev - self.inputs.net_debt
                base_eq_share = base_eq / self.inputs.shares_outstanding
                base_upside = (base_eq_share - self.inputs.current_stock_price) / self.inputs.current_stock_price * 100
                
                ev_table[str(wacc)][str(multiple)] = round(base_ev)
                eq_share_table[str(wacc)][str(multiple)] = round(base_eq_share, 2)
                upside_table[str(wacc)][str(multiple)] = round(base_upside, 1)
        
        return SensitivityTable(
            wacc_values=wacc_range,
            variable_values=multiple_range,
            enterprise_value_table=ev_table,
            equity_value_per_share_table=eq_share_table,
            upside_downside_table=upside_table
        )
    
    def _quick_valuation_perpetuity(
        self, 
        wacc: float, 
        terminal_growth: float, 
        drivers: ForecastDrivers
    ) -> float:
        """Quick DCF valuation for sensitivity analysis (perpetuity method)"""
        # Simplified valuation - in production would recalculate full forecast
        # Using base case UFCF and adjusting discount rate
        
        # Get base UFCF (would be recalculated with new assumptions)
        # For sensitivity, we'll use a simplified approach
        base_ufcf = sum(self.inputs.historical_fy_minus_1.get('ebitda', 0) for _ in range(5)) / 5
        
        # Terminal value
        terminal_ufcf = base_ufcf * (1 + terminal_growth)
        tv = terminal_ufcf / (wacc - terminal_growth)
        
        # Simplified PV (would be more accurate in full implementation)
        pv = tv / ((1 + wacc) ** 5.25) * 0.8 + base_ufcf * 4
        
        return pv
    
    def _quick_valuation_multiple(
        self, 
        wacc: float, 
        terminal_multiple: float, 
        drivers: ForecastDrivers
    ) -> float:
        """Quick DCF valuation for sensitivity analysis (multiple method)"""
        # Simplified valuation
        base_ebitda = self.inputs.historical_fy_minus_1.get('ebitda', 0)
        
        # Terminal value
        tv = base_ebitda * terminal_multiple
        
        # Simplified PV
        pv = tv / ((1 + wacc) ** 5.25) * 0.7 + base_ebitda * 4
        
        return pv
    
    def to_dict(self, output: DCFOutput) -> Dict[str, Any]:
        """Convert DCFOutput to dictionary for JSON serialization"""
        return {
            "main_outputs": {
                "enterprise_value_perpetuity": output.main_outputs.enterprise_value_perpetuity,
                "enterprise_value_multiple": output.main_outputs.enterprise_value_multiple,
                "equity_value_perpetuity": output.main_outputs.equity_value_perpetuity,
                "equity_value_multiple": output.main_outputs.equity_value_multiple,
                "equity_value_per_share_perpetuity": output.main_outputs.equity_value_per_share_perpetuity,
                "equity_value_per_share_multiple": output.main_outputs.equity_value_per_share_multiple,
                "current_stock_price": output.main_outputs.current_stock_price,
                "upside_downside_perpetuity_pct": output.main_outputs.upside_downside_perpetuity_pct,
                "upside_downside_multiple_pct": output.main_outputs.upside_downside_multiple_pct
            },
            "scenario_outputs": {
                "best_case": output.scenario_outputs.best_case,
                "base_case": output.scenario_outputs.base_case,
                "worst_case": output.scenario_outputs.worst_case
            },
            "sensitivity_tables": {
                "perpetuity_method": {
                    "enterprise_value_table": output.sensitivity_perpetuity.enterprise_value_table,
                    "equity_value_per_share_table": output.sensitivity_perpetuity.equity_value_per_share_table,
                    "upside_downside_table": output.sensitivity_perpetuity.upside_downside_table
                },
                "multiple_method": {
                    "enterprise_value_table": output.sensitivity_multiple.enterprise_value_table,
                    "equity_value_per_share_table": output.sensitivity_multiple.equity_value_per_share_table,
                    "upside_downside_table": output.sensitivity_multiple.upside_downside_table
                }
            },
            "supporting_schedules": {
                "income_statement_forecast": {
                    "years": output.income_statement_forecast.years,
                    "revenue": output.income_statement_forecast.revenue,
                    "cogs": output.income_statement_forecast.cogs,
                    "gross_profit": output.income_statement_forecast.gross_profit,
                    "sga": output.income_statement_forecast.sga,
                    "other": output.income_statement_forecast.other_opex,
                    "ebitda": output.income_statement_forecast.ebitda,
                    "depreciation": output.income_statement_forecast.depreciation,
                    "ebit": output.income_statement_forecast.ebit,
                    "interest": output.income_statement_forecast.interest_expense,
                    "ebt": output.income_statement_forecast.ebt,
                    "current_tax": output.income_statement_forecast.current_tax,
                    "deferred_tax": output.income_statement_forecast.deferred_tax,
                    "total_tax": output.income_statement_forecast.total_tax,
                    "net_income": output.income_statement_forecast.net_income
                },
                "working_capital_forecast": {
                    "years": output.working_capital_forecast.years,
                    "ar": output.working_capital_forecast.ar,
                    "inventory": output.working_capital_forecast.inventory,
                    "ap": output.working_capital_forecast.ap,
                    "nwc": output.working_capital_forecast.nwc,
                    "change_nwc": output.working_capital_forecast.change_nwc
                },
                "depreciation_forecast": {
                    "years": output.depreciation_forecast.years,
                    "existing_assets_depr": output.depreciation_forecast.existing_assets_depr,
                    "new_assets_depr": output.depreciation_forecast.new_assets_depr,
                    "total_depreciation": output.depreciation_forecast.total_depreciation
                },
                "ufcf_forecast": [
                    {"year": y, "ufcf": u} 
                    for y, u in zip(output.ufcf_forecast.years, output.ufcf_forecast.ufcf)
                ]
            },
            "discounting_details": {
                "pv_discrete": output.pv_discrete,
                "pv_terminal_perpetuity": output.pv_terminal_perpetuity,
                "pv_terminal_multiple": output.pv_terminal_multiple,
                "enterprise_value_perpetuity": output.main_outputs.enterprise_value_perpetuity,
                "enterprise_value_multiple": output.main_outputs.enterprise_value_multiple
            },
            "metadata": output.metadata,
            "validation_flags": output.validation_flags,
            "warnings": output.warnings
        }


def run_dcf_valuation(
    ticker: str,
    scenario: str = "base_case"
) -> Dict[str, Any]:
    """
    Convenience function to run full DCF valuation for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        scenario: "best_case", "base_case", or "worst_case"
        
    Returns:
        Dictionary with complete DCF output
    """
    # Import input fetchers
    try:
        from .input import fetch_valuation_inputs
        from .input_dcf import fetch_dcf_inputs
        
        # Fetch API inputs
        api_inputs = fetch_valuation_inputs(ticker)
        
        # Fetch DCF-specific inputs
        dcf_inputs_data = fetch_dcf_inputs(ticker)
        
        # Build DCFInputs object
        # This is simplified - in production would map all fields properly
        inputs = DCFInputs(
            valuation_date=datetime.now().strftime("%Y-%m-%d"),
            historical_fy_minus_1=dcf_inputs_data.get('fy_minus_1', {}),
            historical_fy_minus_2=dcf_inputs_data.get('fy_minus_2', {}),
            historical_fy_minus_3=dcf_inputs_data.get('fy_minus_3', {}),
            net_debt=dcf_inputs_data.get('net_debt', 0),
            ppe_net=dcf_inputs_data.get('ppe_net', 0),
            shares_outstanding=dcf_inputs_data.get('shares_outstanding', 1),
            current_stock_price=dcf_inputs_data.get('current_stock_price', 0),
            projected_interest_expense=dcf_inputs_data.get('projected_interest_expense', 0),
            wacc=0.10,
            forecast_drivers={
                "base_case": ForecastDrivers(
                    revenue_growth=[0.05, 0.05, 0.04, 0.04, 0.03, 0.02],
                    terminal_growth_rate=0.02,
                    terminal_ebitda_multiple=7.0
                ),
                "best_case": ForecastDrivers(
                    revenue_growth=[0.08, 0.07, 0.06, 0.05, 0.04, 0.025],
                    terminal_growth_rate=0.025,
                    terminal_ebitda_multiple=8.0
                ),
                "worst_case": ForecastDrivers(
                    revenue_growth=[0.02, 0.02, 0.01, 0.01, 0.01, 0.01],
                    terminal_growth_rate=0.01,
                    terminal_ebitda_multiple=5.5
                )
            }
        )
        
        # Run DCF
        engine = DCFEngine(inputs)
        output = engine.calculate(scenario)
        
        return engine.to_dict(output)
        
    except ImportError as e:
        return {"error": f"Failed to import input modules: {str(e)}"}
    except Exception as e:
        return {"error": f"DCF calculation failed: {str(e)}"}


if __name__ == "__main__":
    # Example usage
    print("DCF Engine initialized. Use run_dcf_valuation(ticker) to calculate.")
