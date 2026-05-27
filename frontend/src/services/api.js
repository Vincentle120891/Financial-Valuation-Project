import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Helper to get stored API keys from localStorage
const getStoredApiKeys = () => ({
  alphaVantage: localStorage.getItem('alpha_vantage_api_key') || '',
  fmp: localStorage.getItem('fmp_api_key') || '',
  fred: localStorage.getItem('fred_api_key') || '',
  secEdgar: localStorage.getItem('sec_edgar_email') || ''
});

// Helper to inject API keys into request headers
const injectApiKeys = (headers = {}) => {
  const apiKeys = getStoredApiKeys();
  
  if (apiKeys.alphaVantage) {
    headers['X-API-Key-AlphaVantage'] = apiKeys.alphaVantage;
  }
  if (apiKeys.fmp) {
    headers['X-API-Key-FMP'] = apiKeys.fmp;
  }
  if (apiKeys.fred) {
    headers['X-API-Key-FRED'] = apiKeys.fred;
  }
  if (apiKeys.secEdgar) {
    headers['X-API-Key-SECEdgar'] = apiKeys.secEdgar;
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
    return config;
  },
  (error) => Promise.reject(error)
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
    const response = await api.post('/step-1-search', { query, market });
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
    market,
    max_peers: maxPeers,
    method: method, // Pass selected valuation method for method-specific peer criteria
    session_id: sessionId // Include session_id to store suggestions and prevent re-fetching loop
  });
  return response.data;
};

// Step 2: Select Company (Create Session)
export const selectCompany = async (sessionId, ticker, market = 'international') => {
  const response = await api.post('/step-2-create-session', { session_id: sessionId, ticker, market });
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
    market
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
    market
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
      market
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
      market
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
      market
    });
    return response.data;
  } catch (error) {
    if (error.code === 'ECONNABORTED') {
      throw new Error('AI suggestion generation timed out. Please try again.');
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
    market
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
    market
  });
  return response.data;
};

// Step 10: Run Valuation (Multiple Methods - Parallel Execution)
// NEW: Orchestrates multiple valuation methods in a single request
export const runValuationMulti = async (sessionId, methods, market = 'international') => {
  const response = await api.post('/step-10-valuate-multi', {
    session_id: sessionId,
    methods,
    market
  });
  return response.data;
};

// Get DCF Inputs with historical data
export const getDcfInputs = async (sessionId) => {
  const response = await api.post('/dcf/inputs', { session_id: sessionId });
  return response.data;
};

// Get Peer Data for Comps
export const getPeerData = async (sessionId, minPeers = 5) => {
  const response = await api.post('/comps/peers', { session_id: sessionId, min_peers: minPeers });
  return response.data;
};

// Get DuPont Analysis
export const getDupontAnalysis = async (sessionId, years = 5) => {
  const response = await api.post('/dupont/analyze', { session_id: sessionId, years });
  return response.data;
};

// Get Forecast Benchmarks
export const getForecastBenchmarks = async (sessionId) => {
  const response = await api.post('/forecast/benchmarks', { session_id: sessionId });
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