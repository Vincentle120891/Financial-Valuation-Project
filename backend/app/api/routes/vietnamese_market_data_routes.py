"""
Vietnamese Stock Valuation API Routes

This module provides strict routing for Vietnamese stock valuation workflows.
It enforces complete separation from international workflows by:

1. Using only Vietnamese modules (vietnamese_inputs, vietnamese_input_manager, vietnamese_dcf_engine)
2. Routing exclusively through VND-currency endpoints
3. No imports from yfinance or international services
4. Dedicated endpoints: /vn-valuate, /vn-comps, /vn-dupont

NO CROSS-CONTAMINATION:
- Does NOT import international_routes or international dependencies
- Does NOT use yfinance_service or international_ticker_service
- Does NOT accept non-Vietnamese tickers
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
import logging

from app.models.vietnamese import (
    VietnameseDCFRequest,
    VietnameseCompsSelectionRequest,
    VietnameseCompsValuationRequest,
    VietnameseDuPontRequest,
    VNFinancialData
)
from app.services.vietnamese import get_vietnamese_input_manager
from app.services.vietnamese.vietnamese_dcf_engine import get_vietnamese_dcf_engine
from app.services.vietnamese.vietnamese_comps_engine import (
    VNTradingCompsAnalyzer,
    VNTargetCompanyData,
    VNPeerCompanyData,
)
from app.services.vietnamese.vietnamese_dupont_engine import (
    VNDuPontAnalyzer,
    VNFinancialStatements,
)
from app.services.vietnamese.step5_requirements_processor import (
    VNStep5RequirementsProcessor,
    VNRequirementsInput,
)
from app.services.vietnamese.step6_data_fetch_processor import (
    VNStep6DataFetchProcessor,
    VNDataFetchInput,
)
from app.services.vietnamese.step7_historical_processor import (
    VNStep7HistoricalProcessor,
    VNHistoricalDataInput,
)
from app.services.vietnamese.step8_assumptions_processor import (
    VNStep8AssumptionsProcessor,
    VNAIAssumptionsInput,
)
from app.core.session_service import session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vietnamese", tags=["Vietnamese Valuation"])


# ──────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ──────────────────────────────────────────────────────────────────────────────

class VNDcfRequest(BaseModel):
    """Request model for Vietnamese DCF valuation."""
    ticker: str = Field(..., description="Vietnamese ticker (e.g., VNM, VCB)")
    company_name: str = Field(..., description="Company name")
    exchange: str = Field(..., description="Exchange: HOSE, HNX, or UPCOM")
    sector: str = Field(..., description="Industry sector")
    current_price_vnd: float = Field(..., gt=0, description="Current price in VND")
    shares_outstanding: float = Field(..., gt=0, description="Shares outstanding")

    # Optional parameters with Vietnam defaults
    beta: Optional[float] = Field(1.0, ge=0, le=3.0)
    risk_free_rate_vn: Optional[float] = Field(None, ge=0.01, le=0.20)
    market_risk_premium_vn: Optional[float] = Field(None, ge=0.03, le=0.15)
    terminal_growth_rate: Optional[float] = Field(0.03, ge=0, le=0.08)
    forecast_years: int = Field(5, ge=3, le=10)
    wacc_override: Optional[float] = Field(None, ge=0, le=0.30)

    # Financial data for projections
    revenue: float = Field(..., gt=0, description="Base year revenue (tỷ VND)")
    ebit_margin: float = Field(..., gt=0, le=1, description="EBIT margin")
    depreciation: float = Field(0, ge=0, description="Depreciation (tỷ VND)")
    capex: float = Field(0, ge=0, description="CapEx (tỷ VND)")
    change_in_nwc: float = Field(0, description="Change in NWC (tỷ VND)")
    revenue_growth_rates: List[float] = Field(default_factory=lambda: [0.08] * 5)
    cost_of_debt: float = Field(0.10, ge=0, le=0.30, description="Cost of debt")
    debt_to_equity: float = Field(0.5, ge=0, description="D/E ratio")
    total_debt: float = Field(0, ge=0, description="Total debt (tỷ VND)")
    cash: float = Field(0, ge=0, description="Cash (tỷ VND)")


class VnCompsRequest(BaseModel):
    """Request model for Vietnamese comps analysis."""
    target_ticker: str = Field(..., description="Target ticker")
    target_company_name: str = Field(..., description="Target company name")
    sector: str = Field(..., description="Sector")

    # Target financials
    target_revenue_vnd: float = Field(..., gt=0, description="Revenue (tỷ VND)")
    target_ebitda_vnd: float = Field(..., gt=0, description="EBITDA (tỷ VND)")
    target_net_income_vnd: float = Field(..., description="Net income (tỷ VND)")
    target_eps_vnd: float = Field(..., description="EPS (VND)")
    target_book_value_vnd: float = Field(..., gt=0, description="Book value (tỷ VND)")

    # Peer data
    peer_multiples: List[Dict[str, Any]] = Field(..., min_length=3)

    # Filtering options
    apply_outlier_filtering: bool = Field(True)
    iqr_multiplier: float = Field(1.5, ge=0.5, le=3.0)
    outlier_metric: str = Field("ev_ebitda_ltm")


class VnDupontRequest(BaseModel):
    """Request model for Vietnamese DuPont analysis."""
    ticker: str = Field(..., description="Vietnamese ticker")
    company_name: str = Field(..., description="Company name")
    exchange: str = Field(..., description="Exchange: HOSE, HNX, or UPCOM")
    years: List[int] = Field(..., min_length=1, max_length=10)

    # Optional financial data by year
    financial_data_by_year: Optional[Dict[int, Dict[str, Any]]] = None

    # Or pre-calculated ratios
    custom_ratios: Optional[Dict[int, Dict[str, float]]] = None


# ──────────────────────────────────────────────────────────────────────────────
# DCF Valuation Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/vn-valuate", response_model=Dict[str, Any])
async def valuate_vietnamese_stock(request: VNDcfRequest):
    """
    Perform DCF valuation for a Vietnamese stock.

    This endpoint uses Vietnam-specific parameters:
    - Vietnam risk-free rate (10-year government bond)
    - Vietnam market risk premium
    - 20% corporate tax rate
    - All calculations in VND

    Args:
        request: VNDcfRequest with company and financial data

    Returns:
        Complete DCF valuation results including:
        - Intrinsic value per share (VND)
        - Upside/downside percentage
        - WACC breakdown
        - FCF projections
        - Terminal value calculation

    Example:
        POST /vietnamese/vn-valuate
        {
            "ticker": "VNM",
            "company_name": "Vinamilk",
            "exchange": "HOSE",
            "sector": "Consumer Goods",
            "current_price_vnd": 75000,
            "shares_outstanding": 1000000000,
            "revenue": 85500,
            "ebit_margin": 0.185,
            "depreciation": 2500,
            "capex": 3000,
            "total_debt": 5000,
            "cash": 8500
        }
    """
    try:
        # Get service components
        input_manager = get_vietnamese_input_manager()
        dcf_engine = get_vietnamese_dcf_engine()

        # Build Vietnamese DCF request
        dcf_request = input_manager.build_vn_dcf_request(
            ticker=request.ticker,
            company_name=request.company_name,
            exchange=request.exchange,
            sector=request.sector,
            current_price_vnd=request.current_price_vnd,
            shares_outstanding=request.shares_outstanding,
            risk_free_rate_vn=request.risk_free_rate_vn,
            market_risk_premium_vn=request.market_risk_premium_vn,
            beta=request.beta,
            terminal_growth_rate=request.terminal_growth_rate,
            forecast_years=request.forecast_years,
            wacc_override=request.wacc_override
        )

        # Prepare financial data
        financial_data = {
            'revenue': request.revenue,
            'ebit_margin': request.ebit_margin,
            'depreciation': request.depreciation,
            'capex': request.capex,
            'change_in_nwc': request.change_in_nwc,
            'revenue_growth_rates': request.revenue_growth_rates,
            'cost_of_debt': request.cost_of_debt,
            'debt_to_equity': request.debt_to_equity,
            'total_debt': request.total_debt,
            'cash': request.cash
        }

        # Perform DCF valuation
        valuation_results = dcf_engine.valuate_vn_dcf(
            request=dcf_request,
            financial_data=financial_data
        )

        return {
            "success": True,
            "ticker": request.ticker,
            "currency": "VND",
            "results": valuation_results
        }

    except ValueError as e:
        logger.error(f"Validation error for {request.ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        logger.error(f"DCF valuation failed for {request.ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation failed: {str(e)}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Comps Analysis Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/vn-comps", response_model=Dict[str, Any])
async def analyze_vietnamese_comps(request: VnCompsRequest):
    """
    Perform comparable company analysis for Vietnamese stocks.

    This endpoint:
    - Validates peer companies from Vietnamese market
    - Applies IQR outlier filtering on peer multiples
    - Calculates implied valuation multiples
    - Uses VND currency throughout

    Args:
        request: VnCompsRequest with target and peer data

    Returns:
        Comps analysis results including:
        - Filtered peer set
        - Mean/median multiples
        - Implied valuation ranges
        - Target company relative positioning

    Example:
        POST /vietnamese/vn-comps
        {
            "target_ticker": "VNM",
            "target_company_name": "Vinamilk",
            "sector": "Consumer Goods",
            "target_revenue_vnd": 85500,
            "target_ebitda_vnd": 18200,
            "peer_multiples": [...]
        }
    """
    try:
        # Get input manager
        input_manager = get_vietnamese_input_manager()

        # Build comps valuation request
        comps_request = input_manager.build_vn_comps_valuation_request(
            target_ticker=request.target_ticker,
            target_company_name=request.target_company_name,
            sector=request.sector,
            target_revenue_vnd=request.target_revenue_vnd,
            target_ebitda_vnd=request.target_ebitda_vnd,
            target_net_income_vnd=request.target_net_income_vnd,
            target_eps_vnd=request.target_eps_vnd,
            target_book_value_vnd=request.target_book_value_vnd,
            peer_multiples=request.peer_multiples,
            apply_outlier_filtering=request.apply_outlier_filtering,
            iqr_multiplier=request.iqr_multiplier,
            outlier_metric=request.outlier_metric
        )

        # Build target company data for VNTradingCompsAnalyzer
        # Calculate market cap from book value and estimated P/B (use median peer P/B as proxy)
        peer_pb_values = [p.pb_ratio for p in request.peer_multiples if p.pb_ratio and p.pb_ratio > 0]
        median_pb = sorted(peer_pb_values)[len(peer_pb_values)//2] if peer_pb_values else 1.5

        target_market_cap_vnd = request.target_book_value_vnd * median_pb
        target_enterprise_value_vnd = target_market_cap_vnd + request.target_net_income_vnd * 0.5  # Approximate net debt
        target_shares_outstanding = request.target_book_value_vnd / (request.target_book_value_vnd * 0.1)  # Approximate
        target_share_price_vnd = target_market_cap_vnd / target_shares_outstanding if target_shares_outstanding > 0 else request.target_eps_vnd * 10

        target_company = VNTargetCompanyData(
            ticker=request.target_ticker,
            company_name=request.target_company_name,
            market_cap_vnd=target_market_cap_vnd,
            enterprise_value_vnd=target_enterprise_value_vnd,
            ebitda_ltm_vnd=request.target_ebitda_vnd,
            eps_ltm_vnd=request.target_eps_vnd,
            net_debt_vnd=target_enterprise_value_vnd - target_market_cap_vnd,
            shares_outstanding=target_shares_outstanding,
            share_price_vnd=target_share_price_vnd,
            sector=request.sector
        )

        # Build peer company data list
        peer_companies = []
        for peer in request.peer_multiples:
            # Calculate peer metrics from provided multiples
            peer_market_cap = peer.book_value * peer.pb_ratio if peer.pb_ratio and peer.book_value else 0
            peer_ebitda = peer.enterprise_value / peer.ev_ebitda_ltm if peer.ev_ebitda_ltm and peer.ev_ebitda_ltm > 0 else 0
            peer_eps = peer.share_price / peer.pe_ltm if peer.pe_ltm and peer.pe_ltm > 0 else 0
            peer_shares = peer_market_cap / peer.share_price if peer.share_price and peer.share_price > 0 else 1

            peer_company = VNPeerCompanyData(
                ticker=peer.ticker,
                company_name=peer.company_name,
                market_cap_vnd=peer_market_cap,
                enterprise_value_vnd=peer.enterprise_value,
                share_price_vnd=peer.share_price,
                shares_outstanding=peer_shares,
                ebitda_ltm_vnd=peer_ebitda,
                eps_ltm_vnd=peer_eps,
                revenue_ltm_vnd=peer.revenue or 0,
                net_income_ltm_vnd=peer.net_income or 0,
                book_value_vnd=peer.book_value or 0,
                sector=request.sector
            )
            peer_companies.append(peer_company)

        # Run comps analysis using VNTradingCompsAnalyzer
        analyzer = VNTradingCompsAnalyzer(target_company, peer_companies)
        comps_results = analyzer.run_analysis(
            apply_outlier_filtering=request.apply_outlier_filtering,
            iqr_multiplier=request.iqr_multiplier,
            outlier_metric=request.outlier_metric
        )

        # Convert results to API response format
        results = comps_results.to_dict()

        return {
            "success": True,
            "results": results
        }

    except ValueError as e:
        logger.error(f"Validation error for comps {request.target_ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Comps analysis failed for {request.target_ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comps analysis failed: {str(e)}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# DuPont Analysis Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/vn-dupont", response_model=Dict[str, Any])
async def analyze_vietnamese_dupont(request: VnDupontRequest):
    """
    Perform DuPont analysis for Vietnamese companies.

    Decomposes ROE into three components using TT99 financial statements:
    1. Net Profit Margin (Profitability)
    2. Asset Turnover (Efficiency)
    3. Equity Multiplier (Leverage)

    Formula: ROE = Net Profit Margin × Asset Turnover × Equity Multiplier

    Args:
        request: VnDupontRequest with ticker and financial data

    Returns:
        DuPont analysis results including:
        - Component breakdown by year
        - Trend analysis
        - ROE decomposition
        - Comparative metrics

    Example:
        POST /vietnamese/vn-dupont
        {
            "ticker": "VNM",
            "company_name": "Vinamilk",
            "exchange": "HOSE",
            "years": [2021, 2022, 2023],
            "financial_data_by_year": {
                "2023": {
                    "net_income": 12700,
                    "revenue": 85500,
                    "total_assets": 50500,
                    "shareholders_equity": 32300
                }
            }
        }
    """
    try:
        # Get input manager
        input_manager = get_vietnamese_input_manager()

        # Build DuPont request
        dupont_request = input_manager.build_vn_dupont_request(
            ticker=request.ticker,
            company_name=request.company_name,
            exchange=request.exchange,
            years=request.years,
            financial_data_by_year=request.financial_data_by_year,
            custom_ratios=request.custom_ratios
        )

        # Build VNFinancialStatements from the request data
        statements = VNFinancialStatements()

        # Map financial data by year to the 8-year arrays
        # We'll use the first few years based on how many years are requested
        num_years = min(len(request.years), 8)

        if dupont_request.financial_data_by_year:
            for idx, year in enumerate(request.years[:num_years]):
                if str(year) in dupont_request.financial_data_by_year or year in dupont_request.financial_data_by_year:
                    year_key = str(year) if str(year) in dupont_request.financial_data_by_year else year
                    data = dupont_request.financial_data_by_year[year_key]

                    # Map income statement items
                    if idx < len(statements.revenue):
                        statements.revenue[idx] = data.get('revenue', 0)
                        statements.cogs_gross[idx] = -data.get('cogs', abs(data.get('gross_profit', 0)) - data.get('revenue', 0))
                        statements.sga[idx] = -data.get('sga', 0)
                        statements.other_operating_expenses[idx] = -data.get('other_operating_expenses', 0)
                        statements.depreciation[idx] = -data.get('depreciation', 0)
                        statements.interest_expense[idx] = -data.get('interest_expense', 0)
                        statements.interest_income[idx] = data.get('interest_income', 0)
                        statements.tax_current[idx] = -data.get('tax_current', 0)

                        # Balance sheet items
                        statements.cash[idx] = data.get('cash', 0)
                        statements.accounts_receivable[idx] = data.get('accounts_receivable', 0)
                        statements.inventories[idx] = data.get('inventories', 0)
                        statements.ppe_component1[idx] = data.get('ppe', 0)
                        statements.accounts_payable[idx] = data.get('accounts_payable', 0)
                        statements.revolving_credit[idx] = data.get('short_term_debt', 0)
                        statements.long_term_debt[idx] = data.get('long_term_debt', 0)
                        statements.common_equity[idx] = data.get('shareholders_equity', 0)
                        statements.retained_earnings[idx] = data.get('retained_earnings', 0)

                        # Vietnam-specific
                        statements.state_ownership_percent[idx] = data.get('state_ownership_percent', 0)
                        statements.fol_remaining[idx] = data.get('fol_remaining', 49.0)

        # Run DuPont analysis using VNDuPontAnalyzer
        analyzer = VNDuPontAnalyzer()
        analyzer.load_data(statements)
        dupont_result = analyzer.calculate_all()

        # Convert results to API response format
        results = dupont_result.to_dict()

        return {
            "success": True,
            "results": results
        }

    except ValueError as e:
        logger.error(f"Validation error for DuPont {request.ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        logger.error(f"DuPont analysis failed for {request.ticker}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DuPont analysis failed: {str(e)}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Health Check & Info Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/vn-info")
async def get_vietnamese_workflow_info():
    """
    Get information about Vietnamese valuation workflow.

    Returns details about:
    - Supported exchanges (HOSE, HNX, UPCOM)
    - Vietnam-specific parameters
    - Available endpoints
    """
    return {
        "workflow": "Vietnamese Stock Valuation",
        "isolation": "Complete separation from international workflows",
        "supported_exchanges": ["HOSE", "HNX", "UPCOM"],
        "currency": "VND (Vietnamese Dong)",
        "accounting_standard": "TT99 (Thông Tư 99/2025/TT-BTC)",
        "vietnam_parameters": {
            "corporate_tax_rate": "20%",
            "risk_free_rate_default": "~6.8% (10-year government bond)",
            "market_risk_premium_default": "~7.5%",
            "terminal_growth_max": "~6% (aligned with GDP growth)"
        },
        "endpoints": {
            "/vn-valuate": "DCF valuation",
            "/vn-comps": "Comparable company analysis",
            "/vn-dupont": "DuPont ROE decomposition"
        },
        "data_sources": [
            "VNStockDatabase",
            "vndirect API",
            "cafef.vn",
            "Company official reports"
        ]
    }


# ──────────────────────────────────────────────────────────────────────────────
# Step 5: Requirements & Parameters (Vietnamese Market)
# ──────────────────────────────────────────────────────────────────────────────

class VNStep5Request(BaseModel):
    """Request model for Vietnamese Step 5 requirements collection."""
    session_id: str = Field(..., description="Session identifier")
    method: str = Field(..., description="Valuation method: DCF, DuPont, or Comps")

    # DCF-specific parameters
    dcf_forecast_years: int = Field(default=5, ge=3, le=10)
    dcf_terminal_growth_rate: float = Field(default=0.03, ge=0.0, le=0.08)
    dcf_risk_free_rate: float = Field(default=0.068, ge=0.0, le=0.20)
    dcf_market_risk_premium: float = Field(default=0.075, ge=0.0, le=0.15)
    dcf_country_risk_premium: float = Field(default=0.035, ge=0.0, le=0.10)
    dcf_tax_rate: float = Field(default=0.20, ge=0.0, le=0.50)
    dcf_beta: Optional[float] = Field(default=None, ge=-2.0, le=3.0)

    # DuPont-specific parameters
    dupont_peer_count: int = Field(default=5, ge=3, le=10)
    dupont_industry_focus: Optional[str] = Field(default=None)

    # Comps-specific parameters
    comps_peer_count: int = Field(default=5, ge=3, le=10)
    comps_multiples: List[str] = Field(default=["P/E", "P/B", "EV/EBITDA", "P/S"])
    comps_liquidity_filter_days: int = Field(default=60, ge=30, le=252)

    # General parameters
    currency: str = Field(default="VND")
    fiscal_year_end: str = Field(default="12-31", pattern=r"^\d{2}-\d{2}$")

    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate valuation method."""
        allowed_methods = ["DCF", "DuPont", "COMPS", "dcf", "dupont", "comps"]
        if v.upper() not in [m.upper() for m in allowed_methods]:
            raise ValueError(f"Method must be one of: DCF, DuPont, COMPS")
        return v.upper()

    @field_validator('comps_multiples')
    @classmethod
    def validate_multiples(cls, v: List[str]) -> List[str]:
        """Validate that only supported multiples are used."""
        allowed_multiples = {"P/E", "P/B", "EV/EBITDA", "P/S", "PEG", "P/FCF", "EV/Sales"}
        invalid = [m for m in v if m not in allowed_multiples]
        if invalid:
            raise ValueError(f"Unsupported multiples: {invalid}. Allowed: {allowed_multiples}")
        return v


