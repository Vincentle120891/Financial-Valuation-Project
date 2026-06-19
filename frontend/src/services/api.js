import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Helper to get ALL stored API keys from localStorage (for sending to backend)
const getAllStoredApiKeys = () => {
  const getAll = (name) => {
    const raw = localStorage.getItem(`${name}_api_key`) || '';
    return raw.split('\n').map(k => k.trim()).filter(k => k);
  };
  return {
    alpha_vantage: getAll('alpha_vantage'),
    fmp: getAll('fmp'),
    fred: getAll('fred'),
    sec_edgar: getAll('sec_edgar'),
    openrouter: getAll('openrouter'),
    groq: getAll('groq'),
    gemini: getAll('gemini'),
    qwen: getAll('qwen'),
    openai: getAll('openai'),
  };
};

// Helper to inject API keys into request headers (supports multiple keys comma-separated)
const injectApiKeys = (headers = {}) => {
  const allKeys = getAllStoredApiKeys();
  
  // Send all keys as comma-separated for each service
  // Backend parses and registers them in the ApiKeyManager
  for (const [service, keys] of Object.entries(allKeys)) {
    if (keys.length > 0) {
      const headerName = `X-API-Key-${service.replace(/_/g, '-').replace(/\b\w/g, l => l.toUpperCase())}`;
      headers[headerName] = keys.join(',');
    }
  }
  
  return headers;
};

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Add timeout configuration (60 seconds for regular calls, 120 for AI)
  timeout: 60000,
});

// Request interceptor to inject API keys into all requests
api.interceptors.request.use(
  (config) => {
    config.headers = injectApiKeys(config.headers);
    // Log API call for process visibility
    const step = config.url?.match(/step-(\d+)/)?.[1] || 'API';
    const method = config.method?.toUpperCase() || 'GET';
    window.dispatchEvent(new CustomEvent('api-process-log', {
      detail: {
        step: `Step ${step}`,
        message: `${method} ${config.url?.split('/api/')[1] || config.url}`,
        status: 'info'
      }
    }));
    return config;
  },
  (error) => {
    const step = error.config?.url?.match(/step-(\d+)/)?.[1] || 'API';
    const detail = error.response?.data?.detail || error.message;
    window.dispatchEvent(new CustomEvent('api-process-log', {
      detail: { step: `Step ${step}`, message: `❌ ${error.response?.status || 'Error'}: ${detail}`, status: 'error' }
    }));
    return Promise.reject(error);
  }
);

// Response interceptor for success + error logging
api.interceptors.response.use(
  (response) => {
    const step = response.config?.url?.match(/step-(\d+)/)?.[1] || 'API';
    window.dispatchEvent(new CustomEvent('api-process-log', {
      detail: { step: `Step ${step}`, message: `✅ ${response.config?.method?.toUpperCase()} ${response.config?.url?.split('/api/')[1] || ''} — ${response.status} OK`, status: 'success' }
    }));
    return response;
  },
  (error) => {
    const step = error.config?.url?.match(/step-(\d+)/)?.[1] || 'API';
    const status = error.response?.status || 'Error';
    const detail = error.response?.data?.detail || error.message || 'Unknown error';
    window.dispatchEvent(new CustomEvent('api-process-log', {
      detail: { step: `Step ${step}`, message: `❌ ${error.config?.method?.toUpperCase()} ${error.config?.url?.split('/api/')[1] || ''} — ${status}: ${detail}`, status: 'error' }
    }));
    return Promise.reject(error);
  }
);

// Create separate instance for AI calls with longer timeout
const aiApi = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2 minutes for AI generation
});

// Request interceptor for AI API as well
aiApi.interceptors.request.use(
  (config) => {
    config.headers = injectApiKeys(config.headers);
    return config;
  },
  (error) => Promise.reject(error)
);

// Step 1: Search Company
// FIX Issue #1 & #3: Use unified POST endpoint for both markets
export const searchCompanies = async (query, market = 'international') => {
  // Use unified POST endpoint for ALL markets - no routing based on market
  try {
    const response = await api.post('/step-1-search', { query, market: market.toLowerCase() });
    return transformVietnameseResponse(response.data, market);
  } catch (error) {
    console.error('Search companies error:', error);
    throw error;
  }
};

