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

export default api;
