#!/usr/bin/env python3
"""
Python Backend for Financial Valuation Application
Migrated from Node.js/Express to Python/FastAPI
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Import financial data modules
from yfinance_data import fetch_yfinance_data
from dcf_engine import run_complete_dcf as calculate_dcf_valuation
from dupont_engine import perform_dupont_analysis as calculate_dupont_analysis

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# AI SDK imports
try:
    from google import genai
    from google.genai import types
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    GOOGLE_AI_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Environment variables
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY', 'demo')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
PORT = int(os.getenv('PORT', 8000))

# AI Model configuration from environment
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-lite')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'qwen/qwen3-32b')

# Set Groq as primary since Gemini key has quota issues
AI_CONFIG = {
    'primary': 'groq',  # Changed to groq as default due to Gemini quota limits
    'fallback': 'gemini',
    'gemini_model': GEMINI_MODEL,
    'groq_model': GROQ_MODEL,
    'max_retries': 2,
    'timeout_ms': 30000,
    'confidence_threshold': 0.7
}

# Initialize AI clients (needed for health check and fallback)
gemini_client = None
groq_client = None

if GROQ_AVAILABLE and GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
    except Exception:
        pass

if GOOGLE_AI_AVAILABLE and GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        pass

# In-memory state storage (in production, use a database)
valuation_state = {}

MOCK_TICKER_SEARCH = {
    'AAPL': {'ticker': 'AAPL', 'name': 'Apple Inc.', 'exchange': 'NASDAQ'},
    'TSLA': {'ticker': 'TSLA', 'name': 'Tesla, Inc.', 'exchange': 'NASDAQ'},
    'MSFT': {'ticker': 'MSFT', 'name': 'Microsoft Corporation', 'exchange': 'NASDAQ'},
    'GOOGL': {'ticker': 'GOOGL', 'name': 'Alphabet Inc.', 'exchange': 'NASDAQ'},
    'AMZN': {'ticker': 'AMZN', 'name': 'Amazon.com, Inc.', 'exchange': 'NASDAQ'}
}

VALUATION_MODELS = [
    {'id': 'DCF', 'name': 'Discounted Cash Flow', 'description': 'Intrinsic value based on projected free cash flows'},
    {'id': 'COMPS', 'name': 'Trading Comps', 'description': 'Relative valuation using peer company multiples'},
    {'id': 'DUPONT', 'name': 'DuPont Analysis', 'description': 'ROE decomposition into profit margin, asset turnover, and leverage'},
    {'id': 'REALESTATE', 'name': 'Real Estate', 'description': 'Property valuation using NOI and cap rates'}
]


# Pydantic models for request/response validation
class CompanySelect(BaseModel):
    ticker: str
    companyName: str
    exchange: str


class ModelSelect(BaseModel):
    modelType: str


class DataRetrieve(BaseModel):
    modelType: str
    ticker: str


class ConfirmValues(BaseModel):
    confirmedValues: Dict[str, Any]
    auditLog: List[Dict[str, Any]]


class ScenarioSelect(BaseModel):
    scenarioType: str
    customOverrides: Optional[Dict[str, Any]] = None


class ValuationRun(BaseModel):
    modelType: str
    confirmedValues: Dict[str, Any]
    scenario: Dict[str, Any]


class ManualInputSave(BaseModel):
    ticker: str
    model: str
    inputs: Dict[str, Any]


class ValidateManualInput(BaseModel):
    ticker: str
    field: str
    value: Any


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    # Startup
    print(f"Starting Financial Valuation API on port {PORT}")
    yield
    # Shutdown
    print("Shutting down Financial Valuation API")


app = FastAPI(
    title="Financial Valuation API",
    description="Backend API for financial valuation flow with Yahoo Finance integration",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# API INTEGRATION FUNCTIONS
# ============================================

async def fetch_from_alpha_vantage(function_name: str, params: Dict = None) -> Dict:
    """Fetch data from Alpha Vantage API"""
    import aiohttp
    
    base_url = 'https://www.alphavantage.co/query'
    url_params = {
        'function': function_name,
        'apikey': ALPHA_VANTAGE_KEY
    }
    if params:
        url_params.update(params)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=url_params) as response:
                data = await response.json()
                return {'success': True, 'data': data}
    except Exception as e:
        return {'success': False, 'error': str(e)}


async def fetch_comprehensive_financial_data(ticker: str) -> Dict:
    """Get comprehensive financial data for a ticker"""
    timestamp = datetime.now().isoformat()
    
    # Fetch from yfinance
    yahoo_result = fetch_yfinance_data(ticker)
    
    # Fetch from Alpha Vantage in parallel
    tasks = [
        fetch_from_alpha_vantage('INCOME_STATEMENT', {'symbol': ticker}),
        fetch_from_alpha_vantage('BALANCE_SHEET', {'symbol': ticker}),
        fetch_from_alpha_vantage('CASH_FLOW', {'symbol': ticker}),
        fetch_from_alpha_vantage('OVERVIEW', {'symbol': ticker})
    ]
    
    income_statement, balance_sheet, cash_flow, overview = await asyncio.gather(*tasks)
    
    # Build unified data structure
    if yahoo_result.get('success'):
        financial_data = yahoo_result.get('data', {})
        financial_data['metadata']['data_timestamp'] = timestamp
        return {
            'success': True,
            'data': financial_data,
            'sources': ['yfinance', 'alphavantage']
        }
    else:
        return {
            'success': False,
            'error': yahoo_result.get('error', 'Failed to fetch data'),
            'sources': []
        }


async def generate_ai_suggestion(field: str, context: Dict = None) -> Dict:
    """Generate AI suggestion for a field using Gemini or Groq"""
    prompt = f"Provide a reasonable estimate for {field} in financial valuation context."
    if context:
        prompt += f" Context: {json.dumps(context)}"
    
    # Try primary model (Gemini)
    if gemini_client and AI_CONFIG['primary'] == 'gemini':
        try:
            response = gemini_client.models.generate_content(
                model=AI_CONFIG['gemini_model'],
                contents=prompt
            )
            # Handle different response formats
            if hasattr(response, 'text'):
                return {'success': True, 'suggestion': response.text, 'source': 'gemini'}
            elif hasattr(response, 'candidates') and response.candidates:
                content = response.candidates[0].content.parts[0].text
                return {'success': True, 'suggestion': content, 'source': 'gemini'}
            else:
                return {'success': False, 'error': 'Unexpected response format', 'source': 'gemini'}
        except Exception as e:
            pass
    
    # Fallback to Groq
    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model=AI_CONFIG['groq_model'],
                messages=[{'role': 'user', 'content': prompt}]
            )
            return {'success': True, 'suggestion': response.choices[0].message.content, 'source': 'groq'}
        except Exception:
            pass
    
    return {'success': False, 'error': 'AI service unavailable', 'source': None}


# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Root endpoint - API health check"""
    return {
        'message': 'Financial Valuation API v2.0 (Python/FastAPI)',
        'status': 'running',
        'timestamp': datetime.now().isoformat()
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'yfinance': 'available',
            'gemini_ai': 'available' if gemini_client else 'unavailable',
            'groq_ai': 'available' if groq_client else 'unavailable'
        }
    }