// Transform Vietnamese response to match standard schema
const transformVietnameseResponse = (data, market) => {
  if (market !== 'vietnam' || !data) return data;
  
  // Handle array of results
  if (Array.isArray(data)) {
    return data.map(item => ({
      ticker: item.ticker || item.symbol,
      company_name: item.company_name || item.name || item.companyName,
      sector: item.sector || item.industry,
      exchange: item.exchange || item.market || 'HOSE',
      market_cap: item.market_cap || item.marketCap,
      ...item
    }));
  }
  
  // Handle single object
  return {
    ticker: data.ticker || data.symbol,
    company_name: data.company_name || data.name || data.companyName,
    sector: data.sector || data.industry,
    exchange: data.exchange || data.market || 'HOSE',
    market_cap: data.market_cap || data.marketCap,
    ...data
  };
};

// Step 4: Suggest Peers (after model selection)
export const suggestPeers = async (ticker, market = 'international', maxPeers = 10, method = null, sessionId = null) => {
  const response = await api.post('/step-4-discover-peers', {
    ticker,
    market: market.toLowerCase(),
    max_peers: maxPeers,
    method: method ? method.toUpperCase() : null, // Pass selected valuation method for method-specific peer criteria
    session_id: sessionId // Include session_id to store suggestions and prevent re-fetching loop
    // Note: ticker is NOT sent - backend extracts it from session using session_id
  });
  return response.data;
};

// Step 2: Select Company (Create Session)
export const selectCompany = async (sessionId, ticker, market = 'international') => {
  const response = await api.post('/step-2-create-session', { session_id: sessionId, ticker, market: market.toLowerCase() });
  return response.data;
};

// Step 3: Save Selected Peers
export const savePeers = async (sessionId, peers) => {
  const response = await api.post('/step-4-save-peers', { session_id: sessionId, peers });
  return response.data;
};

// Step 5: Validate Manual Peer Tickers
export const validateManualPeers = async (sessionId, tickers, market = 'international') => {
  const response = await api.post('/step-5-validate-manual-peers', {
    session_id: sessionId,
    tickers,
    market: market.toLowerCase()
  });
  return response.data;
};

// Step 3: Select Model - Updated to use unified schema
// Workflow: Select Method → Get Confirmation (Peers are generated in Step 4)
export const selectModels = async (sessionId, method, market = 'international') => {
  const response = await api.post('/step-3-select-models', {
    session_id: sessionId,
    method: method.toUpperCase(),
    market: market.toLowerCase()
  });
  return response.data;
};

// Step 5: Prepare Assumptions - Updated to use unified schema
export const prepareAssumptions = async (sessionId, method, market = 'international', generateAi = true) => {
  const response = await api.post('/step-5-prepare-assumptions', {
    session_id: sessionId,
    method: method.toUpperCase(),
    market: market.toLowerCase(),
    generate_ai: generateAi
  });
  return response.data;
};

// Step 6: Fetch API Data - Unified endpoint for all markets
// Market is passed as a parameter, not used for routing
export const fetchApiData = async (sessionId, method, market = 'international') => {
  // Use unified endpoint for ALL markets - market is passed as parameter
  const response = await api.post('/step-6-fetch-api-data', {
    session_id: sessionId,
    method,
    market: market.toLowerCase()
  });
  return response.data;
};

// Step 7: Retrieve Historical Data Using AI Extraction (uses longer timeout)
// Now requires method and market parameters
export const retrieveHistoricalData = async (sessionId, method, market = 'international') => {
  try {
    const response = await aiApi.post('/step-7-retrieve-historical-data', {
      session_id: sessionId,
      method,
      market: market.toLowerCase()
    });
    return response.data;
  } catch (error) {
    if (error.code === 'ECONNABORTED') {
      throw new Error('Historical data extraction timed out. The request took too long to complete. Please try again or proceed with available data.');
    }
    throw error;
  }
};

// Step 8: Initialize assumptions with historical trendlines
// Now requires method and market parameters
export const initializeStep8Assumptions = async (sessionId, method, market = 'international') => {
  try {
    const response = await api.post('/step-8-initialize', {
      session_id: sessionId,
      method,
      market: market.toLowerCase()
    });
    return response.data;
  } catch (error) {
    if (error.code === 'ECONNABORTED') {
      throw new Error('Step 8 initialization timed out. Please try again.');
    }
    throw error;
  }
};

// Step 8: Generate AI Suggestion for a specific category
// Now requires method and market parameters
export const generateAISuggestion = async (sessionId, category, method, market = 'international') => {
  try {
    const response = await api.post('/step-8-generate-ai-suggestion', {
      session_id: sessionId,
      category,
      method,
      market: market.toLowerCase()
    });
    return response.data;
  } catch (error) {
    if (error.code === 'ECONNABORTED') {
      throw new Error('AI suggestion generation timed out. Please try again.');
    }
    throw error;
  }
};

