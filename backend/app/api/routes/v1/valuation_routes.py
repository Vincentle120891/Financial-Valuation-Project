"""
Valuation Routes - Version 1

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

router = APIRouter(tags=["Valuation"])


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
        )
    return sessions[session_id]


def fetch_financial_data(ticker_symbol: str, market: str) -> Dict:
    """
    Step 7 & 8: Fetch financial data from yFinance.
    
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
        
        # Calculate historical metrics
        revenue_years = list(income_stmt.columns) if income_stmt is not None and not income_stmt.empty else []
        revenue_values = [sanitize_value(income_stmt.loc['Total Revenue', year]) for year in revenue_years] if 'Total Revenue' in income_stmt.index else []
        ebitda_values = [sanitize_value(income_stmt.loc['EBITDA', year]) for year in revenue_years] if 'EBITDA' in income_stmt.index else []
        
        # Calculate CAGR and averages
        revenue_cagr = None
        avg_ebitda_margin = None
        avg_roe = None
        
        if len(revenue_values) >= 3 and revenue_values[0] and revenue_values[-1]:
            n_years = len(revenue_values) - 1
            revenue_cagr = (revenue_values[0] / revenue_values[-1]) ** (1/n_years) - 1
        
        ebitda_margins = []
        net_incomes = []
        total_assets_list = []
        for year in revenue_years:
            rev = sanitize_value(income_stmt.loc['Total Revenue', year]) if 'Total Revenue' in income_stmt.index else None
            ebit = sanitize_value(income_stmt.loc['EBITDA', year]) if 'EBITDA' in income_stmt.index else None
            net = sanitize_value(income_stmt.loc['Net Income', year]) if 'Net Income' in income_stmt.index else None
            assets = sanitize_value(balance_sheet.loc['Total Assets', year]) if 'Total Assets' in balance_sheet.index else None
            
            if rev and ebit:
                ebitda_margins.append(ebit / rev)
            if rev and net:
                net_incomes.append(net)
            if assets and net:
                total_assets_list.append(assets)
        
        if ebitda_margins:
            avg_ebitda_margin = sum(ebitda_margins) / len(ebitda_margins)
        
        if net_incomes and total_assets_list:
            avg_roe = sum([n/a for n,a in zip(net_incomes, total_assets_list)]) / len(net_incomes)
        
        # Build historical financials object
        historical_financials = {
            "revenue": {str(year): sanitize_value(income_stmt.loc['Total Revenue', year]) for year in revenue_years} if 'Total Revenue' in income_stmt.index else {},
            "ebitda": {str(year): sanitize_value(income_stmt.loc['EBITDA', year]) for year in revenue_years} if 'EBITDA' in income_stmt.index else {},
            "revenue_cagr": revenue_cagr,
            "avg_ebitda_margin": avg_ebitda_margin,
            "avg_roe": avg_roe
        }
        
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
                "years": [str(year) for year in revenue_years]
            },
            "historical_financials": historical_financials,
            "raw_info": info
        }
        
        logger.info(f"Successfully fetched financial data for ticker='{ticker_symbol}'")
        return data
        
    except Exception as e:
        logger.error(f"Failed to fetch financial data for ticker='{ticker_symbol}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data retrieval failed: {str(e)}")


