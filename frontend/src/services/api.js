import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const searchTickers = async (query) => {
  const response = await api.get('/search', { params: { q: query } });
  return response.data;
};

export const selectCompany = async (ticker, companyName, exchange) => {
  const response = await api.post('/select-company', { ticker, companyName, exchange });
  return response.data;
};

export const getModels = async () => {
  const response = await api.get('/models');
  return response.data;
};

export const selectModel = async (modelType) => {
  const response = await api.post('/select-model', { modelType });
  return response.data;
};

export const getRequiredFields = async (modelType) => {
  const response = await api.get('/required-fields', { params: { model: modelType } });
  return response.data;
};

export const retrieveData = async (modelType, ticker) => {
  const response = await api.post('/retrieve-data', { modelType, ticker });
  return response.data;
};

export const getAISuggestions = async (field) => {
  const response = await api.get('/ai-suggestions', { params: { field } });
  return response.data;
};

export const confirmValues = async (confirmedValues, auditLog) => {
  const response = await api.post('/confirm-values', { confirmedValues, auditLog });
  return response.data;
};

export const getScenarios = async () => {
  const response = await api.get('/scenarios');
  return response.data;
};

export const selectScenario = async (scenarioType, customOverrides) => {
  const response = await api.post('/select-scenario', { scenarioType, customOverrides });
  return response.data;
};

export const runValuation = async (modelType, confirmedValues, scenario) => {
  const response = await api.post('/run-valuation', { modelType, confirmedValues, scenario });
  return response.data;
};

export const getResults = async () => {
  const response = await api.get('/results');
  return response.data;
};

export const resetState = async () => {
  const response = await api.post('/reset');
  return response.data;
};

export default api;
