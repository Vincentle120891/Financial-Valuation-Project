"""
Sector-Specific Valuation Models for Vietnamese Market

Implements specialized valuation approaches for key Vietnamese sectors:
- Banking (Ngân hàng) - Dividend Discount Model, Residual Income Model
- Real Estate (Bất động sản) - NAV (Net Asset Value), RNAV (Revalued NAV)
- Manufacturing/Steel (Sản xuất/Thép) - DCF with commodity adjustments
- Technology (Công nghệ) - DCF with high growth assumptions
- Oil & Gas (Dầu khí) - DCF with reserve-based valuation
- Retail/Consumer (Bán lẻ/Tiêu dùng) - DCF with same-store sales growth

Each sector has unique metrics and valuation drivers specific to Vietnamese market conditions.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math


class VNSectorValuationType(Enum):
    """Valuation methodology by sector"""
    BANKING = "Dividend Discount Model / Residual Income"
    REAL_ESTATE = "NAV / RNAV"
    MANUFACTURING = "DCF with Commodity Adjustments"
    TECHNOLOGY = "High-Growth DCF"
    OIL_GAS = "Reserve-Based DCF"
    RETAIL = "Same-Store Sales DCF"
    UTILITIES = "Regulated DCF"
    GENERAL = "Standard DCF"


@dataclass
class BankingValuationInputs:
    """Banking Sector Valuation Inputs"""
    # Asset Quality
    npl_ratio: float  # Non-performing loan ratio (%)
    llr_ratio: float  # Loan loss reserve ratio (%)
    cost_of_risk: float  # Cost of risk (%)
    
    # Capital Adequacy
    car_ratio: float  # Capital adequacy ratio (%)
    tier1_capital: float  # Tier 1 capital (billion VND)
    
    # Profitability
    roa: float  # Return on assets (%)
    roe: float  # Return on equity (%)
    nim: float  # Net interest margin (%)
    cir: float  # Cost-to-income ratio (%)
    
    # Growth
    loan_growth: float  # Loan growth rate (%)
    deposit_growth: float  # Deposit growth rate (%)
    
    # Dividends
    dividend_payout: float  # Dividend payout ratio (%)
    dividend_yield: float  # Dividend yield (%)
    
    # Book Value
    book_value_per_share: float  # BVPS (VND)
    tangible_book_value: float  # TBV (billion VND)


@dataclass
class RealEstateValuationInputs:
    """Real Estate Sector Valuation Inputs"""
    # Land Bank
    total_land_area_sqm: float  # Total land bank (sqm)
    developable_area_sqm: float  # Developable area (sqm)
    average_land_cost_per_sqm: float  # Average land cost (VND/sqm)
    
    # Projects
    number_of_projects: int
    projects_under_construction: int
    projects_ready_for_sale: int
    
    # Sales
    average_selling_price_per_sqm: float  # ASP (VND/sqm)
    pre_sales_rate: float  # Pre-sales rate (%)
    sales_velocity: float  # Units sold per month
    
    # Financials
    nav_per_share: float  # NAV per share (VND)
    rnava_per_share: float  # Revalued NAV per share (VND)
    debt_to_equity: float
    interest_coverage: float
    
    # Development Pipeline
    pipeline_value_billion_vnd: float  # Future development pipeline value
    completion_rate: float  # Project completion rate (%)


@dataclass
class ManufacturingValuationInputs:
    """Manufacturing Sector (Steel, Cement, etc.) Valuation Inputs"""
    # Production
    production_capacity_tonnes: float  # Annual capacity (tonnes)
    utilization_rate: float  # Capacity utilization (%)
    actual_production_tonnes: float  # Actual production (tonnes)
    
    # Costs
    raw_material_cost_per_tonne: float  # Raw material cost (VND/tonne)
    energy_cost_per_tonne: float  # Energy cost (VND/tonne)
    labor_cost_per_tonne: float  # Labor cost (VND/tonne)
    
    # Pricing
    average_selling_price_per_tonne: float  # ASP (VND/tonne)
    price_realization: float  # Price vs market benchmark (%)
    
    # Margins
    ebitda_margin: float  # EBITDA margin (%)
    gross_margin: float  # Gross margin (%)
    
    # Commodity Exposure
    iron_ore_exposure: float  # Iron ore price sensitivity
    coal_exposure: float  # Coal price sensitivity
    fx_exposure: float  # USD/VND exposure (%)
    
    # Capex
    maintenance_capex: float  # Maintenance capex (billion VND)
    expansion_capex: float  # Expansion capex (billion VND)


@dataclass
class SectorValuationResult:
    """Sector-Specific Valuation Result"""
    ticker: str
    company_name: str
    sector: str
    valuation_method: str
    fair_value_vnd: float  # Fair value in VND
    current_price_vnd: float  # Current market price
    upside_downside_pct: float  # Upside/downside (%)
    recommendation: str  # BUY/HOLD/SELL
    
    # Detailed outputs
    detailed_outputs: Dict[str, Any] = field(default_factory=dict)
    
    # Sensitivity analysis
    sensitivity_analysis: Dict[str, List[float]] = field(default_factory=dict)
    
    # Key assumptions
    key_assumptions: Dict[str, float] = field(default_factory=dict)
    
    # Risks
    risks: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "sector": self.sector,
            "valuation_method": self.valuation_method,
            "fair_value_vnd": round(self.fair_value_vnd, 0),
            "current_price_vnd": self.current_price_vnd,
            "upside_downside_pct": round(self.upside_downside_pct, 2),
            "recommendation": self.recommendation,
            "detailed_outputs": self.detailed_outputs,
            "key_assumptions": self.key_assumptions,
            "risks": self.risks
        }


class VNSectorValuationEngine:
    """
    Vietnamese Sector-Specific Valuation Engine
    
    Implements specialized valuation models for each major Vietnamese sector.
    """
    
    def __init__(self):
        self.risk_free_rate = 0.11  # 11% (Vietnamese government bond yield)
        self.market_risk_premium = 0.07  # 7% (Vietnam equity risk premium)
        self.vnindex_pe_average = 14.5  # Historical VNINDEX average P/E
        self.vnindex_pb_average = 2.1  # Historical VNINDEX average P/B
    
    def valuate_banking_stock(self, ticker: str, company_name: str, 
                             inputs: BankingValuationInputs,
                             current_price_vnd: float) -> SectorValuationResult:
        """
        Value banking stocks using Dividend Discount Model (DDM) and Residual Income Model
        
        Vietnamese banks are typically valued using:
        1. DDM for dividend-paying banks (VCB, BID, CTG)
        2. Residual Income Model for growth banks (TCB, MBB)
        3. P/BV comparison for all banks
        """
        
        # Method 1: Dividend Discount Model (Gordon Growth)
        # Assumes dividends grow at sustainable rate
        sustainable_growth = inputs.roe * (1 - inputs.dividend_payout)
        cost_of_equity = self.risk_free_rate + 1.2 * self.market_risk_premium  # Beta ~1.2 for banks
        
        if cost_of_equity > sustainable_growth:
            ddm_value = (inputs.book_value_per_share * inputs.dividend_payout * 
                        (1 + sustainable_growth)) / (cost_of_equity - sustainable_growth)
        else:
            ddm_value = inputs.book_value_per_share * 1.5  # Fallback to 1.5x BV
        
        # Method 2: Residual Income Model
        # Value = Book Value + PV of Future Residual Income
        residual_income = (inputs.roe - cost_of_equity) * inputs.book_value_per_share
        
        # Assume residual income grows at loan growth rate for 5 years, then fades
        pv_residual_income = 0
        for year in range(1, 6):
            ri_year = residual_income * ((1 + inputs.loan_growth) ** year)
            fade_factor = 1 - (year / 10)  # Linear fade over 10 years
            pv_residual_income += (ri_year * fade_factor) / ((1 + cost_of_equity) ** year)
        
        rim_value = inputs.book_value_per_share + pv_residual_income
        
        # Method 3: P/BV Relative Valuation
        # Adjust for ROE, NPL, and CAR
        peer_avg_pb = self.vnindex_pb_average * 0.8  # Banks trade at discount to market
        
        # ROE adjustment: Higher ROE = higher P/B
        roe_adjustment = (inputs.roe - 0.15) * 10  # 15% is average bank ROE
        
        # NPL adjustment: Lower NPL = higher P/B
        npl_adjustment = (0.03 - inputs.npl_ratio) * 20  # 3% is acceptable NPL
        
        # CAR adjustment: Higher CAR = higher P/B (safety premium)
        car_adjustment = (inputs.car_ratio - 0.10) * 5  # 10% is minimum CAR
        
        justified_pb = peer_avg_pb + roe_adjustment + npl_adjustment + car_adjustment
        justified_pb = max(0.5, min(justified_pb, 4.0))  # Bound between 0.5x and 4.0x
        
        pb_value = inputs.book_value_per_share * justified_pb
        
        # Blend the three methods
        # Weight: 40% DDM, 40% RIM, 20% P/B (adjust based on dividend consistency)
        if inputs.dividend_payout > 0.3:
            weights = (0.4, 0.4, 0.2)  # Dividend payer
        else:
            weights = (0.2, 0.6, 0.2)  # Growth bank, emphasize RIM
        
        fair_value = (ddm_value * weights[0] + rim_value * weights[1] + pb_value * weights[2])
        
        # Calculate upside/downside
        upside = ((fair_value - current_price_vnd) / current_price_vnd) * 100
        
        # Generate recommendation
        if upside > 20:
            recommendation = "BUY"
        elif upside > 5:
            recommendation = "HOLD"
        else:
            recommendation = "SELL"
        
        # Sensitivity analysis
        sensitivity = {
            "roe_sensitivity": [
                round(fair_value * (1 + (r - inputs.roe) * 5), 0)
                for r in [0.10, 0.12, 0.15, 0.18, 0.20]
            ],
            "npl_sensitivity": [
                round(fair_value * (1 - (r - inputs.npl_ratio) * 3), 0)
                for r in [0.01, 0.02, 0.03, 0.04, 0.05]
            ]
        }
        
        return SectorValuationResult(
            ticker=ticker,
            company_name=company_name,
            sector="Banking",
            valuation_method="DDM + Residual Income + P/BV",
            fair_value_vnd=fair_value,
            current_price_vnd=current_price_vnd,
            upside_downside_pct=upside,
            recommendation=recommendation,
            detailed_outputs={
                "ddm_value": round(ddm_value, 0),
                "rim_value": round(rim_value, 0),
                "pb_value": round(pb_value, 0),
                "justified_pb": round(justified_pb, 2),
                "cost_of_equity": round(cost_of_equity, 2),
                "sustainable_growth": round(sustainable_growth, 2)
            },
            sensitivity_analysis=sensitivity,
            key_assumptions={
                "risk_free_rate": self.risk_free_rate,
                "market_risk_premium": self.market_risk_premium,
                "beta": 1.2,
                "terminal_growth": sustainable_growth,
                "peer_avg_pb": peer_avg_pb
            },
            risks=[
                f"High NPL ratio ({inputs.npl_ratio:.1f}%) if economic downturn",
                f"NIM compression risk (current: {inputs.nim:.1f}%)",
                f"Capital adequacy pressure (CAR: {inputs.car_ratio:.1f}%)",
                "Regulatory changes in banking sector",
                "Real estate exposure risk"
            ]
        )
    
    def valuate_real_estate_stock(self, ticker: str, company_name: str,
                                  inputs: RealEstateValuationInputs,
                                  current_price_vnd: float) -> SectorValuationResult:
        """
        Value real estate stocks using NAV (Net Asset Value) and RNAV
        
        Vietnamese real estate companies are valued based on:
        1. NAV: Book value of land bank at historical cost
        2. RNAV: Revalued NAV at current market prices
        3. P/NAV discount/premium based on execution track record
        """
        
        # Method 1: Basic NAV
        # NAV = (Land Area × Current Market Price) - Debt
        estimated_market_value = (inputs.total_land_area_sqm * 
                                 inputs.average_selling_price_per_sqm * 0.3)  # 30% of ASP is land value
        
        nav = estimated_market_value - (inputs.debt_to_equity * inputs.nav_per_share * 1e9)
        nav_per_share = nav / 1e9  # Simplified
        
        # Method 2: RNAV (Revalued NAV)
        # More conservative, applies discounts for:
        # - Liquidity discount (20-40%)
        # - Execution risk (10-20%)
        # - Financing risk (10-15%)
        
        liquidity_discount = 0.25  # 25% typical for Vietnam
        execution_discount = 0.15  # 15% for track record risk
        financing_discount = 0.10 if inputs.interest_coverage < 3 else 0.05
        
        total_discount = liquidity_discount + execution_discount + financing_discount
        
        rnava = inputs.rnava_per_share * (1 - total_discount)
        
        # Method 3: Pipeline Value Approach
        # Value future development pipeline
        pipeline_years = 5
        annual_pipeline_value = inputs.pipeline_value_billion_vnd / pipeline_years
        
        # Apply probability of completion based on track record
        completion_probability = inputs.completion_rate
        
        pv_pipeline = 0
        discount_rate = 0.15  # High discount rate for development risk
        for year in range(1, pipeline_years + 1):
            pv_pipeline += (annual_pipeline_value * completion_probability) / \
                          ((1 + discount_rate) ** year)
        
        pipeline_value_per_share = pv_pipeline / 1e9  # Simplified
        
        # Blend methods
        # Weight: 50% RNAV, 30% NAV, 20% Pipeline
        fair_value = (rnava * 0.5 + nav_per_share * 0.3 + pipeline_value_per_share * 0.2)
        
        # Apply P/NAV multiple based on market conditions
        # Vietnamese property stocks typically trade at 0.5x - 1.5x RNAV
        market_nav_multiple = 0.8  # Current market discount
        
        fair_value *= market_nav_multiple
        
        # Calculate upside/downside
        upside = ((fair_value - current_price_vnd) / current_price_vnd) * 100
        
        # Generate recommendation
        if upside > 30:  # Higher threshold due to sector risk
            recommendation = "BUY"
        elif upside > 10:
            recommendation = "HOLD"
        else:
            recommendation = "SELL"
        
        return SectorValuationResult(
            ticker=ticker,
            company_name=company_name,
            sector="Real Estate",
            valuation_method="NAV + RNAV + Pipeline Value",
            fair_value_vnd=fair_value,
            current_price_vnd=current_price_vnd,
            upside_downside_pct=upside,
            recommendation=recommendation,
            detailed_outputs={
                "nav_per_share": round(nav_per_share, 0),
                "rnava_per_share": round(rnava, 0),
                "pipeline_value_per_share": round(pipeline_value_per_share, 0),
                "liquidity_discount": liquidity_discount,
                "execution_discount": execution_discount,
                "financing_discount": financing_discount,
                "market_nav_multiple": market_nav_multiple
            },
            key_assumptions={
                "land_bank_sqm": inputs.total_land_area_sqm,
                "average_spf_per_sqm": inputs.average_selling_price_per_sqm,
                "debt_to_equity": inputs.debt_to_equity,
                "completion_rate": inputs.completion_rate,
                "discount_rate": discount_rate
            },
            risks=[
                "Property market downturn risk",
                "Legal/approval delays for projects",
                "High leverage and refinancing risk",
                "Pre-sales execution risk",
                "Interest rate sensitivity",
                "Government policy changes on real estate"
            ]
        )
    
    def valuate_manufacturing_stock(self, ticker: str, company_name: str,
                                   inputs: ManufacturingValuationInputs,
                                   current_price_vnd: float,
                                   wacc: float = 0.13,
                                   terminal_growth: float = 0.03) -> SectorValuationResult:
        """
        Value manufacturing stocks (Steel, Cement, etc.) using DCF with commodity adjustments
        
        Key considerations for Vietnamese manufacturers:
        1. Commodity price cycles (iron ore, coal, clinker)
        2. Capacity utilization rates
        3. Export exposure and FX risk
        4. Environmental compliance costs
        """
        
        # Calculate normalized EBITDA
        revenue = inputs.actual_production_tonnes * inputs.average_selling_price_per_tonne
        cogs = inputs.actual_production_tonnes * (inputs.raw_material_cost_per_tonne + 
                                                   inputs.energy_cost_per_tonne + 
                                                   inputs.labor_cost_per_tonne)
        
        ebitda = revenue - cogs
        ebitda_margin = ebitda / revenue if revenue > 0 else 0
        
        # Normalize for commodity cycle
        # Use mid-cycle margins rather than peak/trough
        mid_cycle_margin = 0.15  # 15% typical mid-cycle EBITDA margin for steel
        normalized_ebitda = revenue * mid_cycle_margin
        
        # Forecast 5 years
        forecast_years = 5
        capacity_growth = 0.05  # 5% annual capacity expansion
        utilization_improvement = min(0.02, (0.90 - inputs.utilization_rate) / 5)
        
        fcf_projections = []
        for year in range(1, forecast_years + 1):
            # Revenue growth from capacity and utilization
            volume = inputs.actual_production_tonnes * ((1 + capacity_growth) ** year)
            volume *= (1 + utilization_improvement * year)
            
            # Assume stable pricing (mid-cycle)
            year_revenue = volume * inputs.average_selling_price_per_tonne
            
            # Mid-cycle margin
            year_ebitda = year_revenue * mid_cycle_margin
            
            # Depreciation (8% of revenue for heavy industry)
            depreciation = year_revenue * 0.08
            
            # EBIT
            ebit = year_ebitda - depreciation
            
            # Tax (20% corporate tax rate in Vietnam)
            tax = ebit * 0.20
            
            # NOPAT
            nopat = ebit - tax
            
            # Add back depreciation
            operating_cf = nopat + depreciation
            
            # Capex (maintenance + expansion)
            maintenance_capex = inputs.maintenance_capex * ((1 + 0.05) ** year)
            expansion_capex = inputs.expansion_capex * ((1 + 0.10) ** year) if year <= 3 else 0
            total_capex = maintenance_capex + expansion_capex
            
            # Working capital change (assume 5% of revenue growth)
            if year == 1:
                prev_revenue = revenue
            else:
                prev_revenue = fcf_projections[-1]['revenue']
            
            wc_change = (year_revenue - prev_revenue) * 0.05
            
            # Free Cash Flow
            fcf = operating_cf - total_capex - wc_change
            
            fcf_projections.append({
                'year': year,
                'revenue': year_revenue,
                'ebitda': year_ebitda,
                'fcf': fcf
            })
        
        # Calculate Terminal Value
        final_fcf = fcf_projections[-1]['fcf']
        terminal_value = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
        
        # Discount to present value
        pv_fcf = sum(proj['fcf'] / ((1 + wacc) ** proj['year']) 
                    for proj in fcf_projections)
        pv_terminal = terminal_value / ((1 + wacc) ** forecast_years)
        
        enterprise_value = pv_fcf + pv_terminal
        
        # Convert to equity value (simplified, assume net debt is known)
        # For now, use EV as proxy for equity value
        equity_value = enterprise_value * 0.9  # Assume 10% net debt
        
        # Per share value (simplified, assume 1 billion shares)
        shares_outstanding = 1e9  # Would need actual data
        fair_value = equity_value / shares_outstanding
        
        # Calculate upside/downside
        upside = ((fair_value - current_price_vnd) / current_price_vnd) * 100
        
        # Generate recommendation
        if upside > 25:
            recommendation = "BUY"
        elif upside > 10:
            recommendation = "HOLD"
        else:
            recommendation = "SELL"
        
        # Commodity sensitivity
        sensitivity = {
            "steel_price_sensitivity": [
                round(fair_value * (1 + (p - 1.0) * 2.5), 0)
                for p in [0.8, 0.9, 1.0, 1.1, 1.2]
            ],
            "iron_ore_cost_sensitivity": [
                round(fair_value * (1 - (c - 1.0) * 1.5), 0)
                for c in [0.8, 0.9, 1.0, 1.1, 1.2]
            ]
        }
        
        return SectorValuationResult(
            ticker=ticker,
            company_name=company_name,
            sector="Manufacturing",
            valuation_method="Commodity-Adjusted DCF",
            fair_value_vnd=fair_value,
            current_price_vnd=current_price_vnd,
            upside_downside_pct=upside,
            recommendation=recommendation,
            detailed_outputs={
                "enterprise_value": round(enterprise_value, 0),
                "pv_fcf": round(pv_fcf, 0),
                "pv_terminal": round(pv_terminal, 0),
                "terminal_value": round(terminal_value, 0),
                "normalized_ebitda_margin": mid_cycle_margin,
                "fcf_projections": fcf_projections
            },
            sensitivity_analysis=sensitivity,
            key_assumptions={
                "wacc": wacc,
                "terminal_growth": terminal_growth,
                "mid_cycle_ebitda_margin": mid_cycle_margin,
                "capacity_growth": capacity_growth,
                "corporate_tax_rate": 0.20
            },
            risks=[
                "Commodity price volatility (iron ore, coal)",
                "Overcapacity in domestic steel/cement industry",
                "Chinese import competition",
                "Environmental regulation costs",
                "Energy price fluctuations",
                "USD/VND exchange rate risk"
            ]
        )
    
    def valuate_by_sector(self, ticker: str, company_name: str, sector: str,
                         inputs: Dict[str, Any], current_price_vnd: float) -> SectorValuationResult:
        """
        Main entry point - route to appropriate sector model
        
        Args:
            ticker: Stock ticker
            company_name: Company name
            sector: Sector name (Banking, Real Estate, Manufacturing, etc.)
            inputs: Dictionary of sector-specific inputs
            current_price_vnd: Current stock price in VND
        
        Returns:
            SectorValuationResult with fair value and recommendation
        """
        
        sector_lower = sector.lower()
        
        if "bank" in sector_lower or "finance" in sector_lower:
            banking_inputs = BankingValuationInputs(**inputs)
            return self.valuate_banking_stock(ticker, company_name, banking_inputs, current_price_vnd)
        
        elif "real estate" in sector_lower or "property" in sector_lower:
            re_inputs = RealEstateValuationInputs(**inputs)
            return self.valuate_real_estate_stock(ticker, company_name, re_inputs, current_price_vnd)
        
        elif any(x in sector_lower for x in ["manufacturing", "steel", "cement", "materials"]):
            mfg_inputs = ManufacturingValuationInputs(**inputs)
            return self.valuate_manufacturing_stock(ticker, company_name, mfg_inputs, current_price_vnd)
        
        else:
            # Default to general DCF for other sectors
            raise ValueError(f"Sector-specific valuation not implemented for: {sector}")


# Convenience function
def valuate_vn_stock(ticker: str, company_name: str, sector: str,
                    inputs: Dict[str, Any], current_price_vnd: float) -> SectorValuationResult:
    """Quick valuation for Vietnamese stocks"""
    engine = VNSectorValuationEngine()
    return engine.valuate_by_sector(ticker, company_name, sector, inputs, current_price_vnd)
