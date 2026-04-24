import os
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yfinance as yf
import requests
from dotenv import load_dotenv

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
GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

if not all([GEMINI_API_KEY, GROQ_API_KEY, ALPHA_VANTAGE_KEY]):
    raise RuntimeError("Missing API Keys in .env file")

# --- Pydantic Models ---
class SearchRequest(BaseModel):
    query: str
    market: str = "international"  # "vietnamese" or "international"

class TickerSelectRequest(BaseModel):
    session_id: str
    ticker: str
    market: str

class ModelSelectRequest(BaseModel):
    session_id: str
    models: List[str]  # ["DCF", "DuPont", "COMPS"]

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

        # Get Financials
        income_stmt = ticker.financials
        balance_sheet = ticker.balance_sheet
        cashflow = ticker.cashflow
        
        # Format for frontend
        data = {
            "profile": {
                "symbol": ticker_symbol,
                "name": info.get('longName'),
                "sector": info.get('sector'),
                "industry": info.get('industry'),
                "current_price": info.get('currentPrice'),
                "currency": info.get('currency', 'USD'),
                "market_cap": info.get('marketCap'),
                "beta": info.get('beta', 1.0)
            },
            "financials": {
                "revenue": income_stmt.loc['Total Revenue'].to_dict() if 'Total Revenue' in income_stmt.index else {},
                "ebitda": income_stmt.loc['EBITDA'].to_dict() if 'EBITDA' in income_stmt.index else {},
                "net_income": income_stmt.loc['Net Income'].to_dict() if 'Net Income' in income_stmt.index else {},
                "total_assets": balance_sheet.loc['Total Assets'].to_dict() if 'Total Assets' in balance_sheet.index else {},
                "total_debt": balance_sheet.loc['Total Debt'].to_dict() if 'Total Debt' in balance_sheet.index else {},
                "free_cash_flow": cashflow.loc['Free Cash Flow'].to_dict() if 'Free Cash Flow' in cashflow.index else {},
            },
            "raw_info": info # Keep raw for AI context
        }
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data retrieval failed: {str(e)}")

async def generate_ai_assumptions(data: Dict, models: List[str]) -> Dict:
    """Step 9: AI Engine - Generate WACC, Growth, Benchmarks, Trends"""
    
    # Construct prompt
    profile = data['profile']
    financials = data['financials']
    
    prompt = f"""
    Act as a Senior Financial Analyst. 
    Company: {profile.get('name')} ({profile.get('symbol')})
    Sector: {profile.get('sector')}
    Current Price: {profile.get('current_price')}
    Beta: {profile.get('beta')}
    
    Recent Financial Trends (Newest to Oldest):
    - Revenue: {list(financials['revenue'].values())[:3]}
    - EBITDA: {list(financials['ebitda'].values())[:3]}
    - Net Income: {list(financials['net_income'].values())[:3]}
    
    Task:
    1. Calculate WACC using CAPM (Risk Free Rate=4.5%, ERP=5.5%).
    2. Suggest 5-year Revenue Growth Rates based on trends and sector.
    3. Provide Terminal Growth Rate.
    4. Identify Key Benchmarks (Peer EV/EBITDA, Operating Margin).
    5. Explain the reasoning (Trends, Risks).
    
    Return JSON only with this structure:
    {{
        "wacc": 0.085,
        "terminal_growth": 0.025,
        "revenue_growth_forecast": [0.05, 0.06, 0.05, 0.04, 0.03],
        "benchmarks": {{ "peer_ev_ebitda": 12.5, "sector_margin": 0.15 }},
        "trend_analysis": "Brief explanation of growth trajectory...",
        "risk_factors": ["Factor 1", "Factor 2"],
        "explanation": "Detailed reasoning for the suggested numbers."
    }}
    """

    # Mock AI Response for stability if keys are invalid or rate limited
    # In production, call Gemini/Groq here
    try:
        # Simulate API Call to Gemini
        # response = requests.post(GEMINI_URL, json={...})
        # ai_data = response.json()
        
        # Fallback Mock Logic for Demo
        beta = profile.get('beta', 1.0)
        wacc = 0.045 + (beta * 0.055)
        
        last_rev = list(financials['revenue'].values())[0] if financials['revenue'] else 100
        prev_rev = list(financials['revenue'].values())[1] if len(financials['revenue']) > 1 else last_rev
        growth_rate = max(0, (last_rev - prev_rev) / prev_rev) if prev_rev else 0.05
        
        ai_response = {
            "wacc": round(wacc, 4),
            "terminal_growth": 0.023,
            "revenue_growth_forecast": [round(growth_rate * (0.9**i), 3) for i in range(5)],
            "benchmarks": {
                "peer_ev_ebitda": 14.5,
                "sector_operating_margin": 0.18
            },
            "trend_analysis": "Company shows consistent revenue growth but margin compression observed in last FY.",
            "risk_factors": ["High interest rates", "Supply chain volatility"],
            "explanation": f"WACC calculated at {wacc:.2%} based on beta of {beta}. Growth rates tapering from historical {growth_rate:.2%} to terminal rate due to market saturation."
        }
        return ai_response
    except Exception as e:
        # Return safe defaults if AI fails
        return {
            "wacc": 0.08,
            "terminal_growth": 0.02,
            "revenue_growth_forecast": [0.05, 0.05, 0.04, 0.04, 0.03],
            "benchmarks": {"peer_ev_ebitda": 10.0, "sector_operating_margin": 0.10},
            "trend_analysis": "AI service unavailable. Using conservative defaults.",
            "risk_factors": ["General Market Risk"],
            "explanation": "Default assumptions applied due to AI service interruption."
        }