@app.get("/api/search")
async def search_tickers(q: str):
    """Search for tickers/companies"""
    query = q.upper()
    
    # Search in mock data
    results = []
    for ticker, info in MOCK_TICKER_SEARCH.items():
        if query in ticker or query in info['name'].upper():
            results.append(info)
    
    # If no exact matches, return partial matches
    if not results:
        for ticker, info in MOCK_TICKER_SEARCH.items():
            if query in ticker[:2] or query in info['name'].upper()[:2]:
                results.append(info)
    
    return {
        'success': True,
        'results': results if results else [{'ticker': query, 'name': f'{query} Inc.', 'exchange': 'UNKNOWN'}],
        'query': q
    }


@app.post("/api/select-company")
async def select_company(company: CompanySelect):
    """Select a company for analysis"""
    global valuation_state
    
    ticker = company.ticker.upper()
    valuation_state['selected_company'] = {
        'ticker': ticker,
        'company_name': company.companyName,
        'exchange': company.exchange,
        'selected_at': datetime.now().isoformat()
    }
    
    return {
        'success': True,
        'message': f'Selected {company.companyName} ({ticker})',
        'company': valuation_state['selected_company']
    }


@app.get("/api/models")
async def get_models():
    """Get available valuation models"""
    return {
        'success': True,
        'models': VALUATION_MODELS
    }


@app.post("/api/select-model")
async def select_model(model: ModelSelect):
    """Select a valuation model"""
    global valuation_state
    
    model_type = model.modelType.upper()
    valuation_state['selected_model'] = {
        'type': model_type,
        'selected_at': datetime.now().isoformat()
    }
    
    return {
        'success': True,
        'message': f'Selected {model_type} model',
        'model': valuation_state['selected_model']
    }


@app.get("/api/required-fields")
async def get_required_fields(model: str = None):
    """Get required input fields for a model"""
    model_type = model.upper() if model else 'DCF'
    
    # Define required fields per model
    field_definitions = {
        'DCF': [
            {'name': 'revenue_current', 'category': 'Historical Data', 'requiresInput': True},
            {'name': 'operating_margin', 'category': 'Historical Data', 'requiresInput': True},
            {'name': 'tax_rate', 'category': 'Forecast Assumptions', 'requiresInput': True},
            {'name': 'terminal_growth_rate', 'category': 'Forecast Assumptions', 'requiresInput': True},
            {'name': 'wacc', 'category': 'Discount Rate', 'requiresInput': True},
            {'name': 'forecast_revenue_growth_y1', 'category': 'Forecast Assumptions', 'requiresInput': True},
            {'name': 'forecast_revenue_growth_y2', 'category': 'Forecast Assumptions', 'requiresInput': True},
            {'name': 'forecast_revenue_growth_y3', 'category': 'Forecast Assumptions', 'requiresInput': True},
            {'name': 'forecast_revenue_growth_y4', 'category': 'Forecast Assumptions', 'requiresInput': True},
            {'name': 'forecast_revenue_growth_y5', 'category': 'Forecast Assumptions', 'requiresInput': True},
            {'name': 'forecast_capex_percent', 'category': 'Forecast Assumptions', 'requiresInput': True},
            {'name': 'forecast_depreciation_percent', 'category': 'Forecast Assumptions', 'requiresInput': True},
            {'name': 'forecast_wc_change_percent', 'category': 'Forecast Assumptions', 'requiresInput': True}
        ],
        'DUPONT': [
            {'name': 'net_income', 'category': 'Income Statement', 'requiresInput': True},
            {'name': 'revenue', 'category': 'Income Statement', 'requiresInput': True},
            {'name': 'total_assets', 'category': 'Balance Sheet', 'requiresInput': True},
            {'name': 'total_equity', 'category': 'Balance Sheet', 'requiresInput': True},
            {'name': 'ebit_operating_income', 'category': 'Income Statement', 'requiresInput': True},
            {'name': 'pre_tax_income_ebt', 'category': 'Income Statement', 'requiresInput': True}
        ],
        'COMPS': [
            {'name': 'peer_ev_ebitda_median', 'category': 'Peer Analysis', 'requiresInput': True},
            {'name': 'peer_pb_median', 'category': 'Peer Analysis', 'requiresInput': True},
            {'name': 'subject_ebitda', 'category': 'Subject Company', 'requiresInput': True},
            {'name': 'subject_net_income', 'category': 'Subject Company', 'requiresInput': True},
            {'name': 'subject_equity', 'category': 'Subject Company', 'requiresInput': True}
        ],
        'REALESTATE': [
            {'name': 'noi', 'category': 'Property Income', 'requiresInput': True},
            {'name': 'cap_rate', 'category': 'Market Data', 'requiresInput': True}
        ]
    }
    
    fields = field_definitions.get(model_type, field_definitions['DCF'])
    
    return {
        'success': True,
        'model': model_type,
        'fields': fields
    }


@app.post("/api/retrieve-data")
async def retrieve_data(data_request: DataRetrieve):
    """Retrieve financial data for a ticker"""
    model_type = data_request.modelType.upper()
    ticker = data_request.ticker.upper()
    
    # Fetch comprehensive data
    financial_data = await fetch_comprehensive_financial_data(ticker)
    
    if financial_data.get('success'):
        # Store in state
        valuation_state[f'data_{ticker}'] = financial_data['data']
        
        return {
            'success': True,
            'message': f'Data retrieved for {ticker}',
            'data': financial_data['data'],
            'sources': financial_data.get('sources', [])
        }
    else:
        return {
            'success': False,
            'error': financial_data.get('error', 'Failed to retrieve data'),
            'sources': financial_data.get('sources', [])
        }


