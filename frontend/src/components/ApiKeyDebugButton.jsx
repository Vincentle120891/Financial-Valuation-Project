import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

/**
 * ApiKeyDebugButton Component
 * 
 * Floating debug button that shows a side-by-side comparison of:
 * - Browser localStorage values
 * - Backend received headers and extracted state
 * 
 * Helps diagnose API key flow issues between frontend and backend.
 */
const ApiKeyDebugButton = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [backendData, setBackendData] = useState(null);
  const [error, setError] = useState(null);

  // Get stored API keys from localStorage
  const getLocalStorageKeys = () => ({
    fmp: localStorage.getItem('fmp_api_key') || '',
    alphaVantage: localStorage.getItem('alpha_vantage_api_key') || '',
    fred: localStorage.getItem('fred_api_key') || '',
    secEdgar: localStorage.getItem('sec_edgar_email') || ''
  });

  // Fetch backend debug data
  const fetchBackendData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_BASE_URL}/debug/api-keys`, {
        headers: {
          'Content-Type': 'application/json',
        }
      });
      setBackendData(response.data.data);
    } catch (err) {
      console.error('Failed to fetch backend debug data:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to fetch debug data');
    } finally {
      setLoading(false);
    }
  };

  // Auto-fetch when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchBackendData();
    }
  }, [isOpen]);

  const localStorageKeys = getLocalStorageKeys();

  const maskKey = (key) => {
    if (!key || key.length < 8) return '****';
    return `${key.substring(0, 4)}...${key.substring(key.length - 4)}`;
  };

  const getStatusIcon = (hasValue) => {
    return hasValue ? (
      <span className="text-green-600">✅</span>
    ) : (
      <span className="text-red-500">❌</span>
    );
  };

  const renderKeyValue = (value, source) => {
    if (!value) return <span className="text-gray-400 italic">Not set</span>;
    return (
      <div>
        <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono">
          {maskKey(value)}
        </code>
        {source && (
          <span className="ml-2 text-xs text-gray-500">({source})</span>
        )}
      </div>
    );
  };

  return (
    <>
      {/* Floating Debug Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-40 inline-flex items-center gap-2 px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-full shadow-lg hover:shadow-xl transition-all cursor-pointer"
        title="Debug API Keys"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
        </svg>
        <span className="hidden sm:inline">🔍 API Keys</span>
      </button>

      {/* Debug Modal */}
      {isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full my-8">
            {/* Header */}
            <div className="p-6 border-b border-gray-200 flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold text-gray-800">API Key Debug Tool</h2>
                <p className="text-sm text-gray-600 mt-1">
                  Compare localStorage values with what the backend receives
                </p>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
              {/* Refresh Button */}
              <div className="flex justify-end">
                <button
                  onClick={fetchBackendData}
                  disabled={loading}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md transition-colors disabled:opacity-50"
                >
                  <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  {loading ? 'Refreshing...' : 'Refresh'}
                </button>
              </div>

              {/* Error Display */}
              {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
                  <strong>Error:</strong> {error}
                </div>
              )}

              {/* Loading State */}
              {loading && !backendData && (
                <div className="text-center py-8 text-gray-500">
                  Loading backend data...
                </div>
              )}

              {/* Comparison Table */}
              {backendData && (
                <div className="space-y-6">
                  {/* FMP API Key */}
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                      <h3 className="font-semibold text-gray-800">
                        🔑 Financial Modeling Prep (FMP)
                      </h3>
                      <p className="text-xs text-gray-600 mt-1">
                        Required for peer discovery, financial statements, and market data
                      </p>
                    </div>
                    <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-medium text-gray-700">📱 Browser localStorage</span>
                          {getStatusIcon(localStorageKeys.fmp)}
                        </div>
                        {renderKeyValue(localStorageKeys.fmp)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-medium text-gray-700">🖥️ Backend Received</span>
                          {getStatusIcon(backendData.received_headers['x-api-key-fmp'])}
                        </div>
                        {renderKeyValue(
                          backendData.received_headers['x-api-key-fmp'],
                          backendData.key_sources.fmp.source
                        )}
                        <div className="mt-2 text-xs text-gray-500">
                          <div>Header present: {backendData.key_sources.fmp.header_present ? '✅ Yes' : '❌ No'}</div>
                          <div>Env fallback: {backendData.key_sources.fmp.env_present ? '✅ Available' : '❌ Not set'}</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Alpha Vantage API Key */}
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                      <h3 className="font-semibold text-gray-800">
                        📊 Alpha Vantage
                      </h3>
                      <p className="text-xs text-gray-600 mt-1">
                        Required for additional market data and technical indicators
                      </p>
                    </div>
                    <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-medium text-gray-700">📱 Browser localStorage</span>
                          {getStatusIcon(localStorageKeys.alphaVantage)}
                        </div>
                        {renderKeyValue(localStorageKeys.alphaVantage)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-medium text-gray-700">🖥️ Backend Received</span>
                          {getStatusIcon(backendData.received_headers['x-api-key-alphavantage'])}
                        </div>
                        {renderKeyValue(
                          backendData.received_headers['x-api-key-alphavantage'],
                          backendData.key_sources.alpha_vantage.source
                        )}
                        <div className="mt-2 text-xs text-gray-500">
                          <div>Header present: {backendData.key_sources.alpha_vantage.header_present ? '✅ Yes' : '❌ No'}</div>
                          <div>Env fallback: {backendData.key_sources.alpha_vantage.env_present ? '✅ Available' : '❌ Not set'}</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* FRED API Key */}
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                      <h3 className="font-semibold text-gray-800">
                        🏛️ FRED API
                      </h3>
                      <p className="text-xs text-gray-600 mt-1">
                        Optional - US Treasury yields (Risk-Free Rate)
                      </p>
                    </div>
                    <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-medium text-gray-700">📱 Browser localStorage</span>
                          {getStatusIcon(localStorageKeys.fred)}
                        </div>
                        {renderKeyValue(localStorageKeys.fred)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-medium text-gray-700">🖥️ Backend Received</span>
                          {getStatusIcon(backendData.received_headers['x-api-key-fred'])}
                        </div>
                        {renderKeyValue(
                          backendData.received_headers['x-api-key-fred'],
                          backendData.key_sources.fred.source
                        )}
                        <div className="mt-2 text-xs text-gray-500">
                          <div>Header present: {backendData.key_sources.fred.header_present ? '✅ Yes' : '❌ No'}</div>
                          <div>Env fallback: {backendData.key_sources.fred.env_present ? '✅ Available' : '❌ Not set'}</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Diagnostic Section */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h3 className="font-semibold text-blue-900 mb-2">
                      🔍 Diagnostic Summary
                    </h3>
                    <p className="text-sm text-blue-800">
                      {backendData.diagnostic.message}
                    </p>
                    {backendData.diagnostic.fmp_flow_ok ? (
                      <div className="mt-2 flex items-center gap-2 text-sm text-green-700">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        FMP API key is flowing correctly
                      </div>
                    ) : (
                      <div className="mt-2 space-y-2 text-sm text-red-700">
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          <strong>Troubleshooting Steps:</strong>
                        </div>
                        <ol className="list-decimal list-inside space-y-1 ml-6">
                          <li>Ensure you've saved your FMP API key in the "Configure API Keys" modal</li>
                          <li>Check that localStorage contains 'fmp_api_key'</li>
                          <li>Verify the header name matches: <code className="bg-gray-200 px-1 rounded">X-API-Key-FMP</code></li>
                          <li>Check browser DevTools Network tab to confirm headers are being sent</li>
                          <li>Try refreshing this debug panel after saving keys</li>
                        </ol>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-6 border-t border-gray-200 bg-gray-50 rounded-b-lg">
              <p className="text-xs text-gray-500">
                💡 <strong>Tip:</strong> If the backend shows "Not set" but localStorage has a value, 
                check that the API request interceptor in <code className="bg-gray-200 px-1 rounded">api.js</code> is working correctly.
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default ApiKeyDebugButton;
