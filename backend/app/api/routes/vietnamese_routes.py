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
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from app.models.vietnamese_inputs import (
    VietnameseDCFRequest,
    VietnameseCompsSelectionRequest,
    VietnameseCompsValuationRequest,
    VietnameseDuPontRequest,
    VNFinancialData
)
from app.services.vietnamese_input_manager import get_vietnamese_input_manager
from app.engines.vietnamese_dcf_engine import get_vietnamese_dcf_engine

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
        
        # Calculate peer statistics
        peers = comps_request.peer_multiples
        
        # Extract multiples for statistical analysis
        ev_ebitda_values = [p.ev_ebitda_ltm for p in peers if p.ev_ebitda_ltm > 0]
        pe_values = [p.pe_ltm for p in peers if p.pe_ltm != 0]
        pb_values = [p.pb_ratio for p in peers if p.pb_ratio > 0]
        
        def calc_stats(values):
            if not values:
                return {'mean': 0, 'median': 0, 'min': 0, 'max': 0}
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            mean_val = sum(sorted_vals) / n
            median_val = sorted_vals[n // 2] if n % 2 == 1 else (sorted_vals[n//2 - 1] + sorted_vals[n//2]) / 2
            return {
                'mean': round(mean_val, 2),
                'median': round(median_val, 2),
                'min': round(min(sorted_vals), 2),
                'max': round(max(sorted_vals), 2)
            }
        
        # Calculate implied valuations
        implied_ev_ebitda = comps_request.target_ebitda_vnd * calc_stats(ev_ebitda_values)['median']
        implied_pe = comps_request.target_net_income_vnd * calc_stats(pe_values)['median']
        
        results = {
            "target_ticker": request.target_ticker,
            "target_company_name": request.target_company_name,
            "sector": request.sector,
            "currency": "VND",
            "peer_analysis": {
                "num_peers_initial": len(request.peer_multiples),
                "num_peers_after_filtering": len(peers),
                "peers_used": [p.ticker for p in peers]
            },
            "multiple_statistics": {
                "ev_ebitda": calc_stats(ev_ebitda_values),
                "pe_ratio": calc_stats(pe_values),
                "pb_ratio": calc_stats(pb_values)
            },
            "implied_valuations": {
                "implied_ev_from_ebitda": round(implied_ev_ebitda, 2),
                "implied_equity_from_pe": round(implied_pe, 2)
            },
            "target_metrics": {
                "revenue_vnd": request.target_revenue_vnd,
                "ebitda_vnd": request.target_ebitda_vnd,
                "net_income_vnd": request.target_net_income_vnd,
                "eps_vnd": request.target_eps_vnd,
                "book_value_vnd": request.target_book_value_vnd
            }
        }
        
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
        
        # Process results
        results = {
            "ticker": request.ticker,
            "company_name": request.company_name,
            "exchange": request.exchange,
            "currency": "VND",
            "analysis_years": request.years,
            "dupont_components": {}
        }
        
        # Calculate or use provided ratios
        if dupont_request.custom_ratios:
            for year in request.years:
                if year in dupont_request.custom_ratios:
                    components = dupont_request.custom_ratios[year]
                    results["dupont_components"][str(year)] = {
                        "net_profit_margin": round(components.net_profit_margin, 4),
                        "asset_turnover": round(components.asset_turnover, 4),
                        "equity_multiplier": round(components.equity_multiplier, 4),
                        "roe": round(components.roe, 4) if components.roe else None,
                        "raw_data": {
                            "net_income_vnd": components.net_income_vnd,
                            "revenue_vnd": components.revenue_vnd,
                            "total_assets_vnd": components.total_assets_vnd,
                            "shareholders_equity_vnd": components.shareholders_equity_vnd
                        }
                    }
        
        # Add trend analysis if multiple years
        if len(request.years) > 1 and results["dupont_components"]:
            years_sorted = sorted(results["dupont_components"].keys())
            roe_values = [
                results["dupont_components"][y]["roe"]
                for y in years_sorted
                if results["dupont_components"][y]["roe"] is not None
            ]
            
            if len(roe_values) > 1:
                roe_change = (roe_values[-1] - roe_values[0]) / roe_values[0] if roe_values[0] != 0 else 0
                results["trend_analysis"] = {
                    "roe_change_pct": round(roe_change * 100, 2),
                    "trend_direction": "IMPROVING" if roe_change > 0 else "DECLINING"
                }
        
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