@app.get("/api/financial-data/{ticker}")
async def get_financial_data(ticker: str):
    """Get financial data for a specific ticker"""
    ticker = ticker.upper()
    
    financial_data = await fetch_comprehensive_financial_data(ticker)
    
    return financial_data


@app.get("/api/ai-inputs/{ticker}")
async def get_ai_inputs(ticker: str):
    """Get AI-suggested inputs for a ticker"""
    ticker = ticker.upper()
    
    # Fetch data first
    financial_data = await fetch_comprehensive_financial_data(ticker)
    
    if not financial_data.get('success'):
        return {'success': False, 'error': 'Failed to fetch data'}
    
    # Generate AI suggestions for key inputs
    data = financial_data.get('data', {})
    market_structure = data.get('market_structure', {})
    income_stmt = data.get('income_statement_raw', {})
    
    suggestions = {
        'wacc': {
            'suggested_value': 0.08 + market_structure.get('beta_5y_monthly', 1.0) * 0.055,
            'source': 'CAPM calculation',
            'confidence': 0.8
        },
        'terminal_growth_rate': {
            'suggested_value': 0.023,  # Long-term inflation expectation
            'source': 'Macro economic data',
            'confidence': 0.7
        },
        'tax_rate': {
            'suggested_value': abs(income_stmt.get('tax_provision', 0)) / abs(income_stmt.get('pre_tax_income_ebt', 1)) if income_stmt.get('pre_tax_income_ebt', 0) != 0 else 0.21,
            'source': 'Historical effective tax rate',
            'confidence': 0.85
        }
    }
    
    return {
        'success': True,
        'ticker': ticker,
        'suggestions': suggestions
    }


@app.get("/api/ai-suggestions")
async def get_ai_suggestions(field: str, ticker: str = None):
    """Get AI suggestions for a specific field"""
    context = {}
    if ticker:
        ticker = ticker.upper()
        if f'data_{ticker}' in valuation_state:
            context = valuation_state[f'data_{ticker}']
    
    suggestion = await generate_ai_suggestion(field, context if context else None)
    
    return suggestion


@app.post("/api/validate-manual-input")
async def validate_manual_input(validation: ValidateManualInput):
    """Validate a manual input value"""
    ticker = validation.ticker.upper()
    field = validation.field
    value = validation.value
    
    # Basic validation rules
    validation_rules = {
        'wacc': {'min': 0.03, 'max': 0.25, 'type': float},
        'terminal_growth_rate': {'min': -0.02, 'max': 0.05, 'type': float},
        'tax_rate': {'min': 0.0, 'max': 0.50, 'type': float},
        'revenue_current': {'min': 0, 'type': (int, float)},
        'operating_margin': {'min': -0.5, 'max': 1.0, 'type': float}
    }
    
    if field in validation_rules:
        rule = validation_rules[field]
        
        # Type check
        if not isinstance(value, rule['type']):
            return {
                'valid': False,
                'error': f'Invalid type. Expected {rule["type"].__name__}'
            }
        
        # Range check
        if 'min' in rule and value < rule['min']:
            return {
                'valid': False,
                'error': f'Value below minimum ({rule["min"]})'
            }
        if 'max' in rule and value > rule['max']:
            return {
                'valid': False,
                'error': f'Value above maximum ({rule["max"]})'
            }
    
    return {
        'valid': True,
        'message': f'{field} value is valid'
    }


@app.post("/api/save-manual-inputs")
async def save_manual_inputs(inputs: ManualInputSave):
    """Save manual inputs for a ticker/model combination"""
    global valuation_state
    
    ticker = inputs.ticker.upper()
    model = inputs.model.upper()
    
    key = f'manual_inputs_{ticker}_{model}'
    valuation_state[key] = {
        'inputs': inputs.inputs,
        'saved_at': datetime.now().isoformat()
    }
    
    return {
        'success': True,
        'message': f'Manual inputs saved for {ticker} ({model})',
        'key': key
    }


@app.get("/api/manual-inputs/{ticker}")
async def get_manual_inputs(ticker: str, model: str = None):
    """Get saved manual inputs for a ticker"""
    ticker = ticker.upper()
    model = model.upper() if model else 'DCF'
    
    key = f'manual_inputs_{ticker}_{model}'
    
    if key in valuation_state:
        return {
            'success': True,
            'ticker': ticker,
            'model': model,
            'inputs': valuation_state[key]['inputs']
        }
    else:
        return {
            'success': True,
            'ticker': ticker,
            'model': model,
            'inputs': {}
        }


@app.post("/api/confirm-values")
async def confirm_values(confirm: ConfirmValues):
    """Confirm input values for valuation"""
    global valuation_state
    
    valuation_state['confirmed_values'] = {
        'values': confirm.confirmedValues,
        'audit_log': confirm.auditLog,
        'confirmed_at': datetime.now().isoformat()
    }
    
    return {
        'success': True,
        'message': 'Values confirmed',
        'confirmed_count': len(confirm.confirmedValues)
    }


@app.get("/api/scenarios")
async def get_scenarios():
    """Get available scenario templates"""
    scenarios = [
        {
            'id': 'BASE',
            'name': 'Base Case',
            'description': 'Most likely scenario based on current trends',
            'overrides': {}
        },
        {
            'id': 'BULL',
            'name': 'Bull Case',
            'description': 'Optimistic scenario with higher growth',
            'overrides': {
                'revenue_growth_adjustment': 0.03,
                'margin_expansion': 0.02
            }
        },
        {
            'id': 'BEAR',
            'name': 'Bear Case',
            'description': 'Pessimistic scenario with lower growth',
            'overrides': {
                'revenue_growth_adjustment': -0.03,
                'margin_contraction': -0.02
            }
        },
        {
            'id': 'RECESSION',
            'name': 'Recession',
            'description': 'Economic downturn scenario',
            'overrides': {
                'revenue_growth_adjustment': -0.08,
                'margin_contraction': -0.05,
                'wacc_adjustment': 0.02
            }
        }
    ]
    
    return {
        'success': True,
        'scenarios': scenarios
    }


