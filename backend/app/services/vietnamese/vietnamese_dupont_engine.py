"""
Vietnamese DuPont Analysis Engine - 3-Step and 5-Step ROE Decomposition

Based on MID RETAILER FINANCIAL ANALYSIS Excel model, adapted for Vietnamese market.
All figures in VND millions unless stated.

Vietnam-Specific Adaptations:
- TT99/VAS accounting standards compliance
- VND currency handling
- FOL (Foreign Ownership Limit) tracking
- State ownership considerations
- Vietnamese corporate tax rate (20%)
- Local market characteristics
"""

from dataclasses import dataclass, field
from typing import Optional
import math


@dataclass
class VNFinancialStatements:
    """8-year financial statements data for Vietnamese companies."""
    
    # Income Statement (TT99/VAS compliant)
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
    
    # Balance Sheet (TT99/VAS compliant)
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
    
    # Vietnam-specific fields
    state_ownership_percent: list[float] = field(default_factory=lambda: [0.0] * 8)
    fol_remaining: list[float] = field(default_factory=lambda: [0.0] * 8)  # Foreign Ownership Limit remaining
    related_party_transactions: list[float] = field(default_factory=lambda: [0.0] * 8)
    
    # Cash Flow Statement
    capex: list[float] = field(default_factory=lambda: [0.0] * 8)  # Negative
    change_in_ltd: list[float] = field(default_factory=lambda: [0.0] * 8)
    change_in_common_equity: list[float] = field(default_factory=lambda: [0.0] * 8)
    dividends: list[float] = field(default_factory=lambda: [0.0] * 8)  # Negative
    beginning_cash: list[float] = field(default_factory=lambda: [0.0] * 8)


@dataclass
class VNDerivedMetrics:
    """Derived financial metrics for Vietnamese companies (Section 1D)."""
    
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
    
    # Vietnam-specific metrics
    state_owned_equity: list[float] = field(default_factory=lambda: [0.0] * 8)
    private_equity: list[float] = field(default_factory=lambda: [0.0] * 8)
    fol_value: list[float] = field(default_factory=lambda: [0.0] * 8)


@dataclass
class VNRatioCalculations:
    """All ratio calculations for Vietnamese companies (Section 2)."""
    
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
    
    # Vietnam-specific ratios
    state_ownership_impact: list[float] = field(default_factory=lambda: [0.0] * 8)
    fol_utilization: list[float] = field(default_factory=lambda: [0.0] * 8)
    related_party_ratio: list[float] = field(default_factory=lambda: [0.0] * 8)


@dataclass
class VNDuPontResult:
    """Complete DuPont analysis result for Vietnamese companies."""
    
    financial_statements: VNFinancialStatements
    derived_metrics: VNDerivedMetrics
    ratios: VNRatioCalculations
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
                    "state_ownership_percent": self.financial_statements.state_ownership_percent,
                    "fol_remaining": self.financial_statements.fol_remaining,
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
                },
                "vietnam_specific": {
                    "state_ownership_impact": self.ratios.state_ownership_impact,
                    "fol_utilization": self.ratios.fol_utilization,
                    "related_party_ratio": self.ratios.related_party_ratio,
                }
            },
            "validation_errors": self.validation_errors,
            "warnings": self.warnings,
        }


