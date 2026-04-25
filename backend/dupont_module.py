"""
DuPont Analysis Module - Inputs, Calculations, and Outputs

This module implements comprehensive DuPont analysis with 3-step and 5-step decomposition,
supporting ratios, growth trends, and validation checks.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json
from datetime import datetime


@dataclass
class DuPontInputs:
    """
    Required input data for DuPont Analysis.
    All arrays should contain historical data for [FY-4, FY-3, FY-2, FY-1] or similar periods.
    """
    
    # Metadata
    ticker: str
    company_name: str
    currency: str = "USD"
    fiscal_year_end_month: int = 12
    valuation_date: str = ""
    
    # Income Statement (arrays for multiple years)
    revenue: List[float] = field(default_factory=list)
    cost_of_revenue: List[float] = field(default_factory=list)
    gross_profit: List[float] = field(default_factory=list)  # Can be calculated if not provided
    operating_expenses: List[float] = field(default_factory=list)  # SG&A + Other OpEx
    ebitda: List[float] = field(default_factory=list)
    depreciation_amortization: List[float] = field(default_factory=list)
    ebit_operating_income: List[float] = field(default_factory=list)
    interest_expense: List[float] = field(default_factory=list)
    interest_income: List[float] = field(default_factory=list)
    pretax_income: List[float] = field(default_factory=list)
    tax_provision: List[float] = field(default_factory=list)
    net_income: List[float] = field(default_factory=list)
    
    # Balance Sheet (period-end values)
    total_assets: List[float] = field(default_factory=list)
    current_assets: List[float] = field(default_factory=list)
    accounts_receivable: List[float] = field(default_factory=list)
    inventory: List[float] = field(default_factory=list)
    cash_and_equivalents: List[float] = field(default_factory=list)
    total_liabilities: List[float] = field(default_factory=list)
    current_liabilities: List[float] = field(default_factory=list)
    accounts_payable: List[float] = field(default_factory=list)
    total_debt: List[float] = field(default_factory=list)
    short_term_debt: List[float] = field(default_factory=list)
    long_term_debt: List[float] = field(default_factory=list)
    total_equity: List[float] = field(default_factory=list)
    retained_earnings: List[float] = field(default_factory=list)
    goodwill: List[float] = field(default_factory=list)
    intangible_assets: List[float] = field(default_factory=list)
    
    # Cash Flow (optional but useful)
    operating_cash_flow: List[float] = field(default_factory=list)
    capital_expenditures: List[float] = field(default_factory=list)
    free_cash_flow: List[float] = field(default_factory=list)
    
    # Share Data
    shares_outstanding_diluted: List[float] = field(default_factory=list)
    
    # Peer Data (optional for benchmarking)
    peer_tickers: List[str] = field(default_factory=list)
    peer_roe_values: List[float] = field(default_factory=list)
    peer_roa_values: List[float] = field(default_factory=list)
    peer_net_margin_values: List[float] = field(default_factory=list)
    peer_asset_turnover_values: List[float] = field(default_factory=list)
    peer_equity_multiplier_values: List[float] = field(default_factory=list)
    
    def validate_inputs(self) -> Dict[str, Any]:
        """Validate input data consistency and completeness."""
        errors = []
        warnings = []
        
        # Check array lengths
        required_arrays = {
            'revenue': self.revenue,
            'net_income': self.net_income,
            'total_assets': self.total_assets,
            'total_equity': self.total_equity,
            'ebit_operating_income': self.ebit_operating_income,
            'pretax_income': self.pretax_income,
        }
        
        lengths = {name: len(arr) for name, arr in required_arrays.items() if arr}
        if len(set(lengths.values())) > 1:
            errors.append(f"Inconsistent array lengths: {lengths}")
        
        min_years = 2  # Need at least 2 years for growth calculations
        if self.revenue and len(self.revenue) < min_years:
            warnings.append(f"Only {len(self.revenue)} year(s) of revenue data. Recommend 3+ years.")
        
        # Check for critical missing data
        if not self.revenue:
            errors.append("Missing revenue data")
        if not self.net_income:
            errors.append("Missing net income data")
        if not self.total_assets:
            errors.append("Missing total assets data")
        if not self.total_equity:
            errors.append("Missing total equity data")
        
        # Check for negative equity (edge case)
        if self.total_equity and any(e <= 0 for e in self.total_equity):
            warnings.append("Negative or zero equity detected - equity multiplier will be invalid")
        
        # Check for division by zero risks
        if self.revenue and any(r == 0 for r in self.revenue):
            warnings.append("Zero revenue detected - margin calculations will fail")
        
        if self.total_assets and any(a == 0 for a in self.total_assets):
            warnings.append("Zero assets detected - turnover calculations will fail")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'years_available': lengths.get('revenue', 0)
        }


@dataclass
class DuPontOutputs:
    """
    Complete DuPont Analysis output structure.
    All arrays correspond to the input periods [FY-4, FY-3, FY-2, FY-1].
    """
    
    # Supporting Ratios (all arrays)
    gross_margin: List[float] = field(default_factory=list)
    ebitda_margin: List[float] = field(default_factory=list)
    operating_margin: List[float] = field(default_factory=list)
    net_profit_margin: List[float] = field(default_factory=list)
    asset_turnover: List[float] = field(default_factory=list)
    ar_days: List[float] = field(default_factory=list)
    inv_days: List[float] = field(default_factory=list)
    ap_days: List[float] = field(default_factory=list)
    cash_conversion_cycle: List[float] = field(default_factory=list)
    debt_to_equity: List[float] = field(default_factory=list)
    current_ratio: List[float] = field(default_factory=list)
    quick_ratio: List[float] = field(default_factory=list)
    interest_coverage: List[float] = field(default_factory=list)
    roe: List[float] = field(default_factory=list)
    roa: List[float] = field(default_factory=list)
    roic: List[float] = field(default_factory=list)
    
    # Additional calculated metrics
    tangible_equity_multiplier: List[float] = field(default_factory=list)
    financial_leverage: List[float] = field(default_factory=list)
    capital_turnover: List[float] = field(default_factory=list)
    noc_margin: List[float] = field(default_factory=list)  # Net Operating Capital margin
    roce: List[float] = field(default_factory=list)  # Return on Capital Employed
    
    # DuPont 3-Step Decomposition
    dupont_3step_net_margin: List[float] = field(default_factory=list)
    dupont_3step_asset_turnover: List[float] = field(default_factory=list)
    dupont_3step_equity_multiplier: List[float] = field(default_factory=list)
    dupont_3step_roe_reconciled: List[float] = field(default_factory=list)
    
    # DuPont 5-Step Decomposition
    dupont_5step_tax_burden: List[float] = field(default_factory=list)
    dupont_5step_interest_burden: List[float] = field(default_factory=list)
    dupont_5step_ebit_margin: List[float] = field(default_factory=list)
    dupont_5step_asset_turnover: List[float] = field(default_factory=list)
    dupont_5step_equity_multiplier: List[float] = field(default_factory=list)
    dupont_5step_roe_reconciled: List[float] = field(default_factory=list)
    
    # Growth Trends
    revenue_growth: List[Optional[float]] = field(default_factory=list)
    ebitda_growth: List[Optional[float]] = field(default_factory=list)
    net_income_growth: List[Optional[float]] = field(default_factory=list)
    dol: List[Optional[float]] = field(default_factory=list)  # Degree of Operating Leverage
    dfl: List[Optional[float]] = field(default_factory=list)  # Degree of Financial Leverage
    dtl: List[Optional[float]] = field(default_factory=list)  # Degree of Total Leverage
    
    # Validation Results
    roe_3step_matches_direct: List[bool] = field(default_factory=list)
    roe_5step_matches_direct: List[bool] = field(default_factory=list)
    
    # Peer Comparison (if available)
    peer_roe_median: Optional[float] = None
    peer_roa_median: Optional[float] = None
    peer_net_margin_median: Optional[float] = None
    peer_asset_turnover_median: Optional[float] = None
    peer_equity_multiplier_median: Optional[float] = None
    target_vs_peer_roe: List[Optional[float]] = field(default_factory=list)
    
    # Metadata
    years_analyzed: int = 0
    currency: str = "USD"
    unit_scaling: str = "thousands"
    calculation_timestamp: str = ""
    data_source: str = ""
    periods: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert output to dictionary format matching JSON schema."""
        return {
            "supporting_ratios": {
                "gross_margin": self.gross_margin,
                "ebitda_margin": self.ebitda_margin,
                "operating_margin": self.operating_margin,
                "net_profit_margin": self.net_profit_margin,
                "asset_turnover": self.asset_turnover,
                "ar_days": self.ar_days,
                "inv_days": self.inv_days,
                "ap_days": self.ap_days,
                "cash_conversion_cycle": self.cash_conversion_cycle,
                "debt_to_equity": self.debt_to_equity,
                "current_ratio": self.current_ratio,
                "interest_coverage": self.interest_coverage,
                "roe": self.roe,
                "roa": self.roa,
                "roic": self.roic
            },
            "dupont_3step": {
                "net_profit_margin": self.dupont_3step_net_margin,
                "asset_turnover": self.dupont_3step_asset_turnover,
                "equity_multiplier": self.dupont_3step_equity_multiplier,
                "roe_reconciled": self.dupont_3step_roe_reconciled
            },
            "dupont_5step": {
                "tax_burden": self.dupont_5step_tax_burden,
                "interest_burden": self.dupont_5step_interest_burden,
                "ebit_margin": self.dupont_5step_ebit_margin,
                "asset_turnover": self.dupont_5step_asset_turnover,
                "equity_multiplier": self.dupont_5step_equity_multiplier,
                "roe_reconciled": self.dupont_5step_roe_reconciled
            },
            "growth_trends": {
                "revenue_growth": self.revenue_growth,
                "ebitda_growth": self.ebitda_growth,
                "net_income_growth": self.net_income_growth,
                "dol": self.dol,
                "dfl": self.dfl,
                "dtl": self.dtl
            },
            "validation": {
                "roe_3step_matches_direct": self.roe_3step_matches_direct,
                "roe_5step_matches_direct": self.roe_5step_matches_direct
            },
            "additional_metrics": {
                "tangible_equity_multiplier": self.tangible_equity_multiplier,
                "financial_leverage": self.financial_leverage,
                "capital_turnover": self.capital_turnover,
                "noc_margin": self.noc_margin,
                "roce": self.roce
            },
            "peer_comparison": {
                "peer_roe_median": self.peer_roe_median,
                "peer_roa_median": self.peer_roa_median,
                "peer_net_margin_median": self.peer_net_margin_median,
                "peer_asset_turnover_median": self.peer_asset_turnover_median,
                "peer_equity_multiplier_median": self.peer_equity_multiplier_median,
                "target_vs_peer_roe": self.target_vs_peer_roe
            },
            "metadata": {
                "years_analyzed": self.years_analyzed,
                "currency": self.currency,
                "unit_scaling": self.unit_scaling,
                "calculation_timestamp": self.calculation_timestamp,
                "data_source": self.data_source,
                "periods": self.periods
            }
        }


