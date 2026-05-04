"""
Valuation Routes

Handles model selection, data fetching, AI assumptions, and valuation calculation.
"""

import os
import logging
from datetime import date
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Request, Body
from pydantic import BaseModel, Field, validator

from app.core.logging_config import get_logger
from app.core.exceptions import (
    SessionNotFoundException,
    DataFetchException,
    CalculationException,
    ValidationException,
)
from app.api.schemas import (
    ModelSelectRequest,
    AssumptionConfirmRequest,
    CalculationRequest,
    SessionFetchRequest,
    FetchDataResponse,
    AIAssumptionsResponse,
    ValuationResultResponse,
    InputRequirement,
    PrepareInputsResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Valuation"])


def get_session(session_id: str, sessions: Dict) -> Dict:
    """
    Get session by ID with validation.
    
    Args:
        session_id: Session identifier
        sessions: Session store dictionary
        
    Returns:
        Session data dictionary
        
    Raises:
        HTTPException: If session not found
    """
    if session_id not in sessions:
        logger.warning(f"Session not found: {session_id}")
        raise SessionNotFoundException(
            session_id=session_id,
            details={"hint": "Please create a new session by selecting a ticker"}
        ).to_dict()
    return sessions[session_id]


def fetch_and_calculate_all_metrics(ticker_symbol: str, market: str) -> Dict[str, Any]:
    """
    Step 5A + 5B: Unified function that fetches raw data AND calculates all metrics.
    
    Executes Step 5A → Step 5B sequentially:
    - Step 5A: Fetch ALL raw data from yfinance (income statement, balance sheet, cash flow, key stats, analyst estimates)
    - Step 5B: Calculate ALL derived metrics (margins, growth rates, working capital days, capex ratios, cost of debt, debt ratios, ROE, ROIC, market multiples)
    
    Args:
        ticker_symbol: Stock ticker symbol
        market: Market type (vietnamese or international)
        
    Returns:
        Comprehensive data package containing both raw and calculated metrics
    """
    from app.services.metrics_calculator import fetch_and_calculate_all_metrics as fetch_calc_metrics
    
    try:
        logger.info(f"Fetching and calculating all metrics for ticker='{ticker_symbol}', market='{market}'")
        
        # Execute Step 5A → Step 5B sequentially
        comprehensive_data = fetch_calc_metrics(ticker_symbol, market)
        
        logger.info(f"Successfully fetched and calculated all metrics for ticker='{ticker_symbol}'")
        return comprehensive_data
        
    except Exception as e:
        logger.error(f"Failed to fetch and calculate metrics for ticker='{ticker_symbol}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data fetch and calculation failed: {str(e)}")


def fetch_financial_data(ticker_symbol: str, market: str) -> Dict:
    """
    Step 7 & 8: Fetch financial data from yFinance.
    (Legacy function - kept for backward compatibility)
    
    Args:
        ticker_symbol: Stock ticker symbol
        market: Market type (vietnamese or international)
        
    Returns:
        Dictionary containing profile and financials data
        
    Raises:
        HTTPException: If data retrieval fails
    """
    import yfinance as yf
    
    try:
        logger.info(f"Fetching financial data for ticker='{ticker_symbol}', market='{market}'")
        
        if market == "vietnamese" and not ticker_symbol.endswith(".VN"):
            ticker_symbol += ".VN"
            
        ticker = yf.Ticker(ticker_symbol)
        
        info = ticker.info
        if not info or 'currentPrice' not in info:
            raise ValueError("Could not retrieve basic info. Ticker might be invalid.")

        def sanitize_value(val):
            if val is None:
                return None
            if isinstance(val, float) and (val != val):  # NaN check
                return None
            return val
        
        def sanitize_dict(d):
            if not d:
                return {}
            return {k: sanitize_value(v) for k, v in d.items()}
        
        income_stmt = ticker.financials
        balance_sheet = ticker.balance_sheet
        cashflow = ticker.cashflow
        
        data = {
            "profile": {
                "symbol": ticker_symbol,
                "name": info.get('longName'),
                "sector": info.get('sector'),
                "industry": info.get('industry'),
                "current_price": sanitize_value(info.get('currentPrice')),
                "currency": "VND" if market == "vietnamese" else info.get('currency', 'USD'),
                "market_cap": sanitize_value(info.get('marketCap')),
                "beta": sanitize_value(info.get('beta', 1.0))
            },
            "financials": {
                "revenue": sanitize_dict(income_stmt.loc['Total Revenue'].to_dict() if 'Total Revenue' in income_stmt.index else {}),
                "ebitda": sanitize_dict(income_stmt.loc['EBITDA'].to_dict() if 'EBITDA' in income_stmt.index else {}),
                "net_income": sanitize_dict(income_stmt.loc['Net Income'].to_dict() if 'Net Income' in income_stmt.index else {}),
                "total_assets": sanitize_dict(balance_sheet.loc['Total Assets'].to_dict() if 'Total Assets' in balance_sheet.index else {}),
                "total_debt": sanitize_dict(balance_sheet.loc['Total Debt'].to_dict() if 'Total Debt' in balance_sheet.index else {}),
                "free_cash_flow": sanitize_dict(cashflow.loc['Free Cash Flow'].to_dict() if 'Free Cash Flow' in cashflow.index else {}),
            },
            "raw_info": info
        }
        
        logger.info(f"Successfully fetched financial data for ticker='{ticker_symbol}'")
        return data
        
    except Exception as e:
        logger.error(f"Failed to fetch financial data for ticker='{ticker_symbol}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data retrieval failed: {str(e)}")


async def generate_ai_assumptions(data: Dict, model: str) -> Dict:
    """
    Step 9: Generate AI assumptions for valuation using comprehensive Step 5 data.
    
    Updated to receive ALL calculated metrics from fetch_and_calculate_all_metrics().
    
    IMPORTANT: The following inputs CANNOT be fetched via API and MUST be AI-generated:
        - Equity Risk Premium (ERP) - Macro/market input based on market conditions
        - Country Risk Premium - Geographic risk adjustment
        - Terminal EBITDA Multiple - Forward-looking exit multiple
        - Terminal Growth Rate - Long-term sustainable growth rate
    
    All other inputs (margins, growth rates, working capital days, capex ratios, 
    cost of debt, debt ratios, ROE, ROIC, market multiples) are calculated from 
    actual financial data fetched in Step 5A.
    
    Args:
        data: Comprehensive financial data dictionary containing:
            - key_stats: Market cap, enterprise value, etc.
            - income_statement: Revenue, EBITDA, net income, interest, D&A
            - balance_sheet: Debt, cash, equity, AR, inventory, AP
            - cash_flow: FCF, operating CF, capex, dividends
            - analyst_estimates: Revenue/earnings estimates, target prices
            - calculated_metrics: Margins, growth rates, working capital days, 
              capex ratios, cost of debt, debt ratios, ROE, ROIC, market multiples
        model: Selected valuation model (DCF, DuPont, COMPS)
        
    Returns:
        Dictionary containing AI-generated assumptions with error info if fallback was used
    """
    from app.engines.ai_engine import ai_engine
    
    logger.info(f"Generating AI assumptions for model='{model}'")
    
    # Extract comprehensive company data from Step 5 results
    symbol = data.get('symbol', 'UNKNOWN')
    key_stats = data.get('key_stats', {})
    income_stmt = data.get('income_statement', {})
    balance_sheet = data.get('balance_sheet', {})
    cash_flow = data.get('cash_flow', {})
    analyst_estimates = data.get('analyst_estimates', {})
    calculated_metrics = data.get('calculated_metrics', {})
    
    # Get historical values from income statement
    revenue_dict = income_stmt.get('total_revenue', {})
    ebitda_dict = income_stmt.get('ebitda', {})
    net_income_dict = income_stmt.get('net_income', {})
    interest_expense_dict = income_stmt.get('interest_expense', {})
    
    # Convert to sorted lists (most recent first)
    def get_sorted_values(d: Dict) -> List[float]:
        items = [(k, v) for k, v in d.items() if v is not None]
        try:
            sorted_items = sorted(items, key=lambda x: str(x[0]), reverse=True)
        except Exception:
            sorted_items = items
        return [v for _, v in sorted_items]
    
    revenue_history = get_sorted_values(revenue_dict)
    ebitda_history = get_sorted_values(ebitda_dict)
    net_income_history = get_sorted_values(net_income_dict)
    interest_expense_history = get_sorted_values(interest_expense_dict)
    
    # Build comprehensive company data package for AI
    company_data = {
        "ticker": symbol,
        "sector": key_stats.get('sector', 'General'),
        "industry": key_stats.get('industry', 'General'),
        
        # Financial metrics from calculated_metrics
        "financials": {
            "revenue_ttm": revenue_history[0] if revenue_history else 0,
            "ebitda_ttm": ebitda_history[0] if ebitda_history else 0,
            "net_income_ttm": net_income_history[0] if net_income_history else 0,
            
            # Margins (historical + 3Y averages)
            "ebitda_margin_latest": calculated_metrics.get('margins', {}).get('ebitda_margin', {}).get('latest'),
            "ebitda_margin_avg_3y": calculated_metrics.get('margins', {}).get('ebitda_margin', {}).get('avg_3y'),
            "net_margin_latest": calculated_metrics.get('margins', {}).get('net_margin', {}).get('latest'),
            "net_margin_avg_3y": calculated_metrics.get('margins', {}).get('net_margin', {}).get('avg_3y'),
            "fcf_margin_latest": calculated_metrics.get('margins', {}).get('fcf_margin', {}).get('latest'),
            "fcf_margin_avg_3y": calculated_metrics.get('margins', {}).get('fcf_margin', {}).get('avg_3y'),
            "operating_margin_latest": calculated_metrics.get('margins', {}).get('operating_margin', {}).get('latest'),
            
            # Growth Rates (CAGR, YoY)
            "revenue_growth_yoy_latest": calculated_metrics.get('growth_rates', {}).get('revenue', {}).get('latest_yoy'),
            "revenue_cagr_3y": calculated_metrics.get('growth_rates', {}).get('revenue', {}).get('cagr_3y'),
            "revenue_cagr_5y": calculated_metrics.get('growth_rates', {}).get('revenue', {}).get('cagr_5y'),
            "ebitda_cagr_3y": calculated_metrics.get('growth_rates', {}).get('ebitda', {}).get('cagr_3y'),
            "net_income_cagr_3y": calculated_metrics.get('growth_rates', {}).get('net_income', {}).get('cagr_3y'),
            "eps_cagr_3y": calculated_metrics.get('growth_rates', {}).get('eps', {}).get('cagr_3y'),
        },
        
        # Working Capital Days (AR, Inv, AP)
        "working_capital": {
            "dso_latest": calculated_metrics.get('working_capital_days', {}).get('dso', {}).get('latest'),
            "dso_avg_3y": calculated_metrics.get('working_capital_days', {}).get('dso', {}).get('avg_3y'),
            "dio_latest": calculated_metrics.get('working_capital_days', {}).get('dio', {}).get('latest'),
            "dio_avg_3y": calculated_metrics.get('working_capital_days', {}).get('dio', {}).get('avg_3y'),
            "dpo_latest": calculated_metrics.get('working_capital_days', {}).get('dpo', {}).get('latest'),
            "dpo_avg_3y": calculated_metrics.get('working_capital_days', {}).get('dpo', {}).get('avg_3y'),
            "cash_conversion_cycle_latest": calculated_metrics.get('working_capital_days', {}).get('cash_conversion_cycle', {}).get('latest'),
        },
        
        # Capex Ratios
        "capex": {
            "capex_to_revenue_latest": calculated_metrics.get('capex_ratios', {}).get('capex_to_revenue', {}).get('latest'),
            "capex_to_revenue_avg_3y": calculated_metrics.get('capex_ratios', {}).get('capex_to_revenue', {}).get('avg_3y'),
            "fcf_to_revenue_latest": calculated_metrics.get('capex_ratios', {}).get('fcf_to_revenue', {}).get('latest'),
            "capex_to_ocf_latest": calculated_metrics.get('capex_ratios', {}).get('capex_to_ocf', {}).get('latest'),
        },
        
        # Cost of Debt (Implied = Interest Expense / Total Debt)
        "debt_cost": {
            "implied_cost_of_debt_latest": calculated_metrics.get('cost_of_debt', {}).get('implied_cost_of_debt', {}).get('latest'),
            "implied_cost_of_debt_avg_3y": calculated_metrics.get('cost_of_debt', {}).get('implied_cost_of_debt', {}).get('avg_3y'),
        },
        
        # Debt Ratios
        "leverage": {
            "debt_to_equity_latest": calculated_metrics.get('debt_ratios', {}).get('debt_to_equity', {}).get('latest'),
            "debt_to_assets_latest": calculated_metrics.get('debt_ratios', {}).get('debt_to_assets', {}).get('latest'),
            "current_ratio_latest": calculated_metrics.get('debt_ratios', {}).get('current_ratio', {}).get('latest'),
            "quick_ratio_latest": calculated_metrics.get('debt_ratios', {}).get('quick_ratio', {}).get('latest'),
            "net_debt_latest": calculated_metrics.get('debt_ratios', {}).get('net_debt', {}).get('latest'),
        },
        
        # Profitability & Returns (ROE, ROIC)
        "returns": {
            "roe_latest": calculated_metrics.get('roe_roic', {}).get('roe', {}).get('latest'),
            "roic_latest": calculated_metrics.get('roe_roic', {}).get('roic', {}).get('latest'),
            "roa_latest": calculated_metrics.get('profitability_ratios', {}).get('roa', {}).get('latest'),
        },
        
        # Market Data
        "market_data": {
            "beta": key_stats.get('beta', 1.0),
            "market_cap": key_stats.get('market_cap'),
            "enterprise_value": key_stats.get('enterprise_value'),
            "current_price": key_stats.get('current_price'),
            "pe_ratio": key_stats.get('pe_ratio'),
            "price_to_book": key_stats.get('price_to_book'),
            "ev_to_ebitda": key_stats.get('ev_to_ebitda'),
            "dividend_yield": key_stats.get('dividend_yield'),
        },
        
        # Market Multiples
        "multiples": calculated_metrics.get('market_multiples', {}),
        
        # Analyst Estimates
        "analyst_estimates": {
            "revenue_growth_estimate": analyst_estimates.get('revenue_estimates', {}).get('growth'),
            "earnings_growth_estimate": analyst_estimates.get('earnings_estimates', {}).get('growth'),
            "target_price_mean": analyst_estimates.get('target_prices', {}).get('mean'),
            "num_analysts": analyst_estimates.get('revenue_estimates', {}).get('num_analysts'),
        },
    }
    
    # Get provider status for transparency
    provider_status = ai_engine.get_provider_status()
    available_providers = [k for k, v in provider_status.items() if v == "configured"]
    
    # Generate AI assumptions with strategy pattern
    # Pass market parameter for proper strategy routing (Vietnam vs US/International)
    market = session_data.get('market', 'US')
    ai_results = ai_engine.generate_assumptions(company_data, model, market)
    
    formatted_results = {"model": model.upper()}
    
    # Extract AI status information for better error reporting
    ai_status = ai_results.pop("_ai_status", None)
    
    # Add metadata about AI generation with detailed error info
    formatted_results["_metadata"] = {
        "provider_status": provider_status,
        "available_providers": available_providers,
        "used_fallback": ai_status.get("success", False) is False if ai_status else (
            len(ai_results.get("equity_risk_premium", {}).get("sources", "").split(":")[0].strip() if isinstance(ai_results.get("equity_risk_premium", {}).get("sources"), str) else "") == 0 or 
            "Fallback" in ai_results.get("equity_risk_premium", {}).get("rationale", "") or
            "CAPM (Fallback" in ai_results.get("equity_risk_premium", {}).get("rationale", "")
        ),
        "ai_success": ai_status.get("success") if ai_status else None,
        "provider_used": ai_status.get("provider_used") if ai_status else None,
        "provider_errors": ai_status.get("errors", {}) if ai_status else {},
        "fallback_reason": ai_status.get("fallback_reason") if ai_status and not ai_status.get("success") else None,
        "comprehensive_data_used": True,  # Flag indicating Step 5 data was used
    }
    
    for key, item in ai_results.items():
        if isinstance(item, dict) and 'value' in item:
            formatted_results[key] = item
        elif isinstance(item, list):
            formatted_list = []
            for idx, val in enumerate(item):
                if isinstance(val, dict) and 'value' in val:
                    formatted_list.append({
                        "year": idx + 1,
                        **val
                    })
                else:
                    formatted_list.append({
                        "year": idx + 1,
                        "value": val,
                        "rationale": "AI Forecast",
                        "sources": "Trend Extrapolation"
                    })
            formatted_results[key] = formatted_list
    
    logger.info(f"AI assumptions generated successfully for model='{model}' using comprehensive Step 5 data")
    return formatted_results


def run_valuation_engine(session_data: Dict) -> Dict:
    """
    Step 11: Run valuation calculations.
    
    Args:
        session_data: Session data containing model, assumptions, and financial data
        
    Returns:
        Dictionary containing valuation results
    """
    from app.engines.dcf_engine import DCFEngine, DCFInputs, ScenarioDrivers, fetch_dcf_inputs
    
    model = session_data.get('selected_model', 'DCF')
    market = session_data.get('market', 'international')
    assumptions = session_data['confirmed_assumptions']
    financial_data = session_data['financial_data']
    financials = financial_data['financials']
    profile = financial_data['profile']
    ticker = session_data.get('ticker', 'UNKNOWN')
    
    logger.info(f"Running valuation engine for model='{model}', ticker='{ticker}', market='{market}'")
    
    selected_model = model.lower() if model else 'dcf'
    
    if selected_model == 'dcf':
        try:
            ticker_symbol = session_data.get('ticker', 'UNKNOWN')
            peer_tickers_from_input = assumptions.get('peer_tickers', None)
            
            logger.info(f"Fetching DCF inputs for ticker='{ticker_symbol}'")
            company_info, comparables = fetch_dcf_inputs(ticker_symbol, peer_tickers_from_input)
            
            revenue_history = list(financials.get('revenue', {}).values())
            ebitda_history = list(financials.get('ebitda', {}).values())
            net_income_history = list(financials.get('net_income', {}).values())
            
            info = profile.get('raw_info', {})
            shares_outstanding = info.get('sharesOutstanding', 1000000) or 1000000
            current_price = profile.get('current_price', 100) or 100
            
            total_debt = info.get('totalDebt', 0) or 0
            cash = info.get('cash', info.get('totalCash', 0)) or 0
            net_debt = total_debt - cash
            ppe_net = info.get('totalAssets', 0) or 0
            
            def build_historical_year(rev, ebitda, ni):
                return {
                    'revenue': rev or 0,
                    'ebitda': ebitda or 0,
                    'net_income': ni or 0,
                    'cogs': (rev or 0) * 0.6 if rev else 0,
                    'sga': (rev or 0) * 0.25 if rev else 0,
                    'other_opex': (rev or 0) * 0.05 if rev else 0,
                    'accounts_receivable': (rev or 0) * 0.1 if rev else 0,
                    'inventory': (rev or 0) * 0.08 if rev else 0,
                    'accounts_payable': (rev or 0) * 0.07 if rev else 0
                }
            
            hist_fy_minus_1 = build_historical_year(
                revenue_history[0] if len(revenue_history) > 0 else None,
                ebitda_history[0] if len(ebitda_history) > 0 else None,
                net_income_history[0] if len(net_income_history) > 0 else None
            )
            hist_fy_minus_2 = build_historical_year(
                revenue_history[1] if len(revenue_history) > 1 else None,
                ebitda_history[1] if len(ebitda_history) > 1 else None,
                net_income_history[1] if len(net_income_history) > 1 else None
            )
            hist_fy_minus_3 = build_historical_year(
                revenue_history[2] if len(revenue_history) > 2 else None,
                ebitda_history[2] if len(ebitda_history) > 2 else None,
                net_income_history[2] if len(net_income_history) > 2 else None
            )
            
            revenue_growth = assumptions.get('revenue_growth_forecast', [0.05, 0.05, 0.04, 0.04, 0.03, 0.02])
            while len(revenue_growth) < 6:
                revenue_growth.append(0.02)
            
            wacc = company_info.get('wacc', assumptions.get('wacc', 0.08))
            terminal_growth = assumptions.get('terminal_growth_rate', 0.023)
            terminal_multiple = assumptions.get('terminal_ebitda_multiple', 8.0)
            
            volume_split = assumptions.get('volume_growth_split', 0.6)
            base_volume_growth = [g * volume_split for g in revenue_growth[:6]]
            base_price_growth = [g * (1 - volume_split) for g in revenue_growth[:6]]
            
            base_drivers = ScenarioDrivers(
                volume_growth=base_volume_growth,
                price_growth=base_price_growth,
                inflation_rate=[assumptions.get('inflation_rate', 0.02)] * 6 if not isinstance(assumptions.get('inflation_rate'), list) else assumptions.get('inflation_rate', [0.02]*6)[:6],
                capex=[hist_fy_minus_1['revenue'] * assumptions.get('capex_pct_of_revenue', 0.05)] * 6,
                ar_days=[assumptions.get('ar_days', 45)] * 5,
                inv_days=[assumptions.get('inv_days', 60)] * 5,
                ap_days=[assumptions.get('ap_days', 30)] * 5,
                terminal_ebitda_multiple=terminal_multiple,
                terminal_growth_rate=terminal_growth
            )
            
            dcf_inputs = DCFInputs(
                valuation_date=date.today().isoformat(),
                currency="VND" if market == "vietnamese" else profile.get('currency', 'USD'),
                historical_fy_minus_1=hist_fy_minus_1,
                historical_fy_minus_2=hist_fy_minus_2,
                historical_fy_minus_3=hist_fy_minus_3,
                net_debt=net_debt,
                ppe_net=ppe_net,
                tax_basis_ppe=ppe_net * 0.8,
                tax_losses_nol=0,
                shares_outstanding=shares_outstanding,
                current_stock_price=current_price,
                projected_interest_expense=net_debt * 0.05 if net_debt > 0 else 0,
                useful_life_existing=assumptions.get('useful_life_existing', 10.0),
                useful_life_new=assumptions.get('useful_life_new', 10.0),
                forecast_drivers={
                    "base_case": base_drivers,
                    "best_case": base_drivers,
                    "worst_case": base_drivers
                },
                wacc=wacc,
                risk_free_rate=assumptions.get('risk_free_rate', 0.045),
                equity_risk_premium=assumptions.get('equity_risk_premium', 0.055),
                beta=assumptions.get('beta', 1.0),
                cost_of_debt=assumptions.get('cost_of_debt', 0.05),
                tax_rate_statutory=assumptions.get('tax_rate', 0.21),
                tax_loss_utilization_limit_pct=assumptions.get('tax_loss_utilization_limit_pct', 0.80)
            )
            
            engine = DCFEngine(dcf_inputs)
            pv_discrete, pv_terminal_perp, ev_perpetuity = engine._calculate_dcf_perpetuity(base_drivers)
            pv_terminal_mult, ev_multiple = engine._calculate_dcf_exit_multiple(base_drivers)
            
            equity_value_perp = ev_perpetuity - net_debt
            equity_value_mult = ev_multiple - net_debt
            share_price_perp = equity_value_perp / shares_outstanding
            share_price_mult = equity_value_mult / shares_outstanding
            upside_perp = (share_price_perp - current_price) / current_price * 100
            upside_mult = (share_price_mult - current_price) / current_price * 100
            
            logger.info(f"DCF valuation completed: EV Perpetuity={ev_perpetuity:.2f}, Share Price={share_price_perp:.2f}")
            
            return {
                "model": "DCF",
                "main_outputs": {
                    "enterprise_value_perpetuity": round(ev_perpetuity, 2),
                    "enterprise_value_multiple": round(ev_multiple, 2),
                    "equity_value_perpetuity": round(equity_value_perp, 2),
                    "equity_value_multiple": round(equity_value_mult, 2),
                    "equity_value_per_share_perpetuity": round(share_price_perp, 2),
                    "equity_value_per_share_multiple": round(share_price_mult, 2),
                    "current_stock_price": current_price,
                    "upside_downside_perpetuity_pct": round(upside_perp, 2),
                    "upside_downside_multiple_pct": round(upside_mult, 2)
                },
                "message": "DCF calculated successfully"
            }
            
        except Exception as e:
            logger.error(f"DCF valuation failed: {str(e)}")
            return {
                "model": "DCF",
                "error": str(e),
                "fallback_message": "DCF calculation failed."
            }
    
    elif selected_model in ['dupont', 'dupont analysis']:
        try:
            from app.engines.dupont_engine import DuPontAnalyzer
            
            api_key = os.getenv('GROQ_API_KEY', '')
            engine = DuPontAnalyzer(api_key=api_key)
            custom_inputs = session_data.get('dupont_custom_inputs', {})
            
            # Note: DuPont analyze is synchronous, not async
            result = engine.analyze(ticker=ticker, custom_inputs=custom_inputs)
            
            if hasattr(result, '__await__'):
                import asyncio
                result = asyncio.get_event_loop().run_until_complete(result)
            
            if result.status == "error":
                raise HTTPException(status_code=400, detail=result.message)
            
            logger.info(f"DuPont analysis completed: ROE={result.roe:.2%}")
            
            return {
                "model": "DuPont",
                "success": True,
                "results": {
                    "roe": result.roe,
                    "net_profit_margin": result.net_profit_margin,
                    "asset_turnover": result.asset_turnover,
                    "equity_multiplier": result.equity_multiplier,
                },
                "message": result.message
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"DuPont analysis failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"DuPont analysis error: {str(e)}")
    
    elif selected_model in ['comps', 'comparable', 'trading comps']:
        try:
            from app.engines.comps_engine import TradingCompsAnalyzer, TargetCompanyData, PeerCompanyData
            
            info = profile.get('raw_info', {})
            market_cap = info.get('marketCap', 1000000000) or 1000000000
            enterprise_value = market_cap + (info.get('totalDebt', 0) or 0) - (info.get('cash', 0) or 0)
            revenue_ltm = list(financials.get('revenue', {}).values())[0] if financials.get('revenue') else 100000000
            ebitda_ltm = list(financials.get('ebitda', {}).values())[0] if financials.get('ebitda') else revenue_ltm * 0.2
            
            target = TargetCompanyData(
                ticker=ticker,
                company_name=profile.get('name', ticker),
                market_cap=market_cap,
                enterprise_value=enterprise_value,
                revenue_ltm=revenue_ltm,
                ebitda_ltm=ebitda_ltm,
                ebit_ltm=ebitda_ltm * 0.75,
                net_income_ltm=revenue_ltm * 0.1,
                free_cash_flow_ltm=ebitda_ltm * 0.7,
                book_equity=market_cap * 0.4,
                shares_outstanding=info.get('sharesOutstanding', 1000000) or 1000000,
                current_stock_price=profile.get('current_price', 100) or 100,
                currency="VND" if market == "vietnamese" else profile.get('currency', 'USD')
            )
            
            sector = info.get('sector', 'Technology')
            industry = info.get('industry', 'Software')
            
            peers = []
            peer_names = ['Peer A', 'Peer B', 'Peer C', 'Peer D', 'Peer E']
            peer_tickers = ['PEERA', 'PEERB', 'PEERC', 'PEERD', 'PEERE']
            
            import random
            random.seed(42)
            
            for i, (name, ticker_sym) in enumerate(zip(peer_names, peer_tickers)):
                variation = 0.8 + (random.random() * 0.4)
                peers.append(PeerCompanyData(
                    ticker=ticker_sym,
                    company_name=f"{name} Corp",
                    market_cap=market_cap * variation,
                    enterprise_value=enterprise_value * variation,
                    revenue_ltm=revenue_ltm * variation,
                    ebitda_ltm=ebitda_ltm * variation,
                    ebit_ltm=ebitda_ltm * 0.75 * variation,
                    net_income_ltm=revenue_ltm * 0.1 * variation,
                    free_cash_flow_ltm=ebitda_ltm * 0.7 * variation,
                    book_equity=market_cap * 0.4 * variation,
                    shares_outstanding=1000000 * variation,
                    current_stock_price=100 * variation,
                    industry=industry,
                    sector=sector,
                    selection_reason=f"Same {sector} sector",
                    similarity_score=0.9 - (i * 0.05)
                ))
            
            analyzer = TradingCompsAnalyzer(target, peers)
            outputs = analyzer.run_analysis(apply_outlier_filtering=True)
            
            logger.info(f"Trading Comps analysis completed with {outputs.peer_count_total} peers")
            
            return {
                "model": "Comps",
                "success": True,
                "result": outputs.to_json_schema_format(),
                "message": "Trading Comps analysis completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Trading Comps analysis failed: {str(e)}")
            return {
                "model": "Comps",
                "error": str(e),
                "fallback_message": "Trading Comps analysis failed."
            }
    
    logger.warning(f"Unknown model requested: {selected_model}")
    return {
        "error": f"Unknown model: {selected_model}",
        "message": "Please select a valid model: DCF, DuPont, or Comps"
    }


@router.post("/step-4-select-models")
async def select_models(request: ModelSelectRequest):
    """
    Step 4: User selects valuation model.
    
    Args:
        request: Model selection request
        
    Returns:
        Confirmation message and next step
    """
    from app.main import get_session_store
    
    logger.info(f"Selecting model='{request.model}' for session='{request.session_id}'")
    
    sessions = get_session_store()
    session = get_session(request.session_id, sessions)
    
    session['selected_model'] = request.model
    session['status'] = "model_selected"
    
    logger.info(f"Model '{request.model}' selected for session='{request.session_id}'")
    
    return {
        "message": "Model selected",
        "next_step": "fetch_data",
        "selected_model": request.model
    }


@router.post("/step-5-prepare-inputs", response_model=PrepareInputsResponse)
async def prepare_inputs(request: dict = Body(...)):
    """
    Step 5: Show required inputs for the selected model.
    
    Args:
        request: Request containing session_id
        
    Returns:
        List of required input fields
    """
    from app.main import get_session_store
    
    session_id = request.get('session_id')
    sessions = get_session_store()
    session = get_session(session_id, sessions)
    
    if not session or not session.get('selected_model'):
        raise HTTPException(status_code=400, detail="No model selected")
    
    selected_model = session['selected_model'].lower()
    required_inputs: List[Dict[str, Any]] = []
    
    required_inputs.append({
        "category": "General",
        "name": "Ticker Confirmation",
        "requiresInput": False
    })
    
    if selected_model == 'dcf':
        required_inputs.extend([
            # Market Structure (from API)
            {"category": "Market Structure", "name": "Current Price", "requiresInput": False, "unit": "USD", "description": "Current stock price"},
            {"category": "Market Structure", "name": "Shares Outstanding", "requiresInput": False, "unit": "thousands", "description": "Number of shares outstanding"},
            {"category": "Market Structure", "name": "Total Debt", "requiresInput": False, "unit": "USD thousands", "description": "Total debt from balance sheet"},
            {"category": "Market Structure", "name": "Cash & Equivalents", "requiresInput": False, "unit": "USD thousands", "description": "Cash and cash equivalents"},
            {"category": "Market Structure", "name": "Net Debt", "requiresInput": False, "unit": "USD thousands", "description": "Total debt minus cash"},
            
            # WACC Inputs (requires user/AI input)
            {"category": "WACC Calculation", "name": "Risk-Free Rate", "requiresInput": True, "defaultValue": 2.4, "unit": "%", "description": "Government bond yield (e.g., 10Y Treasury)"},
            {"category": "WACC Calculation", "name": "Market Risk Premium", "requiresInput": True, "defaultValue": 4.7, "unit": "%", "description": "Expected excess return of market over risk-free rate"},
            {"category": "WACC Calculation", "name": "Country Risk Premium", "requiresInput": True, "defaultValue": 3.6, "unit": "%", "description": "Additional premium for country-specific risk"},
            {"category": "WACC Calculation", "name": "Pre-Tax Cost of Debt", "requiresInput": True, "defaultValue": 5.2, "unit": "%", "description": "Interest rate on company debt before tax"},
            {"category": "WACC Calculation", "name": "Target Debt Weight", "requiresInput": True, "defaultValue": 15.0, "unit": "%", "description": "Target proportion of debt in capital structure"},
            {"category": "WACC Calculation", "name": "Target Equity Weight", "requiresInput": True, "defaultValue": 85.0, "unit": "%", "description": "Target proportion of equity in capital structure"},
            {"category": "WACC Calculation", "name": "Tax Rate", "requiresInput": True, "defaultValue": 30.0, "unit": "%", "description": "Corporate income tax rate"},
            
            # Forecast Assumptions (requires user/AI input)
            {"category": "Forecast Assumptions", "name": "Terminal Growth Rate", "requiresInput": True, "defaultValue": 2.0, "unit": "%", "description": "Perpetual growth rate for terminal value calculation"},
            {"category": "Forecast Assumptions", "name": "Terminal EBITDA Multiple", "requiresInput": True, "defaultValue": 7.0, "unit": "x", "description": "Exit multiple for terminal value calculation"},
            {"category": "Forecast Assumptions", "name": "Revenue Volume Growth (FY1-FY5)", "requiresInput": True, "defaultValue": [2.0, 1.0, 1.0, 0.5, 0.5], "unit": "%", "description": "Annual sales volume growth rates for 5 forecast years"},
            {"category": "Forecast Assumptions", "name": "Revenue Price Growth (FY1-FY5)", "requiresInput": True, "defaultValue": [3.0, 1.0, 1.0, 1.0, 0.5], "unit": "%", "description": "Annual pricing increase rates for 5 forecast years"},
            {"category": "Forecast Assumptions", "name": "Inflation Rate (FY1-FY5)", "requiresInput": True, "defaultValue": [3.5, 3.0, 3.0, 2.5, 2.5], "unit": "%", "description": "Projected cost inflation rates for COGS and OpEx"},
            {"category": "Forecast Assumptions", "name": "Capital Expenditure (FY1-FY5)", "requiresInput": True, "defaultValue": [4550, 4700, 4850, 5000, 5125], "unit": "USD thousands", "description": "Planned capital expenditures for each forecast year"},
            {"category": "Forecast Assumptions", "name": "Accounts Receivable Days", "requiresInput": True, "defaultValue": 45.0, "unit": "days", "description": "Average collection period for receivables"},
            {"category": "Forecast Assumptions", "name": "Inventory Days", "requiresInput": True, "defaultValue": 25.0, "unit": "days", "description": "Average days inventory is held"},
            {"category": "Forecast Assumptions", "name": "Accounts Payable Days", "requiresInput": True, "defaultValue": 40.0, "unit": "days", "description": "Average payment period for payables"},
            
            # Depreciation Parameters
            {"category": "Depreciation Parameters", "name": "Useful Life - Existing Assets", "requiresInput": True, "defaultValue": 16.0, "unit": "years", "description": "Remaining useful life of existing PP&E"},
            {"category": "Depreciation Parameters", "name": "Useful Life - New Assets", "requiresInput": True, "defaultValue": 20.0, "unit": "years", "description": "Useful life of new capital assets"},
            {"category": "Depreciation Parameters", "name": "First Year Tax Depreciation Rate", "requiresInput": True, "defaultValue": 50.0, "unit": "%", "description": "Half-year convention rate for first year tax depreciation"},
            {"category": "Depreciation Parameters", "name": "Blended Tax Depreciation Rate", "requiresInput": True, "defaultValue": 15.0, "unit": "%", "description": "Declining balance depreciation rate for tax purposes"},
            {"category": "Depreciation Parameters", "name": "First Year Accounting Depreciation Rate", "requiresInput": True, "defaultValue": 50.0, "unit": "%", "description": "Half-year convention for accounting depreciation"},
            
            # Opening Balance Sheet
            {"category": "Opening Balance Sheet", "name": "PP&E Gross Book Value", "requiresInput": False, "unit": "USD thousands", "description": "Gross book value of property, plant & equipment"},
            {"category": "Opening Balance Sheet", "name": "Tax Basis of PP&E", "requiresInput": False, "unit": "USD thousands", "description": "Tax basis of PP&E for depreciation calculations"},
            {"category": "Opening Balance Sheet", "name": "Tax Losses Carried Forward", "requiresInput": False, "unit": "USD thousands", "description": "Net operating losses available for carryforward"},
            {"category": "Opening Balance Sheet", "name": "Projected Interest Expense", "requiresInput": True, "defaultValue": 2520.0, "unit": "USD thousands", "description": "Annual interest expense on debt"},
            
            # Dates
            {"category": "Valuation Dates", "name": "Valuation Date", "requiresInput": False, "unit": "date", "description": "Date of valuation"},
            {"category": "Valuation Dates", "name": "First Cash Flow Date", "requiresInput": False, "unit": "date", "description": "Expected date of first cash flow"},
            {"category": "Valuation Dates", "name": "First Fiscal Year End", "requiresInput": False, "unit": "date", "description": "End date of first forecast fiscal year"},
        ])
    elif selected_model in ['comparable', 'comps']:
        required_inputs.extend([
            {"category": "Market Structure", "name": "Current Price", "requiresInput": False},
            {"category": "Market Structure", "name": "Market Capitalization", "requiresInput": False},
            {"category": "Peer Selection", "name": "Peer Group Tickers", "requiresInput": True},
        ])
    elif selected_model == 'dupont':
        required_inputs.extend([
            {"category": "Income Statement", "name": "Revenue", "requiresInput": False},
            {"category": "Income Statement", "name": "Net Income", "requiresInput": False},
            {"category": "Balance Sheet", "name": "Total Assets", "requiresInput": False},
            {"category": "Balance Sheet", "name": "Total Equity", "requiresInput": False},
        ])
    
    logger.info(f"Prepared {len(required_inputs)} input requirements for model='{selected_model}'")
    
    return PrepareInputsResponse(
        status="ready_to_fetch",
        required_inputs=[InputRequirement(**r) for r in required_inputs],
        message=f"Found {len(required_inputs)} required inputs for your selected model"
    )


@router.post("/step-6-fetch-api-data", response_model=FetchDataResponse)
async def fetch_api_data(request: SessionFetchRequest):
    """
    Step 6: Fetch financial data from external APIs.
    
    This endpoint handles ONLY API data retrieval:
    - Historical financials from yFinance
    - Forecast drivers from historical data
    - Peer comparison data
    - DCF inputs (WACC, terminal growth)
    - DuPont analysis results
    - Comps analysis results
    
    Args:
        request: Session fetch request
        
    Returns:
        Financial data retrieved from APIs
    """
    from app.main import get_session_store
    
    logger.info(f"Fetching API data for session='{request.session_id}'")
    
    sessions = get_session_store()
    session = get_session(request.session_id, sessions)
    
    financial_data = fetch_financial_data(session['ticker'], session['market'])
    session['financial_data'] = financial_data
    session['status'] = "data_fetched"
    
    logger.info(f"API data fetched successfully for session='{request.session_id}'")
    
    return FetchDataResponse(
        status="data_ready",
        data=financial_data,
        message="Financial data retrieved successfully from APIs."
    )


@router.post("/step-7-generate-ai-assumptions", response_model=AIAssumptionsResponse)
async def generate_ai_assumptions_endpoint(request: Request):
    """
    Step 7: Generate AI assumptions for valuation.
    
    This endpoint handles ONLY AI generation:
    - WACC with rationale
    - Terminal Growth Rate with rationale
    - Revenue Growth Forecast
    - EBITDA Margin Forecast
    
    Includes proper timeout handling and fallback logic.
    
    Args:
        request: Request containing session_id
        
    Returns:
        AI-generated assumptions with detailed error information if fallback was used
    """
    from app.main import get_session_store
    import asyncio
    from concurrent.futures import TimeoutError as FuturesTimeoutError
    
    data = await request.json()
    session_id = data.get('session_id')
    sessions = get_session_store()
    session = get_session(session_id, sessions)
    
    if not session['financial_data']:
        raise HTTPException(status_code=400, detail="Financial data missing")
    
    try:
        # Add timeout wrapper for AI generation (90 seconds max)
        logger.info(f"Starting AI generation for session='{session_id}' with 90s timeout...")
        
        # Run AI generation with timeout
        ai_results = await asyncio.wait_for(
            generate_ai_assumptions(session['financial_data'], session['selected_model']),
            timeout=90.0
        )
        
        session['ai_suggestions'] = ai_results
        session['status'] = "ai_generated"
        
        logger.info(f"AI assumptions generated successfully for session='{session_id}'")
        
    except asyncio.TimeoutError:
        logger.error(f"AI generation timed out for session='{session_id}' after 90 seconds")
        # Return a structured error response instead of throwing
        return AIAssumptionsResponse(
            status="ai_timeout",
            suggestions={
                "_metadata": {
                    "provider_status": {},
                    "available_providers": [],
                    "used_fallback": True,
                    "ai_success": False,
                    "provider_used": None,
                    "provider_errors": {"timeout": "AI generation exceeded 90 second timeout"},
                    "fallback_reason": "Request timeout - AI providers did not respond within time limit"
                }
            },
            message="⚠️ AI generation timed out after 90 seconds. Using deterministic fallback assumptions based on historical data and standard formulas."
        )
    except Exception as e:
        logger.error(f"AI generation failed for session='{session_id}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")
    
    return AIAssumptionsResponse(
        status="ai_ready",
        suggestions=ai_results,
        message="AI analysis complete. Please review assumptions."
    )


@router.post("/step-10-confirm-assumptions")
async def confirm_assumptions(request: AssumptionConfirmRequest):
    """
    Step 10: User confirms or modifies AI assumptions.
    
    Args:
        request: Assumption confirmation request
        
    Returns:
        Final confirmed assumptions
    """
    from app.main import get_session_store
    
    logger.info(f"Confirming assumptions for session='{request.session_id}'")
    
    sessions = get_session_store()
    session = get_session(request.session_id, sessions)
    
    final_assumptions = {**session['ai_suggestions'], **request.assumptions}
    session['confirmed_assumptions'] = final_assumptions
    session['status'] = "assumptions_confirmed"
    
    logger.info(f"Assumptions confirmed for session='{request.session_id}'")
    
    return {
        "status": "ready_for_valuation",
        "assumptions": final_assumptions
    }


@router.post("/step-11-12-valuate", response_model=ValuationResultResponse)
async def run_valuation(request: CalculationRequest):
    """
    Step 11 & 12: Run valuation engine and return results.
    
    Args:
        request: Calculation request
        
    Returns:
        Valuation results
    """
    from app.main import get_session_store
    
    logger.info(f"Running valuation for session='{request.session_id}'")
    
    sessions = get_session_store()
    session = get_session(request.session_id, sessions)
    
    if not session['confirmed_assumptions']:
        raise ValidationException(
            message="Assumptions not confirmed",
            field="confirmed_assumptions"
        ).to_dict()
    
    results = run_valuation_engine(session)
    session['valuation_result'] = results
    session['status'] = "completed"
    
    logger.info(f"Valuation completed for session='{request.session_id}'")
    
    return ValuationResultResponse(
        status="completed",
        result=results,
        inputs_used=session['confirmed_assumptions']
    )