async def generate_ai_assumptions(data: Dict, model: str) -> Dict:
    """
    Step 9: Generate AI assumptions for valuation.
    
    Args:
        data: Financial data dictionary
        model: Selected valuation model (DCF, DuPont, COMPS)
        
    Returns:
        Dictionary containing AI-generated assumptions
    """
    from app.engines.ai_engine import ai_engine
    
    logger.info(f"Generating AI assumptions for model='{model}'")
    
    profile = data.get('profile', {})
    financials = data.get('financials', {})
    
    revenue_history = list(financials.get('revenue', {}).values())
    ebitda_history = list(financials.get('ebitda', {}).values())
    net_income_history = list(financials.get('net_income', {}).values())
    
    rev_growth_rates = []
    for i in range(min(3, len(revenue_history) - 1)):
        if revenue_history[i] and revenue_history[i+1] and revenue_history[i+1] > 0:
            growth = (revenue_history[i] - revenue_history[i+1]) / revenue_history[i+1]
            rev_growth_rates.append(growth)
    
    avg_hist_growth = sum(rev_growth_rates) / len(rev_growth_rates) if rev_growth_rates else 0.05
    
    ebitda_margins = []
    net_margins = []
    for i in range(min(3, len(revenue_history))):
        if revenue_history[i] and ebitda_history[i]:
            ebitda_margins.append(ebitda_history[i] / revenue_history[i])
        if revenue_history[i] and net_income_history[i]:
            net_margins.append(net_income_history[i] / revenue_history[i])
    
    company_data = {
        "ticker": profile.get('ticker', 'UNKNOWN'),
        "sector": profile.get('sector', 'General'),
        "financials": {
            "revenue_ttm": revenue_history[0] if revenue_history else 0,
            "ebitda_margin_avg": round(sum(ebitda_margins)/len(ebitda_margins)*100, 1) if ebitda_margins else 15.0,
            "net_margin_avg": round(sum(net_margins)/len(net_margins)*100, 1) if net_margins else 10.0,
            "revenue_growth_avg": round(avg_hist_growth * 100, 1)
        },
        "market_data": {
            "beta": profile.get('beta', 1.0),
            "risk_free_rate": 4.5
        }
    }
    
    ai_results = ai_engine.generate_assumptions(company_data, model)
    
    formatted_results = {"model": model.upper()}
    
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
    
    logger.info(f"AI assumptions generated successfully for model='{model}'")
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
            
            # Get the actual historical years from financial data
            years = financials.get('years', [])
            if len(years) >= 3:
                # Use the 3 most recent years for LTM and forward estimates
                revenue_dict = financials.get('revenue', {})
                ebitda_dict = financials.get('ebitda', {})
                
                revenue_ltm = revenue_dict.get(years[0], 100000000) if years else 100000000
                ebitda_ltm = ebitda_dict.get(years[0], revenue_ltm * 0.2) if years else revenue_ltm * 0.2
                
                # Calculate forward estimates based on historical growth
                if len(years) >= 2:
                    growth_rate = (revenue_dict.get(years[0], 0) / revenue_dict.get(years[1], 1)) - 1 if revenue_dict.get(years[1], 0) > 0 else 0.05
                else:
                    growth_rate = 0.05
            else:
                revenue_ltm = list(financials.get('revenue', {}).values())[0] if financials.get('revenue') else 100000000
                ebitda_ltm = list(financials.get('ebitda', {}).values())[0] if financials.get('ebitda') else revenue_ltm * 0.2
                growth_rate = 0.05
            
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
                share_price=profile.get('current_price', 100) or 100,
                currency=profile.get('currency', 'USD')
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
                    ebitda_ltm=ebitda_ltm * variation,
                    ebitda_fy2023=ebitda_ltm * (1 + growth_rate) * variation,
                    ebitda_fy2024=ebitda_ltm * (1 + growth_rate) ** 2 * variation,
                    eps_ltm=(revenue_ltm * 0.1 * variation) / 1000000,
                    eps_fy2023=(revenue_ltm * 0.1 * (1 + growth_rate) * variation) / 1000000,
                    eps_fy2024=(revenue_ltm * 0.1 * (1 + growth_rate) ** 2 * variation) / 1000000,
                    share_price=100 * variation,
                    shares_outstanding=1000000 * variation,
                    industry=industry,
                    sector=sector,
                    selection_reason=f"Same {sector} sector"
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