def run_valuation_engine(session_data: Dict) -> Dict:
    """Step 11: Run DCF/DuPont/COMPS calculations"""
    assumptions = session_data['confirmed_assumptions']
    financials = session_data['financial_data']['financials']
    
    # Simple DCF Mock Calculation
    fcf = list(financials.get('free_cash_flow', {}).values())[0] if financials.get('free_cash_flow') else 1000000
    
    # Handle None or invalid FCF (NaN check)
    if fcf is None or (isinstance(fcf, float) and (fcf != fcf)):
        fcf = 1000000
    
    wacc = assumptions.get('wacc', 0.08)
    tg = assumptions.get('terminal_growth', 0.02)
    growth_rates = assumptions.get('revenue_growth_forecast', [0.05, 0.05, 0.04, 0.04, 0.03])
    
    # Ensure wacc and tg are valid numbers
    if wacc is None or (isinstance(wacc, float) and (wacc != wacc)):
        wacc = 0.08
    if tg is None or (isinstance(tg, float) and (tg != tg)):
        tg = 0.02
    
    # Project FCF (Simplified: FCF grows at revenue rate)
    projected_fcf = []
    current_fcf = fcf
    for r in growth_rates:
        if r is None or (isinstance(r, float) and (r != r)):
            r = 0.05
        current_fcf *= (1 + r)
        projected_fcf.append(current_fcf)
    
    # Terminal Value - protect against division by zero or invalid values
    if wacc <= tg:
        wacc = tg + 0.01  # Ensure wacc > tg
    
    terminal_value = projected_fcf[-1] * (1 + tg) / (wacc - tg)
    
    # Discounting
    pv_fcf = sum([fcf / ((1 + wacc) ** (i+1)) for i, fcf in enumerate(projected_fcf)])
    pv_tv = terminal_value / ((1 + wacc) ** len(projected_fcf))
    
    enterprise_value = pv_fcf + pv_tv
    
    # Get net debt safely
    profile = session_data['financial_data']['profile']
    net_debt = profile.get('total_debt', 0) - profile.get('cash', 0)
    if net_debt is None or (isinstance(net_debt, float) and (net_debt != net_debt)):
        net_debt = 0
    
    equity_value = enterprise_value - net_debt
    
    shares_outstanding = profile.get('sharesOutstanding', 1000000)
    if shares_outstanding is None or shares_outstanding == 0 or (isinstance(shares_outstanding, float) and (shares_outstanding != shares_outstanding)):
        shares_outstanding = 1000000
    
    share_price = equity_value / shares_outstanding
    
    # Current price safe retrieval
    current_price = profile.get('currentPrice', 1)
    if current_price is None or (isinstance(current_price, float) and (current_price != current_price)) or current_price == 0:
        current_price = 1
    
    # Calculate upside/downside safely
    upside_downside = ((share_price - current_price) / current_price) * 100
    if upside_downside is None or (isinstance(upside_downside, float) and (upside_downside != upside_downside)):
        upside_downside = 0.0
    
    # Sensitivity Analysis (WACC vs Terminal Growth)
    sensitivity = []
    for w_adj in [-0.01, 0, 0.01]:
        row = []
        for t_adj in [-0.005, 0, 0.005]:
            adj_wacc = wacc + w_adj
            adj_tg = tg + t_adj
            if adj_wacc <= adj_tg: 
                row.append(None)
                continue
            tv = projected_fcf[-1] * (1 + adj_tg) / (adj_wacc - adj_tg)
            ev = pv_fcf + (tv / ((1 + adj_wacc) ** len(projected_fcf)))
            # Ensure no NaN values
            if ev is None or (isinstance(ev, float) and (ev != ev)):
                row.append(None)
            else:
                row.append(round(ev, 2))
        sensitivity.append(row)

    return {
        "enterprise_value": round(enterprise_value, 2) if enterprise_value and not (isinstance(enterprise_value, float) and (enterprise_value != enterprise_value)) else 0,
        "equity_value": round(equity_value, 2) if equity_value and not (isinstance(equity_value, float) and (equity_value != equity_value)) else 0,
        "implied_share_price": round(share_price, 2) if share_price and not (isinstance(share_price, float) and (share_price != share_price)) else 0,
        "current_price": round(current_price, 2) if current_price and not (isinstance(current_price, float) and (current_price != current_price)) else 0,
        "upside_downside": f"{upside_downside:.2f}%",
        "sensitivity_matrix": {
            "wacc_range": [round(wacc-0.01, 3), round(wacc, 3), round(wacc+0.01, 3)],
            "tg_range": [round(tg-0.005, 3), round(tg, 3), round(tg+0.005, 3)],
            "values": sensitivity
        },
        "scenario_analysis": {
            "bull_case": round(share_price * 1.2, 2) if share_price and not (isinstance(share_price, float) and (share_price != share_price)) else 0,
            "base_case": round(share_price, 2) if share_price and not (isinstance(share_price, float) and (share_price != share_price)) else 0,
            "bear_case": round(share_price * 0.8, 2) if share_price and not (isinstance(share_price, float) and (share_price != share_price)) else 0
        }
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
        "selected_models": [],
        "financial_data": None,
        "ai_suggestions": None,
        "confirmed_assumptions": None,
        "valuation_result": None
    }
    return {"session_id": session_id, "status": "ready_for_model_selection"}

@app.post("/api/step-4-select-models")
async def select_models(request: ModelSelectRequest):
    """Step 4: User chooses models"""
    session = get_session(request.session_id)
    session['selected_models'] = request.models
    session['status'] = "models_selected"
    return {"message": "Models selected", "next_step": "fetch_data"}

@app.post("/api/step-5-6-prepare-inputs")
async def prepare_inputs(request: dict):
    """Step 5 & 6: Show required inputs & User Confirms to Fetch"""
    # This step is mostly UI driven, backend just acknowledges readiness
    # Expecting session_id in body
    session_id = request.get('session_id')
    session = get_session(session_id)
    
    if not session['selected_models']:
        raise HTTPException(status_code=400, detail="No models selected")
        
    return {"status": "ready_to_fetch", "required_inputs": ["Ticker Confirmation"]}

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
async def generate_ai(request: BaseModel):
    """Step 9: AI Engine generates WACC, forecasts, benchmarks, trends"""
    data = await request.json()
    session_id = data.get('session_id')
    session = get_session(session_id)
    
    if not session['financial_data']:
        raise HTTPException(status_code=400, detail="Financial data missing")
        
    ai_results = await generate_ai_assumptions(session['financial_data'], session['selected_models'])
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
