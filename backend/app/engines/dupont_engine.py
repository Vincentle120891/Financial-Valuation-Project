"""
DuPont Analysis Engine - 3-Step and 5-Step ROE Decomposition

Based on MID RETAILER FINANCIAL ANALYSIS Excel model.
All figures in USD millions unless stated.
"""

from dataclasses import dataclass, field
from typing import Optional
import math


@dataclass
class FinancialStatements:
    """8-year financial statements data."""
    
    # Income Statement (rows 8-30)
    revenue: list[float] = field(default_factory=lambda: [0.0] * 8)
    cogs_gross: list[float] = field(default_factory=lambda: [0.0] * 8)  # Negative gross COGS
    depreciation_cogs: list[float] = field(default_factory=lambda: [0.0] * 8)  # Positive component in COGS
    sga: list[float] = field(default_factory=lambda: [0.0] * 8)  # Negative
    other_operating_expenses: list[float] = field(default_factory=lambda: [0.0] * 8)  # Negative
    depreciation: list[float] = field(default_factory=lambda: [0.0] * 8)  # Negative
    interest_expense: list[float] = field(default_factory=lambda: [0.0] * 8)  # Negative
    interest_income: list[float] = field(default_factory=lambda: [0.0] * 8)  # Positive
    tax_current: list[float] = field(default_factory=lambda: [0.0] * 8)  # Negative
    tax_other: list[float] = field(default_factory=lambda: [0.0] * 8)  # Negative
    
    # Balance Sheet (rows 74-107)
    cash: list[float] = field(default_factory=lambda: [0.0] * 8)
    accounts_receivable: list[float] = field(default_factory=lambda: [0.0] * 8)
    inventories: list[float] = field(default_factory=lambda: [0.0] * 8)
    ppe_component1: list[float] = field(default_factory=lambda: [0.0] * 8)
    ppe_component2: list[float] = field(default_factory=lambda: [0.0] * 8)
    accounts_payable: list[float] = field(default_factory=lambda: [0.0] * 8)
    revolving_credit: list[float] = field(default_factory=lambda: [0.0] * 8)
    long_term_debt: list[float] = field(default_factory=lambda: [0.0] * 8)
    common_equity: list[float] = field(default_factory=lambda: [0.0] * 8)
    retained_earnings: list[float] = field(default_factory=lambda: [0.0] * 8)
    
    # Cash Flow Statement (rows 40-65)
    capex: list[float] = field(default_factory=lambda: [0.0] * 8)  # Negative
    change_in_ltd: list[float] = field(default_factory=lambda: [0.0] * 8)
    change_in_common_equity: list[float] = field(default_factory=lambda: [0.0] * 8)
    dividends: list[float] = field(default_factory=lambda: [0.0] * 8)  # Negative
    beginning_cash: list[float] = field(default_factory=lambda: [0.0] * 8)


@dataclass
class DerivedMetrics:
    """Derived financial metrics (Section 1D)."""
    
    # Calculated fields
    net_cogs: list[float] = field(default_factory=lambda: [0.0] * 8)
    gross_profit: list[float] = field(default_factory=lambda: [0.0] * 8)
    ebitda: list[float] = field(default_factory=lambda: [0.0] * 8)
    ebit: list[float] = field(default_factory=lambda: [0.0] * 8)
    ebt: list[float] = field(default_factory=lambda: [0.0] * 8)
    net_income: list[float] = field(default_factory=lambda: [0.0] * 8)
    tax_provision: list[float] = field(default_factory=lambda: [0.0] * 8)
    
    # Supplemental metrics
    nopat: list[float] = field(default_factory=lambda: [0.0] * 8)
    effective_tax_rate: list[float] = field(default_factory=lambda: [0.0] * 8)
    total_current_assets: list[float] = field(default_factory=lambda: [0.0] * 8)
    ppe_total: list[float] = field(default_factory=lambda: [0.0] * 8)
    total_assets: list[float] = field(default_factory=lambda: [0.0] * 8)
    total_current_liabilities: list[float] = field(default_factory=lambda: [0.0] * 8)
    total_liabilities: list[float] = field(default_factory=lambda: [0.0] * 8)
    total_equity: list[float] = field(default_factory=lambda: [0.0] * 8)
    total_liabilities_and_equity: list[float] = field(default_factory=lambda: [0.0] * 8)
    
    # Invested Capital components
    interest_bearing_current_liabilities: list[float] = field(default_factory=lambda: [0.0] * 8)
    interest_bearing_lt_liabilities: list[float] = field(default_factory=lambda: [0.0] * 8)
    total_interest_bearing_liabilities: list[float] = field(default_factory=lambda: [0.0] * 8)
    net_debt: list[float] = field(default_factory=lambda: [0.0] * 8)
    invested_capital: list[float] = field(default_factory=lambda: [0.0] * 8)
    
    # Net Assets components
    net_assets: list[float] = field(default_factory=lambda: [0.0] * 8)


