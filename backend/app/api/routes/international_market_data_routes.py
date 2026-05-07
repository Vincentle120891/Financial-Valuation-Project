"""
API Routes for International & Vietnamese Tickers
Separate endpoints for non-US markets with specialized handling
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from pydantic import BaseModel
import logging

from app.services.international import InternationalTickerService
from app.services.vietnamese import VietnameseTickerService
from app.services.international import MetricsCalculator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["International & Vietnamese Tickers"])

# Initialize services
intl_service = InternationalTickerService()
vn_service = VietnameseTickerService()
metrics_calc = MetricsCalculator()


class TickerRequest(BaseModel):
    ticker: str
    market_code: str = "VN"
    include_estimates: bool = True
    include_historical: bool = True


class VietnamTickerRequest(BaseModel):
    ticker: str
    market_code: str = "VN"
    include_peers: bool = True
    include_index_data: bool = True
    enhanced_mode: bool = True


@router.get("/international/tickers")
async def list_international_markets():
    """
    List all supported international markets and their suffixes
    """
    return {
        "markets": intl_service.MARKET_SUFFIXES,
        "currencies": intl_service.MARKET_CURRENCIES,
        "vietnam_markets": intl_service.VIETNAM_MARKETS,
        "note": "Use market_code when fetching data for international tickers"
    }


@router.get("/international/fetch")
async def fetch_international_ticker(
    ticker: str = Query(..., description="Base ticker symbol (e.g., 'VNM', '7203')"),
    market_code: str = Query("VN", description="Market code (e.g., 'VN', 'T', 'L')")
):
    """
    Fetch data for any international ticker
    
    Examples:
    - Vietnam: ticker=VNM&market_code=VN → VNM.VN
    - Japan: ticker=7203&market_code=T → 7203.T
    - UK: ticker=HSBA&market_code=L → HSBA.L
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(
                status_code=404,
                detail=result.get('error', f'Failed to fetch {ticker}.{market_code}')
            )
        
        # Calculate metrics if financial data available
        if result.get('financials') is not None:
            try:
                metrics = metrics_calc.calculate_all_metrics(result)
                result['calculated_metrics'] = metrics
            except Exception as e:
                logger.warning(f"Could not calculate metrics: {e}")
                result['metrics_error'] = str(e)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching international ticker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vietnam/tickers")
async def list_vietnamese_stocks():
    """
    List commonly tracked Vietnamese stocks
    """
    return {
        "stocks": vn_service.list_available_vietnamese_stocks(),
        "markets": [
            {"code": "VN", "name": "HOSE", "description": "Ho Chi Minh Stock Exchange"},
            {"code": "HA", "name": "HNX", "description": "Hanoi Stock Exchange"},
            {"code": "VC", "name": "UPCOM", "description": "Unlisted Public Company Market"}
        ]
    }


@router.get("/vietnam/search")
async def search_vietnamese_stocks(q: str = Query(..., description="Search query")):
    """
    Search Vietnamese stocks by ticker or name
    """
    results = vn_service.search_vietnamese_stocks(q)
    return {
        "query": q,
        "results_count": len(results),
        "stocks": results
    }


@router.get("/vietnam/fetch")
async def fetch_vietnamese_ticker_basic(
    ticker: str = Query(..., description="Vietnamese ticker (e.g., 'VNM', 'VIC', 'HPG')"),
    market_code: str = Query("VN", description="Market: VN=HOSE, HA=HNX, VC=UPCOM")
):
    """
    Basic fetch for Vietnamese ticker (standard international format)
    """
    try:
        result = vn_service.fetch_vietnamese_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(
                status_code=404,
                detail=result.get('vietnam_specific_error', result.get('error', 'Failed to fetch'))
            )
        
        # Calculate metrics
        if result.get('financials') is not None:
            try:
                metrics = metrics_calc.calculate_all_metrics(result)
                result['calculated_metrics'] = metrics
            except Exception as e:
                logger.warning(f"Could not calculate metrics: {e}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Vietnamese ticker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vietnam/fetch-enhanced")
