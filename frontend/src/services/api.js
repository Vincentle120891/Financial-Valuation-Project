import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Add timeout configuration (60 seconds for regular calls, 120 for AI)
  timeout: 60000,
});

// Create separate instance for AI calls with longer timeout
const aiApi = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2 minutes for AI generation
});

// Step 1: Search Company
export const searchCompanies = async (query, market = 'international') => {
  const response = await api.post('/step-1-search', { query, market });
  return response.data;
};

// Step 3: Select Company
export const selectCompany = async (sessionId, ticker, market = 'international') => {
  const response = await api.post('/step-3-select-ticker', { session_id: sessionId, ticker, market });
  return response.data;
};

// Step 4: Select Models
export const selectModels = async (sessionId, model) => {
  const response = await api.post('/step-4-select-models', { session_id: sessionId, model });
  return response.data;
};

// Step 5: Prepare Inputs
export const prepareInputs = async (sessionId) => {
  const response = await api.post('/step-5-prepare-inputs', { session_id: sessionId });
  return response.data;
};

// Step 6: Fetch API Data
export const fetchApiData = async (sessionId) => {
  const response = await api.post('/step-6-fetch-api-data', { session_id: sessionId });
  return response.data;
};

// Step 7: Generate AI Assumptions (uses longer timeout)
export const generateAI = async (sessionId) => {
  try {
    const response = await aiApi.post('/step-7-generate-ai-assumptions', { session_id: sessionId });
    return response.data;
  } catch (error) {
    if (error.code === 'ECONNABORTED') {
      throw new Error('AI generation timed out. The request took too long to complete. Please try again or proceed with manual inputs.');
    }
    throw error;
  }
};

// Step 10: Confirm Assumptions
export const confirmAssumptions = async (sessionId, assumptions, scenario = 'base_case') => {
  const response = await api.post('/step-10-confirm-assumptions', { 
    session_id: sessionId, 
    assumptions, 
    scenario 
  });
  return response.data;
};

// Step 11-12: Run Valuation
export const runValuation = async (sessionId, model, scenario = 'base_case') => {
  const response = await api.post('/step-11-12-valuate', { 
    session_id: sessionId, 
    model, 
    scenario 
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