@dataclass
class RatioCalculations:
    """All ratio calculations (Section 2)."""
    
    # Profitability and Return Ratios (2A)
    roe: list[float] = field(default_factory=lambda: [0.0] * 8)
    roa: list[float] = field(default_factory=lambda: [0.0] * 8)
    rona: list[float] = field(default_factory=lambda: [0.0] * 8)
    roic: list[float] = field(default_factory=lambda: [0.0] * 8)
    
    # Margin ratios
    gross_margin: list[float] = field(default_factory=lambda: [0.0] * 8)
    sga_percent_revenue: list[float] = field(default_factory=lambda: [0.0] * 8)
    other_opex_percent_revenue: list[float] = field(default_factory=lambda: [0.0] * 8)
    ebitda_margin: list[float] = field(default_factory=lambda: [0.0] * 8)
    depreciation_percent_revenue: list[float] = field(default_factory=lambda: [0.0] * 8)
    ebit_margin: list[float] = field(default_factory=lambda: [0.0] * 8)
    net_finance_cost_percent: list[float] = field(default_factory=lambda: [0.0] * 8)
    ebt_margin: list[float] = field(default_factory=lambda: [0.0] * 8)
    tax_percent_revenue: list[float] = field(default_factory=lambda: [0.0] * 8)
    net_profit_margin: list[float] = field(default_factory=lambda: [0.0] * 8)
    
    # DuPont component ratios
    effective_tax_rate_ratio: list[float] = field(default_factory=lambda: [0.0] * 8)
    tax_burden: list[float] = field(default_factory=lambda: [0.0] * 8)
    effective_interest_rate: list[float] = field(default_factory=lambda: [0.0] * 8)
    interest_burden: list[float] = field(default_factory=lambda: [0.0] * 8)
    
    # Asset Utilization Ratios (2B)
    asset_turnover: list[float] = field(default_factory=lambda: [0.0] * 8)
    ppe_turnover: list[float] = field(default_factory=lambda: [0.0] * 8)
    cash_turnover: list[float] = field(default_factory=lambda: [0.0] * 8)
    cash_days: list[float] = field(default_factory=lambda: [0.0] * 8)
    ar_turnover: list[float] = field(default_factory=lambda: [0.0] * 8)
    ar_days_dso: list[float] = field(default_factory=lambda: [0.0] * 8)
    inventory_turnover: list[float] = field(default_factory=lambda: [0.0] * 8)
    inventory_days_dio: list[float] = field(default_factory=lambda: [0.0] * 8)
    ap_turnover: list[float] = field(default_factory=lambda: [0.0] * 8)
    ap_days_dpo: list[float] = field(default_factory=lambda: [0.0] * 8)
    cash_conversion_cycle: list[float] = field(default_factory=lambda: [0.0] * 8)
    
    # Leverage Ratios (2C)
    total_assets_to_equity: list[float] = field(default_factory=lambda: [0.0] * 8)
    total_liabilities_to_equity: list[float] = field(default_factory=lambda: [0.0] * 8)
    debt_to_equity: list[float] = field(default_factory=lambda: [0.0] * 8)
    debt_to_ebitda: list[float] = field(default_factory=lambda: [0.0] * 8)
    net_debt_to_ebitda: list[float] = field(default_factory=lambda: [0.0] * 8)
    
    # Liquidity Ratios (2D)
    current_ratio: list[float] = field(default_factory=lambda: [0.0] * 8)
    quick_ratio: list[float] = field(default_factory=lambda: [0.0] * 8)
    interest_coverage: list[float] = field(default_factory=lambda: [0.0] * 8)
    
    # Growth Trends (2E) - starts from Year 2 (index 1)
    revenue_growth: list[float] = field(default_factory=lambda: [0.0] * 8)
    ebitda_growth: list[float] = field(default_factory=lambda: [0.0] * 8)
    ebit_growth: list[float] = field(default_factory=lambda: [0.0] * 8)
    net_income_growth: list[float] = field(default_factory=lambda: [0.0] * 8)
    total_asset_growth: list[float] = field(default_factory=lambda: [0.0] * 8)
    dol: list[float] = field(default_factory=lambda: [0.0] * 8)  # Degree of Operating Leverage
    dfl: list[float] = field(default_factory=lambda: [0.0] * 8)  # Degree of Financial Leverage
    dtl: list[float] = field(default_factory=lambda: [0.0] * 8)  # Degree of Total Leverage
    
    # DuPont Checks (2F)
    roe_3step: list[float] = field(default_factory=lambda: [0.0] * 8)
    roe_3step_check: list[bool] = field(default_factory=lambda: [False] * 8)
    roe_5step: list[float] = field(default_factory=lambda: [0.0] * 8)
    roe_5step_check: list[bool] = field(default_factory=lambda: [False] * 8)