@app.post("/api/select-scenario")
async def select_scenario(scenario: ScenarioSelect):
    """Select a scenario for valuation"""
    global valuation_state
    
    valuation_state['selected_scenario'] = {
        'type': scenario.scenarioType,
        'custom_overrides': scenario.customOverrides,
        'selected_at': datetime.now().isoformat()
    }
    
    return {
        'success': True,
        'message': f'Selected {scenario.scenarioType} scenario',
        'scenario': valuation_state['selected_scenario']
    }


@app.post("/api/run-valuation")
async def run_valuation(valuation: ValuationRun):
    """Run valuation calculation"""
    global valuation_state
    
    model_type = valuation.modelType.upper()
    confirmed_values = valuation.confirmedValues
    scenario = valuation.scenario
    
    try:
        result = None
        
        if model_type == 'DCF':
            result = calculate_dcf_valuation(confirmed_values, scenario)
        elif model_type == 'DUPONT':
            result = calculate_dupont_analysis(confirmed_values)
        elif model_type == 'COMPS':
            # Simplified comps calculation
            ebitda = confirmed_values.get('subject_ebitda', 0)
            peer_multiple = confirmed_values.get('peer_ev_ebitda_median', 10)
            enterprise_value = ebitda * peer_multiple
            
            result = {
                'success': True,
                'model': 'COMPS',
                'enterprise_value': enterprise_value,
                'equity_value': enterprise_value - confirmed_values.get('net_debt', 0),
                'methodology': 'EV/EBITDA multiple approach',
                'key_assumptions': {
                    'peer_ev_ebitda_median': peer_multiple,
                    'subject_ebitda': ebitda
                }
            }
        elif model_type == 'REALESTATE':
            # Real estate valuation
            noi = confirmed_values.get('noi', 0)
            cap_rate = confirmed_values.get('cap_rate', 0.06)
            
            if cap_rate > 0:
                property_value = noi / cap_rate
                result = {
                    'success': True,
                    'model': 'REALESTATE',
                    'property_value': property_value,
                    'methodology': 'Direct Capitalization',
                    'key_assumptions': {
                        'noi': noi,
                        'cap_rate': cap_rate
                    }
                }
            else:
                result = {'success': False, 'error': 'Cap rate must be positive'}
        else:
            result = {'success': False, 'error': f'Unknown model type: {model_type}'}
        
        if result and result.get('success'):
            valuation_state['valuation_result'] = {
                'result': result,
                'model': model_type,
                'calculated_at': datetime.now().isoformat()
            }
        
        return result
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'model': model_type
        }


@app.get("/api/results")
async def get_results():
    """Get latest valuation results"""
    global valuation_state
    
    if 'valuation_result' in valuation_state:
        return {
            'success': True,
            'result': valuation_state['valuation_result']
        }
    else:
        return {
            'success': True,
            'result': None,
            'message': 'No valuation results yet'
        }


@app.post("/api/reset")
async def reset_state():
    """Reset all state"""
    global valuation_state
    
    selected_company = valuation_state.get('selected_company')
    valuation_state = {}
    if selected_company:
        valuation_state['selected_company'] = selected_company
    
    return {
        'success': True,
        'message': 'State reset successfully'
    }


@app.get("/api/historical-financials/{ticker}")
async def get_historical_financials(ticker: str, years: int = 5):
    """Get historical financial data for a ticker"""
    ticker = ticker.upper()
    
    financial_data = await fetch_comprehensive_financial_data(ticker)
    
    if financial_data.get('success'):
        data = financial_data.get('data', {})
        return {
            'success': True,
            'ticker': ticker,
            'income_statement': data.get('income_statement_raw', {}),
            'balance_sheet': data.get('balance_sheet_raw', {}),
            'cash_flow': data.get('cash_flow_raw', {}),
            'years': years
        }
    else:
        return financial_data


@app.get("/api/trending-peers/{ticker}")
async def get_trending_peers(ticker: str):
    """Get trending peers for a ticker"""
    ticker = ticker.upper()
    
    # Mock peer data - in production, this would come from industry classification
    peers = {
        'AAPL': ['MSFT', 'GOOGL', 'META', 'AMZN'],
        'MSFT': ['AAPL', 'GOOGL', 'ORCL', 'CRM'],
        'GOOGL': ['META', 'AAPL', 'MSFT', 'AMZN'],
        'TSLA': ['F', 'GM', 'RIVN', 'LCID'],
        'AMZN': ['WMT', 'EBAY', 'SHOP', 'BABA']
    }
    
    peer_list = peers.get(ticker, ['SPY', 'QQQ'])
    
    return {
        'success': True,
        'ticker': ticker,
        'peers': peer_list
    }


@app.get("/api/combined-inputs/{ticker}")
async def get_combined_inputs(ticker: str):
    """Get combined auto-populated and manual inputs for a ticker"""
    ticker = ticker.upper()
    
    # Fetch auto data
    financial_data = await fetch_comprehensive_financial_data(ticker)
    
    # Get manual inputs if any
    manual_key = f'manual_inputs_{ticker}_DCF'
    manual_inputs = valuation_state.get(manual_key, {}).get('inputs', {})
    
    return {
        'success': True,
        'ticker': ticker,
        'auto_data': financial_data.get('data', {}) if financial_data.get('success') else {},
        'manual_inputs': manual_inputs,
        'sources': financial_data.get('sources', [])
    }