@router.post("/step-5-6-prepare-inputs", response_model=PrepareInputsResponse)
async def prepare_inputs(request: dict = Body(...)):
    """
    Step 5 & 6: Show required inputs for the selected model.
    
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
    
    # General inputs (auto-fetched but shown for transparency)
    required_inputs.extend([
        {"category": "Company Profile", "name": "Ticker Symbol", "requiresInput": False},
        {"category": "Company Profile", "name": "Company Name", "requiresInput": False},
        {"category": "Company Profile", "name": "Sector & Industry", "requiresInput": False},
        {"category": "Company Profile", "name": "Currency", "requiresInput": False},
    ])
    
    if selected_model == 'dcf':
        # Historical Financials (auto-fetched from yFinance)
        required_inputs.extend([
            {"category": "Historical Financials", "name": "Revenue (3-5 years)", "requiresInput": False},
            {"category": "Historical Financials", "name": "EBITDA (3-5 years)", "requiresInput": False},
            {"category": "Historical Financials", "name": "Net Income (3-5 years)", "requiresInput": False},
            {"category": "Historical Financials", "name": "COGS", "requiresInput": False},
            {"category": "Historical Financials", "name": "SG&A / OpEx", "requiresInput": False},
            {"category": "Historical Financials", "name": "Depreciation & Amortization", "requiresInput": False},
            {"category": "Historical Financials", "name": "CapEx", "requiresInput": False},
            {"category": "Historical Financials", "name": "Working Capital Items (AR, Inventory, AP)", "requiresInput": False},
        ])
        
        # Market Data (auto-fetched)
        required_inputs.extend([
            {"category": "Market Data", "name": "Current Stock Price", "requiresInput": False},
            {"category": "Market Data", "name": "Shares Outstanding", "requiresInput": False},
            {"category": "Market Data", "name": "Total Debt", "requiresInput": False},
            {"category": "Market Data", "name": "Cash & Equivalents", "requiresInput": False},
            {"category": "Market Data", "name": "Beta", "requiresInput": False},
            {"category": "Market Data", "name": "Market Cap", "requiresInput": False},
        ])
        
        # Forecast Drivers (user input required)
        required_inputs.extend([
            {"category": "Forecast Drivers", "name": "Revenue Growth Forecast (5-10 years)", "requiresInput": True},
            {"category": "Forecast Drivers", "name": "Volume vs Price Growth Split", "requiresInput": True},
            {"category": "Forecast Drivers", "name": "Inflation Rate Assumption", "requiresInput": True},
            {"category": "Forecast Drivers", "name": "EBITDA Margin Forecast", "requiresInput": True},
            {"category": "Forecast Drivers", "name": "Tax Rate", "requiresInput": True},
            {"category": "Forecast Drivers", "name": "CapEx as % of Revenue", "requiresInput": True},
            {"category": "Forecast Drivers", "name": "D&A as % of PPE", "requiresInput": True},
            {"category": "Forecast Drivers", "name": "Working Capital Days (AR, Inv, AP)", "requiresInput": True},
        ])
        
        # DCF Model Inputs (user input required)
        required_inputs.extend([
            {"category": "DCF Model Inputs", "name": "Risk-Free Rate", "requiresInput": True},
            {"category": "DCF Model Inputs", "name": "Equity Risk Premium", "requiresInput": True},
            {"category": "DCF Model Inputs", "name": "Beta (or use market beta)", "requiresInput": True},
            {"category": "DCF Model Inputs", "name": "Cost of Debt", "requiresInput": True},
            {"category": "DCF Model Inputs", "name": "WACC (calculated or manual)", "requiresInput": True},
            {"category": "DCF Model Inputs", "name": "Terminal Growth Rate", "requiresInput": True},
            {"category": "DCF Model Inputs", "name": "Terminal EBITDA Multiple", "requiresInput": True},
            {"category": "DCF Model Inputs", "name": "Useful Life of Assets (existing & new)", "requiresInput": True},
        ])
        
        # Peer Comparison Data (optional, auto-fetched or manual)
        required_inputs.extend([
            {"category": "Peer Comparison", "name": "Peer Ticker List", "requiresInput": False},
            {"category": "Peer Comparison", "name": "Peer Multiples (EV/EBITDA, P/E)", "requiresInput": False},
        ])
        
    elif selected_model in ['comparable', 'comps']:
        required_inputs.extend([
            {"category": "Market Data", "name": "Current Price", "requiresInput": False},
            {"category": "Market Data", "name": "Market Capitalization", "requiresInput": False},
            {"category": "Market Data", "name": "Enterprise Value", "requiresInput": False},
            {"category": "Market Data", "name": "EBITDA (TTM)", "requiresInput": False},
            {"category": "Market Data", "name": "Net Income (TTM)", "requiresInput": False},
            {"category": "Peer Selection", "name": "Peer Group Tickers", "requiresInput": True},
            {"category": "Peer Selection", "name": "Selected Multiples (EV/EBITDA, P/E, EV/Sales)", "requiresInput": True},
            {"category": "Peer Selection", "name": "Premium/Discount Justification", "requiresInput": True},
        ])
        
    elif selected_model == 'dupont':
        required_inputs.extend([
            {"category": "Income Statement", "name": "Revenue (TTM)", "requiresInput": False},
            {"category": "Income Statement", "name": "Net Income (TTM)", "requiresInput": False},
            {"category": "Income Statement", "name": "EBIT", "requiresInput": False},
            {"category": "Income Statement", "name": "Interest Expense", "requiresInput": False},
            {"category": "Balance Sheet", "name": "Total Assets", "requiresInput": False},
            {"category": "Balance Sheet", "name": "Total Equity", "requiresInput": False},
            {"category": "Balance Sheet", "name": "Total Liabilities", "requiresInput": False},
            {"category": "Balance Sheet", "name": "Working Capital", "requiresInput": False},
            {"category": "Balance Sheet", "name": "Fixed Assets", "requiresInput": False},
            {"category": "DuPont Analysis", "name": "Net Profit Margin Target", "requiresInput": True},
            {"category": "DuPont Analysis", "name": "Asset Turnover Target", "requiresInput": True},
            {"category": "DuPont Analysis", "name": "Equity Multiplier Target", "requiresInput": True},
        ])
    
    logger.info(f"Prepared {len(required_inputs)} input requirements for model='{selected_model}'")
    
    return PrepareInputsResponse(
        status="ready_to_fetch",
        required_inputs=[InputRequirement(**r) for r in required_inputs],
        message=f"Found {len(required_inputs)} required inputs for your selected model"
    )


@router.post("/step-7-8-fetch-data", response_model=FetchDataResponse)
async def fetch_data(request: SessionFetchRequest):
    """
    Step 7 & 8: Fetch financial data from external sources.
    
    Args:
        request: Session fetch request
        
    Returns:
        Financial data
    """
    from app.main import get_session_store
    
    logger.info(f"Fetching data for session='{request.session_id}'")
    
    sessions = get_session_store()
    session = get_session(request.session_id, sessions)
    
    financial_data = fetch_financial_data(session['ticker'], session['market'])
    session['financial_data'] = financial_data
    
    # Generate peer data and comps results for DCF model
    if session.get('selected_model') == 'DCF':
        try:
            from app.engines.comps_engine import TradingCompsAnalyzer, TargetCompanyData, PeerCompanyData
            
            info = financial_data.get('raw_info', {})
            market_cap = info.get('marketCap', 1000000000) or 1000000000
            enterprise_value = market_cap + (info.get('totalDebt', 0) or 0) - (info.get('cash', 0) or 0)
            revenue_ltm = list(financial_data.get('financials', {}).get('revenue', {}).values())[0] if financial_data.get('financials', {}).get('revenue') else 100000000
            ebitda_ltm = list(financial_data.get('financials', {}).get('ebitda', {}).values())[0] if financial_data.get('financials', {}).get('ebitda') else revenue_ltm * 0.2

            target = TargetCompanyData(
                ticker=session['ticker'],
                company_name=financial_data.get('profile', {}).get('name', session['ticker']),
                market_cap=market_cap,
                enterprise_value=enterprise_value,
                revenue_ltm=revenue_ltm,
                ebitda_ltm=ebitda_ltm,
                ebit_ltm=ebitda_ltm * 0.75,
                net_income_ltm=revenue_ltm * 0.1,
                free_cash_flow_ltm=ebitda_ltm * 0.7,
                book_equity=market_cap * 0.4,
                shares_outstanding=info.get('sharesOutstanding', 1000000) or 1000000,
                share_price=financial_data.get('profile', {}).get('current_price', 100) or 100,
                currency=financial_data.get('profile', {}).get('currency', 'USD')
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
                    ebitda_ltm=ebitda_ltm * variation,
                    ebitda_fy2023=ebitda_ltm * 1.05 * variation,
                    ebitda_fy2024=ebitda_ltm * 1.10 * variation,
                    eps_ltm=(revenue_ltm * 0.1 * variation) / 1000000,
                    eps_fy2023=(revenue_ltm * 0.105 * variation) / 1000000,
                    eps_fy2024=(revenue_ltm * 0.110 * variation) / 1000000,
                    share_price=100 * variation,
                    shares_outstanding=1000000 * variation,
                    industry=industry,
                    sector=sector,
                    selection_reason=f"Same {sector} sector"
                ))

            analyzer = TradingCompsAnalyzer(target, peers)
            outputs = analyzer.run_analysis(apply_outlier_filtering=True)

            logger.info(f"Generated comps analysis with {outputs.peer_count_total} peers")
            
            comps_result = outputs.to_json_schema_format()
            # Extract peer_data from peer_multiples for frontend display
            financial_data['peers'] = comps_result.get('peer_multiples', [])
            financial_data['comps_results'] = comps_result
        except Exception as e:
            logger.warning(f"Failed to generate comps analysis: {e}")
            financial_data['peers'] = []
            financial_data['comps_results'] = {}
    else:
        financial_data['peers'] = []
        financial_data['comps_results'] = {}
    
    session['status'] = "data_fetched"
    
    logger.info(f"Data fetched successfully for session='{request.session_id}'")
    
    return FetchDataResponse(
        status="data_ready",
        data=financial_data,
        message="Financial data retrieved successfully."
    )


@router.post("/step-9-generate-ai", response_model=AIAssumptionsResponse)
async def generate_ai(request: Request):
    """
    Step 9: Generate AI assumptions for valuation.
    
    Args:
        request: Request containing session_id
        
    Returns:
        AI-generated assumptions
    """
    from app.main import get_session_store
    
    data = await request.json()
    session_id = data.get('session_id')
    sessions = get_session_store()
    session = get_session(session_id, sessions)
    
    if not session['financial_data']:
        raise HTTPException(status_code=400, detail="Financial data missing")
    
    ai_results = await generate_ai_assumptions(session['financial_data'], session['selected_model'])
    session['ai_suggestions'] = ai_results
    session['status'] = "ai_generated"
    
    logger.info(f"AI assumptions generated for session='{session_id}'")
    
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
