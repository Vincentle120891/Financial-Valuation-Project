"""
Vietnamese DCF Valuation Engine

This module provides DCF valuation specifically for Vietnamese stocks.
It enforces strict separation from international workflows by:

1. Using Vietnam-specific risk-free rates (10-year government bond)
2. Applying Vietnam country risk premium and market premium
3. Using 20% Vietnamese corporate tax rate
4. Filtering peers from VNINDEX, VN30, or local sector indices
5. All calculations in VND currency

NO CROSS-CONTAMINATION:
- Does NOT use US Treasury rates or international risk-free rates
- Does NOT apply developed market risk premiums
- Does NOT accept non-Vietnamese tickers or data
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import date

from app.models.vietnamese.vietnamese_inputs import (
    VietnameseDCFRequest,
    VNDuPontComponents,
    VNSector
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Vietnam-Specific Constants
# ──────────────────────────────────────────────────────────────────────────────

VIETNAM_CORPORATE_TAX_RATE = 0.20  # Standard corporate income tax rate
VIETNAM_RISK_FREE_RATE_DEFAULT = 0.068  # ~6.8% (10-year government bond yield)
VIETNAM_MARKET_RISK_PREMIUM_DEFAULT = 0.075  # ~7.5% Vietnam ERP
VIETNAM_SIZE_PREMIUM_SMALL_CAP = 0.02  # Additional premium for small caps
VIETNAM_SIZE_PREMIUM_MID_CAP = 0.01   # Additional premium for mid caps

# Terminal growth rate constraints (aligned with Vietnam GDP growth expectations)
VIETNAM_GDP_GROWTH_LONG_TERM = 0.05  # ~5% long-term GDP growth expectation
VIETNAM_TERMINAL_GROWTH_MAX = 0.06   # Max terminal growth (GDP + 1%)
VIETNAM_TERMINAL_GROWTH_MIN = 0.02   # Min terminal growth


class VietnameseDCFEngine:
    """
    DCF Valuation Engine for Vietnamese Stocks
    
    Implements discounted cash flow valuation using Vietnam-specific parameters:
    - WACC calculation with Vietnam risk-free rate and market premium
    - 20% corporate tax rate
    - Terminal value based on Vietnam long-term GDP growth expectations
    - Peer filtering from VNINDEX/VN30 for beta estimation
    
    Attributes:
        corporate_tax_rate: Vietnamese corporate tax rate (20%)
        risk_free_rate: Current Vietnam 10-year government bond yield
        market_risk_premium: Vietnam equity risk premium
    """
    
    def __init__(
        self,
        corporate_tax_rate: float = VIETNAM_CORPORATE_TAX_RATE,
        risk_free_rate: Optional[float] = None,
        market_risk_premium: Optional[float] = None
    ):
        """
        Initialize Vietnamese DCF Engine.
        
        Args:
            corporate_tax_rate: Corporate tax rate (default: 20% for Vietnam)
            risk_free_rate: Vietnam risk-free rate (default: 6.8%)
            market_risk_premium: Vietnam market risk premium (default: 7.5%)
        """
        self.corporate_tax_rate = corporate_tax_rate
        self.risk_free_rate = risk_free_rate or VIETNAM_RISK_FREE_RATE_DEFAULT
        self.market_risk_premium = market_risk_premium or VIETNAM_MARKET_RISK_PREMIUM_DEFAULT
        
        logger.info(
            f"Vietnamese DCF Engine initialized: "
            f"Tax={self.corporate_tax_rate:.1%}, Rf={self.risk_free_rate:.2%}, "
            f"MRP={self.market_risk_premium:.2%}"
        )
    
    def calculate_wacc(
        self,
        beta: float,
        cost_of_debt: float,
        debt_to_equity: float,
        risk_free_rate: Optional[float] = None,
        market_risk_premium: Optional[float] = None,
        size_premium: float = 0.0,
        country_risk_premium: float = 0.0
    ) -> float:
        """
        Calculate Weighted Average Cost of Capital (WACC) for Vietnamese company.
        
        Uses Vietnam-specific risk-free rate and market risk premium.
        
        Formula:
            WACC = (E/V) × Re + (D/V) × Rd × (1 - T)
            
            Where:
            - Re = Rf + β × MRP + Size Premium + Country Risk Premium
            - Rd = Cost of debt
            - T = Corporate tax rate (20% Vietnam)
            - E/V = Equity weight
            - D/V = Debt weight
        
        Args:
            beta: Stock beta relative to VNINDEX
            cost_of_debt: Pre-tax cost of debt (VND lending rate)
            debt_to_equity: Debt-to-equity ratio (D/E)
            risk_free_rate: Override default Vietnam Rf
            market_risk_premium: Override default Vietnam MRP
            size_premium: Size premium for small/mid caps
            country_risk_premium: Additional country risk (usually 0 for domestic firms)
            
        Returns:
            WACC as decimal (e.g., 0.105 for 10.5%)
        """
        rf = risk_free_rate or self.risk_free_rate
        mrp = market_risk_premium or self.market_risk_premium
        
        # Cost of equity using CAPM with Vietnam parameters
        cost_of_equity = rf + beta * mrp + size_premium + country_risk_premium
        
        # Calculate weights
        if debt_to_equity >= 0:
            equity_weight = 1 / (1 + debt_to_equity)
            debt_weight = debt_to_equity / (1 + debt_to_equity)
        else:
            # Negative D/E (net cash position)
            equity_weight = 1.0
            debt_weight = 0.0
            cost_of_debt = 0.0
        
        # WACC calculation with Vietnamese tax shield
        wacc = (
            equity_weight * cost_of_equity +
            debt_weight * cost_of_debt * (1 - self.corporate_tax_rate)
        )
        
        # Sanity checks
        wacc = max(wacc, rf)  # WACC should not be below risk-free rate
        wacc = min(wacc, 0.30)  # Cap at 30% for sanity
        
        logger.debug(
            f"WACC Calculation: Re={cost_of_equity:.2%}, Rd={cost_of_debt:.2%}, "
            f"We={equity_weight:.2%}, Wd={debt_weight:.2%}, WACC={wacc:.2%}"
        )
        
        return wacc
    
    def calculate_terminal_value(
        self,
        final_fcf: float,
        terminal_growth_rate: float,
        wacc: float
    ) -> float:
        """
        Calculate terminal value using Gordon Growth Model.
        
        Constrains terminal growth rate to Vietnam long-term GDP growth expectations.
        
        Args:
            final_fcf: Final year free cash flow
            terminal_growth_rate: Perpetual growth rate
            wacc: Weighted average cost of capital
            
        Returns:
            Terminal value in VND
        """
        # Constrain growth rate to reasonable bounds for Vietnam
        g = max(
            VIETNAM_TERMINAL_GROWTH_MIN,
            min(terminal_growth_rate, VIETNAM_TERMINAL_GROWTH_MAX)
        )
        
        if g >= wacc:
            logger.warning(
                f"Terminal growth rate {g:.2%} >= WACC {wacc:.2%}. "
                f"Adjusting growth to {wacc - 0.01:.2%}"
            )
            g = wacc - 0.01
        
        # Gordon Growth Model: TV = FCF × (1 + g) / (WACC - g)
        terminal_value = final_fcf * (1 + g) / (wacc - g)
        
        logger.debug(
            f"Terminal Value: FCF={final_fcf:,.0f}, g={g:.2%}, WACC={wacc:.2%}, "
            f"TV={terminal_value:,.0f}"
        )
        
        return terminal_value
    
    def project_free_cash_flows(
        self,
        revenue_base: float,
        ebit_margin: float,
        tax_rate: float,
        depreciation: float,
        capex: float,
        change_in_nwc: float,
        revenue_growth_rates: List[float],
        forecast_years: int
    ) -> List[Dict[str, float]]:
        """
        Project free cash flows for forecast period.
        
        FCFF = EBIT × (1 - Tax Rate) + Depreciation - CapEx - ΔNWC
        
        Args:
            revenue_base: Base year revenue (billion VND)
            ebit_margin: EBIT margin (decimal)
            tax_rate: Tax rate (use Vietnam 20%)
            depreciation: Annual depreciation (billion VND)
            capex: Annual capital expenditures (billion VND)
            change_in_nwc: Annual change in net working capital (billion VND)
            revenue_growth_rates: Revenue growth rates for each year
            forecast_years: Number of forecast years
            
        Returns:
            List of yearly projections with FCF calculations
        """
        projections = []
        current_revenue = revenue_base
        
        for year_idx in range(forecast_years):
            year = year_idx + 1
            growth_rate = (
                revenue_growth_rates[year_idx]
                if year_idx < len(revenue_growth_rates)
                else revenue_growth_rates[-1] if revenue_growth_rates else 0.05
            )
            
            # Project revenue
            current_revenue = current_revenue * (1 + growth_rate)
            
            # Calculate EBIT
            ebit = current_revenue * ebit_margin
            
            # NOPAT (Net Operating Profit After Tax)
            nopat = ebit * (1 - tax_rate)
            
            # Free Cash Flow to Firm
            fcff = nopat + depreciation - capex - change_in_nwc
            
            projections.append({
                'year': year,
                'revenue': current_revenue,
                'revenue_growth': growth_rate,
                'ebit': ebit,
                'nopat': nopat,
                'depreciation': depreciation,
                'capex': capex,
                'change_in_nwc': change_in_nwc,
                'fcff': fcff
            })
            
            logger.debug(
                f"Year {year}: Revenue={current_revenue:,.0f}, EBIT={ebit:,.0f}, "
                f"FCFF={fcff:,.0f}"
            )
        
        return projections
    
    def calculate_enterprise_value(
        self,
        fcf_projections: List[Dict[str, float]],
        terminal_value: float,
        wacc: float
    ) -> Dict[str, float]:
        """
        Calculate enterprise value from projected FCFs and terminal value.
        
        Args:
            fcf_projections: List of yearly FCF projections
            terminal_value: Terminal value at end of forecast period
            wacc: Discount rate
            
        Returns:
            Dictionary with PV of FCFs, PV of TV, and total EV
        """
        pv_fcfs = []
        total_pv_fcf = 0.0
        
        for proj in fcf_projections:
            year = proj['year']
            fcff = proj['fcff']
            pv = fcff / ((1 + wacc) ** year)
            pv_fcfs.append(pv)
            total_pv_fcf += pv
        
        # PV of terminal value
        n = len(fcf_projections)
        pv_terminal_value = terminal_value / ((1 + wacc) ** n)
        
        # Enterprise Value
        enterprise_value = total_pv_fcf + pv_terminal_value
        
        logger.info(
            f"Enterprise Value Calculation: "
            f"PV(FCFs)={total_pv_fcf:,.0f}, PV(TV)={pv_terminal_value:,.0f}, "
            f"EV={enterprise_value:,.0f}"
        )
        
        return {
            'pv_fcfs': pv_fcfs,
            'total_pv_fcf': total_pv_fcf,
            'pv_terminal_value': pv_terminal_value,
            'enterprise_value': enterprise_value
        }
    
    def calculate_equity_value(
        self,
        enterprise_value: float,
        total_debt: float,
        cash_and_equivalents: float,
        minority_interest: float = 0.0,
        preferred_equity: float = 0.0
    ) -> float:
        """
        Calculate equity value from enterprise value.
        
        Equity Value = EV - Debt + Cash - Minority Interest - Preferred Equity
        
        Args:
            enterprise_value: Enterprise value (billion VND)
            total_debt: Total debt (billion VND)
            cash_and_equivalents: Cash and equivalents (billion VND)
            minority_interest: Minority interest (billion VND)
            preferred_equity: Preferred equity (billion VND)
            
        Returns:
            Equity value in billion VND
        """
        equity_value = (
            enterprise_value
            - total_debt
            + cash_and_equivalents
            - minority_interest
            - preferred_equity
        )
        
        logger.debug(
            f"Equity Value: EV={enterprise_value:,.0f}, Debt={total_debt:,.0f}, "
            f"Cash={cash_and_equivalents:,.0f}, Equity={equity_value:,.0f}"
        )
        
        return equity_value
    
    def calculate_intrinsic_value_per_share(
        self,
        equity_value: float,
        shares_outstanding: float,
        diluted_shares: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate intrinsic value per share.
        
        Args:
            equity_value: Total equity value (billion VND)
            shares_outstanding: Basic shares outstanding
            diluted_shares: Diluted shares (optional)
            
        Returns:
            Dictionary with basic and diluted value per share (VND)
        """
        basic_value_per_share = equity_value / shares_outstanding if shares_outstanding > 0 else 0
        
        diluted_value_per_share = (
            equity_value / diluted_shares
            if diluted_shares and diluted_shares > 0
            else basic_value_per_share
        )
        
        return {
            'basic_value_per_share': basic_value_per_share,
            'diluted_value_per_share': diluted_value_per_share
        }
    
    def valuate_vn_dcf(
        self,
        request: VietnameseDCFRequest,
        financial_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform complete DCF valuation for Vietnamese stock.
        
        Orchestrates all valuation steps:
        1. Calculate WACC with Vietnam parameters
        2. Project free cash flows
        3. Calculate terminal value
        4. Discount to present value
        5. Calculate equity value and per-share value
        
        Args:
            request: VietnameseDCFRequest with valuation parameters
            financial_data: Dict with financial metrics:
                - revenue: Base year revenue
                - ebit_margin: EBIT margin
                - depreciation: Annual depreciation
                - capex: Annual capex
                - change_in_nwc: Change in NWC
                - revenue_growth_rates: List of growth rates
                - cost_of_debt: Pre-tax cost of debt
                - debt_to_equity: D/E ratio
                - total_debt: Total debt
                - cash: Cash and equivalents
                
        Returns:
            Complete valuation results dictionary
        """
        # Extract parameters from request
        beta = request.beta
        terminal_growth = request.terminal_growth_rate
        forecast_years = request.forecast_years
        
        # Use override WACC if provided
        if request.wacc_override:
            wacc = request.wacc_override
            logger.info(f"Using WACC override: {wacc:.2%}")
        else:
            # Calculate WACC with Vietnam parameters
            cost_of_debt = financial_data.get('cost_of_debt', 0.10)  # ~10% VND lending rate
            debt_to_equity = financial_data.get('debt_to_equity', 0.5)
            
            # Apply size premium based on market cap
            market_cap_vnd = request.current_price_vnd * request.shares_outstanding
            size_premium = self._get_size_premium(market_cap_vnd)
            
            wacc = self.calculate_wacc(
                beta=beta,
                cost_of_debt=cost_of_debt,
                debt_to_equity=debt_to_equity,
                risk_free_rate=request.risk_free_rate_vn,
                market_risk_premium=request.market_risk_premium_vn,
                size_premium=size_premium
            )
        
        # Project FCFs
        fcf_projections = self.project_free_cash_flows(
            revenue_base=financial_data.get('revenue', 0),
            ebit_margin=financial_data.get('ebit_margin', 0.15),
            tax_rate=request.corporate_tax_rate,
            depreciation=financial_data.get('depreciation', 0),
            capex=financial_data.get('capex', 0),
            change_in_nwc=financial_data.get('change_in_nwc', 0),
            revenue_growth_rates=financial_data.get('revenue_growth_rates', [0.08] * forecast_years),
            forecast_years=forecast_years
        )
        
        # Calculate terminal value
        final_fcf = fcf_projections[-1]['fcff'] if fcf_projections else 0
        terminal_value = self.calculate_terminal_value(
            final_fcf=final_fcf,
            terminal_growth_rate=terminal_growth,
            wacc=wacc
        )
        
        # Calculate enterprise value
        ev_results = self.calculate_enterprise_value(
            fcf_projections=fcf_projections,
            terminal_value=terminal_value,
            wacc=wacc
        )
        
        # Calculate equity value
        equity_value = self.calculate_equity_value(
            enterprise_value=ev_results['enterprise_value'],
            total_debt=financial_data.get('total_debt', 0),
            cash_and_equivalents=financial_data.get('cash', 0)
        )
        
        # Calculate per-share value
        per_share_results = self.calculate_intrinsic_value_per_share(
            equity_value=equity_value,
            shares_outstanding=request.shares_outstanding
        )
        
        # Compare with current price
        current_price = request.current_price_vnd
        intrinsic_value = per_share_results['basic_value_per_share']
        upside_downside = (intrinsic_value - current_price) / current_price if current_price > 0 else 0
        
        # Build results
        results = {
            'ticker': request.ticker,
            'company_name': request.company_name,
            'currency': 'VND',
            'valuation_summary': {
                'intrinsic_value_per_share': intrinsic_value,
                'current_price': current_price,
                'upside_downside_pct': upside_downside * 100,
                'recommendation': self._get_recommendation(upside_downside)
            },
            'wacc_analysis': {
                'wacc': wacc,
                'risk_free_rate_vn': request.risk_free_rate_vn,
                'market_risk_premium_vn': request.market_risk_premium_vn,
                'beta': beta,
                'corporate_tax_rate': request.corporate_tax_rate
            },
            'dcf_components': {
                'enterprise_value': ev_results['enterprise_value'],
                'total_debt': financial_data.get('total_debt', 0),
                'cash': financial_data.get('cash', 0),
                'equity_value': equity_value,
                'shares_outstanding': request.shares_outstanding
            },
            'projections': fcf_projections,
            'terminal_value': {
                'final_fcf': final_fcf,
                'terminal_growth_rate': terminal_growth,
                'terminal_value': terminal_value,
                'pv_terminal_value': ev_results['pv_terminal_value']
            }
        }
        
        logger.info(
            f"DCF Valuation complete for {request.ticker}: "
            f"Intrinsic Value={intrinsic_value:,.0f} VND, "
            f"Current Price={current_price:,.0f} VND, "
            f"Upside={upside_downside*100:.1f}%"
        )
        
        return results
    
    def _get_size_premium(self, market_cap_vnd: float) -> float:
        """
        Determine size premium based on market capitalization.
        
        Args:
            market_cap_vnd: Market cap in VND
            
        Returns:
            Size premium (0%, 1%, or 2%)
        """
        # Thresholds in billion VND
        SMALL_CAP_THRESHOLD = 5000  # < 5,000 tỷ VND
        MID_CAP_THRESHOLD = 20000   # < 20,000 tỷ VND
        
        if market_cap_vnd < SMALL_CAP_THRESHOLD:
            return VIETNAM_SIZE_PREMIUM_SMALL_CAP
        elif market_cap_vnd < MID_CAP_THRESHOLD:
            return VIETNAM_SIZE_PREMIUM_MID_CAP
        else:
            return 0.0
    
    def _get_recommendation(self, upside_downside: float) -> str:
        """
        Generate investment recommendation based on upside/downside.
        
        Args:
            upside_downside: Upside/downside percentage as decimal
            
        Returns:
            Recommendation string
        """
        if upside_downside > 0.20:
            return "STRONG BUY"
        elif upside_downside > 0.10:
            return "BUY"
        elif upside_downside > 0.05:
            return "HOLD"
        elif upside_downside > -0.10:
            return "HOLD"
        elif upside_downside > -0.20:
            return "SELL"
        else:
            return "STRONG SELL"


# Singleton instance
_vn_dcf_engine: Optional[VietnameseDCFEngine] = None


def get_vietnamese_dcf_engine() -> VietnameseDCFEngine:
    """Get or create VietnameseDCFEngine singleton."""
    global _vn_dcf_engine
    if _vn_dcf_engine is None:
        _vn_dcf_engine = VietnameseDCFEngine()
    return _vn_dcf_engine
