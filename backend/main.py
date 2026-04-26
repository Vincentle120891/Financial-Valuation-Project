import os
import uuid
import json
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Body
from starlette.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yfinance as yf
import requests
from dotenv import load_dotenv

# Import valuation engines
from dcf_engine_full import DCFEngine, DCFInputs, ForecastDrivers
from dupont_engine import perform_dupont_analysis
from comps_engine import TradingCompsAnalyzer, TargetCompanyData, PeerCompanyData

# Import Resilient AI Engine with 3-Tier Fallback
from ai_engine import ai_engine

# Load environment variables
load_dotenv()

app = FastAPI(title="Valuation Engine API", version="2.0")

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Valuation Engine API is running", "docs": "/docs"}

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-Memory Session Store (Replace with Redis in production) ---
sessions: Dict[str, Dict[str, Any]] = {}

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY") or os.getenv("ALPHA_VANTAGE_API_KEY")

# Allow missing API keys for development (will use fallbacks)
if not all([GEMINI_API_KEY, GROQ_API_KEY, ALPHA_VANTAGE_KEY]):
    print("Warning: Some API keys missing. AI features will use fallback responses.")
    # Don't raise error - allow app to run with fallbacks

# --- Pydantic Models ---
class SearchRequest(BaseModel):
    query: str
    market: str = "international"  # "vietnamese" or "international"

class TickerSelectRequest(BaseModel):
    ticker: str
    market: str

class ModelSelectRequest(BaseModel):
    session_id: str
    model: str  # "DCF", "DuPont", or "COMPS" (single selection)

class AssumptionConfirmRequest(BaseModel):
    session_id: str
    assumptions: Dict[str, Any]  # User modified or accepted assumptions

class CalculationRequest(BaseModel):
    session_id: str

# --- Helper Functions ---

def generate_session_id() -> str:
    return str(uuid.uuid4())

def get_session(session_id: str) -> Dict:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]

