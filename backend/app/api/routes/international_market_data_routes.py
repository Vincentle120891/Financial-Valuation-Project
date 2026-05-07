"""
API Routes for International & Vietnamese Tickers
Refactored for granular, model-specific data retrieval supporting 94+ inputs across DCF, Comps, and DuPont models.

Endpoint Organization:
1. General Market Data (Common to all models) - 4 endpoints
2. DCF Model Specific Inputs (~40 inputs) - 8 endpoints  
3. Comps (Relative Valuation) Specific Inputs (~30 inputs) - 7 endpoints
4. DuPont Analysis Specific Inputs (~24 inputs) - 6 endpoints
5. Batch Operations - 3 endpoints
6. Vietnamese Market Enhanced - 5 endpoints

Total: ~33 granular endpoints for precise frontend integration
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import logging

from app.services.international import InternationalTickerService
from app.services.vietnamese import VietnameseTickerService
from app.services.international import MetricsCalculator
from app.services.international.step5_assumptions_processor import Step5AssumptionsProcessor, ValuationModel
from app.services.international.step6_data_review import Step6DataReviewProcessor
from app.services.international.yfinance_service import YFinanceService
from app.services.international.ai_engine import suggest_peer_companies

logger = logging.getLogger(__name__)

router = APIRouter(tags=["International & Vietnamese Tickers"])

# Initialize services
intl_service = InternationalTickerService()
vn_service = VietnameseTickerService()
metrics_calc = MetricsCalculator()
step5_processor = Step5AssumptionsProcessor()
step6_processor = Step6DataReviewProcessor()
yfinance_service = YFinanceService()


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


# =============================================================================
# SECTION 1: GENERAL MARKET DATA (Common to all models) - 3 endpoints
# =============================================================================

@router.get("/market-data/{ticker}/profile")
async def get_company_profile(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code")
):
    """
    Get company profile data common to all valuation models.
    
    Returns:
        - Company name, sector, industry
        - Beta, shares outstanding
        - Exchange, currency, country
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        return {
            "ticker": result['ticker'],
            "company_name": result['company_info'].get('name'),
            "sector": result['company_info'].get('sector'),
            "industry": result['company_info'].get('industry'),
            "country": result['company_info'].get('country'),
            "exchange": result['company_info'].get('exchange'),
            "currency": result['currency'],
            "shares_outstanding": result['key_stats'].get('shares_outstanding'),
            "beta": result['key_stats'].get('beta'),
            "employees": result['company_info'].get('employees'),
            "description": result['company_info'].get('description')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching company profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-data/{ticker}/price-history")
async def get_price_history(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code"),
    period: str = Query("2y", description="Period: 1mo, 3mo, 6mo, 1y, 2y, 5y, max")
):
    """
    Get historical price data for volatility and beta calculations.
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        historical_prices = result.get('historical_prices')
        
        volatility = None
        if historical_prices is not None and not historical_prices.empty:
            returns = historical_prices['Close'].pct_change().dropna()
            volatility = float(returns.std()) * (252 ** 0.5)
        
        return {
            "ticker": result['ticker'],
            "52_week_high": result['key_stats'].get('52_week_high'),
            "52_week_low": result['key_stats'].get('52_week_low'),
            "average_volume": result['key_stats'].get('average_volume'),
            "volatility_annualized": volatility,
            "period": period
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching price history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-data/{ticker}/key-statistics")
async def get_key_statistics(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code")
):
    """
    Get key financial statistics and ratios.
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        return {
            "ticker": result['ticker'],
            "valuation_metrics": {
                "market_cap": result['key_stats'].get('market_cap'),
                "enterprise_value": result['key_stats'].get('enterprise_value'),
                "trailing_pe": result['key_stats'].get('trailing_pe'),
                "forward_pe": result['key_stats'].get('forward_pe'),
                "price_to_book": result['key_stats'].get('price_to_book'),
                "price_to_sales": result['key_stats'].get('price_to_sales'),
                "ev_to_revenue": result['key_stats'].get('ev_to_revenue'),
                "ev_to_ebitda": result['key_stats'].get('ev_to_ebitda'),
            },
            "profitability_metrics": {
                "profit_margin": result['key_stats'].get('profit_margin'),
                "operating_margin": result['key_stats'].get('operating_margin'),
                "return_on_assets": result['key_stats'].get('return_on_assets'),
                "return_on_equity": result['key_stats'].get('return_on_equity'),
            },
            "financial_health": {
                "debt_to_equity": result['key_stats'].get('debt_to_equity'),
                "current_ratio": result['key_stats'].get('current_ratio'),
                "quick_ratio": result['key_stats'].get('quick_ratio'),
            },
            "dividends": {
                "dividend_yield": result['key_stats'].get('dividend_yield'),
                "payout_ratio": result['key_stats'].get('payout_ratio'),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching key statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SECTION 2: DCF MODEL SPECIFIC INPUTS (~40 inputs) - 8 endpoints
# =============================================================================

@router.get("/models/dcf/{ticker}/historical-financials")
async def get_dcf_historical_financials(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code"),
    years: int = Query(5, description="Number of historical years (3-5)")
):
    """
    Get historical financial statements for DCF modeling.
    
    Returns:
        Income Statement: Total Revenue, EBITDA, Operating Income, Net Income
        Balance Sheet: Total Assets, Total Debt, AR, Inventory, AP
        Cash Flow: OCF, Capex, FCF, Change in WC
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        financials = result.get('financials')
        balance_sheet = result.get('balance_sheet')
        cashflow = result.get('cashflow')
        
        def extract_series(data, key, n_years=None):
            if data is None or data.empty:
                return {}
            row = data.loc[key] if key in data.index else None
            if row is None:
                return {}
            periods = row.to_dict()
            if n_years:
                items = list(periods.items())[:n_years]
                return dict(items)
            return periods
        
        return {
            "ticker": result['ticker'],
            "income_statement": {
                "total_revenue": extract_series(financials, "Total Revenue", years),
                "ebitda": extract_series(financials, "EBITDA", years),
                "operating_income": extract_series(financials, "Operating Income", years),
                "net_income": extract_series(financials, "Net Income", years),
            },
            "balance_sheet": {
                "total_assets": extract_series(balance_sheet, "Total Assets", years + 1),
                "total_debt": extract_series(balance_sheet, "Total Debt", years + 1),
                "accounts_receivable": extract_series(balance_sheet, "Accounts Receivable", years + 1),
                "inventory": extract_series(balance_sheet, "Inventory", years + 1),
                "accounts_payable": extract_series(balance_sheet, "Accounts Payable", years + 1),
            },
            "cash_flow": {
                "operating_cash_flow": extract_series(cashflow, "Operating Cash Flow", years),
                "capital_expenditure": extract_series(cashflow, "Capital Expenditure", years),
                "change_in_working_capital": extract_series(cashflow, "Change In Working Capital", years),
            },
            "currency": result['currency']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching DCF historical financials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/dcf/{ticker}/growth-rates")
async def get_dcf_growth_rates(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code")
):
    """Get historical growth rates for DCF projections."""
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        if result.get('financials') is None:
            raise HTTPException(status_code=400, detail="No financial data available")
        
        metrics = metrics_calc.calculate_all_metrics(result)
        
        return {
            "ticker": result['ticker'],
            "growth_rates": metrics.get('growth_rates', {}),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching DCF growth rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/dcf/{ticker}/margins")
async def get_dcf_margins(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code")
):
    """Get historical margin analysis for DCF modeling."""
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        if result.get('financials') is None:
            raise HTTPException(status_code=400, detail="No financial data available")
        
        metrics = metrics_calc.calculate_all_metrics(result)
        
        return {
            "ticker": result['ticker'],
            "margins": metrics.get('margins', {}),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching DCF margins: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/dcf/{ticker}/working-capital")
async def get_dcf_working_capital(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code")
):
    """Get working capital efficiency metrics (DSO, DIO, DPO, CCC)."""
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        if result.get('financials') is None:
            raise HTTPException(status_code=400, detail="No financial data available")
        
        metrics = metrics_calc.calculate_all_metrics(result)
        
        return {
            "ticker": result['ticker'],
            "working_capital_days": metrics.get('working_capital_days', {}),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching DCF working capital: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/dcf/{ticker}/capex-depreciation")
async def get_dcf_capex_depreciation(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code")
):
    """Get Capex and depreciation ratios."""
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        if result.get('financials') is None:
            raise HTTPException(status_code=400, detail="No financial data available")
        
        metrics = metrics_calc.calculate_all_metrics(result)
        
        return {
            "ticker": result['ticker'],
            "capex_ratios": metrics.get('capex_ratios', {}),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching DCF capex/depreciation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/dcf/{ticker}/peer-suggestions")
async def get_dcf_peer_suggestions(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code"),
    num_peers: int = Query(5, description="Number of peer companies")
):
    """Get AI-suggested peer companies for WACC calculation."""
    try:
        full_ticker = f"{ticker.upper()}.{market_code.upper()}" if market_code.upper() != 'US' else ticker.upper()
        peers = suggest_peer_companies(full_ticker, num_peers=num_peers)
        
        return {
            "target_ticker": full_ticker,
            "suggested_peers": peers,
            "num_peers": len(peers),
        }
    except Exception as e:
        logger.error(f"Error suggesting peers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/dcf/{ticker}/debt-cost")
async def get_dcf_debt_cost(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code")
):
    """Get implied cost of debt and debt ratios."""
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        if result.get('financials') is None:
            raise HTTPException(status_code=400, detail="No financial data available")
        
        metrics = metrics_calc.calculate_all_metrics(result)
        
        return {
            "ticker": result['ticker'],
            "cost_of_debt": metrics.get('cost_of_debt', {}),
            "debt_ratios": metrics.get('debt_ratios', {}),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching debt cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/dcf/{ticker}/profitability")
async def get_dcf_profitability(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code")
):
    """Get profitability ratios (ROE, ROA, ROIC)."""
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        if result.get('financials') is None:
            raise HTTPException(status_code=400, detail="No financial data available")
        
        metrics = metrics_calc.calculate_all_metrics(result)
        
        return {
            "ticker": result['ticker'],
            "roe_roic": metrics.get('roe_roic', {}),
            "profitability_ratios": metrics.get('profitability_ratios', {}),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profitability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SECTION 3: COMPS MODEL SPECIFIC INPUTS (~30 inputs) - 5 endpoints
# =============================================================================

@router.get("/models/comps/{ticker}/peer-list")
async def get_comps_peer_list(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code"),
    num_peers: int = Query(5, description="Number of peer companies")
):
    """Get auto-suggested peer companies based on sector/market cap."""
    try:
        full_ticker = f"{ticker.upper()}.{market_code.upper()}" if market_code.upper() != 'US' else ticker.upper()
        peers = suggest_peer_companies(full_ticker, num_peers=num_peers)
        
        return {
            "target_ticker": full_ticker,
            "peer_count": len(peers),
            "peers": peers
        }
    except Exception as e:
        logger.error(f"Error getting peer list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/comps/{ticker}/peer-metrics")
async def get_comps_peer_metrics(
    ticker: str = Path(..., description="Target ticker"),
    market_code: str = Query("VN", description="Market code"),
    peers: str = Query(..., description="Comma-separated peer tickers")
):
    """Get valuation multiples for peer companies."""
    try:
        peer_list = [p.strip().upper() for p in peers.split(',')]
        peer_data = []
        
        for peer_ticker in peer_list:
            try:
                result = intl_service.fetch_international_data(peer_ticker, market_code)
                if result['success']:
                    peer_data.append({
                        "ticker": result['ticker'],
                        "company_name": result['company_info'].get('name'),
                        "market_cap": result['key_stats'].get('market_cap'),
                        "enterprise_value": result['key_stats'].get('enterprise_value'),
                        "ev_ebitda": result['key_stats'].get('ev_to_ebitda'),
                        "pe_ratio": result['key_stats'].get('trailing_pe'),
                        "pb_ratio": result['key_stats'].get('price_to_book'),
                        "ps_ratio": result['key_stats'].get('price_to_sales'),
                    })
                else:
                    peer_data.append({"ticker": peer_ticker, "error": result.get('error')})
            except Exception as e:
                peer_data.append({"ticker": peer_ticker, "error": str(e)})
        
        return {
            "target_ticker": f"{ticker.upper()}.{market_code.upper()}",
            "peer_count": len(peer_data),
            "successful": sum(1 for p in peer_data if 'error' not in p),
            "peers": peer_data
        }
    except Exception as e:
        logger.error(f"Error fetching peer metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/comps/{ticker}/target-metrics")
async def get_comps_target_metrics(
    ticker: str = Path(..., description="Target ticker"),
    market_code: str = Query("VN", description="Market code")
):
    """Get target company's current valuation multiples."""
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        return {
            "ticker": result['ticker'],
            "current_multiples": {
                "ev_ebitda": result['key_stats'].get('ev_to_ebitda'),
                "pe_ratio": result['key_stats'].get('trailing_pe'),
                "forward_pe": result['key_stats'].get('forward_pe'),
                "pb_ratio": result['key_stats'].get('price_to_book'),
                "ps_ratio": result['key_stats'].get('price_to_sales'),
            },
            "valuation": {
                "market_cap": result['key_stats'].get('market_cap'),
                "enterprise_value": result['key_stats'].get('enterprise_value'),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching target metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/comps/{ticker}/multiples-analysis")
async def get_comps_multiples_analysis(
    ticker: str = Path(..., description="Target ticker"),
    market_code: str = Query("VN", description="Market code"),
    peers: str = Query(..., description="Comma-separated peer tickers")
):
    """Get comparative multiples analysis with min/avg/max statistics."""
    try:
        target_result = intl_service.fetch_international_data(ticker, market_code)
        if not target_result['success']:
            raise HTTPException(status_code=404, detail="Failed to fetch target")
        
        peer_list = [p.strip().upper() for p in peers.split(',')]
        peer_ev_ebitda, peer_pe, peer_pb, peer_ps = [], [], [], []
        
        for peer_ticker in peer_list:
            try:
                result = intl_service.fetch_international_data(peer_ticker, market_code)
                if result['success']:
                    ks = result['key_stats']
                    if ks.get('ev_to_ebitda'): peer_ev_ebitda.append(ks['ev_to_ebitda'])
                    if ks.get('trailing_pe'): peer_pe.append(ks['trailing_pe'])
                    if ks.get('price_to_book'): peer_pb.append(ks['price_to_book'])
                    if ks.get('price_to_sales'): peer_ps.append(ks['price_to_sales'])
            except:
                continue
        
        def calc_stats(values):
            if not values: return {"min": None, "avg": None, "max": None}
            return {"min": min(values), "avg": sum(values)/len(values), "max": max(values)}
        
        return {
            "target_ticker": target_result['ticker'],
            "multiple_analysis": {
                "ev_ebitda": {"peer_stats": calc_stats(peer_ev_ebitda), "target": target_result['key_stats'].get('ev_to_ebitda')},
                "pe_ratio": {"peer_stats": calc_stats(peer_pe), "target": target_result['key_stats'].get('trailing_pe')},
                "pb_ratio": {"peer_stats": calc_stats(peer_pb), "target": target_result['key_stats'].get('price_to_book')},
                "ps_ratio": {"peer_stats": calc_stats(peer_ps), "target": target_result['key_stats'].get('price_to_sales')},
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in multiples analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/comps/{ticker}/implied-valuation")
async def get_comps_implied_valuation(
    ticker: str = Path(..., description="Target ticker"),
    market_code: str = Query("VN", description="Market code"),
    peers: str = Query(..., description="Comma-separated peer tickers")
):
    """Calculate implied valuation using peer multiples."""
    try:
        target_result = intl_service.fetch_international_data(ticker, market_code)
        if not target_result['success']:
            raise HTTPException(status_code=404, detail="Failed to fetch target")
        
        peer_list = [p.strip().upper() for p in peers.split(',')]
        peer_ev_ebitda = []
        
        for peer_ticker in peer_list:
            try:
                result = intl_service.fetch_international_data(peer_ticker, market_code)
                if result['success'] and result['key_stats'].get('ev_to_ebitda'):
                    peer_ev_ebitda.append(result['key_stats']['ev_to_ebitda'])
            except:
                continue
        
        if not peer_ev_ebitda:
            raise HTTPException(status_code=400, detail="No valid peer multiples found")
        
        target_ebitda = target_result['key_stats'].get('ebitda')
        
        implied = {}
        if target_ebitda:
            implied = {
                "using_min": min(peer_ev_ebitda) * target_ebitda,
                "using_avg": sum(peer_ev_ebitda)/len(peer_ev_ebitda) * target_ebitda,
                "using_max": max(peer_ev_ebitda) * target_ebitda,
            }
        
        return {
            "target_ticker": target_result['ticker'],
            "current_market_cap": target_result['key_stats'].get('market_cap'),
            "implied_valuations": implied,
            "peer_ev_ebitda_range": {"min": min(peer_ev_ebitda), "avg": sum(peer_ev_ebitda)/len(peer_ev_ebitda), "max": max(peer_ev_ebitda)}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating implied valuation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SECTION 4: DUPONT ANALYSIS SPECIFIC INPUTS (~24 inputs) - 4 endpoints
# =============================================================================

@router.get("/models/dupont/{ticker}/profitability-drivers")
async def get_dupont_profitability_drivers(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code")
):
    """Get DuPont profitability drivers (Tax Burden, Interest Burden, EBIT Margin)."""
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        financials = result.get('financials')
        
        def extract_series(data, key, n_years=5):
            if data is None or data.empty: return {}
            row = data.loc[key] if key in data.index else None
            if row is None: return {}
            return dict(list(row.to_dict().items())[:n_years])
        
        net_income = extract_series(financials, "Net Income")
        pretax_income = extract_series(financials, "Pretax Income")
        ebit = extract_series(financials, "Operating Income")
        revenue = extract_series(financials, "Total Revenue")
        
        tax_burden = {y: net_income[y]/pretax_income[y] for y in net_income if pretax_income.get(y) and pretax_income[y] != 0}
        interest_burden = {y: pretax_income[y]/ebit[y] for y in pretax_income if ebit.get(y) and ebit[y] != 0}
        ebit_margin = {y: ebit.get(y, 0)/revenue[y] for y in revenue if revenue[y] != 0}
        
        return {
            "ticker": result['ticker'],
            "profitability_components": {"net_income": net_income, "pretax_income": pretax_income, "ebit": ebit, "revenue": revenue},
            "dupont_ratios": {"tax_burden": tax_burden, "interest_burden": interest_burden, "ebit_margin": ebit_margin},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching DuPont profitability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/dupont/{ticker}/efficiency-drivers")
async def get_dupont_efficiency_drivers(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code")
):
    """Get DuPont efficiency drivers (Asset Turnover)."""
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        financials = result.get('financials')
        balance_sheet = result.get('balance_sheet')
        
        def extract_series(data, key, n_years=5):
            if data is None or data.empty: return {}
            row = data.loc[key] if key in data.index else None
            if row is None: return {}
            return dict(list(row.to_dict().items())[:n_years])
        
        revenue = extract_series(financials, "Total Revenue")
        total_assets = extract_series(balance_sheet, "Total Assets")
        
        asset_turnover = {y: revenue[y]/total_assets[y] for y in revenue if total_assets.get(y) and total_assets[y] != 0}
        
        return {
            "ticker": result['ticker'],
            "efficiency_components": {"revenue": revenue, "total_assets": total_assets},
            "asset_turnover": asset_turnover,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching DuPont efficiency: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/dupont/{ticker}/leverage-drivers")
async def get_dupont_leverage_drivers(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code")
):
    """Get DuPont leverage drivers (Equity Multiplier, Debt/Equity)."""
    try:
        result = intl_service.fetch_international_data(ticker, market_code)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Failed to fetch'))
        
        balance_sheet = result.get('balance_sheet')
        
        def extract_series(data, key, n_years=5):
            if data is None or data.empty: return {}
            row = data.loc[key] if key in data.index else None
            if row is None: return {}
            return dict(list(row.to_dict().items())[:n_years])
        
        total_assets = extract_series(balance_sheet, "Total Assets")
        equity = extract_series(balance_sheet, "Stockholders Equity")
        total_debt = extract_series(balance_sheet, "Total Debt")
        
        equity_multiplier = {y: total_assets[y]/equity[y] for y in total_assets if equity.get(y) and equity[y] != 0}
        debt_to_equity = {y: total_debt[y]/equity[y] for y in total_debt if equity.get(y) and equity[y] != 0}
        
        return {
            "ticker": result['ticker'],
            "leverage_components": {"total_assets": total_assets, "shareholders_equity": equity, "total_debt": total_debt},
            "leverage_ratios": {"equity_multiplier": equity_multiplier, "debt_to_equity": debt_to_equity},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching DuPont leverage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/dupont/{ticker}/full-analysis")
async def get_dupont_full_analysis(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("VN", description="Market code")
):
    """Get complete 3-step and 5-step DuPont analysis."""
    try:
        # Get components from other endpoints
        profitability = await get_dupont_profitability_drivers(ticker, market_code)
        efficiency = await get_dupont_efficiency_drivers(ticker, market_code)
        leverage = await get_dupont_leverage_drivers(ticker, market_code)
        
        # Calculate 3-step ROE
        roe_3step = {}
        rev = profitability['profitability_components'].get('revenue', {})
        ni = profitability['profitability_components'].get('net_income', {})
        for year in rev.keys():
            npm = ni[year]/rev[year] if rev[year] and ni.get(year) else None
            at = efficiency['asset_turnover'].get(year)
            em = leverage['leverage_ratios']['equity_multiplier'].get(year)
            if npm and at and em:
                roe_3step[year] = npm * at * em
        
        return {
            "ticker": f"{ticker.upper()}.{market_code.upper()}",
            "three_step_dupont": {
                "formula": "ROE = Net Profit Margin × Asset Turnover × Equity Multiplier",
                "roe_calculated": roe_3step,
            },
            "five_step_dupont": {
                "formula": "ROE = Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Equity Multiplier",
                "components": {
                    "tax_burden": profitability['dupont_ratios'].get('tax_burden', {}),
                    "interest_burden": profitability['dupont_ratios'].get('interest_burden', {}),
                    "ebit_margin": profitability['dupont_ratios'].get('ebit_margin', {}),
                    "asset_turnover": efficiency['asset_turnover'],
                    "equity_multiplier": leverage['leverage_ratios']['equity_multiplier']
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in DuPont full analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SECTION 5: BATCH OPERATIONS (Existing endpoints preserved)
# =============================================================================


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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
    ticker: str = Path(..., description="Ticker symbol"),
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