async def fetch_vietnamese_ticker_enhanced(
    ticker: str = Query(..., description="Vietnamese ticker (e.g., 'VNM', 'VIC', 'HPG')"),
    market_code: str = Query("VN", description="Market: VN=HOSE, HA=HNX, VC=UPCOM"),
    include_peers: bool = Query(True, description="Include sector peers"),
    include_index_data: bool = Query(True, description="Include VNINDEX data")
):
    """
    Enhanced fetch for Vietnamese ticker with local market context
    
    Includes:
    - Sector peers
    - VNINDEX/HNXINDEX performance
    - Trading calendar
    - Regulatory notes
    - Foreign ownership status
    - VND/USD conversions
    - Data quality assessment
    """
    try:
        result = vn_service.fetch_vietnamese_data_enhanced(
            ticker,
            market_code,
            include_peers=include_peers,
            include_index_data=include_index_data
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=404,
                detail=result.get('vietnam_specific_error', result.get('error', 'Failed to fetch'))
            )
        
        # Calculate metrics
        if result.get('financials') is not None:
            try:
                metrics = metrics_calc.calculate_all_metrics(result)
                result['calculated_metrics'] = metrics
                
                # Integrate with vietnam_metrics
                if 'vietnam_metrics' in result:
                    result['vietnam_metrics']['calculated_ratios'] = {
                        'margins': metrics.get('margins', {}),
                        'growth_rates': metrics.get('growth_rates', {}),
                        'working_capital_days': metrics.get('working_capital_days', {}),
                        'capex_ratios': metrics.get('capex_ratios', {}),
                        'debt_ratios': metrics.get('debt_ratios', {}),
                        'profitability': metrics.get('profitability', {}),
                    }
            except Exception as e:
                logger.warning(f"Could not calculate metrics: {e}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching enhanced Vietnamese ticker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vietnam/market-overview")
async def get_vietnam_market_overview():
    """
    Get overview of Vietnamese stock market
    """
    return vn_service.get_vietnam_market_overview()


@router.get("/vietnam/market-info/{market_code}")
async def get_vietnam_market_info(market_code: str):
    """
    Get detailed information about a specific Vietnamese market
    
    Args:
        market_code: VN, HA, or VC
    """
    if market_code.upper() not in ['VN', 'HA', 'VC']:
        raise HTTPException(
            status_code=400,
            detail="Invalid market code. Use VN (HOSE), HA (HNX), or VC (UPCOM)"
        )
    
    return intl_service.get_market_info(market_code)


@router.post("/international/fetch-batch")
async def fetch_batch_international(requests: list[TickerRequest]):
    """
    Fetch multiple international tickers in batch
    
    Body:
    [
        {"ticker": "VNM", "market_code": "VN"},
        {"ticker": "VIC", "market_code": "VN"},
        {"ticker": "7203", "market_code": "T"}
    ]
    """
    results = []
    
    for req in requests:
        try:
            data = intl_service.fetch_international_data(req.ticker, req.market_code)
            
            if data['success']:
                # Calculate metrics if possible
                if data.get('financials') is not None:
                    try:
                        metrics = metrics_calc.calculate_all_metrics(data)
                        data['calculated_metrics'] = metrics
                    except Exception as e:
                        data['metrics_error'] = str(e)
            
            results.append({
                'request': {'ticker': req.ticker, 'market_code': req.market_code},
                'success': data['success'],
                'data': data if data['success'] else None,
                'error': data.get('error') if not data['success'] else None
            })
            
        except Exception as e:
            results.append({
                'request': {'ticker': req.ticker, 'market_code': req.market_code},
                'success': False,
                'data': None,
                'error': str(e)
            })
    
    return {
        'total_requests': len(requests),
        'successful': sum(1 for r in results if r['success']),
        'failed': sum(1 for r in results if not r['success']),
        'results': results
    }