@dataclass
class DuPontResult:
    """Complete DuPont analysis result."""
    
    financial_statements: FinancialStatements
    derived_metrics: DerivedMetrics
    ratios: RatioCalculations
    years: list[str] = field(default_factory=lambda: [f"Year {i+1}" for i in range(8)])
    validation_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert result to dictionary for API response."""
        return {
            "years": self.years,
            "financial_statements": {
                "income_statement": {
                    "revenue": self.financial_statements.revenue,
                    "gross_profit": self.derived_metrics.gross_profit,
                    "ebitda": self.derived_metrics.ebitda,
                    "ebit": self.derived_metrics.ebit,
                    "ebt": self.derived_metrics.ebt,
                    "net_income": self.derived_metrics.net_income,
                },
                "balance_sheet": {
                    "total_assets": self.derived_metrics.total_assets,
                    "total_equity": self.derived_metrics.total_equity,
                    "total_liabilities": self.derived_metrics.total_liabilities,
                    "cash": self.financial_statements.cash,
                    "net_debt": self.derived_metrics.net_debt,
                },
                "cash_flow": {
                    "capex": self.financial_statements.capex,
                }
            },
            "ratios": {
                "profitability": {
                    "roe": self.ratios.roe,
                    "roa": self.ratios.roa,
                    "rona": self.ratios.rona,
                    "roic": self.ratios.roic,
                },
                "margins": {
                    "gross_margin": self.ratios.gross_margin,
                    "ebitda_margin": self.ratios.ebitda_margin,
                    "ebit_margin": self.ratios.ebit_margin,
                    "net_profit_margin": self.ratios.net_profit_margin,
                },
                "dupont_3step": {
                    "net_profit_margin": self.ratios.net_profit_margin,
                    "asset_turnover": self.ratios.asset_turnover,
                    "asset_to_equity": self.ratios.total_assets_to_equity,
                    "roe_calculated": self.ratios.roe_3step,
                    "check_passed": self.ratios.roe_3step_check,
                },
                "dupont_5step": {
                    "tax_burden": self.ratios.tax_burden,
                    "interest_burden": self.ratios.interest_burden,
                    "ebit_margin": self.ratios.ebit_margin,
                    "asset_turnover": self.ratios.asset_turnover,
                    "asset_to_equity": self.ratios.total_assets_to_equity,
                    "roe_calculated": self.ratios.roe_5step,
                    "check_passed": self.ratios.roe_5step_check,
                },
                "asset_utilization": {
                    "asset_turnover": self.ratios.asset_turnover,
                    "inventory_turnover": self.ratios.inventory_turnover,
                    "ar_turnover": self.ratios.ar_turnover,
                    "ap_turnover": self.ratios.ap_turnover,
                    "cash_conversion_cycle": self.ratios.cash_conversion_cycle,
                },
                "leverage": {
                    "debt_to_equity": self.ratios.debt_to_equity,
                    "debt_to_ebitda": self.ratios.debt_to_ebitda,
                    "net_debt_to_ebitda": self.ratios.net_debt_to_ebitda,
                    "interest_coverage": self.ratios.interest_coverage,
                },
                "liquidity": {
                    "current_ratio": self.ratios.current_ratio,
                    "quick_ratio": self.ratios.quick_ratio,
                },
                "growth": {
                    "revenue_growth": self.ratios.revenue_growth,
                    "ebitda_growth": self.ratios.ebitda_growth,
                    "ebit_growth": self.ratios.ebit_growth,
                    "net_income_growth": self.ratios.net_income_growth,
                    "dol": self.ratios.dol,
                    "dfl": self.ratios.dfl,
                    "dtl": self.ratios.dtl,
                }
            },
            "validation_errors": self.validation_errors,
            "warnings": self.warnings,
        }


class DuPontAnalyzer:
    """
    DuPont Analysis Engine implementing 3-step and 5-step ROE decomposition.
    
    Follows the exact calculation methodology from the MID RETAILER Excel model.
    """
    
    def __init__(self):
        self.statements: Optional[FinancialStatements] = None
        self.metrics: Optional[DerivedMetrics] = None
        self.ratios: Optional[RatioCalculations] = None
        self.validation_errors: list[str] = []
        self.warnings: list[str] = []
    
    def load_data(self, statements: FinancialStatements) -> None:
        """Load financial statements data."""
        self.statements = statements
        self.validation_errors = []
        self.warnings = []
    
    def calculate_all(self) -> DuPontResult:
        """
        Perform complete DuPont analysis.
        
        Returns:
            DuPontResult with all calculated metrics and ratios
        """
        if self.statements is None:
            raise ValueError("No financial statements loaded. Call load_data() first.")
        
        # Calculate derived metrics
        self._calculate_derived_metrics()
        
        # Calculate all ratios
        self._calculate_ratios()
        
        # Validate results
        self._validate_results()
        
        return DuPontResult(
            financial_statements=self.statements,
            derived_metrics=self.metrics,
            ratios=self.ratios,
            validation_errors=self.validation_errors,
            warnings=self.warnings,
        )
    
    def _safe_divide(self, numerator: float, denominator: float, default: float = 0.0) -> float:
        """Safe division with zero handling."""
        if abs(denominator) < 1e-10:
            return default
        return numerator / denominator
    
    def _calculate_derived_metrics(self) -> None:
        """Calculate all derived financial metrics (Section 1D)."""
        self.metrics = DerivedMetrics()
        
        for i in range(8):
            # Net COGS = gross COGS + depreciation component (row 9 formula)
            self.metrics.net_cogs[i] = self.statements.cogs_gross[i] + self.statements.depreciation_cogs[i]
            
            # Gross Profit = Revenue + Net COGS (row 10)
            self.metrics.gross_profit[i] = self.statements.revenue[i] + self.metrics.net_cogs[i]
            
            # EBITDA = Gross Profit + SG&A + Other Operating Expenses (row 15)
            self.metrics.ebitda[i] = (
                self.metrics.gross_profit[i] + 
                self.statements.sga[i] + 
                self.statements.other_operating_expenses[i]
            )
            
            # Depreciation (row 18) - already negative
            depreciation = self.statements.depreciation[i]
            
            # EBIT = EBITDA + Depreciation (row 19)
            self.metrics.ebit[i] = self.metrics.ebitda[i] + depreciation
            
            # Interest Expense + Interest Income (rows 22-23)
            net_interest = self.statements.interest_expense[i] + self.statements.interest_income[i]
            
            # EBT = EBIT + Interest Expense + Interest Income (row 24)
            self.metrics.ebt[i] = self.metrics.ebit[i] + net_interest
            
            # Tax Provision = current tax + other tax (row 27)
            self.metrics.tax_provision[i] = self.statements.tax_current[i] + self.statements.tax_other[i]
            
            # Net Income = EBT + Tax Provision (row 30)
            self.metrics.net_income[i] = self.metrics.ebt[i] + self.metrics.tax_provision[i]
            
            # Effective Tax Rate = -Tax / EBT (row 118)
            self.metrics.effective_tax_rate[i] = self._safe_divide(
                -self.metrics.tax_provision[i], 
                self.metrics.ebt[i], 
                0.0
            )
            
            # NOPAT = EBIT × (1 - Effective Tax Rate) (row 119)
            self.metrics.nopat[i] = self.metrics.ebit[i] * (1 - self.metrics.effective_tax_rate[i])
            
            # Balance Sheet totals
            # Total Current Assets = Cash + AR + Inventory (row 79)
            self.metrics.total_current_assets[i] = (
                self.statements.cash[i] + 
                self.statements.accounts_receivable[i] + 
                self.statements.inventories[i]
            )
            
            # PP&E Total = component1 + component2 (row 81)
            self.metrics.ppe_total[i] = (
                self.statements.ppe_component1[i] + 
                self.statements.ppe_component2[i]
            )
            
            # Total Assets = Current Assets + PP&E (row 84)
            self.metrics.total_assets[i] = (
                self.metrics.total_current_assets[i] + 
                self.metrics.ppe_total[i]
            )
            
            # Total Current Liabilities = AP + Revolver (row 91)
            self.metrics.total_current_liabilities[i] = (
                self.statements.accounts_payable[i] + 
                self.statements.revolving_credit[i]
            )
            
            # Total Liabilities = Current Liabilities + LTD (row 94)
            self.metrics.total_liabilities[i] = (
                self.metrics.total_current_liabilities[i] + 
                self.statements.long_term_debt[i]
            )
            
            # Total Equity = Common Equity + Retained Earnings (row 101)
            self.metrics.total_equity[i] = (
                self.statements.common_equity[i] + 
                self.statements.retained_earnings[i]
            )
            
            # Total Liabilities & Equity (row 104)
            self.metrics.total_liabilities_and_equity[i] = (
                self.metrics.total_liabilities[i] + 
                self.metrics.total_equity[i]
            )
            
            # Invested Capital components (rows 121-128)
            # Interest Bearing Current Liabilities = Revolver (row 122)
            self.metrics.interest_bearing_current_liabilities[i] = self.statements.revolving_credit[i]
            
            # Interest Bearing LT Liabilities = LTD (row 123)
            self.metrics.interest_bearing_lt_liabilities[i] = self.statements.long_term_debt[i]
            
            # Total Interest Bearing Liabilities (row 124)
            self.metrics.total_interest_bearing_liabilities[i] = (
                self.metrics.interest_bearing_current_liabilities[i] + 
                self.metrics.interest_bearing_lt_liabilities[i]
            )
            
            # Net Debt = Total Interest Bearing Liabilities - Cash (row 126)
            self.metrics.net_debt[i] = (
                self.metrics.total_interest_bearing_liabilities[i] - 
                self.statements.cash[i]
            )
            
            # Invested Capital = Net Debt + Equity (row 128)
            self.metrics.invested_capital[i] = (
                self.metrics.net_debt[i] + 
                self.metrics.total_equity[i]
            )
            
            # Net Assets (rows 131-135)
            # Net Assets = (Current Assets - Cash) + PP&E - AP
            self.metrics.net_assets[i] = (
                (self.metrics.total_current_assets[i] - self.statements.cash[i]) + 
                self.metrics.ppe_total[i] - 
                self.statements.accounts_payable[i]
            )
    
    def _calculate_ratios(self) -> None:
        """Calculate all financial ratios (Section 2)."""
        self.ratios = RatioCalculations()
        
        for i in range(8):
            # === 2A. PROFITABILITY AND RETURN RATIOS ===
            
            # ROE = Net Income / Total Shareholders' Equity (row 8)
            self.ratios.roe[i] = self._safe_divide(
                self.metrics.net_income[i], 
                self.metrics.total_equity[i]
            )
            
            # ROA = Net Income / Total Assets (row 11)
            self.ratios.roa[i] = self._safe_divide(
                self.metrics.net_income[i], 
                self.metrics.total_assets[i]
            )
            
            # RONA = Net Income / Net Assets (row 14)
            self.ratios.rona[i] = self._safe_divide(
                self.metrics.net_income[i], 
                self.metrics.net_assets[i]
            )
            
            # ROIC = NOPAT / Invested Capital (row 17)
            self.ratios.roic[i] = self._safe_divide(
                self.metrics.nopat[i], 
                self.metrics.invested_capital[i]
            )
            
            # === INCOME STATEMENT MARGIN BRIDGE ===
            
            # Gross Margin = Gross Profit / Revenue (row 20)
            self.ratios.gross_margin[i] = self._safe_divide(
                self.metrics.gross_profit[i], 
                self.statements.revenue[i]
            )
            
            # SG&A % of Revenue (row 23)
            self.ratios.sga_percent_revenue[i] = self._safe_divide(
                self.statements.sga[i], 
                self.statements.revenue[i]
            )
            
            # Other OpEx % of Revenue (row 26)
            self.ratios.other_opex_percent_revenue[i] = self._safe_divide(
                self.statements.other_operating_expenses[i], 
                self.statements.revenue[i]
            )
            
            # EBITDA Margin = EBITDA / Revenue (row 29)
            self.ratios.ebitda_margin[i] = self._safe_divide(
                self.metrics.ebitda[i], 
                self.statements.revenue[i]
            )
            
            # Depreciation % Revenue (row 33)
            self.ratios.depreciation_percent_revenue[i] = self._safe_divide(
                self.statements.depreciation[i], 
                self.statements.revenue[i]
            )
            
            # EBIT Margin = EBIT / Revenue (row 36)
            self.ratios.ebit_margin[i] = self._safe_divide(
                self.metrics.ebit[i], 
                self.statements.revenue[i]
            )
            
            # Net Finance Cost % = -(Interest Expense + Interest Income) / Revenue (row 40)
            net_finance = -(self.statements.interest_expense[i] + self.statements.interest_income[i])
            self.ratios.net_finance_cost_percent[i] = self._safe_divide(
                net_finance, 
                self.statements.revenue[i]
            )
            
            # EBT Margin = EBT / Revenue (row 44)
            self.ratios.ebt_margin[i] = self._safe_divide(
                self.metrics.ebt[i], 
                self.statements.revenue[i]
            )
            
            # Tax % of Revenue (row 48)
            self.ratios.tax_percent_revenue[i] = self._safe_divide(
                self.metrics.tax_provision[i], 
                self.statements.revenue[i]
            )
            
            # Net Profit Margin = Net Income / Revenue (row 51)
            self.ratios.net_profit_margin[i] = self._safe_divide(
                self.metrics.net_income[i], 
                self.statements.revenue[i]
            )
            
            # === DUPONT COMPONENT RATIOS ===
            
            # Effective Tax Rate = Tax / EBT (row 55)
            self.ratios.effective_tax_rate_ratio[i] = self._safe_divide(
                self.metrics.tax_provision[i], 
                self.metrics.ebt[i]
            )
            
            # Tax Burden = Net Income / EBT (row 58)
            self.ratios.tax_burden[i] = self._safe_divide(
                self.metrics.net_income[i], 
                self.metrics.ebt[i]
            )
            
            # Effective Interest Rate = Interest Expense / Total Interest Bearing Liabilities (row 61)
            self.ratios.effective_interest_rate[i] = self._safe_divide(
                self.statements.interest_expense[i], 
                self.metrics.total_interest_bearing_liabilities[i]
            )
            
            # Interest Burden = EBT / EBIT (row 64)
            # Note: This shows how much EBIT survives after interest (before tax)
            self.ratios.interest_burden[i] = self._safe_divide(
                self.metrics.ebt[i], 
                self.metrics.ebit[i]
            )
            
            # === 2B. ASSET UTILIZATION RATIOS ===
            
            # Asset Turnover = Revenue / Total Assets (row 73)
            self.ratios.asset_turnover[i] = self._safe_divide(
                self.statements.revenue[i], 
                self.metrics.total_assets[i]
            )
            
            # PPE Turnover = Revenue / PP&E (row 76)
            self.ratios.ppe_turnover[i] = self._safe_divide(
                self.statements.revenue[i], 
                self.metrics.ppe_total[i]
            )
            
            # Cash Turnover = Revenue / Cash (row 79)
            self.ratios.cash_turnover[i] = self._safe_divide(
                self.statements.revenue[i], 
                self.statements.cash[i]
            )
            
            # Cash Days = (Cash × 365) / Revenue (row 82)
            self.ratios.cash_days[i] = self._safe_divide(
                self.statements.cash[i] * 365, 
                self.statements.revenue[i]
            )
            
            # A/R Turnover = Revenue / Accounts Receivable (row 85)
            self.ratios.ar_turnover[i] = self._safe_divide(
                self.statements.revenue[i], 
                self.statements.accounts_receivable[i]
            )
            
            # A/R Days (DSO) = (AR × 365) / Revenue (row 88)
            self.ratios.ar_days_dso[i] = self._safe_divide(
                self.statements.accounts_receivable[i] * 365, 
                self.statements.revenue[i]
            )
            
            # Inventory Turnover = COGS / Inventory (row 91)
            # Note: Using absolute value of net COGS
            self.ratios.inventory_turnover[i] = self._safe_divide(
                abs(self.metrics.net_cogs[i]), 
                self.statements.inventories[i]
            )
            
            # Inventory Days (DIO) = (Inventory × 365) / COGS (row 94)
            self.ratios.inventory_days_dio[i] = self._safe_divide(
                self.statements.inventories[i] * 365, 
                abs(self.metrics.net_cogs[i])
            )
            
            # A/P Turnover = COGS / Accounts Payable (row 97)
            self.ratios.ap_turnover[i] = self._safe_divide(
                abs(self.metrics.net_cogs[i]), 
                self.statements.accounts_payable[i]
            )
            
            # A/P Days (DPO) = (AP × 365) / COGS (row 100)
            self.ratios.ap_days_dpo[i] = self._safe_divide(
                self.statements.accounts_payable[i] * 365, 
                abs(self.metrics.net_cogs[i])
            )
            
            # Cash Conversion Cycle = DSO + DIO - DPO (row 103)
            self.ratios.cash_conversion_cycle[i] = (
                self.ratios.ar_days_dso[i] + 
                self.ratios.inventory_days_dio[i] - 
                self.ratios.ap_days_dpo[i]
            )
            
            # === 2C. LEVERAGE RATIOS ===
            
            # Total Assets to Equity (row 111)
            self.ratios.total_assets_to_equity[i] = self._safe_divide(
                self.metrics.total_assets[i], 
                self.metrics.total_equity[i]
            )
            
            # Total Liabilities to Equity (row 114)
            self.ratios.total_liabilities_to_equity[i] = self._safe_divide(
                self.metrics.total_liabilities[i], 
                self.metrics.total_equity[i]
            )
            
            # Debt to Equity = (Revolver + LTD) / Equity (row 117)
            total_debt = self.statements.revolving_credit[i] + self.statements.long_term_debt[i]
            self.ratios.debt_to_equity[i] = self._safe_divide(
                total_debt, 
                self.metrics.total_equity[i]
            )
            
            # Debt to EBITDA (row 120)
            self.ratios.debt_to_ebitda[i] = self._safe_divide(
                total_debt, 
                self.metrics.ebitda[i]
            )
            
            # Net Debt to EBITDA (row 123)
            self.ratios.net_debt_to_ebitda[i] = self._safe_divide(
                self.metrics.net_debt[i], 
                self.metrics.ebitda[i]
            )
            
            # === 2D. LIQUIDITY RATIOS ===
            
            # Current Ratio = Current Assets / Current Liabilities (row 132)
            self.ratios.current_ratio[i] = self._safe_divide(
                self.metrics.total_current_assets[i], 
                self.metrics.total_current_liabilities[i]
            )
            
            # Quick Ratio = (Current Assets - Inventory) / Current Liabilities (row 135)
            self.ratios.quick_ratio[i] = self._safe_divide(
                self.metrics.total_current_assets[i] - self.statements.inventories[i], 
                self.metrics.total_current_liabilities[i]
            )
            
            # Interest Coverage = EBITDA / Interest Expense (row 138)
            self.ratios.interest_coverage[i] = self._safe_divide(
                self.metrics.ebitda[i], 
                self.statements.interest_expense[i]
            )
            
            # === 2E. GROWTH TRENDS (starts from Year 2, index 1) ===
            if i > 0:
                # Revenue Growth = (Current - Prior) / Prior (row 147)
                self.ratios.revenue_growth[i] = self._safe_divide(
                    self.statements.revenue[i] - self.statements.revenue[i-1], 
                    self.statements.revenue[i-1]
                )
                
                # EBITDA Growth (row 150)
                self.ratios.ebitda_growth[i] = self._safe_divide(
                    self.metrics.ebitda[i] - self.metrics.ebitda[i-1], 
                    self.metrics.ebitda[i-1]
                )
                
                # EBIT Growth (row 153)
                self.ratios.ebit_growth[i] = self._safe_divide(
                    self.metrics.ebit[i] - self.metrics.ebit[i-1], 
                    self.metrics.ebit[i-1]
                )
                
                # Net Income Growth (row 156)
                self.ratios.net_income_growth[i] = self._safe_divide(
                    self.metrics.net_income[i] - self.metrics.net_income[i-1], 
                    self.metrics.net_income[i-1]
                )
                
                # Total Asset Growth (row 159)
                self.ratios.total_asset_growth[i] = self._safe_divide(
                    self.metrics.total_assets[i] - self.metrics.total_assets[i-1], 
                    self.metrics.total_assets[i-1]
                )
                
                # Degree of Operating Leverage (DOL) = %ΔEBIT / %ΔRevenue (row 162)
                if abs(self.ratios.revenue_growth[i]) > 1e-10:
                    self.ratios.dol[i] = self.ratios.ebit_growth[i] / self.ratios.revenue_growth[i]
                
                # Degree of Financial Leverage (DFL) = %ΔNet Income / %ΔEBIT (row 165)
                if abs(self.ratios.ebit_growth[i]) > 1e-10:
                    self.ratios.dfl[i] = self.ratios.net_income_growth[i] / self.ratios.ebit_growth[i]
                
                # Degree of Total Leverage (DTL) = %ΔNet Income / %ΔRevenue (row 168)
                if abs(self.ratios.revenue_growth[i]) > 1e-10:
                    self.ratios.dtl[i] = self.ratios.net_income_growth[i] / self.ratios.revenue_growth[i]
            
            # === 2F. DUPONT CHECKS ===
            
            # 3-Step DuPont: ROE = Net Profit Margin × Asset Turnover × Asset to Equity
            self.ratios.roe_3step[i] = (
                self.ratios.net_profit_margin[i] * 
                self.ratios.asset_turnover[i] * 
                self.ratios.total_assets_to_equity[i]
            )
            
            # Check if 3-step matches actual ROE (within 0.0001 tolerance)
            self.ratios.roe_3step_check[i] = abs(self.ratios.roe_3step[i] - self.ratios.roe[i]) < 0.0001
            
            # 5-Step DuPont: ROE = Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Asset to Equity
            self.ratios.roe_5step[i] = (
                self.ratios.tax_burden[i] * 
                self.ratios.interest_burden[i] * 
                self.ratios.ebit_margin[i] * 
                self.ratios.asset_turnover[i] * 
                self.ratios.total_assets_to_equity[i]
            )
            
            # Check if 5-step matches actual ROE (within 0.0001 tolerance)
            self.ratios.roe_5step_check[i] = abs(self.ratios.roe_5step[i] - self.ratios.roe[i]) < 0.0001
    
    def _validate_results(self) -> None:
        """Validate calculation results and add warnings/errors."""
        
        # Check balance sheet balancing
        for i in range(8):
            balance_check = self.metrics.total_assets[i] - self.metrics.total_liabilities_and_equity[i]
            if abs(balance_check) > 0.01:  # Allow small rounding differences
                self.validation_errors.append(
                    f"Year {i+1}: Balance sheet does not balance. Difference: {balance_check:.2f}"
                )
        
        # Check DuPont identity validations
        for i in range(8):
            if not self.ratios.roe_3step_check[i]:
                self.warnings.append(
                    f"Year {i+1}: 3-step DuPont check failed. "
                    f"ROE={self.ratios.roe[i]:.4f}, Calculated={self.ratios.roe_3step[i]:.4f}"
                )
            
            if not self.ratios.roe_5step_check[i]:
                self.warnings.append(
                    f"Year {i+1}: 5-step DuPont check failed. "
                    f"ROE={self.ratios.roe[i]:.4f}, Calculated={self.ratios.roe_5step[i]:.4f}"
                )
        
        # Check for negative equity
        for i in range(8):
            if self.metrics.total_equity[i] < 0:
                self.warnings.append(f"Year {i+1}: Negative shareholders' equity detected")
        
        # Check for negative EBITDA
        for i in range(8):
            if self.metrics.ebitda[i] < 0:
                self.warnings.append(f"Year {i+1}: Negative EBITDA detected")
        
        # Check interest coverage
        for i in range(8):
            if self.ratios.interest_coverage[i] < 1.0:
                self.warnings.append(
                    f"Year {i+1}: Low interest coverage ({self.ratios.interest_coverage[i]:.2f}x). "
                    "Company may struggle to meet interest obligations."
                )
        
        # Check debt levels
        for i in range(8):
            if self.ratios.debt_to_ebitda[i] > 5.0:
                self.warnings.append(
                    f"Year {i+1}: High debt-to-EBITDA ratio ({self.ratios.debt_to_ebitda[i]:.2f}x)"
                )
        
        # Check cash conversion cycle
        for i in range(8):
            if self.ratios.cash_conversion_cycle[i] > 90:
                self.warnings.append(
                    f"Year {i+1}: Long cash conversion cycle ({self.ratios.cash_conversion_cycle[i]:.1f} days)"
                )