// Step 8: Generate Best/Worst Scenarios from Base Case
export const generateScenarios = async (sessionId, method, market = 'international', baseCase = {}) => {
  try {
    const response = await api.post('/step-8-generate-scenarios', {
      session_id: sessionId,
      method: method.toUpperCase(),
      market: market.toLowerCase(),
      base_case: baseCase
    });
    return response.data;
  } catch (error) {
    if (error.code === 'ECONNABORTED') {
      throw new Error('Scenario generation timed out. Please try again.');
    }
    throw error;
  }
};

// Step 9: Confirm Assumptions
// Now requires method and market parameters
export const confirmAssumptions = async (sessionId, confirmedValues, scenario = 'base_case', method, market = 'international') => {
  const response = await api.post('/step-9-confirm-assumptions', {
    session_id: sessionId,
    confirmed_values: confirmedValues,
    scenario,
    method,
    market: market.toLowerCase()
  });
  return response.data;
};

// Step 9: Calculate Building Block Schedules (replaces client-side dcfCalculator)
export const calculateBuildingBlocks = async (
  sessionId,
  scenario = 'base_case',
  method = 'DCF',
  market = 'international',
  assumptionOverrides = null
) => {
  const response = await api.post('/step-9-calculate-building-blocks', {
    session_id: sessionId,
    scenario,
    method: method.toUpperCase(),
    market: market.toLowerCase(),
    assumption_overrides: assumptionOverrides,
  });
  return response.data;
};

// Step 10: Run Valuation (Single Method)
// Now requires method and market parameters
export const runValuation = async (sessionId, method, scenario = 'base_case', market = 'international') => {
  const response = await api.post('/step-10-valuate', {
    session_id: sessionId,
    method,
    scenario,
    market: market.toLowerCase()
  });
  return response.data;
};

// =====================
// Complete Financial Statements (Step 8 merger)
// =====================

export const getCompleteFinancialStatements = async (sessionId, market = 'international', method = 'dcf') => {
  const response = await api.get('/complete-financial-statements', {
    params: { session_id: sessionId, market: market.toLowerCase(), method: method.toLowerCase() }
  });
  return response.data;
};

// =====================
// International Markets
// =====================

// Get list of supported international markets
export const getInternationalMarkets = async () => {
  const response = await api.get('/international/tickers');
  return response.data;
};

// Fetch international ticker data
export const fetchInternationalTicker = async (ticker, marketCode) => {
  const response = await api.get('/international/fetch', {
    params: { ticker, market_code: marketCode }
  });
  return response.data;
};

// Batch fetch international tickers
export const fetchInternationalTickersBatch = async (tickers) => {
  const response = await api.post('/international/fetch-batch', { tickers });
  return response.data;
};

// =====================
// Vietnamese Market
// =====================

// Get list of all Vietnamese stocks
export const getVietnameseStocks = async () => {
  const response = await api.get('/vietnam/tickers');
  return response.data;
};

// Search Vietnamese stocks
export const searchVietnameseStocks = async (query) => {
  const response = await api.get('/vietnam/search', {
    params: { q: query }
  });
  return response.data;
};

// Fetch Vietnamese ticker (basic)
export const fetchVietnameseTicker = async (ticker, marketCode = 'VN') => {
  const response = await api.get('/vietnam/fetch', {
    params: { ticker, market_code: marketCode }
  });
  return response.data;
};

// Fetch Vietnamese ticker (enhanced with peers, index data, etc.)
export const fetchVietnameseTickerEnhanced = async (ticker, includePeers = true, includeIndexData = true) => {
  const response = await api.get('/vietnam/fetch-enhanced', {
    params: {
      ticker,
      include_peers: includePeers,
      include_index_data: includeIndexData
    }
  });
  return response.data;
};

// Get Vietnam market overview
export const getVietnamMarketOverview = async () => {
  const response = await api.get('/vietnam/market-overview');
  return response.data;
};

// Get specific Vietnam market info (VN, HA, VC)
export const getVietnamMarketInfo = async (marketCode) => {
  const response = await api.get(`/vietnam/market-info/${marketCode}`);
  return response.data;
};

// Get stocks by sector
export const getVietnameseStocksBySector = async (sectorName) => {
  const response = await api.get(`/vietnam/sector/${sectorName}`);
  return response.data;
};

// Batch fetch Vietnamese stocks
export const fetchVietnameseTickersBatch = async (tickers) => {
  const response = await api.post('/vietnam/fetch-batch', { tickers });
  return response.data;
};

export default api;