class VNDuPontAnalyzer:
    """
    Vietnamese DuPont Analysis Engine implementing 3-step and 5-step ROE decomposition.
    
    Follows the exact calculation methodology from the MID RETAILER Excel model,
    adapted for Vietnamese market conditions and TT99/VAS accounting standards.
    
    Vietnam-Specific Features:
    - TT99/VAS accounting compliance
    - VND currency handling
    - FOL (Foreign Ownership Limit) tracking
    - State ownership impact analysis
    - Related party transaction monitoring
    - 20% Vietnamese corporate tax rate
    """
    
    # Vietnam-specific constants
    VIETNAM_CORPORATE_TAX_RATE = 0.20
    VIETNAM_FOL_DEFAULT_MAX = 0.49  # Default 49% FOL for most sectors
    VIETNAM_STATE_OWNERSHIP_THRESHOLD = 0.50  # 50%+ = state-controlled
    
    def __init__(self):
        self.statements: Optional[VNFinancialStatements] = None
        self.metrics: Optional[VNDerivedMetrics] = None
        self.ratios: Optional[VNRatioCalculations] = None
        self.validation_errors: list[str] = []
        self.warnings: list[str] = []
    
    def load_data(self, statements: VNFinancialStatements) -> None:
        """Load financial statements data."""
        self.statements = statements
        self.validation_errors = []
        self.warnings = []
    
    async def analyze(self) -> VNDuPontResult:
        """
        Perform complete DuPont analysis (async wrapper).
        
        Returns:
            VNDuPontResult with all calculated metrics and ratios
        """
        if self.statements is None:
            raise ValueError("No financial statements loaded. Call load_data() first.")
        
        # Calculate derived metrics
        self._calculate_derived_metrics()
        
        # Calculate all ratios
        self._calculate_ratios()
        
        # Validate results
        self._validate_results()
        
        return VNDuPontResult(
            financial_statements=self.statements,
            derived_metrics=self.metrics,
            ratios=self.ratios,
            validation_errors=self.validation_errors,
            warnings=self.warnings,
        )
    
    def calculate_all(self) -> VNDuPontResult:
        """
        Perform complete DuPont analysis (sync method for backward compatibility).
        
        Returns:
            VNDuPontResult with all calculated metrics and ratios
        """
        if self.statements is None:
            raise ValueError("No financial statements loaded. Call load_data() first.")
        
        # Calculate derived metrics
        self._calculate_derived_metrics()
        
        # Calculate all ratios
        self._calculate_ratios()
        
        # Validate results
        self._validate_results()
        
        return VNDuPontResult(
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
        self.metrics = VNDerivedMetrics()
        
        for i in range(8):
            # Net COGS = gross COGS + depreciation component (row 9 formula)
            self.metrics.net_cogs[i] = self.statements.cogs_gross[i] + self.statements.depreciation_cogs[i]
            
            # Gross Profit = Revenue + Net COGS (remember COGS is negative)
            self.metrics.gross_profit[i] = self.statements.revenue[i] + self.metrics.net_cogs[i]
            
            # EBITDA = Gross Profit + SGA + Other OpEx (all negative)
            self.metrics.ebitda[i] = (
                self.metrics.gross_profit[i] 
                + self.statements.sga[i] 
                + self.statements.other_operating_expenses[i]
            )
            
            # EBIT = EBITDA + Depreciation (negative)
            self.metrics.ebit[i] = self.metrics.ebitda[i] + self.statements.depreciation[i]
            
            # EBT = EBIT + Interest Expense + Interest Income
            self.metrics.ebt[i] = (
                self.metrics.ebit[i] 
                + self.statements.interest_expense[i] 
                + self.statements.interest_income[i]
            )
            
            # Tax Provision = Current Tax + Other Tax (both negative)
            self.metrics.tax_provision[i] = self.statements.tax_current[i] + self.statements.tax_other[i]
            
            # Net Income = EBT + Tax Provision (tax is negative)
            self.metrics.net_income[i] = self.metrics.ebt[i] + self.metrics.tax_provision[i]
            
            # NOPAT = EBIT * (1 - Tax Rate)
            # Using effective tax rate
            if abs(self.metrics.ebt[i]) > 1e-10:
                effective_tax = abs(self.metrics.tax_provision[i]) / abs(self.metrics.ebt[i])
                self.metrics.nopat[i] = self.metrics.ebit[i] * (1 - effective_tax)
            else:
                self.metrics.nopat[i] = self.metrics.ebit[i] * (1 - self.VIETNAM_CORPORATE_TAX_RATE)
            
            # Effective Tax Rate
            self.metrics.effective_tax_rate[i] = self._safe_divide(
                abs(self.metrics.tax_provision[i]), 
                abs(self.metrics.ebt[i]), 
                self.VIETNAM_CORPORATE_TAX_RATE
            )
            
            # Balance Sheet Totals
            self.metrics.total_current_assets[i] = (
                self.statements.cash[i] 
                + self.statements.accounts_receivable[i] 
                + self.statements.inventories[i]
            )
            
            self.metrics.ppe_total[i] = (
                self.statements.ppe_component1[i] 
                + self.statements.ppe_component2[i]
            )
            
            self.metrics.total_assets[i] = (
                self.metrics.total_current_assets[i] 
                + self.metrics.ppe_total[i]
            )
            
            self.metrics.total_current_liabilities[i] = (
                self.statements.accounts_payable[i] 
                + self.statements.revolving_credit[i]
            )
            
            self.metrics.total_liabilities[i] = (
                self.metrics.total_current_liabilities[i] 
                + self.statements.long_term_debt[i]
            )
            
            self.metrics.total_equity[i] = (
                self.statements.common_equity[i] 
                + self.statements.retained_earnings[i]
            )
            
            self.metrics.total_liabilities_and_equity[i] = (
                self.metrics.total_liabilities[i] 
                + self.metrics.total_equity[i]
            )
            
            # Invested Capital Components
            self.metrics.interest_bearing_current_liabilities[i] = self.statements.revolving_credit[i]
            self.metrics.interest_bearing_lt_liabilities[i] = self.statements.long_term_debt[i]
            self.metrics.total_interest_bearing_liabilities[i] = (
                self.metrics.interest_bearing_current_liabilities[i] 
                + self.metrics.interest_bearing_lt_liabilities[i]
            )
            
            self.metrics.net_debt[i] = (
                self.metrics.total_interest_bearing_liabilities[i] 
                + self.statements.cash[i]  # Cash is positive, so this subtracts it
            )
            
            self.metrics.invested_capital[i] = (
                self.metrics.total_equity[i] 
                + self.metrics.net_debt[i]
            )
            
            # Net Assets
            self.metrics.net_assets[i] = self.metrics.total_assets[i] - self.metrics.total_current_liabilities[i]
            
            # Vietnam-specific: State ownership and FOL calculations
            self.metrics.state_owned_equity[i] = self.metrics.total_equity[i] * self.statements.state_ownership_percent[i]
            self.metrics.private_equity[i] = self.metrics.total_equity[i] * (1 - self.statements.state_ownership_percent[i])
            self.metrics.fol_value[i] = self.metrics.total_equity[i] * (1 - self.statements.fol_remaining[i])
    
    def _calculate_ratios(self) -> None:
        """Calculate all financial ratios (Section 2)."""
        self.ratios = VNRatioCalculations()
        
        for i in range(8):
            # === 2A: Profitability and Return Ratios ===
            
            # ROE = Net Income / Average Equity
            avg_equity = self.metrics.total_equity[i]
            if i > 0:
                avg_equity = (self.metrics.total_equity[i] + self.metrics.total_equity[i-1]) / 2
            self.ratios.roe[i] = self._safe_divide(self.metrics.net_income[i], avg_equity)
            
            # ROA = Net Income / Average Total Assets
            avg_assets = self.metrics.total_assets[i]
            if i > 0:
                avg_assets = (self.metrics.total_assets[i] + self.metrics.total_assets[i-1]) / 2
            self.ratios.roa[i] = self._safe_divide(self.metrics.net_income[i], avg_assets)
            
            # RONA = NOPAT / Net Assets
            self.ratios.rona[i] = self._safe_divide(self.metrics.nopat[i], self.metrics.net_assets[i])
            
            # ROIC = NOPAT / Invested Capital
            self.ratios.roic[i] = self._safe_divide(self.metrics.nopat[i], self.metrics.invested_capital[i])
            
            # === Margin Ratios ===
            
            self.ratios.gross_margin[i] = self._safe_divide(self.metrics.gross_profit[i], self.statements.revenue[i])
            self.ratios.sga_percent_revenue[i] = self._safe_divide(abs(self.statements.sga[i]), self.statements.revenue[i])
            self.ratios.other_opex_percent_revenue[i] = self._safe_divide(abs(self.statements.other_operating_expenses[i]), self.statements.revenue[i])
            self.ratios.ebitda_margin[i] = self._safe_divide(self.metrics.ebitda[i], self.statements.revenue[i])
            self.ratios.depreciation_percent_revenue[i] = self._safe_divide(abs(self.statements.depreciation[i]), self.statements.revenue[i])
            self.ratios.ebit_margin[i] = self._safe_divide(self.metrics.ebit[i], self.statements.revenue[i])
            
            net_finance_cost = self.statements.interest_expense[i] + self.statements.interest_income[i]
            self.ratios.net_finance_cost_percent[i] = self._safe_divide(abs(net_finance_cost), self.statements.revenue[i])
            
            self.ratios.ebt_margin[i] = self._safe_divide(self.metrics.ebt[i], self.statements.revenue[i])
            self.ratios.tax_percent_revenue[i] = self._safe_divide(abs(self.metrics.tax_provision[i]), self.statements.revenue[i])
            self.ratios.net_profit_margin[i] = self._safe_divide(self.metrics.net_income[i], self.statements.revenue[i])
            
            # DuPont Component Ratios
            self.ratios.effective_tax_rate_ratio[i] = self._safe_divide(abs(self.metrics.tax_provision[i]), abs(self.metrics.ebt[i]))
            self.ratios.tax_burden[i] = self._safe_divide(self.metrics.net_income[i], self.metrics.ebt[i])
            self.ratios.effective_interest_rate[i] = self._safe_divide(abs(net_finance_cost), abs(self.metrics.total_interest_bearing_liabilities[i]))
            self.ratios.interest_burden[i] = self._safe_divide(self.metrics.ebt[i], self.metrics.ebit[i])
            
            # === 2B: Asset Utilization Ratios ===
            
            avg_assets_for_turnover = self.metrics.total_assets[i]
            if i > 0:
                avg_assets_for_turnover = (self.metrics.total_assets[i] + self.metrics.total_assets[i-1]) / 2
            
            self.ratios.asset_turnover[i] = self._safe_divide(self.statements.revenue[i], avg_assets_for_turnover)
            self.ratios.ppe_turnover[i] = self._safe_divide(self.statements.revenue[i], self.metrics.ppe_total[i])
            self.ratios.cash_turnover[i] = self._safe_divide(self.statements.revenue[i], self.statements.cash[i])
            self.ratios.cash_days[i] = self._safe_divide(self.statements.cash[i], self.statements.revenue[i]) * 365
            
            avg_ar = self.statements.accounts_receivable[i]
            if i > 0:
                avg_ar = (self.statements.accounts_receivable[i] + self.statements.accounts_receivable[i-1]) / 2
            self.ratios.ar_turnover[i] = self._safe_divide(self.statements.revenue[i], avg_ar)
            self.ratios.ar_days_dso[i] = self._safe_divide(avg_ar, self.statements.revenue[i]) * 365
            
            avg_inv = self.statements.inventories[i]
            if i > 0:
                avg_inv = (self.statements.inventories[i] + self.statements.inventories[i-1]) / 2
            self.ratios.inventory_turnover[i] = self._safe_divide(abs(self.metrics.net_cogs[i]), avg_inv)
            self.ratios.inventory_days_dio[i] = self._safe_divide(avg_inv, abs(self.metrics.net_cogs[i])) * 365
            
            avg_ap = self.statements.accounts_payable[i]
            if i > 0:
                avg_ap = (self.statements.accounts_payable[i] + self.statements.accounts_payable[i-1]) / 2
            self.ratios.ap_turnover[i] = self._safe_divide(abs(self.metrics.net_cogs[i]), avg_ap)
            self.ratios.ap_days_dpo[i] = self._safe_divide(avg_ap, abs(self.metrics.net_cogs[i])) * 365
            
            # Cash Conversion Cycle = DIO + DSO - DPO
            self.ratios.cash_conversion_cycle[i] = (
                self.ratios.inventory_days_dio[i] 
                + self.ratios.ar_days_dso[i] 
                - self.ratios.ap_days_dpo[i]
            )
            
            # === 2C: Leverage Ratios ===
            
            self.ratios.total_assets_to_equity[i] = self._safe_divide(self.metrics.total_assets[i], self.metrics.total_equity[i])
            self.ratios.total_liabilities_to_equity[i] = self._safe_divide(self.metrics.total_liabilities[i], self.metrics.total_equity[i])
            self.ratios.debt_to_equity[i] = self._safe_divide(self.metrics.total_interest_bearing_liabilities[i], self.metrics.total_equity[i])
            self.ratios.debt_to_ebitda[i] = self._safe_divide(self.metrics.total_interest_bearing_liabilities[i], self.metrics.ebitda[i])
            self.ratios.net_debt_to_ebitda[i] = self._safe_divide(self.metrics.net_debt[i], self.metrics.ebitda[i])
            
            # === 2D: Liquidity Ratios ===
            
            self.ratios.current_ratio[i] = self._safe_divide(self.metrics.total_current_assets[i], self.metrics.total_current_liabilities[i])
            quick_assets = self.metrics.total_current_assets[i] - self.statements.inventories[i]
            self.ratios.quick_ratio[i] = self._safe_divide(quick_assets, self.metrics.total_current_liabilities[i])
            self.ratios.interest_coverage[i] = self._safe_divide(self.metrics.ebit[i], abs(net_finance_cost))
            
            # === 2E: Growth Trends (starting from Year 2) ===
            
            if i > 0:
                self.ratios.revenue_growth[i] = self._safe_divide(
                    self.statements.revenue[i] - self.statements.revenue[i-1],
                    abs(self.statements.revenue[i-1])
                )
                self.ratios.ebitda_growth[i] = self._safe_divide(
                    self.metrics.ebitda[i] - self.metrics.ebitda[i-1],
                    abs(self.metrics.ebitda[i-1])
                )
                self.ratios.ebit_growth[i] = self._safe_divide(
                    self.metrics.ebit[i] - self.metrics.ebit[i-1],
                    abs(self.metrics.ebit[i-1])
                )
                self.ratios.net_income_growth[i] = self._safe_divide(
                    self.metrics.net_income[i] - self.metrics.net_income[i-1],
                    abs(self.metrics.net_income[i-1])
                )
                self.ratios.total_asset_growth[i] = self._safe_divide(
                    self.metrics.total_assets[i] - self.metrics.total_assets[i-1],
                    abs(self.metrics.total_assets[i-1])
                )
                
                # Degree of Operating Leverage = %ΔEBIT / %ΔRevenue
                self.ratios.dol[i] = self._safe_divide(self.ratios.ebit_growth[i], self.ratios.revenue_growth[i])
                
                # Degree of Financial Leverage = %ΔNet Income / %ΔEBIT
                self.ratios.dfl[i] = self._safe_divide(self.ratios.net_income_growth[i], self.ratios.ebit_growth[i])
                
                # Degree of Total Leverage = DOL * DFL
                self.ratios.dtl[i] = self.ratios.dol[i] * self.ratios.dfl[i]
            
            # === 2F: DuPont Checks ===
            
            # 3-Step DuPont: ROE = Net Profit Margin × Asset Turnover × Asset-to-Equity
            self.ratios.roe_3step[i] = (
                self.ratios.net_profit_margin[i] 
                * self.ratios.asset_turnover[i] 
                * self.ratios.total_assets_to_equity[i]
            )
            self.ratios.roe_3step_check[i] = abs(self.ratios.roe_3step[i] - self.ratios.roe[i]) < 0.01  # 1% tolerance
            
            # 5-Step DuPont: ROE = Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Asset-to-Equity
            self.ratios.roe_5step[i] = (
                self.ratios.tax_burden[i] 
                * self.ratios.interest_burden[i] 
                * self.ratios.ebit_margin[i] 
                * self.ratios.asset_turnover[i] 
                * self.ratios.total_assets_to_equity[i]
            )
            self.ratios.roe_5step_check[i] = abs(self.ratios.roe_5step[i] - self.ratios.roe[i]) < 0.01  # 1% tolerance
            
            # === Vietnam-Specific Ratios ===
            
            # State ownership impact on ROE
            self.ratios.state_ownership_impact[i] = self.ratios.roe[i] * self.statements.state_ownership_percent[i]
            
            # FOL utilization rate
            self.ratios.fol_utilization[i] = 1 - self.statements.fol_remaining[i]
            
            # Related party transaction ratio
            self.ratios.related_party_ratio[i] = self._safe_divide(
                self.statements.related_party_transactions[i], 
                self.statements.revenue[i]
            )
    
    def _validate_results(self) -> None:
        """Validate DuPont analysis results and add warnings/errors."""
        
        # Check for negative equity
        for i in range(8):
            if self.metrics.total_equity[i] < 0:
                self.validation_errors.append(f"Year {i+1}: Negative equity detected")
        
        # Check DuPont reconciliation
        for i in range(8):
            if not self.ratios.roe_3step_check[i]:
                self.warnings.append(f"Year {i+1}: 3-step DuPont reconciliation failed (diff > 1%)")
            if not self.ratios.roe_5step_check[i]:
                self.warnings.append(f"Year {i+1}: 5-step DuPont reconciliation failed (diff > 1%)")
        
        # Vietnam-specific validations
        
        # Check FOL limits
        for i in range(8):
            fol_utilization = self.ratios.fol_utilization[i]
            if fol_utilization > 0.49:  # Above 49%
                self.warnings.append(f"Year {i+1}: FOL utilization exceeds 49% - check sector-specific limits")
        
        # Check state ownership threshold
        for i in range(8):
            if self.statements.state_ownership_percent[i] >= self.VIETNAM_STATE_OWNERSHIP_THRESHOLD:
                self.warnings.append(f"Year {i+1}: State ownership >= 50% - company is state-controlled")
        
        # Check related party transactions
        for i in range(8):
            if self.ratios.related_party_ratio[i] > 0.30:  # > 30% of revenue
                self.warnings.append(f"Year {i+1}: Related party transactions exceed 30% of revenue - governance concern")
        
        # Check effective tax rate vs statutory rate
        for i in range(8):
            tax_rate = self.metrics.effective_tax_rate[i]
            if abs(tax_rate - self.VIETNAM_CORPORATE_TAX_RATE) > 0.05:  # > 5% difference
                self.warnings.append(f"Year {i+1}: Effective tax rate ({tax_rate:.1%}) differs significantly from statutory 20%")
        
        # Check cash conversion cycle
        for i in range(8):
            ccc = self.ratios.cash_conversion_cycle[i]
            if ccc > 180:  # > 6 months
                self.warnings.append(f"Year {i+1}: Cash conversion cycle exceeds 180 days - working capital efficiency concern")
        
        # Check net debt to EBITDA
        for i in range(8):
            nd_ebitda = self.ratios.net_debt_to_ebitda[i]
            if nd_ebitda > 4.0:
                self.warnings.append(f"Year {i+1}: Net Debt/EBITDA > 4x - high leverage")
        
        # Check interest coverage
        for i in range(8):
            ic = self.ratios.interest_coverage[i]
            if ic < 2.0:
                self.warnings.append(f"Year {i+1}: Interest coverage < 2x - debt service concern")
