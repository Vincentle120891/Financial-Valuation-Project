/**
 * Type-Safe API Client using openapi-fetch
 * 
 * This client provides compile-time safety for all API calls:
 * - Endpoint paths are validated against OpenAPI spec
 * - Request bodies are type-checked
 * - Response types are inferred automatically
 * - No more typos in endpoint URLs or field names
 * 
 * Usage:
 * ```typescript
 * import apiClient from './client';
 * 
 * const { data, error } = await apiClient.POST('/api/step-4-discover-peers', {
 *   body: {
 *     session_id: '123',
 *     ticker: 'AAPL',
 *     market: 'international',
 *     method: 'DCF',
 *     max_peers: 10
 *   }
 * });
 * ```
 */

import createClient from 'openapi-fetch';
import type { paths } from './schema.d.ts';

// Create the type-safe client instance
const client = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Helper to get stored API keys from localStorage
const getStoredApiKeys = () => ({
  alphaVantage: localStorage.getItem('alpha_vantage_api_key') || '',
  fmp: localStorage.getItem('fmp_api_key') || '',
  fred: localStorage.getItem('fred_api_key') || '',
  secEdgar: localStorage.getItem('sec_edgar_email') || ''
});

// Helper to inject API keys into request headers
const injectApiKeys = (headers: Record<string, string> = {}) => {
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

// Enhanced client with API key injection
export const typedApiClient = {
  /**
   * GET request with type-safe response
   */
  GET: async <Path extends keyof paths>(
    path: Path,
    options?: any
  ) => {
    const enhancedOptions = {
      ...options,
      headers: injectApiKeys(options?.headers),
    };
    return client.GET(path as string, enhancedOptions);
  },

  /**
   * POST request with type-safe request/response
   */
  POST: async <Path extends keyof paths>(
    path: Path,
    options: {
      body: paths[Path]['post']['requestBody']['content']['application/json'];
      headers?: Record<string, string>;
      params?: any;
    }
  ) => {
    const enhancedOptions = {
      ...options,
      headers: injectApiKeys(options?.headers),
    };
    return client.POST(path as string, enhancedOptions);
  },

  /**
   * PUT request with type-safe request/response
   */
  PUT: async <Path extends keyof paths>(
    path: Path,
    options: {
      body: paths[Path]['put']['requestBody']['content']['application/json'];
      headers?: Record<string, string>;
      params?: any;
    }
  ) => {
    const enhancedOptions = {
      ...options,
      headers: injectApiKeys(options?.headers),
    };
    return client.PUT(path as string, enhancedOptions);
  },

  /**
   * DELETE request with type-safe response
   */
  DELETE: async <Path extends keyof paths>(
    path: Path,
    options?: any
  ) => {
    const enhancedOptions = {
      ...options,
      headers: injectApiKeys(options?.headers),
    };
    return client.DELETE(path as string, enhancedOptions);
  },
};

// Convenience methods for common valuation workflow operations
export const valuationApi = {
  // Step 1: Search Company
  searchCompany: (query: string, market: string = 'international') =>
    typedApiClient.POST('/api/step-1-search', {
      body: { query, market }
    }),

  // Step 2: Create Session
  createSession: (sessionId: string, ticker: string, market: string = 'international') =>
    typedApiClient.POST('/api/step-2-create-session', {
      body: { session_id: sessionId, ticker, market }
    }),

  // Step 3: Select Model
  selectModel: (sessionId: string, method: string, market: string = 'international') =>
    typedApiClient.POST('/api/step-3-select-models', {
      body: { session_id: sessionId, method: method.toUpperCase(), market: market.toLowerCase() }
    }),

  // Step 4: Discover Peers
  discoverPeers: (sessionId: string, ticker: string, market: string, method: string, maxPeers: number = 10) =>
    typedApiClient.POST('/api/step-4-discover-peers', {
      body: { session_id: sessionId, ticker, market, method, max_peers: maxPeers }
    }),

  // Step 4: Save Selected Peers
  savePeers: (sessionId: string, peers: string[]) =>
    typedApiClient.POST('/api/step-4-save-peers', {
      body: { session_id: sessionId, peers }
    }),

  // Step 5: Prepare Assumptions
  prepareAssumptions: (sessionId: string, method: string, market: string, generateAi: boolean = true) =>
    typedApiClient.POST('/api/step-5-prepare-assumptions', {
      body: { session_id: sessionId, method, market, generate_ai: generateAi }
    }),

  // Step 6: Fetch API Data
  fetchApiData: (sessionId: string, method: string, market: string) =>
    typedApiClient.POST('/api/step-6-fetch-api-data', {
      body: { session_id: sessionId, method, market }
    }),

  // Step 7: Retrieve Historical Data
  retrieveHistoricalData: (sessionId: string, method: string, market: string) =>
    typedApiClient.POST('/api/step-7-retrieve-historical-data', {
      body: { session_id: sessionId, method, market }
    }),

  // Step 8: Initialize Assumptions
  initializeAssumptions: (sessionId: string, method: string, market: string) =>
    typedApiClient.POST('/api/step-8-initialize', {
      body: { session_id: sessionId, method, market }
    }),

  // Step 8: Generate AI Suggestion
  generateAiSuggestion: (sessionId: string, category: string, method: string, market: string) =>
    typedApiClient.POST('/api/step-8-generate-ai-suggestion', {
      body: { session_id: sessionId, category, method, market }
    }),

  // Step 9: Confirm Assumptions
  confirmAssumptions: (sessionId: string, confirmedValues: any, scenario: string, method: string, market: string) =>
    typedApiClient.POST('/api/step-9-confirm-assumptions', {
      body: { session_id: sessionId, confirmed_values: confirmedValues, scenario, method, market }
    }),

  // Step 10: Run Valuation (Single)
  runValuation: (sessionId: string, method: string, scenario: string, market: string) =>
    typedApiClient.POST('/api/step-10-valuate', {
      body: { session_id: sessionId, method, scenario, market }
    }),

  // Step 10: Run Valuation (Multi)
  runValuationMulti: (sessionId: string, methods: string[], market: string) =>
    typedApiClient.POST('/api/step-10-valuate-multi', {
      body: { session_id: sessionId, methods, market }
    }),
};

export default typedApiClient;
