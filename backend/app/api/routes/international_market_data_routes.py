"""
API Routes for International Market Data
Refactored for granular, model-specific data retrieval supporting 94+ inputs across DCF, Comps, and DuPont models.

Endpoint Organization:
1. General Market Data (Common to all models) - 4 endpoints
2. DCF Model Specific Inputs (~40 inputs) - 8 endpoints  
3. Comps (Relative Valuation) Specific Inputs (~30 inputs) - 5 endpoints
4. DuPont Analysis Specific Inputs (~24 inputs) - 4 endpoints
5. Batch Operations - 1 endpoint

Total: 22 granular endpoints for precise frontend integration

NOTE: Vietnamese Market routes have been moved to vietnamese_market_data_routes.py (Version 2)
"""

from fastapi import APIRouter, HTTPException, Query, Path
import pandas as pd
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import logging

from app.services.international import InternationalTickerService
from app.services.international import MetricsCalculator
from app.services.international.step5_required_inputs_processor import Step5RequiredInputsProcessor, ValuationModel
from app.services.international.step6_data_review import Step6DataReviewProcessor
from app.services.international.yfinance_service import YFinanceService
from app.services.international.ai_engine import suggest_peer_companies

logger = logging.getLogger(__name__)

router = APIRouter(tags=["International Market Data"])

# Initialize services
intl_service = InternationalTickerService()
metrics_calc = MetricsCalculator()
step5_processor = Step5RequiredInputsProcessor()
step6_processor = Step6DataReviewProcessor()
yfinance_service = YFinanceService()

class TickerRequest(BaseModel):
    ticker: str
    market_code: str = "US"
    include_estimates: bool = True
    include_historical: bool = True

@router.get("/international/tickers")
async def list_international_markets():
    """
    List all supported international markets and their suffixes
    
    Markets included:
    - US: No suffix (e.g., AAPL)
    - Japan: .T (e.g., 7203.T)
    - UK: .L (e.g., HSBA.L)
    - Germany: .DE (e.g., VOW3.DE)
    - France: .PA (e.g., AIR.PA)
    - Canada: .TO (e.g., RY.TO)
    - Australia: .AX (e.g., BHP.AX)
    - Hong Kong: .HK (e.g., 0700.HK)
    - Singapore: .SI (e.g., D05.SI)
    
    NOTE: Vietnamese market (.VN) is handled separately in vietnamese_market_data_routes.py
    """
    return {
        "markets": intl_service.MARKET_SUFFIXES,
        "currencies": intl_service.MARKET_CURRENCIES,
        "note": "Use market_code when fetching data for international tickers. Vietnam is Version 2."
    }

@router.get("/international/fetch")
async def fetch_international_ticker(
    ticker: str = Query(..., description="Base ticker symbol (e.g., 'AAPL', '7203', 'HSBA')"),
    market_code: str = Query("US", description="Market code (e.g., 'US', 'T', 'L', 'DE')")
):
    """
    Fetch data for any international ticker (NON-Vietnamese markets)
    
    Examples:
    - US: ticker=AAPL&market_code=US → AAPL
    - Japan: ticker=7203&market_code=T → 7203.T
    - UK: ticker=HSBA&market_code=L → HSBA.L
    - Germany: ticker=VOW3&market_code=DE → VOW3.DE
    
    Returns:
    - Company profile
    - Financial statements (income, balance sheet, cash flow)
    - Key statistics
    - Calculated metrics (margins, growth rates, ratios)
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

@router.get("/market-data/{ticker}/profile")
async def get_company_profile(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("US", description="Market code")
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
    market_code: str = Query("US", description="Market code"),
    period: str = Query("3mo", description="Period: 1mo, 3mo, 6mo, 1y, 2y, 5y, max")
):
    """
    Get historical price data for volatility and beta calculations.
    Returns formatted data for charts.
    
    Period options:
    - 1mo: ~21 trading days
    - 3mo: ~63 trading days
    - 6mo: ~126 trading days
    - 1y: ~252 trading days
    - 2y: ~504 trading days
    - 5y: ~1260 trading days
    - max: All available data
    
    Error Handling:
    - Returns 404 if ticker not found or delisted
    - Returns 422 if insufficient data available
    """
    try:
        result = intl_service.fetch_international_data(ticker, market_code)

        if not result['success']:
            error_msg = result.get('error', 'Failed to fetch')
            # Check for specific error conditions
            if 'not found' in error_msg.lower() or 'delisted' in error_msg.lower():
                raise HTTPException(
                    status_code=404, 
                    detail=f"Ticker {ticker} not found or may be delisted. Error: {error_msg}"
                )
            raise HTTPException(status_code=404, detail=error_msg)

        historical_prices = result.get('historical_prices')

        # Validate we have price data
        if historical_prices is None or historical_prices.empty:
            raise HTTPException(
                status_code=422,
                detail=f"No price history available for {ticker}. Insufficient trading data."
            )

        # Map period to number of trading days
        period_map = {
            '1mo': 21,
            '3mo': 63,
            '6mo': 126,
            '1y': 252,
            '2y': 504,
            '5y': 1260,
            'max': None  # No limit
        }
        
        num_days = period_map.get(period, 63)  # Default to 3mo
        
        # Filter by period if specified
        if num_days is not None:
            historical_prices = historical_prices.tail(num_days)
            # Check if we got enough data
            if len(historical_prices) < num_days // 2:
                logger.warning(f"Only {len(historical_prices)} days of data available for {ticker}, expected {num_days}")
        
        # Format data for chart
        chart_data = []
        for date, row in historical_prices.iterrows():
            chart_data.append({
                "date": date.strftime('%Y-%m-%d'),
                "open": float(row['Open']) if pd.notna(row['Open']) else None,
                "high": float(row['High']) if pd.notna(row['High']) else None,
                "low": float(row['Low']) if pd.notna(row['Low']) else None,
                "close": float(row['Close']) if pd.notna(row['Close']) else None,
                "volume": int(row['Volume']) if pd.notna(row['Volume']) else None
            })

        if not chart_data:
            raise HTTPException(
                status_code=422,
                detail=f"No valid price data points for {ticker} in the requested period."
            )

        return {
            "ticker": ticker,
            "market_code": market_code,
            "period": period,
            "data_points": len(chart_data),
            "prices": chart_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching price history for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch price history: {str(e)}")

@router.get("/market-data/{ticker}/key-statistics")
async def get_key_statistics(
    ticker: str = Path(..., description="Ticker symbol"),
    market_code: str = Query("US", description="Market code")
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
    market_code: str = Query("US", description="Market code"),
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
    market_code: str = Query("US", description="Market code")
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
    market_code: str = Query("US", description="Market code")
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
    market_code: str = Query("US", description="Market code")
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
    market_code: str = Query("US", description="Market code")
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
    market_code: str = Query("US", description="Market code"),
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
    market_code: str = Query("US", description="Market code")
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
    market_code: str = Query("US", description="Market code")
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
    market_code: str = Query("US", description="Market code"),
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
    market_code: str = Query("US", description="Market code"),
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
    market_code: str = Query("US", description="Market code")
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
    market_code: str = Query("US", description="Market code"),
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
    market_code: str = Query("US", description="Market code"),
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
    market_code: str = Query("US", description="Market code")
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
    market_code: str = Query("US", description="Market code")
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
    market_code: str = Query("US", description="Market code")
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
    market_code: str = Query("US", description="Market code")
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