class VNStep5Response(BaseModel):
    """Response model for Vietnamese Step 5 requirements collection."""
    session_id: str
    status: str
    dcf_parameters: Dict[str, Any]
    dupont_parameters: Dict[str, Any]
    comps_parameters: Dict[str, Any]
    parameter_validation: Dict[str, bool]
    market_context: Dict[str, Any]
    input_sources: Dict[str, str]
    message: str
    next_step: int


@router.post("/vn-step-5-collect-requirements", response_model=VNStep5Response)
async def collect_vn_requirements(request: VNStep5Request):
    """
    Step 5: Collect Valuation Requirements & Parameters (Vietnamese Market)

    Collects and validates all valuation parameters specific to Vietnamese market,
    ensuring complete transparency and adherence to Model Integrity principles.

    This step gathers:
    - Forecast periods and growth assumptions
    - Risk-free rates (Vietnamese government bonds)
    - Market risk premiums (Vietnam-specific)
    - Country risk premiums
    - Tax rates (Vietnamese corporate tax)
    - Currency settings (VND)
    - Model-specific parameters

    Vietnam-Specific Features:
    - Uses Vietnamese 10Y government bond yield for risk-free rate (~6.8%)
    - Applies Vietnam-specific market risk premium (~7.5%)
    - Includes country risk premium for emerging market (~3.5%)
    - Standard corporate tax rate of 20% per Vietnamese Tax Law
    - GDP growth reference for terminal value (~5.5%)

    Args:
        request: VNStep5Request with session_id, method, and all parameters

    Returns:
        VNStep5Response with:
        - Validated parameters by model (DCF, DuPont, Comps)
        - Market context and benchmarks
        - Input source tracking
        - Validation status

    Example:
        POST /vietnamese/vn-step-5-collect-requirements
        {
            "session_id": "vn-session-123",
            "method": "DCF",
            "dcf_forecast_years": 5,
            "dcf_terminal_growth_rate": 0.03,
            "dcf_risk_free_rate": 0.068,
            "dcf_market_risk_premium": 0.075,
            "dcf_country_risk_premium": 0.035,
            "dcf_tax_rate": 0.20,
            "comps_peer_count": 5,
            "comps_multiples": ["P/E", "P/B", "EV/EBITDA", "P/S"]
        }
    """
    try:
        # Get session data
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        company_name = session.get("company_name", ticker)
        exchange = session.get("exchange", "HOSE")

        if not ticker:
            raise HTTPException(status_code=400, detail="No ticker found in session")

        # Build input for Vietnamese Step 5 processor
        vn_input = VNRequirementsInput(
            session_id=request.session_id,
            dcf_forecast_years=request.dcf_forecast_years,
            dcf_terminal_growth_rate=request.dcf_terminal_growth_rate,
            dcf_risk_free_rate=request.dcf_risk_free_rate,
            dcf_market_risk_premium=request.dcf_market_risk_premium,
            dcf_country_risk_premium=request.dcf_country_risk_premium,
            dcf_tax_rate=request.dcf_tax_rate,
            dcf_beta=request.dcf_beta,
            dupont_peer_count=request.dupont_peer_count,
            dupont_industry_focus=request.dupont_industry_focus,
            comps_peer_count=request.comps_peer_count,
            comps_multiples=request.comps_multiples,
            comps_liquidity_filter_days=request.comps_liquidity_filter_days,
            currency=request.currency,
            fiscal_year_end=request.fiscal_year_end
        )

        # Execute Vietnamese Step 5 processor
        processor = VNStep5RequirementsProcessor(session_service=session_service)
        result = await processor.process(vn_input)

        # Update session step
        market = "vietnam"
        method = request.method.upper()
        session_service.update_session_step(
            request.session_id,
            step_number=5,
            market=market,
            method=method.lower()
        )

        logger.info(
            f"VN Step 5 complete for {ticker}: "
            f"Parameters validated for DCF={result.parameter_validation.get('dcf')}, "
            f"DuPont={result.parameter_validation.get('dupont')}, "
            f"Comps={result.parameter_validation.get('comps')}"
        )

        return VNStep5Response(
            session_id=result.session_id,
            status="requirements_collected",
            dcf_parameters=result.dcf_parameters,
            dupont_parameters=result.dupont_parameters,
            comps_parameters=result.comps_parameters,
            parameter_validation=result.parameter_validation,
            market_context=result.market_context,
            input_sources=result.input_sources,
            message=f"Requirements collected successfully. "
                    f"Risk-free rate: {result.dcf_parameters.get('risk_free_rate', 0)*100:.1f}%, "
                    f"Market premium: {result.dcf_parameters.get('market_risk_premium', 0)*100:.1f}%, "
                    f"Tax rate: {result.dcf_parameters.get('tax_rate', 0)*100:.0f}%",
            next_step=result.next_step
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VN Step 5 requirements collection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Step 6: Data Fetch (Vietnamese Market) - "Fetch Once, Use Many"
# ──────────────────────────────────────────────────────────────────────────────

class VNStep6FetchRequest(BaseModel):
    """Request model for Vietnamese Step 6 data fetch."""
    session_id: str = Field(..., description="Session identifier")
    method: str = Field(..., description="Valuation method: DCF, DuPont, or Comps")
    history_years: int = Field(default=5, ge=3, le=10, description="Number of historical years to fetch")
    include_quarterly: bool = Field(default=True, description="Include quarterly data for TTM")
    fetch_peer_data: bool = Field(default=False, description="Fetch peer data if Comps model selected")
    peer_tickers: List[str] = Field(default_factory=list, description="List of peer tickers to fetch")
    fallback_to_ai_extraction: bool = Field(default=True, description="Allow AI PDF extraction if API fails")

    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate valuation method."""
        allowed_methods = ["DCF", "DuPont", "COMPS", "dcf", "dupont", "comps"]
        if v.upper() not in [m.upper() for m in allowed_methods]:
            raise ValueError(f"Method must be one of: DCF, DuPont, COMPS")
        return v.upper()


class VNStep6FetchResponse(BaseModel):
    """Response model for Vietnamese Step 6 data fetch."""
    session_id: str
    status: str
    ticker: str
    success: bool
    source_provider: str
    fetch_timestamp: str
    currency_unit: str
    periods_fetched: List[str]
    missing_periods: List[str]
    data_quality_flags: List[str]
    pdf_sources_used: List[str]
    message: str
    next_step: str = "step7_historical_processing"


@router.post("/vn-step-6-fetch-data", response_model=VNStep6FetchResponse)
async def fetch_vn_data(request: VNStep6FetchRequest):
    """
    Step 6: Fetch Raw Financial Data (Vietnamese Market)
    
    Implements "Fetch Once, Use Many" architecture for Vietnamese market:
    - Fetches ALL market data in ONE API call
    - Stores in shared cache session['vietnam_market_data']
    - Reuses cached data when switching between DCF/DuPont/Comps models
    
    Vietnam-Specific Features:
    - Uses Vietnamese data sources (Vietstock, FireAnt, company reports)
    - Handles VND currency and TT99 accounting standards
    - Falls back to AI PDF extraction for missing data
    - Fetches peer data for Comps/WACC calculations
    
    Args:
        request: VNStep6FetchRequest with session_id, method, and fetch parameters
        
    Returns:
        VNStep6FetchResponse with:
        - Fetched data summary
        - Source provider information
        - Data quality flags
        - Periods covered
        
    Example:
        POST /vietnamese/vn-step-6-fetch-data
        {
            "session_id": "vn-session-123",
            "method": "DCF",
            "history_years": 5,
            "include_quarterly": true,
            "fetch_peer_data": false
        }
    """
    try:
        # Get session data
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        ticker = session.get("ticker")
        company_name = session.get("company_name", ticker)
        exchange = session.get("exchange", "HOSE")
        
        if not ticker:
            raise HTTPException(status_code=400, detail="No ticker found in session")
        
        # GAP 1 FIX: Check session cache for "Fetch Once, Use Many"
        market = "vietnam"
        method = request.method.upper()
        
        # Check if vietnam_market_data already exists in session cache
        cached_market_data = session_service.get_session_value(
            request.session_id,
            "vietnam_market_data"
        )
        
        if cached_market_data:
            # Check cache age (valid for 5 minutes)
            from datetime import datetime, timedelta
            cache_timestamp = cached_market_data.get('timestamp')
            if cache_timestamp:
                cache_age = datetime.now() - cache_timestamp
                if cache_age < timedelta(minutes=5):
                    logger.info(f"Using cached Vietnam market data for {ticker} (age: {cache_age.seconds}s)")
                    # Return cached data without re-fetching
                    return VNStep6FetchResponse(
                        session_id=request.session_id,
                        status="cached_data_used",
                        ticker=ticker,
                        success=True,
                        source_provider=cached_market_data.get('source_provider', 'cache'),
                        fetch_timestamp=cached_market_data.get('fetch_timestamp', '').isoformat() if hasattr(cached_market_data.get('fetch_timestamp'), 'isoformat') else str(cached_market_data.get('fetch_timestamp', '')),
                        currency_unit=cached_market_data.get('currency_unit', 'millions_VND'),
                        periods_fetched=cached_market_data.get('periods_fetched', []),
                        missing_periods=cached_market_data.get('missing_periods', []),
                        data_quality_flags=cached_market_data.get('data_quality_flags', []),
                        pdf_sources_used=cached_market_data.get('pdf_sources_used', []),
                        message=f"Using cached data for {ticker} - no API call needed"
                    )
        
        # Build input for Vietnamese Step 6 processor
        vn_input = VNDataFetchInput(
            ticker=ticker,
            company_name=company_name,
            exchange=exchange,
            currency="VND",
            history_years=request.history_years,
            include_quarterly=request.include_quarterly,
            fetch_income_statement=True,
            fetch_balance_sheet=True,
            fetch_cash_flow=True,
            fetch_peer_data=request.fetch_peer_data,
            peer_tickers=request.peer_tickers,
            preferred_source="vietstock",
            fallback_to_ai_extraction=request.fallback_to_ai_extraction
        )
        
        # Execute Vietnamese Step 6 processor with session cache for "Fetch Once, Use Many"
        processor = VNStep6DataFetchProcessor()
        result = await processor.execute(vn_input, session_cache=session)
        
        # GAP 1 FIX: Store fetched data in session cache for "Fetch Once, Use Many"
        if result.success:
            from datetime import datetime
            cache_data = {
                'timestamp': datetime.now(),
                'source_provider': result.data_bundle.source_provider,
                'fetch_timestamp': result.data_bundle.fetch_timestamp,
                'currency_unit': result.data_bundle.currency_unit,
                'income_statement_raw': result.data_bundle.income_statement_raw,
                'balance_sheet_raw': result.data_bundle.balance_sheet_raw,
                'cash_flow_raw': result.data_bundle.cash_flow_raw,
                'peer_data_raw': result.data_bundle.peer_data_raw,
                'missing_periods': result.data_bundle.missing_periods,
                'data_quality_flags': result.data_bundle.data_quality_flags,
                'pdf_sources_used': result.data_bundle.pdf_sources_used,
                'periods_fetched': list(result.data_bundle.income_statement_raw.keys()) if result.data_bundle.income_statement_raw else []
            }
            
            # Store in session under shared cache key
            session_service.update_session_value(
                request.session_id,
                "vietnam_market_data",
                cache_data
            )
            
            # Also store in method-specific track for backward compatibility
            session_service.update_session_data(
                request.session_id,
                "financial_data",
                cache_data,
                market=market,
                method=method.lower()
            )
            
            logger.info(f"Cached Vietnam market data for {ticker} in session")
        
        return VNStep6FetchResponse(
            session_id=request.session_id,
            status="data_fetched" if result.success else "partial_success",
            ticker=ticker,
            success=result.success,
            source_provider=result.data_bundle.source_provider,
            fetch_timestamp=result.data_bundle.fetch_timestamp.isoformat() if hasattr(result.data_bundle.fetch_timestamp, 'isoformat') else str(result.data_bundle.fetch_timestamp),
            currency_unit=result.data_bundle.currency_unit,
            periods_fetched=list(result.data_bundle.income_statement_raw.keys()) if result.data_bundle.income_statement_raw else [],
            missing_periods=result.data_bundle.missing_periods,
            data_quality_flags=result.data_bundle.data_quality_flags,
            pdf_sources_used=result.data_bundle.pdf_sources_used,
            message=result.message,
            next_step=result.next_step
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VN Step 6 data fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Step 7: Historical Data Retrieval (Vietnamese Market)
# ──────────────────────────────────────────────────────────────────────────────

class VNStep7Request(BaseModel):
    """Request model for Vietnamese Step 7 historical data retrieval."""
    session_id: str = Field(..., description="Session identifier")
    method: str = Field(..., description="Valuation method: DCF, DuPont, or Comps")

    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate valuation method."""
        allowed_methods = ["DCF", "DuPont", "COMPS", "dcf", "dupont", "comps"]
        if v.upper() not in [m.upper() for m in allowed_methods]:
            raise ValueError(f"Method must be one of: DCF, DuPont, COMPS")
        return v.upper()


class VNStep7Response(BaseModel):
    """Response model for Vietnamese Step 7 historical data retrieval."""
    status: str
    ticker: str
    success: bool
    completeness_score: float
    periods_covered: List[str]
    missing_critical_fields: List[str]
    data_warnings: List[str]
    source_breakdown: Dict[str, int]
    message: str


@router.post("/vn-step-7-retrieve-historical-data", response_model=VNStep7Response)
async def retrieve_vn_historical_data(request: VNStep7Request):
    """
    Step 7: Retrieve Historical Data Using AI Extraction (Vietnamese Market)

    Uses AI to extract historical financial data from Vietnamese sources when
    standard APIs don't have complete data. This is strictly for HISTORICAL data
    retrieval - NO forward-looking assumptions are generated here.

    Purpose:
    - Fill gaps in historical financial statements from Vietnamese sources
    - Extract historical metrics from PDF reports (annual reports, filings) using AI
    - Provide complete historical dataset for Step 8 assumption generation

    Vietnam-Specific Features:
    - Maps Vietnamese accounting terms (TT99) to standard English keys
    - Validates accounting identity (Assets = Liabilities + Equity)
    - Extracts from Vietnamese PDF sources (cafef.vn, company reports)
    - Handles VND currency units properly

    Args:
        request: VNStep7Request with session_id and method

    Returns:
        VNStep7Response with:
        - Completeness score (0-1)
        - Periods covered
        - Missing critical fields
        - Data warnings
        - Source breakdown (API vs AI)

    Example:
        POST /vietnamese/vn-step-7-retrieve-historical-data
        {
            "session_id": "vn-session-123",
            "method": "DCF"
        }
    """
    try:
        # Get session data
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        company_name = session.get("company_name", ticker)
        exchange = session.get("exchange", "HOSE")

        if not ticker:
            raise HTTPException(status_code=400, detail="No ticker found in session")

        # Get financial data from the specific valuation track
        market = "vietnam"
        method = request.method.upper()

        financial_data = session_service.get_session_value(
            request.session_id,
            "financial_data",
            market=market,
            method=method.lower()
        )

        # Fallback to shared context if not found in track
        if not financial_data:
            financial_data = session_service.get_session_value(
                request.session_id,
                "financial_data"
            )

        if not financial_data:
            raise HTTPException(status_code=400, detail="No financial data available")

        # Build input for Vietnamese Step 7 processor
        vn_input = VNHistoricalDataInput(
            ticker=ticker,
            company_name=company_name,
            exchange=exchange,
            currency_unit=financial_data.get("currency_unit", "millions_VND"),
            income_statement_raw=financial_data.get("income_statement", {}),
            balance_sheet_raw=financial_data.get("balance_sheet", {}),
            cash_flow_raw=financial_data.get("cash_flow", {}),
            data_quality_flags=financial_data.get("quality_flags", []),
            pdf_sources=financial_data.get("pdf_sources", []),
            fallback_to_ai=True,
            selected_model=method
        )

        # Execute Vietnamese Step 7 processor
        processor = VNStep7HistoricalProcessor()
        result = await processor.execute(vn_input)

        # Store historical data in session
        session_service.update_session_data(
            request.session_id,
            "historical_data_gaps_filled",
            result.model_dump() if hasattr(result, 'model_dump') else result.dict(),
            market=market,
            method=method.lower()
        )

        session_service.update_session_step(
            request.session_id,
            step_number=7,
            market=market,
            method=method.lower()
        )

        logger.info(
            f"VN Step 7 complete for {ticker}: "
            f"{result.completeness_score:.1%} completeness, "
            f"{len(result.periods_covered)} periods covered"
        )

        return VNStep7Response(
            status="historical_data_ready" if result.success else "partial_success",
            ticker=ticker,
            success=result.success,
            completeness_score=result.completeness_score,
            periods_covered=result.periods_covered,
            missing_critical_fields=result.missing_critical_fields,
            data_warnings=result.data_warnings,
            source_breakdown=result.source_breakdown,
            message=f"Historical data retrieval complete. "
                    f"Completeness: {result.completeness_score:.1%}. "
                    f"Periods: {', '.join(result.periods_covered)}."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VN Step 7 historical data retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Step 8: AI Assumptions Generation (Vietnamese Market)
# ──────────────────────────────────────────────────────────────────────────────

class VNStep8InitializeRequest(BaseModel):
    """Request model for Vietnamese Step 8 initialization."""
    session_id: str = Field(..., description="Session identifier")
    method: str = Field(..., description="Valuation method: DCF, DuPont, or Comps")

    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate valuation method."""
        allowed_methods = ["DCF", "DuPont", "COMPS", "dcf", "dupont", "comps"]
        if v.upper() not in [m.upper() for m in allowed_methods]:
            raise ValueError(f"Method must be one of: DCF, DuPont, COMPS")
        return v.upper()


class VNStep8InitializeResponse(BaseModel):
    """Response model for Vietnamese Step 8 initialization."""
    session_id: str
    model_type: str
    assumptions: List[Dict[str, Any]]
    sector_analysis: Dict[str, Any]
    macro_integration: Dict[str, Any]
    warnings: List[str]
    status: str
    message: str


@router.post("/vn-step-8-initialize", response_model=VNStep8InitializeResponse)
async def initialize_vn_step8_assumptions(request: VNStep8InitializeRequest):
    """
    Step 8: Initialize AI Assumptions (Vietnamese Market)

    Generates forward-looking assumptions calibrated for Vietnamese market conditions.
    Uses historical data from Step 7 and Vietnam-specific macroeconomic indicators.

    Vietnam-Specific Features:
    - Sector-specific growth ranges for Vietnamese industries
    - Vietnam macroeconomic integration (GDP growth, inflation, risk-free rate)
    - Country risk premium calibration
    - TT99 accounting standard compliance
    - Exchange-specific considerations (HOSE, HNX, UPCOM)

    Args:
        request: VNStep8InitializeRequest with session_id and method

    Returns:
        VNStep8InitializeResponse with:
        - AI-generated assumptions with confidence scores
        - Sector analysis for Vietnamese market
        - Macro integration details
        - Warnings for Vietnam-specific risks

    Example:
        POST /vietnamese/vn-step-8-initialize
        {
            "session_id": "vn-session-123",
            "method": "DCF"
        }
    """
    try:
        # Get session data
        session = session_service.get_session_data(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ticker = session.get("ticker")
        company_name = session.get("company_name", ticker)
        exchange = session.get("exchange", "HOSE")
        sector = session.get("sector", "General")
        industry = session.get("industry", sector)

        if not ticker:
            raise HTTPException(status_code=400, detail="No ticker found in session")

        # Get data from the specific valuation track
        market = "vietnam"
        method = request.method.upper()

        step6_data = session_service.get_session_value(
            request.session_id,
            "financial_data",
            {},
            market=market,
            method=method.lower()
        )

        step7_data = session_service.get_session_value(
            request.session_id,
            "historical_data_gaps_filled",
            {},
            market=market,
            method=method.lower()
        )

        # Build input for Vietnamese Step 8 processor
        vn_input = VNAIAssumptionsInput(
            session_id=request.session_id,
            company_name=company_name,
            ticker=ticker,
            exchange=exchange,  # type: ignore
            selected_model=method.lower(),  # type: ignore
            sector=sector,
            industry=industry,
            historical_financials=step7_data.get("normalized_financials", {}) if step7_data else step6_data,
            vietnam_macro={
                "gdp_growth": 0.055,
                "inflation_target": 0.04,
                "risk_free_rate": 0.068,
                "country_risk_premium": 0.035
            }
        )

        # Execute Vietnamese Step 8 processor
        processor = VNStep8AssumptionsProcessor()
        result = await processor.process(vn_input)

        # Store assumptions in session
        session_service.update_session_data(
            request.session_id,
            "step8_assumptions",
            result.model_dump() if hasattr(result, 'model_dump') else result.dict(),
            market=market,
            method=method.lower()
        )

        session_service.update_session_step(
            request.session_id,
            step_number=8,
            market=market,
            method=method.lower()
        )

        logger.info(
            f"VN Step 8 initialized for {ticker}: "
            f"{len(result.assumptions)} assumptions generated"
        )

        # Convert assumptions to dict format
        assumptions_dict = []
        for assumption in result.assumptions:
            assumptions_dict.append(assumption.model_dump() if hasattr(assumption, 'model_dump') else assumption.dict())

        return VNStep8InitializeResponse(
            session_id=request.session_id,
            model_type=result.model_type,
            assumptions=assumptions_dict,
            sector_analysis=result.sector_analysis,
            macro_integration=result.macro_integration,
            warnings=result.warnings,
            status=result.status,
            message=f"Generated {len(result.assumptions)} AI assumptions for {method} valuation"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VN Step 8 initialization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))