@app.post("/api/dcf/calculate")
async def calculate_dcf(dcf_request: dict):
    """Run DCF calculation with detailed inputs"""
    try:
        base_period_data = dcf_request.get('base_period_data', {})
        forecast_drivers = dcf_request.get('forecast_drivers', {})
        assumptions = dcf_request.get('assumptions', {})
        ticker = dcf_request.get('ticker', 'UNKNOWN')
        
        # Validate required inputs
        if not base_period_data or not forecast_drivers:
            return {
                'success': False,
                'error': 'Missing required fields: base_period_data and forecast_drivers'
            }
        
        # Ensure forecast drivers have exactly 6 values (5 years + terminal)
        drivers = ['revenue_growth', 'inflation_rate', 'opex_growth', 'ar_days', 'inv_days', 'ap_days']
        for driver in drivers:
            if driver not in forecast_drivers or len(forecast_drivers[driver]) != 6:
                return {
                    'success': False,
                    'error': f'{driver} must have exactly 6 values (5 forecast years + terminal year)',
                    'received': len(forecast_drivers.get(driver, []))
                }
        
        # Ensure capital_expenditure has exactly 5 values (forecast years only)
        if 'capital_expenditure' not in forecast_drivers or len(forecast_drivers['capital_expenditure']) != 5:
            return {
                'success': False,
                'error': 'capital_expenditure must have exactly 5 values (forecast years only)',
                'received': len(forecast_drivers.get('capital_expenditure', []))
            }
        
        # Map input schema to engine schema
        engine_inputs = {
            # Base period data (FY-1 / 2022A)
            'base_revenue': base_period_data.get('revenue', 0),
            'base_cogs': base_period_data.get('cogs', 0),
            'base_sga': base_period_data.get('sga', 0),
            'base_other': base_period_data.get('other_opex', 0),
            'base_existing_ppe': base_period_data.get('ppe_gross', 0),
            'base_nol': base_period_data.get('nol_remaining', 0),
            'base_net_debt': base_period_data.get('net_debt', 0),
            'base_current_stock_price': base_period_data.get('current_stock_price', 0),
            'base_shares_outstanding': base_period_data.get('shares_outstanding', 0),
            
            # Forecast drivers (6 values each)
            'revenue_growth_rates': [g / 100 for g in forecast_drivers['revenue_growth']],
            'inflation_rates': [g / 100 for g in forecast_drivers['inflation_rate']],
            'opex_growth_rates': [g / 100 for g in forecast_drivers['opex_growth']],
            'capital_expenditures': forecast_drivers['capital_expenditure'],
            'ar_days': forecast_drivers['ar_days'],
            'inv_days': forecast_drivers['inv_days'],
            'ap_days': forecast_drivers['ap_days'],
            
            # Assumptions
            'useful_life_existing': assumptions.get('useful_life_existing', 10),
            'useful_life_new': assumptions.get('useful_life_new', 5),
            'tax_rate': assumptions.get('tax_rate', 0.21),
            'nol_utilization_limit': assumptions.get('nol_utilization_limit', 0.80),
            'wacc': assumptions.get('wacc', 0.097),
            'terminal_growth_rate': assumptions.get('terminal_growth_rate', 0.02),
            'terminal_multiple': assumptions.get('terminal_multiple', 7.0),
            
            # Metadata
            'valuation_date': assumptions.get('valuation_date', datetime.now().isoformat().split('T')[0]),
            'scenario': assumptions.get('scenario', 'base_case')
        }
        
        # Run DCF calculation
        result = calculate_dcf_valuation(engine_inputs, {})
        
        # Add ticker and additional metadata
        if result:
            result['metadata']['ticker'] = ticker
        
        return {
            'success': True,
            'data': result,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': 'DCF calculation failed',
            'details': str(e)
        }


@app.post("/api/dcf/calculate-scenarios")
async def calculate_dcf_scenarios(request_data: dict):
    """Run DCF with multiple scenarios"""
    try:
        base_period_data = request_data.get('base_period_data', {})
        forecast_drivers = request_data.get('forecast_drivers', {})
        scenarios = request_data.get('scenarios', ['base_case', 'bull_case', 'bear_case'])
        ticker = request_data.get('ticker', 'UNKNOWN')
        
        results = {}
        for scenario_name in scenarios:
            scenario_drivers = forecast_drivers.get(scenario_name, forecast_drivers.get('base_case', {}))
            
            engine_inputs = {
                'base_revenue': base_period_data.get('revenue', 0),
                'base_cogs': base_period_data.get('cogs', 0),
                'base_sga': base_period_data.get('sga', 0),
                'base_other': base_period_data.get('other_opex', 0),
                'base_existing_ppe': base_period_data.get('ppe_gross', 0),
                'base_net_debt': base_period_data.get('net_debt', 0),
                'base_current_stock_price': base_period_data.get('current_stock_price', 0),
                'base_shares_outstanding': base_period_data.get('shares_outstanding', 0),
                'revenue_growth_rates': [g / 100 for g in scenario_drivers.get('revenue_growth', [0.05] * 6)],
                'inflation_rates': [g / 100 for g in scenario_drivers.get('inflation_rate', [0.02] * 6)],
                'opex_growth_rates': [g / 100 for g in scenario_drivers.get('opex_growth', [0.02] * 6)],
                'capital_expenditures': scenario_drivers.get('capital_expenditure', [5000] * 5),
                'ar_days': scenario_drivers.get('ar_days', 45),
                'inv_days': scenario_drivers.get('inv_days', 30),
                'ap_days': scenario_drivers.get('ap_days', 60),
                'wacc': scenario_drivers.get('wacc', 0.097),
                'terminal_growth_rate': scenario_drivers.get('terminal_growth_rate', 0.02),
                'terminal_multiple': scenario_drivers.get('terminal_multiple', 7.0),
                'scenario': scenario_name
            }
            
            result = calculate_dcf_valuation(engine_inputs, {})
            if result:
                results[scenario_name] = result
        
        return {
            'success': True,
            'data': results,
            'ticker': ticker,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': 'DCF scenario calculation failed',
            'details': str(e)
        }