@router.post("/vietnam/fetch-batch")
async def fetch_batch_vietnamese(requests: list[VietnamTickerRequest]):
    """
    Fetch multiple Vietnamese tickers in batch
    
    Body:
    [
        {"ticker": "VNM", "market_code": "VN", "include_peers": true},
        {"ticker": "VIC", "market_code": "VN", "enhanced_mode": true},
        {"ticker": "HPG", "market_code": "VN"}
    ]
    """
    results = []
    
    for req in requests:
        try:
            if req.enhanced_mode:
                data = vn_service.fetch_vietnamese_data_enhanced(
                    req.ticker,
                    req.market_code,
                    include_peers=req.include_peers,
                    include_index_data=req.include_index_data
                )
            else:
                data = vn_service.fetch_vietnamese_data(req.ticker, req.market_code)
            
            if data['success']:
                # Calculate metrics if possible
                if data.get('financials') is not None:
                    try:
                        metrics = metrics_calc.calculate_all_metrics(data)
                        data['calculated_metrics'] = metrics
                    except Exception as e:
                        data['metrics_error'] = str(e)
            
            results.append({
                'request': {
                    'ticker': req.ticker,
                    'market_code': req.market_code,
                    'enhanced_mode': req.enhanced_mode
                },
                'success': data['success'],
                'data': data if data['success'] else None,
                'error': data.get('vietnam_specific_error') or data.get('error') if not data['success'] else None
            })
            
        except Exception as e:
            results.append({
                'request': {
                    'ticker': req.ticker,
                    'market_code': req.market_code,
                    'enhanced_mode': req.enhanced_mode
                },
                'success': False,
                'data': None,
                'error': str(e)
            })
    
    return {
        'total_requests': len(requests),
        'successful': sum(1 for r in results if r['success']),
        'failed': sum(1 for r in results if not r['success']),
        'results': results
    }


@router.get("/vietnam/sector/{sector_name}")
async def get_vietnam_sector_stocks(sector_name: str):
    """
    Get all Vietnamese stocks in a specific sector
    
    Args:
        sector_name: Banking, Real Estate, Consumer Staples, Materials, etc.
    """
    sector_mapping = {
        'banking': 'Banking',
        'real-estate': 'Real Estate',
        'consumer-staples': 'Consumer Staples',
        'materials': 'Materials',
        'energy': 'Energy',
        'technology': 'Technology',
        'utilities': 'Utilities',
        'healthcare': 'Healthcare',
        'telecommunications': 'Telecommunications',
    }
    
    normalized_sector = sector_mapping.get(sector_name.lower(), sector_name.title())
    
    stocks_in_sector = vn_service.VIETNAM_SECTORS.get(normalized_sector, [])
    
    if not stocks_in_sector:
        raise HTTPException(
            status_code=404,
            detail=f"Sector '{sector_name}' not found. Available sectors: {list(vn_service.VIETNAM_SECTORS.keys())}"
        )
    
    return {
        'sector': normalized_sector,
        'stocks_count': len(stocks_in_sector),
        'stocks': [
            {'ticker': ticker, 'market': 'VN', 'sector': normalized_sector}
            for ticker in stocks_in_sector
        ]
    }


