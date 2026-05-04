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