@app.post("/api/dcf/sensitivity")
async def calculate_dcf_sensitivity(request_data: dict):
    """Calculate DCF sensitivity analysis"""
    try:
        base_values = request_data.get('base_values', {})
        wacc_range = request_data.get('wacc_range', [0.06, 0.08, 0.10, 0.12, 0.14])
        terminal_growth_range = request_data.get('terminal_growth_range', [0.01, 0.02, 0.03, 0.04])
        
        sensitivity_matrix = []
        
        for wacc in wacc_range:
            row = {'wacc': wacc}
            for terminal_growth in terminal_growth_range:
                engine_inputs = {
                    'base_revenue': base_values.get('base_revenue', 100000),
                    'base_cogs': base_values.get('base_cogs', 60000),
                    'base_sga': base_values.get('base_sga', 20000),
                    'base_other': base_values.get('base_other', 5000),
                    'base_existing_ppe': base_values.get('base_existing_ppe', 50000),
                    'base_net_debt': base_values.get('base_net_debt', 0),
                    'base_current_stock_price': base_values.get('base_current_stock_price', 100),
                    'base_shares_outstanding': base_values.get('base_shares_outstanding', 1000),
                    'revenue_growth_rates': base_values.get('revenue_growth_rates', [0.05] * 6),
                    'inflation_rates': base_values.get('inflation_rates', [0.02] * 6),
                    'opex_growth_rates': base_values.get('opex_growth_rates', [0.02] * 6),
                    'capital_expenditures': base_values.get('capital_expenditures', [5000] * 5),
                    'ar_days': base_values.get('ar_days', 45),
                    'inv_days': base_values.get('inv_days', 30),
                    'ap_days': base_values.get('ap_days', 60),
                    'wacc': wacc,
                    'terminal_growth_rate': terminal_growth,
                    'terminal_multiple': base_values.get('terminal_multiple', 7.0),
                    'scenario': 'sensitivity'
                }
                
                result = calculate_dcf_valuation(engine_inputs, {})
                if result:
                    row[f'tg_{int(terminal_growth*100)}'] = result['main_outputs'].get('enterprise_value_perpetuity', 0)
            
            sensitivity_matrix.append(row)
        
        return {
            'success': True,
            'data': {
                'sensitivity_matrix': sensitivity_matrix,
                'wacc_range': wacc_range,
                'terminal_growth_range': terminal_growth_range
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': 'DCF sensitivity calculation failed',
            'details': str(e)
        }


@app.post("/api/dcf/validate")
async def validate_dcf_inputs(request_data: dict):
    """Validate DCF input data"""
    try:
        validations = {'critical': [], 'warnings': []}
        
        base_period_data = request_data.get('base_period_data', {})
        forecast_drivers = request_data.get('forecast_drivers', {})
        assumptions = request_data.get('assumptions', {})
        
        # Check required base period fields
        required_base_fields = ['revenue', 'cogs', 'sga']
        for field in required_base_fields:
            if field not in base_period_data:
                validations['critical'].append({
                    'field': field,
                    'rule': 'required',
                    'message': f'{field} is required in base_period_data'
                })
            elif base_period_data[field] <= 0:
                validations['warnings'].append({
                    'field': field,
                    'rule': 'positive',
                    'message': f'{field} should be positive'
                })
        
        # Check forecast driver array lengths
        array_drivers = ['revenue_growth', 'inflation_rate', 'opex_growth', 'ar_days', 'inv_days', 'ap_days']
        for driver in array_drivers:
            if driver in forecast_drivers:
                if len(forecast_drivers[driver]) != 6:
                    validations['critical'].append({
                        'field': driver,
                        'rule': 'length',
                        'message': f'{driver} must have exactly 6 values, got {len(forecast_drivers[driver])}'
                    })
        
        # Check CapEx array length
        if 'capital_expenditure' in forecast_drivers:
            if len(forecast_drivers['capital_expenditure']) != 5:
                validations['critical'].append({
                    'field': 'capital_expenditure',
                    'rule': 'length',
                    'message': f'capital_expenditure must have exactly 5 values, got {len(forecast_drivers["capital_expenditure"])}'
                })
        
        # Check WACC range
        wacc = assumptions.get('wacc', 0.097)
        if wacc < 0.03 or wacc > 0.25:
            validations['warnings'].append({
                'field': 'wacc',
                'rule': 'range',
                'message': f'WACC ({wacc:.2%}) is outside typical range (3%-25%)'
            })
        
        # Check terminal growth rate
        terminal_growth = assumptions.get('terminal_growth_rate', 0.02)
        if terminal_growth < -0.02 or terminal_growth > 0.05:
            validations['warnings'].append({
                'field': 'terminal_growth_rate',
                'rule': 'range',
                'message': f'Terminal growth rate ({terminal_growth:.2%}) is outside typical range (-2%-5%)'
            })
        
        is_valid = len(validations['critical']) == 0
        
        return {
            'success': True,
            'valid': is_valid,
            'validations': validations,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': 'Validation failed',
            'details': str(e)
        }


@app.post("/api/auto-populate-inputs")
async def auto_populate_inputs(data_request: DataRetrieve):
    """Auto-populate inputs from financial data"""
    model_type = data_request.modelType.upper()
    ticker = data_request.ticker.upper()
    
    financial_data = await fetch_comprehensive_financial_data(ticker)
    
    if not financial_data.get('success'):
        return financial_data
    
    data = financial_data.get('data', {})
    market_structure = data.get('market_structure', {})
    income_stmt = data.get('income_statement_raw', {})
    balance_sheet = data.get('balance_sheet_raw', {})
    calculated_metrics = data.get('calculated_metrics_common', {})
    
    # Auto-populate based on model type
    auto_populated = {}
    
    if model_type == 'DCF':
        auto_populated = {
            'revenue_current': income_stmt.get('revenue_total', 0),
            'operating_margin': calculated_metrics.get('operating_margin', 0),
            'tax_rate': calculated_metrics.get('effective_tax_rate', 0.21),
            'wacc': 0.08 + market_structure.get('beta_5y_monthly', 1.0) * 0.055,
            'terminal_growth_rate': 0.023,
            'current_price': market_structure.get('current_price', 0),
            'shares_outstanding': market_structure.get('shares_outstanding_diluted', 0)
        }
    elif model_type == 'DUPONT':
        auto_populated = {
            'net_income': income_stmt.get('net_income', 0),
            'revenue': income_stmt.get('revenue_total', 0),
            'total_assets': balance_sheet.get('total_assets', 0),
            'total_equity': balance_sheet.get('total_equity', 0),
            'ebit_operating_income': income_stmt.get('ebit_operating_income', 0),
            'pre_tax_income_ebt': income_stmt.get('pre_tax_income_ebt', 0)
        }
    elif model_type == 'COMPS':
        auto_populated = {
            'subject_ebitda': income_stmt.get('ebitda', 0),
            'subject_net_income': income_stmt.get('net_income', 0),
            'subject_equity': balance_sheet.get('total_equity', 0)
        }
    
    return {
        'success': True,
        'ticker': ticker,
        'model': model_type,
        'auto_populated': auto_populated,
        'source': 'yfinance'
    }


@app.get("/api/forecast-benchmarks/{ticker}")
async def get_forecast_benchmarks(ticker: str):
    """Get forecast benchmarks for a ticker"""
    ticker = ticker.upper()
    
    financial_data = await fetch_comprehensive_financial_data(ticker)
    
    if not financial_data.get('success'):
        return financial_data
    
    data = financial_data.get('data', {})
    calculated_metrics = data.get('calculated_metrics_common', {})
    
    # Industry benchmark growth rates (simplified)
    benchmarks = {
        'revenue_growth': {
            'industry_median': 0.08,
            'industry_75th_pct': 0.15,
            'industry_25th_pct': 0.03,
            'historical_company': calculated_metrics.get('revenue_growth_yoy', 0.05)
        },
        'margin': {
            'industry_median': calculated_metrics.get('operating_margin', 0.15),
            'historical_company': calculated_metrics.get('operating_margin', 0.15)
        }
    }
    
    return {
        'success': True,
        'ticker': ticker,
        'benchmarks': benchmarks
    }


@app.get("/api/forecast-suggestion/{ticker}/{driver}")
async def get_forecast_suggestion(ticker: str, driver: str):
    """Get AI-powered forecast suggestion for a driver"""
    ticker = ticker.upper()
    
    financial_data = await fetch_comprehensive_financial_data(ticker)
    
    if not financial_data.get('success'):
        return financial_data
    
    data = financial_data.get('data', {})
    calculated_metrics = data.get('calculated_metrics_common', {})
    
    # Simple heuristic-based suggestions
    suggestions = {
        'revenue_growth': {
            'suggested_value': min(0.15, max(0.03, calculated_metrics.get('revenue_growth_yoy', 0.05))),
            'rationale': 'Based on historical growth and industry trends',
            'confidence': 0.7
        },
        'margin': {
            'suggested_value': calculated_metrics.get('operating_margin', 0.15),
            'rationale': 'Based on historical operating margin',
            'confidence': 0.8
        },
        'capex_percent': {
            'suggested_value': 0.05,
            'rationale': 'Typical capex as % of revenue',
            'confidence': 0.6
        }
    }
    
    suggestion = suggestions.get(driver, {
        'suggested_value': 0.05,
        'rationale': 'Default assumption',
        'confidence': 0.5
    })
    
    return {
        'success': True,
        'ticker': ticker,
        'driver': driver,
        'suggestion': suggestion
    }


@app.get("/api/ai-peer-analysis/{ticker}")
async def get_ai_peer_analysis(ticker: str):
    """Get AI-powered peer analysis"""
    ticker = ticker.upper()
    
    # Get peers
    peers_response = await get_trending_peers(ticker)
    peers = peers_response.get('peers', [])
    
    # In production, fetch actual peer data and perform AI analysis
    analysis = {
        'ticker': ticker,
        'peers_analyzed': peers,
        'comparative_metrics': {
            'ev_ebitda': {
                'subject': 15.2,
                'peer_median': 14.8,
                'peer_mean': 16.1,
                'percentile': 55
            },
            'pe_ratio': {
                'subject': 25.3,
                'peer_median': 23.1,
                'peer_mean': 26.4,
                'percentile': 58
            },
            'roe': {
                'subject': 0.28,
                'peer_median': 0.24,
                'peer_mean': 0.26,
                'percentile': 68
            }
        },
        'ai_summary': f'{ticker} trades at a slight premium to peers on EV/EBITDA but shows superior ROE, suggesting quality justification for the multiple.',
        'source': 'heuristic'
    }
    
    return {
        'success': True,
        'analysis': analysis
    }


@app.get("/api/ai-valuation-suggestions/{ticker}")
async def get_ai_valuation_suggestions(ticker: str):
    """Get AI-powered valuation method suggestions"""
    ticker = ticker.upper()
    
    financial_data = await fetch_comprehensive_financial_data(ticker)
    
    if not financial_data.get('success'):
        return financial_data
    
    data = financial_data.get('data', {})
    market_structure = data.get('market_structure', {})
    income_stmt = data.get('income_statement_raw', {})
    
    # Determine best valuation methods based on company characteristics
    suggestions = []
    
    # DCF suitability
    has_positive_fcf = data.get('cash_flow_raw', {}).get('free_cash_flow', 0) > 0
    stable_business = market_structure.get('beta_5y_monthly', 1.0) < 1.5
    
    if has_positive_fcf and stable_business:
        suggestions.append({
            'method': 'DCF',
            'suitability_score': 0.9,
            'rationale': 'Stable business with positive free cash flow - ideal for DCF'
        })
    elif has_positive_fcf:
        suggestions.append({
            'method': 'DCF',
            'suitability_score': 0.7,
            'rationale': 'Positive FCF but higher volatility - use with caution'
        })
    
    # Comps suitability
    has_peers = True  # Assume peers exist
    suggestions.append({
        'method': 'COMPS',
        'suitability_score': 0.85 if has_peers else 0.5,
        'rationale': 'Market-based valuation provides reality check' if has_peers else 'Limited peer set available'
    })
    
    # DuPont suitability
    has_complete_financials = all([
        income_stmt.get('net_income', 0),
        data.get('balance_sheet_raw', {}).get('total_equity', 0),
        income_stmt.get('revenue_total', 0)
    ])
    
    if has_complete_financials:
        suggestions.append({
            'method': 'DUPONT',
            'suitability_score': 0.8,
            'rationale': 'Complete financial statements available for ROE decomposition'
        })
    
    # Sort by suitability
    suggestions.sort(key=lambda x: x['suitability_score'], reverse=True)
    
    return {
        'success': True,
        'ticker': ticker,
        'suggestions': suggestions
    }


@app.get("/api/manual-input-benchmark/{ticker}/{model}/{field}")
async def get_manual_input_benchmark(ticker: str, model: str, field: str):
    """Get benchmark value for a manual input field"""
    ticker = ticker.upper()
    model = model.upper()
    
    financial_data = await fetch_comprehensive_financial_data(ticker)
    
    if not financial_data.get('success'):
        return financial_data
    
    data = financial_data.get('data', {})
    calculated_metrics = data.get('calculated_metrics_common', {})
    market_structure = data.get('market_structure', {})
    
    benchmarks = {
        'wacc': {
            'benchmark': 0.08 + market_structure.get('beta_5y_monthly', 1.0) * 0.055,
            'source': 'CAPM',
            'range': {'min': 0.05, 'max': 0.15}
        },
        'terminal_growth_rate': {
            'benchmark': 0.023,
            'source': 'Long-term inflation expectation',
            'range': {'min': 0.01, 'max': 0.04}
        },
        'tax_rate': {
            'benchmark': calculated_metrics.get('effective_tax_rate', 0.21),
            'source': 'Historical effective rate',
            'range': {'min': 0.15, 'max': 0.35}
        },
        'operating_margin': {
            'benchmark': calculated_metrics.get('operating_margin', 0.15),
            'source': 'Historical operating margin',
            'range': {'min': 0.05, 'max': 0.35}
        }
    }
    
    benchmark = benchmarks.get(field, {
        'benchmark': None,
        'source': 'Not available',
        'range': None
    })
    
    return {
        'success': True,
        'ticker': ticker,
        'model': model,
        'field': field,
        'benchmark': benchmark
    }


@app.post("/api/dupont/analyze")
async def analyze_dupont(request_data: dict):
    """Perform complete DuPont analysis"""
    try:
        input_data = request_data
        
        # Validate input structure
        if not input_data or not isinstance(input_data, dict):
            return {
                'success': False,
                'error': 'Invalid input: expected JSON object with financial data arrays'
            }
        
        # Check that all required arrays have 6-10 values
        required_fields = [
            'revenue', 'gross_profit', 'ebitda', 'operating_income', 'net_income',
            'total_assets', 'accounts_receivable', 'inventory', 'accounts_payable',
            'cogs', 'total_debt', 'total_equity', 'current_assets', 'current_liabilities',
            'interest_expense', 'ebt', 'ebit'
        ]
        
        validation_errors = []
        for field in required_fields:
            if field not in input_data:
                validation_errors.append(f'Missing required field: {field}')
            elif not isinstance(input_data[field], list):
                validation_errors.append(f'{field} must be an array')
            elif len(input_data[field]) < 6 or len(input_data[field]) > 10:
                validation_errors.append(f'{field} must have 6-10 values, got {len(input_data[field])}')
        
        if validation_errors:
            return {
                'success': False,
                'errors': validation_errors
            }
        
        # Perform DuPont analysis
        result = calculate_dupont_analysis(input_data)
        
        return {
            'success': True,
            'data': result,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': 'DuPont analysis failed',
            'details': str(e)
        }


@app.post("/api/dupont/supporting-ratios")
async def get_dupont_supporting_ratios(request_data: dict):
    """Get supporting ratios only"""
    try:
        from dupont_engine import calculate_supporting_ratios
        
        ratios = calculate_supporting_ratios(request_data)
        
        return {
            'success': True,
            'data': {'supporting_ratios': ratios},
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': 'Failed to calculate supporting ratios',
            'details': str(e)
        }


@app.post("/api/dupont/3step")
async def get_dupont_3step(request_data: dict):
    """Get 3-Step DuPont Analysis only"""
    try:
        from dupont_engine import calculate_dupont_3step
        
        result = calculate_dupont_3step(request_data)
        
        return {
            'success': True,
            'data': {'dupont_3step': result},
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': 'Failed to calculate 3-step DuPont',
            'details': str(e)
        }


@app.post("/api/dupont/5step")
async def get_dupont_5step(request_data: dict):
    """Get 5-Step DuPont Analysis only"""
    try:
        from dupont_engine import calculate_dupont_5step
        
        result = calculate_dupont_5step(request_data)
        
        return {
            'success': True,
            'data': {'dupont_5step': result},
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': 'Failed to calculate 5-step DuPont',
            'details': str(e)
        }


@app.post("/api/dupont/growth-trends")
async def get_dupont_growth_trends(request_data: dict):
    """Get growth trends and leverage metrics"""
    try:
        from dupont_engine import calculate_growth_trends
        
        trends = calculate_growth_trends(request_data)
        
        return {
            'success': True,
            'data': {'growth_trends': trends},
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': 'Failed to calculate growth trends',
            'details': str(e)
        }


@app.post("/api/dupont/validate")
async def validate_dupont_inputs(request_data: dict):
    """Validate DuPont input data"""
    try:
        validations = {'critical': [], 'warnings': []}
        
        # Required fields for complete DuPont analysis
        required_fields = [
            'revenue', 'gross_profit', 'ebitda', 'operating_income', 'net_income',
            'total_assets', 'accounts_receivable', 'inventory', 'accounts_payable',
            'cogs', 'total_debt', 'total_equity', 'current_assets', 'current_liabilities',
            'interest_expense', 'ebt', 'ebit'
        ]
        
        # Check required fields and array lengths
        for field in required_fields:
            if field not in request_data:
                validations['critical'].append({
                    'field': field,
                    'rule': 'required',
                    'message': f'{field} is required'
                })
            elif not isinstance(request_data[field], list):
                validations['critical'].append({
                    'field': field,
                    'rule': 'type',
                    'message': f'{field} must be an array'
                })
            elif len(request_data[field]) < 6 or len(request_data[field]) > 10:
                validations['critical'].append({
                    'field': field,
                    'rule': 'length',
                    'message': f'{field} must have 6-10 values, got {len(request_data[field])}'
                })
        
        # Additional validation: check for negative values where inappropriate
        if 'revenue' in request_data:
            for idx, val in enumerate(request_data['revenue']):
                if val <= 0:
                    validations['warnings'].append({
                        'field': 'revenue',
                        'year_index': idx,
                        'rule': 'positive',
                        'message': f'Revenue in year {idx} is non-positive ({val})'
                    })
        
        is_valid = len(validations['critical']) == 0
        
        return {
            'success': True,
            'valid': is_valid,
            'validations': validations,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': 'Validation failed',
            'details': str(e)
        }


@app.get("/api/required-inputs-checklist")
async def get_required_inputs_checklist(model: str = None):
    """Get checklist of required inputs for current model"""
    model_type = (model or 'DCF').upper()
    
    response = await get_required_fields(model_type)
    
    return {
        'success': True,
        'model': model_type,
        'checklist': response.get('fields', []),
        'completion_status': {
            'total': len(response.get('fields', [])),
            'completed': 0,
            'pending': len(response.get('fields', []))
        }
    }


# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True
    )
