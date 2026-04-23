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

# AI SDK imports
try:
    from google.genai import Client as GoogleGenAIClient
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

# Initialize AI clients
gemini_client = None
groq_client = None

if GOOGLE_AI_AVAILABLE and GEMINI_API_KEY:
    try:
        gemini_client = GoogleGenAIClient(api_key=GEMINI_API_KEY)
    except Exception:
        pass

if GROQ_AVAILABLE and GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
    except Exception:
        pass

# AI Model configuration
AI_CONFIG = {
    'primary': 'gemini',
    'fallback': 'groq',
    'gemini_model': 'gemini-1.5-flash',
    'groq_model': 'llama-3.2-90b-vision-preview',
    'max_retries': 2,
    'timeout_ms': 30000,
    'confidence_threshold': 0.7
}

# In-memory state storage (in production, use a database)
valuation_state = {}

# Mock data for demonstration
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
            return {'success': True, 'suggestion': response.text, 'source': 'gemini'}
        except Exception:
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