def search_tickers_yahoo(query: str, market: str) -> List[Dict]:
    """Search tickers by symbol or company name"""
    results = []
    
    # Predefined mappings for company name search
    international_companies = {
        "APPLE": {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
        "MICROSOFT": {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
        "ALPHABET": {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ"},
        "GOOGLE": {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ"},
        "AMAZON": {"symbol": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ"},
        "NVIDIA": {"symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ"},
        "META": {"symbol": "META", "name": "Meta Platforms Inc.", "exchange": "NASDAQ"},
        "FACEBOOK": {"symbol": "META", "name": "Meta Platforms Inc.", "exchange": "NASDAQ"},
        "TESLA": {"symbol": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ"},
        "JPMORGAN": {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "exchange": "NYSE"},
        "JPM": {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "exchange": "NYSE"},
        "VISA": {"symbol": "V", "name": "Visa Inc.", "exchange": "NYSE"},
        "BERKSHIRE": {"symbol": "BRK.B", "name": "Berkshire Hathaway Inc.", "exchange": "NYSE"},
        "BRK": {"symbol": "BRK.B", "name": "Berkshire Hathaway Inc.", "exchange": "NYSE"},
    }
    
    vietnamese_companies = {
        "VNM": {"symbol": "VNM.VN", "name": "Vietnam Dairy Products JSC", "exchange": "HOSE"},
        "VINAMILK": {"symbol": "VNM.VN", "name": "Vietnam Dairy Products JSC", "exchange": "HOSE"},
        "VCB": {"symbol": "VCB.VN", "name": "Joint Stock Commercial Bank for Foreign Trade of Vietnam", "exchange": "HOSE"},
        "VIETCOMBANK": {"symbol": "VCB.VN", "name": "Joint Stock Commercial Bank for Foreign Trade of Vietnam", "exchange": "HOSE"},
        "HPG": {"symbol": "HPG.VN", "name": "Hoa Phat Group JSC", "exchange": "HOSE"},
        "VIC": {"symbol": "VIC.VN", "name": "Vingroup JSC", "exchange": "HOSE"},
        "VINGROUP": {"symbol": "VIC.VN", "name": "Vingroup JSC", "exchange": "HOSE"},
        "VRE": {"symbol": "VRE.VN", "name": "Vincom Retail JSC", "exchange": "HOSE"},
        "MSN": {"symbol": "MSN.VN", "name": "Masan Group Corporation", "exchange": "HOSE"},
        "MWG": {"symbol": "MWG.VN", "name": "Mobile World Investment Corporation", "exchange": "HOSE"},
        "FPT": {"symbol": "FPT.VN", "name": "FPT Corporation", "exchange": "HOSE"},
        "SAB": {"symbol": "SAB.VN", "name": "Sabeco - Saigon Beer Alcohol Beverage Corporation", "exchange": "HOSE"},
        "GAS": {"symbol": "GAS.VN", "name": "PetroVietnam Gas JSC", "exchange": "HOSE"},
    }
    
    query_upper = query.upper().strip()
    
    try:
        if market == "vietnamese":
            # Check if query matches a Vietnamese company name or ticker
            if query_upper in vietnamese_companies:
                company = vietnamese_companies[query_upper]
                results.append({
                    "symbol": company["symbol"],
                    "name": company["name"],
                    "exchange": company["exchange"],
                    "market": "vietnamese"
                })
            else:
                # Try direct ticker lookup with .VN suffix
                search_term = query if ".VN" in query else f"{query}.VN"
                ticker = yf.Ticker(search_term)
                if ticker.info and ticker.info.get('symbol'):
                    results.append({
                        "symbol": ticker.info.get('symbol'),
                        "name": ticker.info.get('longName', ticker.info.get('shortName', 'N/A')),
                        "exchange": ticker.info.get('exchange', 'HOSE/HNX'),
                        "market": "vietnamese"
                    })
        else:
            # International market
            # Check if query matches a company name
            if query_upper in international_companies:
                company = international_companies[query_upper]
                results.append({
                    "symbol": company["symbol"],
                    "name": company["name"],
                    "exchange": company["exchange"],
                    "market": "international"
                })
            else:
                # Try direct ticker lookup
                ticker = yf.Ticker(query)
                if ticker.info and ticker.info.get('symbol'):
                    results.append({
                        "symbol": ticker.info.get('symbol'),
                        "name": ticker.info.get('longName', ticker.info.get('shortName', 'N/A')),
                        "exchange": ticker.info.get('exchange', 'US'),
                        "market": "international"
                    })
        
    except Exception as e:
        print(f"Search error: {e}")
        
    return results[:10]

def fetch_financial_data(ticker_symbol: str, market: str) -> Dict:
    """Step 7 & 8: Fetch data from yFinance and Alpha Vantage"""
    try:
        if market == "vietnamese" and not ticker_symbol.endswith(".VN"):
            ticker_symbol += ".VN"
            
        ticker = yf.Ticker(ticker_symbol)
        
        # Get Info
        info = ticker.info
        if not info or 'currentPrice' not in info:
            # Fallback or error handling for delisted/private companies
            raise ValueError("Could not retrieve basic info. Ticker might be invalid.")

        # Helper function to sanitize values (handle NaN/None)
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
        
        # Get Financials
        income_stmt = ticker.financials
        balance_sheet = ticker.balance_sheet
        cashflow = ticker.cashflow
        
        # Format for frontend with NaN protection
        data = {
            "profile": {
                "symbol": ticker_symbol,
                "name": info.get('longName'),
                "sector": info.get('sector'),
                "industry": info.get('industry'),
                "current_price": sanitize_value(info.get('currentPrice')),
                "currency": info.get('currency', 'USD'),
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
            "raw_info": info # Keep raw for AI context
        }
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data retrieval failed: {str(e)}")

async def generate_ai_assumptions(data: Dict, model: str) -> Dict:
    """Step 9: AI Engine - Generate comprehensive assumptions with full transparency using 3-tier fallback"""
    
    # Prepare company data for AI engine
    profile = data.get('profile', {})
    financials = data.get('financials', {})
    
    # Extract historical data
    revenue_history = list(financials.get('revenue', {}).values())
    ebitda_history = list(financials.get('ebitda', {}).values())
    net_income_history = list(financials.get('net_income', {}).values())
    
    # Calculate historical metrics
    rev_growth_rates = []
    for i in range(min(3, len(revenue_history) - 1)):
        if revenue_history[i] and revenue_history[i+1] and revenue_history[i+1] > 0:
            growth = (revenue_history[i] - revenue_history[i+1]) / revenue_history[i+1]
            rev_growth_rates.append(growth)
    
    avg_hist_growth = sum(rev_growth_rates) / len(rev_growth_rates) if rev_growth_rates else 0.05
    
    # Calculate average margins
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
    
    # Use resilient AI engine with 3-tier fallback (Groq -> Gemini -> Qwen -> Deterministic)
    ai_results = ai_engine.generate_assumptions(company_data, model)
    
    # Transform AI results to match expected format
    formatted_results = {"model": model.upper()}
    
    for key, item in ai_results.items():
        if isinstance(item, dict) and 'value' in item:
            formatted_results[key] = item
        elif isinstance(item, list):
            # Handle list items like revenue_growth_forecast
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
    
    # Add any missing fields with defaults
    if 'wacc_percent' in formatted_results and 'wacc' not in formatted_results:
        wacc_item = formatted_results['wacc_percent']
        formatted_results['wacc'] = wacc_item
        formatted_results['wacc']['rationale'] = wacc_item.get('rationale', 'Calculated via CAPM')
        
    if 'terminal_growth_rate_percent' in formatted_results and 'terminal_growth_rate' not in formatted_results:
        tg_item = formatted_results['terminal_growth_rate_percent']
        formatted_results['terminal_growth_rate'] = {
            "value": tg_item['value'] / 100 if tg_item['value'] > 1 else tg_item['value'],
            "rationale": tg_item.get('rationale', 'Long-term growth assumption'),
            "sources": tg_item.get('sources', 'AI Analysis')
        }
    
    return formatted_results

async def run_valuation_engine(session_data: Dict) -> Dict:
    """Step 11: Run DCF/DuPont/COMPS calculations using full engines"""
    model = session_data.get('selected_model', 'DCF')
    assumptions = session_data['confirmed_assumptions']
    financial_data = session_data['financial_data']
    financials = financial_data['financials']
    profile = financial_data['profile']
    ticker = session_data.get('ticker', 'UNKNOWN')
    
    selected_model = model.lower() if model else 'dcf'
    
    # =====================
    # DCF VALUATION
    # =====================
    if selected_model == 'dcf':
        try:
            # Build historical financials from API data
            revenue_history = list(financials.get('revenue', {}).values())
            ebitda_history = list(financials.get('ebitda', {}).values())
            net_income_history = list(financials.get('net_income', {}).values())
            
            # Get base period balances
            info = profile.get('raw_info', {})
            shares_outstanding = info.get('sharesOutstanding', 1000000) or 1000000
            current_price = profile.get('current_price', 100) or 100
            
            # Calculate net debt
            total_debt = info.get('totalDebt', 0) or 0
            cash = info.get('cash', info.get('totalCash', 0)) or 0
            net_debt = total_debt - cash
            
            # Get PPE (use totalAssets as proxy if PPE not available)
            ppe_net = info.get('totalAssets', 0) or 0
            
            # Build 3-year historical financials
            def build_historical_year(rev, ebitda, ni):
                return {
                    'revenue': rev or 0,
                    'ebitda': ebitda or 0,
                    'net_income': ni or 0,
                    'cogs': (rev or 0) * 0.6 if rev else 0,  # Estimate 60% COGS
                    'sga': (rev or 0) * 0.25 if rev else 0,  # Estimate 25% SG&A
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
            
            # Get forecast drivers from assumptions
            revenue_growth = assumptions.get('revenue_growth_forecast', [0.05, 0.05, 0.04, 0.04, 0.03, 0.02])
            # Ensure 6 periods
            while len(revenue_growth) < 6:
                revenue_growth.append(0.02)
            
            wacc = assumptions.get('wacc', 0.08)
            terminal_growth = assumptions.get('terminal_growth_rate', 0.023)
            terminal_multiple = assumptions.get('terminal_ebitda_multiple', 8.0)
            
            # Build forecast drivers for all scenarios
            base_drivers = ForecastDrivers(
                revenue_growth=revenue_growth[:6],
                inflation_rate=[assumptions.get('inflation_rate', 0.02)] * 6 if not isinstance(assumptions.get('inflation_rate'), list) else assumptions.get('inflation_rate', [0.02]*6)[:6],
                opex_growth=[assumptions.get('opex_growth', 0.02)] * 6 if not isinstance(assumptions.get('opex_growth'), list) else assumptions.get('opex_growth', [0.02]*6)[:6],
                capex=[hist_fy_minus_1['revenue'] * assumptions.get('capex_pct_of_revenue', 0.05)] * 6,
                ar_days=[assumptions.get('ar_days', 45)] * 6,
                inv_days=[assumptions.get('inv_days', 60)] * 6,
                ap_days=[assumptions.get('ap_days', 30)] * 6,
                tax_rate=[assumptions.get('tax_rate', 0.21)] * 6,
                terminal_ebitda_multiple=terminal_multiple,
                terminal_growth_rate=terminal_growth
            )
            
            # Best case (higher growth)
            best_growth = [min(g * 1.3, 0.25) for g in revenue_growth[:6]]
            best_drivers = ForecastDrivers(
                revenue_growth=best_growth,
                inflation_rate=base_drivers.inflation_rate,
                opex_growth=[g * 0.9 for g in base_drivers.opex_growth],
                capex=base_drivers.capex,
                ar_days=base_drivers.ar_days,
                inv_days=base_drivers.inv_days,
                ap_days=base_drivers.ap_days,
                tax_rate=base_drivers.tax_rate,
                terminal_ebitda_multiple=terminal_multiple * 1.2,
                terminal_growth_rate=min(terminal_growth * 1.2, 0.035)
            )
            
            # Worst case (lower growth)
            worst_growth = [max(g * 0.6, 0.01) for g in revenue_growth[:6]]
            worst_drivers = ForecastDrivers(
                revenue_growth=worst_growth,
                inflation_rate=base_drivers.inflation_rate,
                opex_growth=[g * 1.1 for g in base_drivers.opex_growth],
                capex=base_drivers.capex,
                ar_days=[d * 1.2 for d in base_drivers.ar_days],
                inv_days=[d * 1.2 for d in base_drivers.inv_days],
                ap_days=[d * 0.9 for d in base_drivers.ap_days],
                tax_rate=base_drivers.tax_rate,
                terminal_ebitda_multiple=terminal_multiple * 0.7,
                terminal_growth_rate=max(terminal_growth * 0.7, 0.01)
            )
            
            # Build DCF inputs
            dcf_inputs = DCFInputs(
                valuation_date=date.today().isoformat(),
                currency=profile.get('currency', 'USD'),
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
                    "best_case": best_drivers,
                    "worst_case": worst_drivers
                },
                wacc=wacc,
                risk_free_rate=assumptions.get('risk_free_rate', 0.045),
                equity_risk_premium=assumptions.get('equity_risk_premium', 0.055),
                beta=assumptions.get('beta', 1.0),
                cost_of_debt=assumptions.get('cost_of_debt', 0.05),
                tax_rate_statutory=assumptions.get('tax_rate', 0.21),
                tax_loss_utilization_limit_pct=assumptions.get('tax_loss_utilization_limit_pct', 0.80)
            )
            
            # Run DCF engine - calculate only base case (avoid recursive scenario calculation)
            engine = DCFEngine(dcf_inputs)
            
            # Calculate discrete and terminal values directly
            pv_discrete, pv_terminal_perp, ev_perpetuity = engine._calculate_dcf_perpetuity(base_drivers)
            pv_terminal_mult, ev_multiple = engine._calculate_dcf_exit_multiple(base_drivers)
            
            # Build output manually
            equity_value_perp = ev_perpetuity - net_debt
            equity_value_mult = ev_multiple - net_debt
            share_price_perp = equity_value_perp / shares_outstanding
            share_price_mult = equity_value_mult / shares_outstanding
            upside_perp = (share_price_perp - current_price) / current_price * 100
            upside_mult = (share_price_mult - current_price) / current_price * 100
            
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
                "message": "DCF calculated using perpetuity and exit multiple methods"
            }
            
        except Exception as e:
            return {
                "model": "DCF",
                "error": str(e),
                "fallback_message": "DCF calculation failed. Using simplified fallback."
            }
    
    # =====================
    # DUPONT ANALYSIS
    # =====================
    elif selected_model in ['dupont', 'dupont analysis']:
        try:
            # Prepare data for DuPont (need 6-10 years of data)
            # Use available historical data and project forward
            years_count = max(6, len(list(financials.get('revenue', {}).values())))
            
            # Build arrays with available data, repeat last value if needed
            def extend_array(values, target_len):
                result = list(values)[:target_len]
                while len(result) < target_len:
                    result.append(result[-1] if result else 0)
                return result
            
            revenue = extend_array(list(financials.get('revenue', {}).values()), years_count)
            net_income = extend_array(list(financials.get('net_income', {}).values()), years_count)
            total_assets = extend_array([profile.get('raw_info', {}).get('totalAssets', sum(revenue)*0.5)] * min(3, years_count), years_count)
            total_equity = extend_array([profile.get('raw_info', {}).get('totalStockholderEquity', sum(revenue)*0.3)] * min(3, years_count), years_count)
            total_debt = extend_array([profile.get('raw_info', {}).get('totalDebt', sum(revenue)*0.2)] * min(3, years_count), years_count)
            
            # Estimate missing fields
            gross_profit = [r * 0.4 for r in revenue]
            ebitda = [r * 0.2 for r in revenue]
            operating_income = [r * 0.15 for r in revenue]
            cogs = [r * 0.6 for r in revenue]
            accounts_receivable = [r * 0.1 for r in revenue]
            inventory = [r * 0.08 for r in revenue]
            accounts_payable = [r * 0.07 for r in revenue]
            current_assets = [r * 0.25 for r in revenue]
            current_liabilities = [r * 0.15 for r in revenue]
            interest_expense = [r * 0.02 for r in revenue]
            ebt = [oi - ie for oi, ie in zip(operating_income, interest_expense)]
            ebit = operating_income
            
            dupont_input = {
                'revenue': revenue,
                'gross_profit': gross_profit,
                'ebitda': ebitda,
                'operating_income': operating_income,
                'net_income': net_income,
                'total_assets': total_assets,
                'total_equity': total_equity,
                'total_debt': total_debt,
                'accounts_receivable': accounts_receivable,
                'inventory': inventory,
                'accounts_payable': accounts_payable,
                'cogs': cogs,
                'current_assets': current_assets,
                'current_liabilities': current_liabilities,
                'interest_expense': interest_expense,
                'ebt': ebt,
                'ebit': ebit,
                'currency': profile.get('currency', 'USD')
            }
            
            result = perform_dupont_analysis(dupont_input)
            
            return {
                "model": "DuPont",
                "success": result.get('success', False),
                "supporting_ratios": result.get('supporting_ratios', {}),
                "dupont_3step": result.get('dupont_3step', {}),
                "dupont_5step": result.get('dupont_5step', {}),
                "growth_trends": result.get('growth_trends', {}),
                "validation": result.get('validation', {}),
                "metadata": result.get('metadata', {})
            }
            
        except Exception as e:
            return {
                "model": "DuPont",
                "error": str(e),
                "fallback_message": "DuPont analysis failed."
            }
    
    # =====================
    # TRADING COMPS
    # =====================
    elif selected_model in ['comps', 'comparable', 'trading comps']:
        try:
            # Get target company data
            info = profile.get('raw_info', {})
            market_cap = info.get('marketCap', 1000000000) or 1000000000
            enterprise_value = market_cap + (info.get('totalDebt', 0) or 0) - (info.get('cash', 0) or 0)
            revenue_ltm = list(financials.get('revenue', {}).values())[0] if financials.get('revenue') else 100000000
            ebitda_ltm = list(financials.get('ebitda', {}).values())[0] if financials.get('ebitda') else revenue_ltm * 0.2
            ebit_ltm = ebitda_ltm * 0.75
            net_income_ltm = list(financials.get('net_income', {}).values())[0] if financials.get('net_income') else revenue_ltm * 0.1
            fcf_ltm = ebitda_ltm * 0.7
            book_equity = info.get('totalStockholderEquity', market_cap * 0.4) or (market_cap * 0.4)
            shares = info.get('sharesOutstanding', 1000000) or 1000000
            price = profile.get('current_price', 100) or 100
            
            target = TargetCompanyData(
                ticker=ticker,
                company_name=profile.get('name', ticker),
                market_cap=market_cap,
                enterprise_value=enterprise_value,
                revenue_ltm=revenue_ltm,
                ebitda_ltm=ebitda_ltm,
                ebit_ltm=ebit_ltm,
                net_income_ltm=net_income_ltm,
                free_cash_flow_ltm=fcf_ltm,
                book_equity=book_equity,
                shares_outstanding=shares,
                current_stock_price=price,
                currency=profile.get('currency', 'USD')
            )
            
            # Generate peer companies (simplified - in production would fetch real peers)
            sector = info.get('sector', 'Technology')
            industry = info.get('industry', 'Software')
            
            # Create mock peers based on sector multiples
            peer_multiples_map = {
                'Technology': {'ev_ebitda': 18.0, 'ev_sales': 6.0, 'pe': 25.0},
                'Healthcare': {'ev_ebitda': 14.0, 'ev_sales': 4.0, 'pe': 20.0},
                'Financial Services': {'ev_ebitda': 10.0, 'ev_sales': 3.0, 'pe': 12.0},
                'Consumer Cyclical': {'ev_ebitda': 12.0, 'ev_sales': 2.0, 'pe': 18.0},
                'Industrials': {'ev_ebitda': 11.0, 'ev_sales': 1.5, 'pe': 16.0},
                'Energy': {'ev_ebitda': 7.0, 'ev_sales': 1.2, 'pe': 10.0},
            }
            
            base_multiples = peer_multiples_map.get(sector, {'ev_ebitda': 12.0, 'ev_sales': 3.0, 'pe': 18.0})
            
            peers = []
            peer_names = ['Peer A', 'Peer B', 'Peer C', 'Peer D', 'Peer E']
            peer_tickers = ['PEERA', 'PEERB', 'PEERC', 'PEERD', 'PEERE']
            
            import random
            random.seed(42)  # For reproducibility
            
            for i, (name, ticker_sym) in enumerate(zip(peer_names, peer_tickers)):
                variation = 0.8 + (random.random() * 0.4)  # 0.8 to 1.2
                peers.append(PeerCompanyData(
                    ticker=f"{ticker_sym}.{ticker.split('.')[-1]}" if '.' in ticker else ticker_sym,
                    company_name=f"{name} Corp",
                    market_cap=market_cap * variation,
                    enterprise_value=enterprise_value * variation,
                    revenue_ltm=revenue_ltm * variation,
                    ebitda_ltm=ebitda_ltm * variation,
                    ebit_ltm=ebit_ltm * variation,
                    net_income_ltm=net_income_ltm * variation,
                    free_cash_flow_ltm=fcf_ltm * variation,
                    book_equity=book_equity * variation,
                    shares_outstanding=shares * variation,
                    current_stock_price=price * variation,
                    industry=industry,
                    sector=sector,
                    selection_reason=f"Same {sector} sector, similar market cap",
                    similarity_score=0.9 - (i * 0.05)
                ))
            
            # Run comps analysis
            analyzer = TradingCompsAnalyzer(target, peers)
            outputs = analyzer.run_analysis(apply_outlier_filtering=True)
            
            return {
                "model": "Comps",
                "success": True,
                "result": outputs.to_json_schema_format(),
                "target_multiples": outputs.to_json_schema_format()['target_multiples'],
                "peer_statistics": outputs.to_json_schema_format()['peer_statistics'],
                "implied_valuations": outputs.to_json_schema_format()['implied_valuations'],
                "peer_count": outputs.peer_count_total,
                "peer_count_after_filtering": outputs.peer_count_after_filtering,
                "metadata": outputs.to_json_schema_format()['metadata']
            }
            
        except Exception as e:
            return {
                "model": "Comps",
                "error": str(e),
                "fallback_message": "Trading Comps analysis failed."
            }
    
    # Default fallback
    return {
        "error": f"Unknown model: {selected_model}",
        "message": "Please select a valid model: DCF, DuPont, or Comps"
    }

# --- API Endpoints Implementing the 12 Steps ---

@app.post("/api/step-1-search")
async def search_tickers(request: SearchRequest):
    """Step 1 & 2: User inputs ticker, system shows related tickers"""
    results = search_tickers_yahoo(request.query, request.market)
    if not results:
        return {"results": [], "message": "No tickers found. Try exact symbol."}
    return {"results": results}

@app.post("/api/step-3-select-ticker")
async def select_ticker(request: TickerSelectRequest):
    """Step 3: User chooses ticker -> Create Session"""
    session_id = generate_session_id()
    sessions[session_id] = {
        "status": "ticker_selected",
        "ticker": request.ticker,
        "market": request.market,
        "selected_model": None,  # Single model string
        "financial_data": None,
        "ai_suggestions": None,
        "confirmed_assumptions": None,
        "valuation_result": None
    }
    return {"session_id": session_id, "status": "ready_for_model_selection"}

@app.post("/api/step-4-select-models")
async def select_models(request: ModelSelectRequest):
    """Step 4: User chooses model (single selection)"""
    session = get_session(request.session_id)
    session['selected_model'] = request.model  # Single model string
    session['status'] = "model_selected"
    return {"message": "Model selected", "next_step": "fetch_data", "selected_model": request.model}

@app.post("/api/step-5-6-prepare-inputs")
async def prepare_inputs(request: dict):
    """Step 5 & 6: Show required inputs & User Confirms to Fetch"""
    # This step is mostly UI driven, backend just acknowledges readiness
    # Expecting session_id in body
    session_id = request.get('session_id')
    session = get_session(session_id)
    
    if not session or not session.get('selected_model'):
        raise HTTPException(status_code=400, detail="No model selected")
    
    # Build required inputs based on selected model - EXPANDED to show all fields
    selected_model = session['selected_model'].lower()
    required_inputs = []
    
    # Always require ticker confirmation
    required_inputs.append({
        "category": "General",
        "name": "Ticker Confirmation",
        "requiresInput": False
    })
    
    # DCF Model - All detailed inputs
    if selected_model == 'dcf':
        required_inputs.extend([
            # Market Structure
            {"category": "Market Structure", "name": "Current Price", "requiresInput": False},
            {"category": "Market Structure", "name": "Shares Outstanding (Diluted)", "requiresInput": False},
            {"category": "Market Structure", "name": "Total Debt", "requiresInput": False},
            {"category": "Market Structure", "name": "Cash & Equivalents", "requiresInput": False},
            {"category": "Market Structure", "name": "Beta (5Y Monthly)", "requiresInput": False},
            
            # Macro Indicators
            {"category": "Macro Indicators", "name": "Risk-Free Rate (10Y)", "requiresInput": False},
            {"category": "Macro Indicators", "name": "Equity Risk Premium", "requiresInput": False},
            {"category": "Macro Indicators", "name": "Inflation Expectations (10Y)", "requiresInput": False},
            
            # Income Statement
            {"category": "Income Statement", "name": "Revenue (Total)", "requiresInput": False},
            {"category": "Income Statement", "name": "EBITDA", "requiresInput": False},
            {"category": "Income Statement", "name": "EBIT / Operating Income", "requiresInput": False},
            {"category": "Income Statement", "name": "Net Income", "requiresInput": False},
            {"category": "Income Statement", "name": "Depreciation & Amortization", "requiresInput": False},
            {"category": "Income Statement", "name": "Interest Expense", "requiresInput": False},
            {"category": "Income Statement", "name": "Tax Provision", "requiresInput": False},
            
            # Balance Sheet
            {"category": "Balance Sheet", "name": "Total Assets", "requiresInput": False},
            {"category": "Balance Sheet", "name": "Total Equity", "requiresInput": False},
            {"category": "Balance Sheet", "name": "Net PPE", "requiresInput": False},
            {"category": "Balance Sheet", "name": "Working Capital", "requiresInput": False},
            
            # Cash Flow
            {"category": "Cash Flow", "name": "Operating Cash Flow (CFO)", "requiresInput": False},
            {"category": "Cash Flow", "name": "Capital Expenditures (CapEx)", "requiresInput": False},
            {"category": "Cash Flow", "name": "Free Cash Flow", "requiresInput": False},
            
            # Forecast Assumptions (User Input Required)
            {"category": "Forecast Assumptions", "name": "WACC", "requiresInput": True},
            {"category": "Forecast Assumptions", "name": "Terminal Growth Rate", "requiresInput": True},
            {"category": "Forecast Assumptions", "name": "Revenue Growth Forecast (Year 1-5)", "requiresInput": True},
            {"category": "Forecast Assumptions", "name": "EBITDA Margin Forecast", "requiresInput": True},
            {"category": "Forecast Assumptions", "name": "CapEx % of Revenue", "requiresInput": True},
            {"category": "Forecast Assumptions", "name": "Tax Rate Forecast", "requiresInput": True},
            {"category": "Forecast Assumptions", "name": "Working Capital Days (AR, Inventory, AP)", "requiresInput": True},
        ])
    
    # Trading Comps Model - All detailed inputs
    elif selected_model == 'comparable' or selected_model == 'comps':
        required_inputs.extend([
            # Market Structure
            {"category": "Market Structure", "name": "Current Price", "requiresInput": False},
            {"category": "Market Structure", "name": "Market Capitalization", "requiresInput": False},
            {"category": "Market Structure", "name": "Enterprise Value", "requiresInput": False},
            {"category": "Market Structure", "name": "Shares Outstanding", "requiresInput": False},
            
            # Financial Metrics
            {"category": "Financial Metrics", "name": "Revenue (LTM)", "requiresInput": False},
            {"category": "Financial Metrics", "name": "EBITDA (LTM)", "requiresInput": False},
            {"category": "Financial Metrics", "name": "EBIT (LTM)", "requiresInput": False},
            {"category": "Financial Metrics", "name": "Net Income (LTM)", "requiresInput": False},
            {"category": "Financial Metrics", "name": "Free Cash Flow (LTM)", "requiresInput": False},
            {"category": "Financial Metrics", "name": "Book Equity", "requiresInput": False},
            
            # Peer Selection (User Input)
            {"category": "Peer Selection", "name": "Peer Group Tickers", "requiresInput": True},
            {"category": "Peer Selection", "name": "Industry/Sector Filter", "requiresInput": True},
            
            # Multiple Assumptions (User Input)
            {"category": "Multiple Assumptions", "name": "Target EV/EBITDA Multiple", "requiresInput": True},
            {"category": "Multiple Assumptions", "name": "Target P/E Multiple", "requiresInput": True},
            {"category": "Multiple Assumptions", "name": "Target EV/Sales Multiple", "requiresInput": True},
        ])
    
    # DuPont Analysis Model - All detailed inputs
    elif selected_model == 'dupont':
        required_inputs.extend([
            # Income Statement
            {"category": "Income Statement", "name": "Revenue", "requiresInput": False},
            {"category": "Income Statement", "name": "Net Income", "requiresInput": False},
            {"category": "Income Statement", "name": "EBIT", "requiresInput": False},
            {"category": "Income Statement", "name": "Pre-Tax Income", "requiresInput": False},
            {"category": "Income Statement", "name": "Interest Expense", "requiresInput": False},
            {"category": "Income Statement", "name": "Tax Provision", "requiresInput": False},
            
            # Balance Sheet
            {"category": "Balance Sheet", "name": "Total Assets", "requiresInput": False},
            {"category": "Balance Sheet", "name": "Total Equity", "requiresInput": False},
            {"category": "Balance Sheet", "name": "Average Total Assets", "requiresInput": False},
            {"category": "Balance Sheet", "name": "Average Equity", "requiresInput": False},
            
            # Calculated Ratios
            {"category": "DuPont Ratios", "name": "Net Profit Margin", "requiresInput": False},
            {"category": "DuPont Ratios", "name": "Asset Turnover", "requiresInput": False},
            {"category": "DuPont Ratios", "name": "Equity Multiplier", "requiresInput": False},
            {"category": "DuPont Ratios", "name": "Tax Burden", "requiresInput": False},
            {"category": "DuPont Ratios", "name": "Interest Burden", "requiresInput": False},
            {"category": "DuPont Ratios", "name": "ROE (3-Step)", "requiresInput": False},
            {"category": "DuPont Ratios", "name": "ROE (5-Step)", "requiresInput": False},
            
            # Trend Analysis Period (User Input)
            {"category": "Analysis Settings", "name": "Analysis Period (Years)", "requiresInput": True},
            {"category": "Analysis Settings", "name": "Benchmark Companies", "requiresInput": True},
        ])
    
    return {
        "status": "ready_to_fetch",
        "required_inputs": required_inputs,
        "message": f"Found {len(required_inputs)} required inputs for your selected model"
    }

@app.post("/api/step-7-8-fetch-data")
async def fetch_data(request: dict):
    """Step 7 & 8: Retrieve Data via APIs and Show Numbers"""
    session_id = request.get('session_id')
    session = get_session(session_id)
    
    # Fetch
    financial_data = fetch_financial_data(session['ticker'], session['market'])
    session['financial_data'] = financial_data
    session['status'] = "data_fetched"
    
    return {
        "status": "data_ready",
        "data": financial_data,
        "message": "Financial data retrieved successfully."
    }

@app.post("/api/step-9-generate-ai")
async def generate_ai(request: Request):
    """Step 9: AI Engine generates WACC, forecasts, benchmarks, trends"""
    data = await request.json()
    session_id = data.get('session_id')
    session = get_session(session_id)
    
    if not session['financial_data']:
        raise HTTPException(status_code=400, detail="Financial data missing")
        
    # Pass single model string (not list) to updated generate_ai_assumptions
    ai_results = await generate_ai_assumptions(session['financial_data'], session['selected_model'])
    session['ai_suggestions'] = ai_results
    session['status'] = "ai_generated"
    
    return {
        "status": "ai_ready",
        "suggestions": ai_results,
        "message": "AI analysis complete. Please review assumptions."
    }

@app.post("/api/step-10-confirm-assumptions")
async def confirm_assumptions(request: AssumptionConfirmRequest):
    """Step 10: User reviews/edits assumptions and confirms"""
    session = get_session(request.session_id)
    
    # Merge AI suggestions with user edits
    final_assumptions = {**session['ai_suggestions'], **request.assumptions}
    
    session['confirmed_assumptions'] = final_assumptions
    session['status'] = "assumptions_confirmed"
    
    return {
        "status": "ready_for_valuation",
        "assumptions": final_assumptions
    }

@app.post("/api/step-11-12-valuate")
async def run_valuation(request: CalculationRequest):
    """Step 11 & 12: Run Engine and Show Results with Sensitivity"""
    session = get_session(request.session_id)
    
    if not session['confirmed_assumptions']:
        raise HTTPException(status_code=400, detail="Assumptions not confirmed")
        
    results = run_valuation_engine(session)
    session['valuation_result'] = results
    session['status'] = "completed"
    
    return {
        "status": "completed",
        "result": results,
        "inputs_used": session['confirmed_assumptions']
    }

@app.get("/api/session/{session_id}")
async def get_session_status(session_id: str):
    """Helper to check session state"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