class DuPontAnalyzer:
    """
    DuPont Analysis calculation engine.
    
    Formulas:
    =========
    3-Step DuPont: ROE = Net Profit Margin × Asset Turnover × Equity Multiplier
                   ROE = (Net Income / Revenue) × (Revenue / Assets) × (Assets / Equity)
    
    5-Step DuPont: ROE = Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Equity Multiplier
                   ROE = (NI/EBT) × (EBT/EBIT) × (EBIT/Revenue) × (Revenue/Assets) × (Assets/Equity)
    
    Supporting Ratios:
    - Gross Margin = Gross Profit / Revenue
    - EBITDA Margin = EBITDA / Revenue
    - Operating Margin = EBIT / Revenue
    - Net Profit Margin = Net Income / Revenue
    - Asset Turnover = Revenue / Average Total Assets
    - AR Days = (Accounts Receivable / Revenue) × 365
    - Inventory Days = (Inventory / COGS) × 365
    - AP Days = (Accounts Payable / COGS) × 365
    - CCC = AR Days + Inventory Days - AP Days
    - Current Ratio = Current Assets / Current Liabilities
    - Quick Ratio = (Current Assets - Inventory) / Current Liabilities
    - Debt-to-Equity = Total Debt / Total Equity
    - Interest Coverage = EBITDA / Interest Expense
    - ROE = Net Income / Average Equity
    - ROA = Net Income / Average Total Assets
    - ROIC = NOPAT / Invested Capital
    
    Edge Case Handling:
    - Division by zero returns None or 0.0
    - Negative equity flags warning and returns None for equity multiplier
    - Missing prior period data returns None for growth rates
    """
    
    def __init__(self, inputs: DuPontInputs):
        self.inputs = inputs
        self.outputs = DuPontOutputs()
        self.validation_results = {}
    
    def _safe_divide(self, numerator: float, denominator: float, default: float = 0.0) -> float:
        """Safe division handling zero denominators."""
        if denominator == 0:
            return default
        return numerator / denominator
    
    def _calculate_average(self, current: float, prior: Optional[float]) -> float:
        """Calculate average of current and prior period values."""
        if prior is None or prior == 0:
            return current
        return (current + prior) / 2
    
    def calculate_supporting_ratios(self):
        """Calculate all supporting financial ratios."""
        n = len(self.inputs.revenue)
        
        for i in range(n):
            # Margins
            rev = self.inputs.revenue[i] if self.inputs.revenue else 0
            gp = self.inputs.gross_profit[i] if self.inputs.gross_profit else (rev - (self.inputs.cost_of_revenue[i] if i < len(self.inputs.cost_of_revenue) else 0))
            ebitda = self.inputs.ebitda[i] if i < len(self.inputs.ebitda) else 0
            ebit = self.inputs.ebit_operating_income[i] if i < len(self.inputs.ebit_operating_income) else 0
            ni = self.inputs.net_income[i] if i < len(self.inputs.net_income) else 0
            
            self.outputs.gross_margin.append(self._safe_divide(gp, rev))
            self.outputs.ebitda_margin.append(self._safe_divide(ebitda, rev))
            self.outputs.operating_margin.append(self._safe_divide(ebit, rev))
            self.outputs.net_profit_margin.append(self._safe_divide(ni, rev))
            
            # Asset Turnover (using average assets)
            assets_curr = self.inputs.total_assets[i] if i < len(self.inputs.total_assets) else 0
            assets_prior = self.inputs.total_assets[i-1] if i > 0 and len(self.inputs.total_assets) > i-1 else None
            avg_assets = self._calculate_average(assets_curr, assets_prior)
            self.outputs.asset_turnover.append(self._safe_divide(rev, avg_assets))
            
            # Working Capital Days
            ar = self.inputs.accounts_receivable[i] if i < len(self.inputs.accounts_receivable) else 0
            inv = self.inputs.inventory[i] if i < len(self.inputs.inventory) else 0
            ap = self.inputs.accounts_payable[i] if i < len(self.inputs.accounts_payable) else 0
            cogs = self.inputs.cost_of_revenue[i] if i < len(self.inputs.cost_of_revenue) else 0
            
            ar_days = self._safe_divide(ar, rev) * 365
            inv_days = self._safe_divide(inv, cogs) * 365 if cogs > 0 else 0
            ap_days = self._safe_divide(ap, cogs) * 365 if cogs > 0 else 0
            
            self.outputs.ar_days.append(ar_days)
            self.outputs.inv_days.append(inv_days)
            self.outputs.ap_days.append(ap_days)
            self.outputs.cash_conversion_cycle.append(ar_days + inv_days - ap_days)
            
            # Liquidity & Leverage Ratios
            curr_assets = self.inputs.current_assets[i] if i < len(self.inputs.current_assets) else 0
            curr_liab = self.inputs.current_liabilities[i] if i < len(self.inputs.current_liabilities) else 0
            total_debt = self.inputs.total_debt[i] if i < len(self.inputs.total_debt) else 0
            total_eq = self.inputs.total_equity[i] if i < len(self.inputs.total_equity) else 0
            int_exp = self.inputs.interest_expense[i] if i < len(self.inputs.interest_expense) else 0
            
            self.outputs.current_ratio.append(self._safe_divide(curr_assets, curr_liab))
            self.outputs.quick_ratio.append(self._safe_divide(curr_assets - inv, curr_liab))
            self.outputs.debt_to_equity.append(self._safe_divide(total_debt, total_eq))
            self.outputs.interest_coverage.append(self._safe_divide(ebitda, int_exp))
            
            # Return Metrics
            eq_curr = self.inputs.total_equity[i] if i < len(self.inputs.total_equity) else 0
            eq_prior = self.inputs.total_equity[i-1] if i > 0 and len(self.inputs.total_equity) > i-1 else None
            avg_eq = self._calculate_average(eq_curr, eq_prior)
            
            self.outputs.roe.append(self._safe_divide(ni, avg_eq))
            self.outputs.roa.append(self._safe_divide(ni, avg_assets))
            
            # ROIC calculation (simplified)
            nopat = ebit * (1 - self._safe_divide(self.inputs.tax_provision[i] if i < len(self.inputs.tax_provision) else 0, 
                                                   self.inputs.pretax_income[i] if i < len(self.inputs.pretax_income) else 1))
            invested_capital = total_debt + total_eq
            self.outputs.roic.append(self._safe_divide(nopat, invested_capital))
            
            # Additional metrics
            goodwill = self.inputs.goodwill[i] if i < len(self.inputs.goodwill) else 0
            intangibles = self.inputs.intangible_assets[i] if i < len(self.inputs.intangible_assets) else 0
            tangible_eq = total_eq - goodwill - intangibles
            self.outputs.tangible_equity_multiplier.append(self._safe_divide(assets_curr, tangible_eq))
            self.outputs.financial_leverage.append(self._safe_divide(assets_curr, avg_eq))
    
    def calculate_dupont_3step(self):
        """
        3-Step DuPont Analysis:
        ROE = Net Profit Margin × Asset Turnover × Equity Multiplier
        """
        n = len(self.inputs.revenue)
        
        for i in range(n):
            ni = self.inputs.net_income[i] if i < len(self.inputs.net_income) else 0
            rev = self.inputs.revenue[i] if i < len(self.inputs.revenue) else 0
            assets_curr = self.inputs.total_assets[i] if i < len(self.inputs.total_assets) else 0
            assets_prior = self.inputs.total_assets[i-1] if i > 0 and len(self.inputs.total_assets) > i-1 else None
            avg_assets = self._calculate_average(assets_curr, assets_prior)
            eq_curr = self.inputs.total_equity[i] if i < len(self.inputs.total_equity) else 0
            eq_prior = self.inputs.total_equity[i-1] if i > 0 and len(self.inputs.total_equity) > i-1 else None
            avg_eq = self._calculate_average(eq_curr, eq_prior)
            
            net_margin = self._safe_divide(ni, rev)
            asset_turnover = self._safe_divide(rev, avg_assets)
            equity_multiplier = self._safe_divide(avg_assets, avg_eq)
            
            roe_reconciled = net_margin * asset_turnover * equity_multiplier
            
            self.outputs.dupont_3step_net_margin.append(net_margin)
            self.outputs.dupont_3step_asset_turnover.append(asset_turnover)
            self.outputs.dupont_3step_equity_multiplier.append(equity_multiplier)
            self.outputs.dupont_3step_roe_reconciled.append(roe_reconciled)
    
    def calculate_dupont_5step(self):
        """
        5-Step DuPont Analysis:
        ROE = Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Equity Multiplier
        """
        n = len(self.inputs.revenue)
        
        for i in range(n):
            ni = self.inputs.net_income[i] if i < len(self.inputs.net_income) else 0
            ebt = self.inputs.pretax_income[i] if i < len(self.inputs.pretax_income) else 0
            ebit = self.inputs.ebit_operating_income[i] if i < len(self.inputs.ebit_operating_income) else 0
            rev = self.inputs.revenue[i] if i < len(self.inputs.revenue) else 0
            assets_curr = self.inputs.total_assets[i] if i < len(self.inputs.total_assets) else 0
            assets_prior = self.inputs.total_assets[i-1] if i > 0 and len(self.inputs.total_assets) > i-1 else None
            avg_assets = self._calculate_average(assets_curr, assets_prior)
            eq_curr = self.inputs.total_equity[i] if i < len(self.inputs.total_equity) else 0
            eq_prior = self.inputs.total_equity[i-1] if i > 0 and len(self.inputs.total_equity) > i-1 else None
            avg_eq = self._calculate_average(eq_curr, eq_prior)
            
            tax_burden = self._safe_divide(ni, ebt)
            interest_burden = self._safe_divide(ebt, ebit)
            ebit_margin = self._safe_divide(ebit, rev)
            asset_turnover = self._safe_divide(rev, avg_assets)
            equity_multiplier = self._safe_divide(avg_assets, avg_eq)
            
            roe_reconciled = tax_burden * interest_burden * ebit_margin * asset_turnover * equity_multiplier
            
            self.outputs.dupont_5step_tax_burden.append(tax_burden)
            self.outputs.dupont_5step_interest_burden.append(interest_burden)
            self.outputs.dupont_5step_ebit_margin.append(ebit_margin)
            self.outputs.dupont_5step_asset_turnover.append(asset_turnover)
            self.outputs.dupont_5step_equity_multiplier.append(equity_multiplier)
            self.outputs.dupont_5step_roe_reconciled.append(roe_reconciled)
    
    def calculate_growth_trends(self):
        """Calculate growth rates and leverage degrees."""
        n = len(self.inputs.revenue)
        
        for i in range(n):
            # Revenue Growth
            if i == 0:
                self.outputs.revenue_growth.append(None)
                self.outputs.ebitda_growth.append(None)
                self.outputs.net_income_growth.append(None)
                self.outputs.dol.append(None)
                self.outputs.dfl.append(None)
                self.outputs.dtl.append(None)
            else:
                rev_curr = self.inputs.revenue[i]
                rev_prior = self.inputs.revenue[i-1]
                rev_growth = self._safe_divide(rev_curr - rev_prior, rev_prior)
                self.outputs.revenue_growth.append(rev_growth)
                
                ebitda_curr = self.inputs.ebitda[i] if i < len(self.inputs.ebitda) else 0
                ebitda_prior = self.inputs.ebitda[i-1] if i-1 < len(self.inputs.ebitda) else 0
                self.outputs.ebitda_growth.append(self._safe_divide(ebitda_curr - ebitda_prior, ebitda_prior))
                
                ni_curr = self.inputs.net_income[i]
                ni_prior = self.inputs.net_income[i-1]
                self.outputs.net_income_growth.append(self._safe_divide(ni_curr - ni_prior, ni_prior))
                
                # Degree of Operating Leverage = %ΔEBIT / %ΔRevenue
                ebit_curr = self.inputs.ebit_operating_income[i] if i < len(self.inputs.ebit_operating_income) else 0
                ebit_prior = self.inputs.ebit_operating_income[i-1] if i-1 < len(self.inputs.ebit_operating_income) else 0
                ebit_growth = self._safe_divide(ebit_curr - ebit_prior, ebit_prior)
                self.outputs.dol.append(self._safe_divide(ebit_growth, rev_growth) if rev_growth != 0 else None)
                
                # Degree of Financial Leverage = %ΔNet Income / %ΔEBIT
                self.outputs.dfl.append(self._safe_divide(self.outputs.net_income_growth[i], ebit_growth) if ebit_growth != 0 else None)
                
                # Degree of Total Leverage = DOL × DFL
                dol = self.outputs.dol[i]
                dfl = self.outputs.dfl[i]
                self.outputs.dtl.append(dol * dfl if dol is not None and dfl is not None else None)
    
    def validate_results(self):
        """Validate DuPont calculations match direct ROE calculations."""
        n = len(self.inputs.revenue)
        
        for i in range(n):
            direct_roe = self.outputs.roe[i] if i < len(self.outputs.roe) else 0
            roe_3step = self.outputs.dupont_3step_roe_reconciled[i] if i < len(self.outputs.dupont_3step_roe_reconciled) else 0
            roe_5step = self.outputs.dupont_5step_roe_reconciled[i] if i < len(self.outputs.dupont_5step_roe_reconciled) else 0
            
            # Allow small floating point differences
            tolerance = 0.0001
            self.outputs.roe_3step_matches_direct.append(abs(direct_roe - roe_3step) < tolerance)
            self.outputs.roe_5step_matches_direct.append(abs(direct_roe - roe_5step) < tolerance)
    
    def calculate_peer_comparison(self):
        """Calculate peer benchmarking metrics if peer data is available."""
        if not self.inputs.peer_roe_values:
            return
        
        # Calculate medians
        sorted_peers = sorted(self.inputs.peer_roe_values)
        n = len(sorted_peers)
        self.outputs.peer_roe_median = sorted_peers[n//2] if n % 2 == 1 else (sorted_peers[n//2-1] + sorted_peers[n//2]) / 2
        
        # Similar calculations for other metrics
        if self.inputs.peer_roa_values:
            sorted_peers = sorted(self.inputs.peer_roa_values)
            n = len(sorted_peers)
            self.outputs.peer_roa_median = sorted_peers[n//2] if n % 2 == 1 else (sorted_peers[n//2-1] + sorted_peers[n//2]) / 2
        
        if self.inputs.peer_net_margin_values:
            sorted_peers = sorted(self.inputs.peer_net_margin_values)
            n = len(sorted_peers)
            self.outputs.peer_net_margin_median = sorted_peers[n//2] if n % 2 == 1 else (sorted_peers[n//2-1] + sorted_peers[n//2]) / 2
        
        # Compare target vs peers
        for roe in self.outputs.roe:
            if self.outputs.peer_roe_median and roe is not None:
                self.outputs.target_vs_peer_roe.append(roe - self.outputs.peer_roe_median)
            else:
                self.outputs.target_vs_peer_roe.append(None)
    
    def run_analysis(self) -> DuPontOutputs:
        """Execute complete DuPont analysis."""
        # Validate inputs first
        self.validation_results = self.inputs.validate_inputs()
        
        if not self.validation_results['valid']:
            raise ValueError(f"Input validation failed: {self.validation_results['errors']}")
        
        # Set metadata
        self.outputs.years_analyzed = len(self.inputs.revenue)
        self.outputs.currency = self.inputs.currency
        self.outputs.calculation_timestamp = datetime.now().isoformat()
        self.outputs.data_source = "yfinance"  # Can be updated based on actual source
        
        # Generate period labels
        current_year = datetime.now().year
        self.outputs.periods = [f"FY{current_year - self.outputs.years_analyzed + i}" for i in range(self.outputs.years_analyzed)]
        
        # Run all calculations
        self.calculate_supporting_ratios()
        self.calculate_dupont_3step()
        self.calculate_dupont_5step()
        self.calculate_growth_trends()
        self.validate_results()
        self.calculate_peer_comparison()
        
        return self.outputs


def analyze_dupont(ticker: str, historical_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function to run DuPont analysis for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        historical_data: Optional dict with historical financial data
        
    Returns:
        Dictionary containing complete DuPont analysis results
    """
    # In production, fetch data from yfinance or other API
    # For now, create placeholder inputs
    inputs = DuPontInputs(
        ticker=ticker,
        company_name="",
        revenue=[1000, 1100, 1200, 1300],
        cost_of_revenue=[600, 650, 700, 750],
        gross_profit=[400, 450, 500, 550],
        operating_expenses=[200, 210, 220, 230],
        ebitda=[250, 280, 310, 340],
        depreciation_amortization=[50, 55, 60, 65],
        ebit_operating_income=[200, 225, 250, 275],
        interest_expense=[20, 22, 24, 26],
        pretax_income=[180, 203, 226, 249],
        tax_provision=[36, 41, 45, 50],
        net_income=[144, 162, 181, 199],
        total_assets=[2000, 2200, 2400, 2600],
        current_assets=[800, 880, 960, 1040],
        accounts_receivable=[200, 220, 240, 260],
        inventory=[150, 165, 180, 195],
        cash_and_equivalents=[100, 110, 120, 130],
        total_liabilities=[1200, 1300, 1400, 1500],
        current_liabilities=[400, 440, 480, 520],
        accounts_payable=[180, 198, 216, 234],
        total_debt=[600, 650, 700, 750],
        total_equity=[800, 900, 1000, 1100],
        goodwill=[50, 50, 50, 50],
        intangible_assets=[30, 30, 30, 30],
    )
    
    analyzer = DuPontAnalyzer(inputs)
    outputs = analyzer.run_analysis()
    
    return outputs.to_dict()


if __name__ == "__main__":
    # Example usage
    result = analyze_dupont("AAPL")
    print(json.dumps(result, indent=2))