# ──────────────────────────────────────────────────────────────────────────────
# Granular Endpoints for DCF Model Inputs
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/data/{ticker}/dcf/historical-financials")
async def get_dcf_historical_financials(
    ticker: str,
    market_code: str = Query("VN", description="Market code")
):
    """
    Fetch historical financial data required for DCF model inputs.
    
    Returns:
    - Revenue, EBIT, EBITDA, Net Income (5 years)
    - Depreciation & Amortization
    - Capital Expenditures
    - Change in Working Capital
    - Total Debt, Cash & Equivalents
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        financials = result.get('financials', {})
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "input_category": "historical_financials",
            "data": {
                "income_statement": financials.get('income_statement', {}),
                "cash_flow_statement": financials.get('cash_flow_statement', {}),
                "balance_sheet": financials.get('balance_sheet', {})
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching DCF historical financials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{ticker}/dcf/growth-rates")
async def get_dcf_growth_rates(
    ticker: str,
    market_code: str = Query("VN", description="Market code")
):
    """
    Calculate historical growth rates for DCF projections.
    
    Returns:
    - Revenue CAGR (1Y, 3Y, 5Y)
    - EBIT CAGR (1Y, 3Y, 5Y)
    - EPS CAGR (1Y, 3Y, 5Y)
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        metrics = metrics_calc.calculate_all_metrics(result)
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "input_category": "growth_rates",
            "data": metrics.get('growth_rates', {})
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating growth rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{ticker}/dcf/margins")
async def get_dcf_margins(
    ticker: str,
    market_code: str = Query("VN", description="Market code")
):
    """
    Calculate margin metrics for DCF model.
    
    Returns:
    - Gross Margin
    - EBIT Margin
    - EBITDA Margin
    - Net Profit Margin
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        metrics = metrics_calc.calculate_all_metrics(result)
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "input_category": "margins",
            "data": metrics.get('margins', {})
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating margins: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{ticker}/dcf/working-capital")
async def get_dcf_working_capital(
    ticker: str,
    market_code: str = Query("VN", description="Market code")
):
    """
    Calculate working capital metrics for DCF model.
    
    Returns:
    - Days Sales Outstanding (DSO)
    - Days Inventory Outstanding (DIO)
    - Days Payable Outstanding (DPO)
    - Cash Conversion Cycle
    - Change in NWC
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        metrics = metrics_calc.calculate_all_metrics(result)
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "input_category": "working_capital",
            "data": metrics.get('working_capital_days', {})
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating working capital: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{ticker}/dcf/capex")
async def get_dcf_capex(
    ticker: str,
    market_code: str = Query("VN", description="Market code")
):
    """
    Calculate CapEx metrics for DCF model.
    
    Returns:
    - Capital Expenditures (absolute)
    - CapEx / Revenue ratio
    - CapEx / EBITDA ratio
    - Depreciation / CapEx ratio
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        metrics = metrics_calc.calculate_all_metrics(result)
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "input_category": "capex",
            "data": metrics.get('capex_ratios', {})
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating capex ratios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{ticker}/dcf/debt-metrics")
async def get_dcf_debt_metrics(
    ticker: str,
    market_code: str = Query("VN", description="Market code")
):
    """
    Calculate debt metrics for WACC calculation.
    
    Returns:
    - Total Debt
    - Net Debt
    - Debt-to-Equity ratio
    - Debt-to-EBITDA ratio
    - Interest Coverage ratio
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        metrics = metrics_calc.calculate_all_metrics(result)
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "input_category": "debt_metrics",
            "data": metrics.get('debt_ratios', {})
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating debt metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{ticker}/dcf/wacc-inputs")
async def get_dcf_wacc_inputs(
    ticker: str,
    market_code: str = Query("VN", description="Market code")
):
    """
    Fetch WACC calculation inputs.
    
    Returns:
    - Beta (levered/unlevered)
    - Risk-free rate (market-specific)
    - Market risk premium (market-specific)
    - Cost of debt estimate
    - Tax rate (jurisdiction-specific)
    - Equity/Debt weights
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        profile = result.get('profile', {})
        metrics = metrics_calc.calculate_all_metrics(result)
        
        # Get market-specific rates
        market_info = intl_service.get_market_info(market_code)
        
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "input_category": "wacc_inputs",
            "data": {
                "beta": profile.get('beta', 1.0),
                "risk_free_rate": market_info.get('risk_free_rate', 0.05),
                "market_risk_premium": market_info.get('market_risk_premium', 0.06),
                "cost_of_debt_estimate": metrics.get('debt_ratios', {}).get('interest_coverage', 0),
                "tax_rate": market_info.get('corporate_tax_rate', 0.20),
                "capital_structure": metrics.get('debt_ratios', {})
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching WACC inputs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Granular Endpoints for Comps Model Inputs
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/data/{ticker}/comps/peer-list")
async def get_comps_peer_list(
    ticker: str,
    market_code: str = Query("VN", description="Market code"),
    sector: Optional[str] = Query(None, description="Filter by sector")
):
    """
    Get list of comparable companies (peers) for comps analysis.
    
    Returns:
    - Peer tickers with basic info
    - Sector classification
    - Market cap ranges
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        profile = result.get('profile', {})
        company_sector = sector or profile.get('sector', 'Unknown')
        
        # Get peers from sector
        if market_code == "VN":
            sector_peers = vn_service.VIETNAM_SECTORS.get(company_sector, [])
        else:
            # For international, use basic sector matching
            sector_peers = [ticker]  # Placeholder
        
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "sector": company_sector,
            "input_category": "peer_list",
            "data": {
                "target_ticker": ticker,
                "target_sector": company_sector,
                "potential_peers": sector_peers,
                "peer_count": len(sector_peers)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching peer list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{ticker}/comps/peer-multiples")
async def get_comps_peer_multiples(
    ticker: str,
    market_code: str = Query("VN", description="Market code"),
    peer_tickers: Optional[str] = Query(None, description="Comma-separated peer tickers")
):
    """
    Fetch valuation multiples for peer companies.
    
    Returns:
    - EV/EBITDA (LTM, NTM)
    - P/E Ratio (LTM, NTM)
    - P/B Ratio
    - EV/Sales
    - P/FCF
    """
    try:
        if not peer_tickers:
            # Fetch target's own multiples as baseline
            result = intl_service.fetch_international_data(ticker, market_code)
            if not result['success']:
                raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
            
            profile = result.get('profile', {})
            return {
                "success": True,
                "ticker": ticker,
                "market": market_code,
                "input_category": "peer_multiples",
                "data": {
                    "multiples": [{
                        "ticker": ticker,
                        "ev_ebitda_ltm": profile.get('enterprise_to_revenue', 0),
                        "pe_ltm": profile.get('trailing_pe', 0),
                        "pb_ratio": profile.get('price_to_book', 0),
                        "ev_sales": profile.get('enterprise_to_revenue', 0)
                    }]
                }
            }
        
        # Fetch multiples for specified peers
        peer_list = [p.strip() for p in peer_tickers.split(',')]
        peer_multiples = []
        
        for peer in peer_list:
            result = intl_service.fetch_international_data(peer, market_code)
            if result['success']:
                profile = result.get('profile', {})
                peer_multiples.append({
                    "ticker": peer,
                    "ev_ebitda_ltm": profile.get('enterprise_to_revenue', 0),
                    "pe_ltm": profile.get('trailing_pe', 0),
                    "pb_ratio": profile.get('price_to_book', 0),
                    "ev_sales": profile.get('enterprise_to_revenue', 0)
                })
        
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "input_category": "peer_multiples",
            "data": {
                "multiples": peer_multiples,
                "peer_count": len(peer_multiples)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching peer multiples: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{ticker}/comps/target-metrics")
async def get_comps_target_metrics(
    ticker: str,
    market_code: str = Query("VN", description="Market code")
):
    """
    Fetch target company metrics for comps valuation.
    
    Returns:
    - Revenue (LTM)
    - EBITDA (LTM)
    - Net Income (LTM)
    - EPS (LTM)
    - Book Value
    - Shares Outstanding
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        financials = result.get('financials', {})
        profile = result.get('profile', {})
        
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "input_category": "target_metrics",
            "data": {
                "revenue_ltm": financials.get('income_statement', {}).get('total_revenue', 0),
                "ebitda_ltm": financials.get('income_statement', {}).get('ebitda', 0),
                "net_income_ltm": financials.get('income_statement', {}).get('net_income', 0),
                "eps_ltm": profile.get('trailing_eps', 0),
                "book_value": financials.get('balance_sheet', {}).get('stockholders_equity', 0),
                "shares_outstanding": profile.get('shares_outstanding', 0)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching target metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Granular Endpoints for DuPont Analysis Inputs
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/data/{ticker}/dupont/profitability")
async def get_dupont_profitability(
    ticker: str,
    market_code: str = Query("VN", description="Market code"),
    years: Optional[int] = Query(5, description="Number of years")
):
    """
    Fetch profitability metrics for DuPont analysis.
    
    Returns:
    - Net Profit Margin
    - Gross Profit Margin
    - Operating Profit Margin
    - EBIT Margin
    - Tax Rate
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        metrics = metrics_calc.calculate_all_metrics(result)
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "input_category": "dupont_profitability",
            "data": {
                "profitability_ratios": metrics.get('profitability', {}),
                "margins": metrics.get('margins', {})
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profitability metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{ticker}/dupont/efficiency")
async def get_dupont_efficiency(
    ticker: str,
    market_code: str = Query("VN", description="Market code"),
    years: Optional[int] = Query(5, description="Number of years")
):
    """
    Fetch efficiency metrics for DuPont analysis.
    
    Returns:
    - Asset Turnover Ratio
    - Inventory Turnover
    - Receivables Turnover
    - Fixed Asset Turnover
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        financials = result.get('financials', {})
        balance_sheet = financials.get('balance_sheet', {})
        income_stmt = financials.get('income_statement', {})
        
        revenue = income_stmt.get('total_revenue', 0)
        total_assets = balance_sheet.get('total_assets', 0)
        inventory = balance_sheet.get('inventory', 0)
        receivables = balance_sheet.get('accounts_receivable', 0)
        
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "input_category": "dupont_efficiency",
            "data": {
                "asset_turnover": revenue / total_assets if total_assets > 0 else 0,
                "inventory_turnover": revenue / inventory if inventory > 0 else 0,
                "receivables_turnover": revenue / receivables if receivables > 0 else 0,
                "fixed_asset_turnover": revenue / balance_sheet.get('property_plant_equipment', 0) if balance_sheet.get('property_plant_equipment', 0) > 0 else 0
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching efficiency metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{ticker}/dupont/leverage")
async def get_dupont_leverage(
    ticker: str,
    market_code: str = Query("VN", description="Market code"),
    years: Optional[int] = Query(5, description="Number of years")
):
    """
    Fetch leverage metrics for DuPont analysis.
    
    Returns:
    - Equity Multiplier (Assets/Equity)
    - Debt-to-Equity Ratio
    - Debt-to-Assets Ratio
    - Interest Coverage Ratio
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        metrics = metrics_calc.calculate_all_metrics(result)
        financials = result.get('financials', {})
        balance_sheet = financials.get('balance_sheet', {})
        
        total_assets = balance_sheet.get('total_assets', 0)
        equity = balance_sheet.get('stockholders_equity', 0)
        
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "input_category": "dupont_leverage",
            "data": {
                "equity_multiplier": total_assets / equity if equity > 0 else 0,
                "debt_to_equity": metrics.get('debt_ratios', {}).get('debt_to_equity', 0),
                "debt_to_assets": metrics.get('debt_ratios', {}).get('debt_to_assets', 0),
                "interest_coverage": metrics.get('debt_ratios', {}).get('interest_coverage', 0)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching leverage metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{ticker}/dupont/roe-decomposition")
async def get_dupont_roe_decomposition(
    ticker: str,
    market_code: str = Query("VN", description="Market code")
):
    """
    Get complete DuPont ROE decomposition.
    
    Returns:
    - ROE = Net Margin × Asset Turnover × Equity Multiplier
    - Component breakdown
    - Historical trend (5 years)
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        financials = result.get('financials', {})
        income_stmt = financials.get('income_statement', {})
        balance_sheet = financials.get('balance_sheet', {})
        
        net_income = income_stmt.get('net_income', 0)
        revenue = income_stmt.get('total_revenue', 0)
        total_assets = balance_sheet.get('total_assets', 0)
        equity = balance_sheet.get('stockholders_equity', 0)
        
        net_margin = net_income / revenue if revenue > 0 else 0
        asset_turnover = revenue / total_assets if total_assets > 0 else 0
        equity_multiplier = total_assets / equity if equity > 0 else 0
        roe = net_income / equity if equity > 0 else 0
        
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "input_category": "roe_decomposition",
            "data": {
                "roe": roe,
                "components": {
                    "net_profit_margin": net_margin,
                    "asset_turnover": asset_turnover,
                    "equity_multiplier": equity_multiplier
                },
                "verification": net_margin * asset_turnover * equity_multiplier
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating ROE decomposition: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Combined Data Endpoints for Model Initialization
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/data/{ticker}/initialize-dcf")
async def initialize_dcf_model(
    ticker: str,
    market_code: str = Query("VN", description="Market code")
):
    """
    Initialize DCF model with all required input data.
    
    Combines:
    - Historical financials
    - Growth rates
    - Margins
    - Working capital metrics
    - CapEx ratios
    - Debt metrics
    - WACC inputs
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        metrics = metrics_calc.calculate_all_metrics(result)
        profile = result.get('profile', {})
        financials = result.get('financials', {})
        market_info = intl_service.get_market_info(market_code)
        
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "model_type": "DCF",
            "data": {
                "historical_financials": financials,
                "growth_rates": metrics.get('growth_rates', {}),
                "margins": metrics.get('margins', {}),
                "working_capital": metrics.get('working_capital_days', {}),
                "capex_ratios": metrics.get('capex_ratios', {}),
                "debt_metrics": metrics.get('debt_ratios', {}),
                "wacc_inputs": {
                    "beta": profile.get('beta', 1.0),
                    "risk_free_rate": market_info.get('risk_free_rate', 0.05),
                    "market_risk_premium": market_info.get('market_risk_premium', 0.06),
                    "tax_rate": market_info.get('corporate_tax_rate', 0.20)
                },
                "current_price": profile.get('current_price', 0),
                "shares_outstanding": profile.get('shares_outstanding', 0)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing DCF model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{ticker}/initialize-comps")
async def initialize_comps_model(
    ticker: str,
    market_code: str = Query("VN", description="Market code")
):
    """
    Initialize Comps model with target metrics and peer data.
    
    Combines:
    - Target company metrics
    - Peer list by sector
    - Peer valuation multiples
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        profile = result.get('profile', {})
        financials = result.get('financials', {})
        company_sector = profile.get('sector', 'Unknown')
        
        # Get sector peers
        if market_code == "VN":
            sector_peers = vn_service.VIETNAM_SECTORS.get(company_sector, [])
        else:
            sector_peers = [ticker]
        
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "model_type": "Comps",
            "data": {
                "target_metrics": {
                    "revenue_ltm": financials.get('income_statement', {}).get('total_revenue', 0),
                    "ebitda_ltm": financials.get('income_statement', {}).get('ebitda', 0),
                    "net_income_ltm": financials.get('income_statement', {}).get('net_income', 0),
                    "eps_ltm": profile.get('trailing_eps', 0),
                    "book_value": financials.get('balance_sheet', {}).get('stockholders_equity', 0)
                },
                "sector": company_sector,
                "peer_list": sector_peers,
                "own_multiples": {
                    "ev_ebitda_ltm": profile.get('enterprise_to_revenue', 0),
                    "pe_ltm": profile.get('trailing_pe', 0),
                    "pb_ratio": profile.get('price_to_book', 0)
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing Comps model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{ticker}/initialize-dupont")
async def initialize_dupont_model(
    ticker: str,
    market_code: str = Query("VN", description="Market code")
):
    """
    Initialize DuPont analysis with all required components.
    
    Combines:
    - Profitability metrics
    - Efficiency ratios
    - Leverage ratios
    - ROE decomposition
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        metrics = metrics_calc.calculate_all_metrics(result)
        financials = result.get('financials', {})
        income_stmt = financials.get('income_statement', {})
        balance_sheet = financials.get('balance_sheet', {})
        
        net_income = income_stmt.get('net_income', 0)
        revenue = income_stmt.get('total_revenue', 0)
        total_assets = balance_sheet.get('total_assets', 0)
        equity = balance_sheet.get('stockholders_equity', 0)
        
        net_margin = net_income / revenue if revenue > 0 else 0
        asset_turnover = revenue / total_assets if total_assets > 0 else 0
        equity_multiplier = total_assets / equity if equity > 0 else 0
        
        return {
            "success": True,
            "ticker": ticker,
            "market": market_code,
            "model_type": "DuPont",
            "data": {
                "profitability": {
                    "net_margin": net_margin,
                    "gross_margin": metrics.get('margins', {}).get('gross_margin', 0),
                    "operating_margin": metrics.get('margins', {}).get('operating_margin', 0)
                },
                "efficiency": {
                    "asset_turnover": asset_turnover,
                    "inventory_turnover": metrics.get('working_capital_days', {}).get('inventory_days', 0),
                    "receivables_turnover": metrics.get('working_capital_days', {}).get('receivables_days', 0)
                },
                "leverage": {
                    "equity_multiplier": equity_multiplier,
                    "debt_to_equity": metrics.get('debt_ratios', {}).get('debt_to_equity', 0),
                    "debt_to_assets": metrics.get('debt_ratios', {}).get('debt_to_assets', 0)
                },
                "roe_decomposition": {
                    "roe": net_income / equity if equity > 0 else 0,
                    "components": {
                        "net_profit_margin": net_margin,
                        "asset_turnover": asset_turnover,
                        "equity_multiplier": equity_multiplier
                    }
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing DuPont model: {e}")
        raise HTTPException(status_code=500, detail=str(e))
