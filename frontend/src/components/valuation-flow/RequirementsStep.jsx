import React from 'react';

/**
 * RequirementsStep Component
 * Step 5: Review Data Requirements BEFORE Retrieval
 *
 * Features:
 * - Model-specific data requirements display in table format
 * - Clear "Pending Retrieval" status (not "MISSING" since we haven't fetched yet)
 * - Organized by category with color-coded headers
 * - Back navigation to model selection
 * - Continue button to trigger data retrieval
 */
const RequirementsStep = ({
  selectedModel,
  onBackToModelSelection,
  onRetrieveData,
  loading,
  historicalData,
  forecastDrivers,
  peerData,
  dcfInputs,
  dupontResults,
  compsResults,
  aiData: historicalGapsData,
  aiError,
  onShowInputs,
  requiredFields = []
  // Note: valuationData prop removed - Step 5 only shows requirements before data fetch
  // Unified schema data is only available after Step 6 retrieves it
}) => {
  // FIX Issue #5: Backward compatibility layer for legacy aiData prop name
  const aiData = historicalGapsData;

  // Check if data has already been retrieved (user is re-visiting or refreshing)
  const hasRetrievedData = historicalData || peerData || dcfInputs || dupontResults || compsResults || (aiData && Object.keys(aiData).length > 0);

  // Category color mapping for better visual organization
  const getCategoryColor = (categoryName) => {
    const colorMap = {
      'historical_financials': { bg: 'bg-blue-50', border: 'border-blue-200', header: 'bg-blue-600' },
      'market_data': { bg: 'bg-purple-50', border: 'border-purple-200', header: 'bg-purple-600' },
      'balance_sheet_opening': { bg: 'bg-teal-50', border: 'border-teal-200', header: 'bg-teal-600' },
      'peer_comparables_for_wacc': { bg: 'bg-indigo-50', border: 'border-indigo-200', header: 'bg-indigo-600' },
      'forecast_drivers': { bg: 'bg-green-50', border: 'border-green-200', header: 'bg-green-600' }
    };
    return colorMap[categoryName] || { bg: 'bg-gray-50', border: 'border-gray-200', header: 'bg-gray-600' };
  };

  // Format category name for display
  const formatCategoryName = (categoryName) => {
    const nameMap = {
      'historical_financials': '📊 Historical Financials',
      'market_data': '🏛️ Market Data',
      'balance_sheet_opening': '📋 Balance Sheet (Opening)',
      'peer_comparables_for_wacc': '👥 Peer Comparables (for WACC)',
      'forecast_drivers': '🔮 Forecast Drivers'
    };
    return nameMap[categoryName] || categoryName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  // Render all required inputs in a clean table format
  const renderAllRequiredInputs = () => {
    if (!requiredFields || requiredFields.length === 0) {
      return (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading data requirements...</p>
        </div>
      );
    }

    // Group flat requiredFields array by category
    const groupedFields = requiredFields.reduce((groups, field) => {
      const categoryName = field.category || 'Other';
      if (!groups[categoryName]) {
        groups[categoryName] = [];
      }
      groups[categoryName].push(field);
      return groups;
    }, {});

    return (
      <div className="space-y-6">
        {/* Info Banner */}
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <span className="text-2xl">ℹ️</span>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">About This Step</h3>
              <p className="mt-1 text-sm text-blue-700">
                Below are all the data points that will be automatically retrieved from financial APIs (yfinance, Alpha Vantage) 
                for your <strong>{selectedModel}</strong> analysis. Click <strong>"Retrieve Data"</strong> to fetch this information.
              </p>
            </div>
          </div>
        </div>

        {Object.entries(groupedFields).map(([categoryName, fields], catIdx) => {
          const colors = getCategoryColor(categoryName);
          
          return (
            <div key={catIdx} className={`rounded-lg shadow-sm border ${colors.border} overflow-hidden`}>
              {/* Category Header */}
              <div className={`${colors.header} px-4 py-3`}>
                <h3 className="text-lg font-semibold text-white">{formatCategoryName(categoryName)}</h3>
                <p className="text-sm text-blue-100">{fields.length} data point{fields.length !== 1 ? 's' : ''} required</p>
              </div>
              
              {/* Data Table */}
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className={`${colors.bg}`}>
                    <tr>
                      <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                        Data Field
                      </th>
                      <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                        Description
                      </th>
                      <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                        API Source
                      </th>
                      <th scope="col" className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase tracking-wider">
                        Status
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-100">
                    {fields.map((field, fieldIdx) => (
                      <tr key={fieldIdx} className="hover:bg-gray-50 transition-colors">
                        {/* Field Name */}
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">{field.name || field.fieldName}</div>
                          <div className="text-xs text-gray-500">Field: {field.fieldName}</div>
                        </td>
                        
                        {/* Description */}
                        <td className="px-4 py-3">
                          <div className="text-sm text-gray-600 max-w-md">
                            {field.description || 'Required for valuation calculation'}
                          </div>
                        </td>
                        
                        {/* API Source */}
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center">
                            {field.fieldName.toLowerCase().includes('beta') || 
                             field.fieldName.toLowerCase().includes('price') ||
                             field.fieldName.toLowerCase().includes('market') ? (
                              <>
                                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                                  📈 yfinance
                                </span>
                              </>
                            ) : field.fieldName.toLowerCase().includes('peer') ? (
                              <>
                                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                                  🔍 AlphaVantage + yfinance
                                </span>
                              </>
                            ) : (
                              <>
                                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                  💰 yfinance
                                </span>
                              </>
                            )}
                          </div>
                        </td>
                        
                        {/* Status */}
                        <td className="px-4 py-3 whitespace-nowrap text-center">
                          {hasRetrievedData ? (
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              ✓ Retrieved
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                              ⏳ Pending Retrieval
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // Render AI error warning in Step 5 with detailed provider errors
  const renderAiError = () => {
    if (!aiError || !hasRetrievedData) return null;

    // Try to parse detailed error info from aiError
    let detailedErrors = null;
    let fallbackReason = null;
    try {
      // Check if aiError contains JSON string with details
      if (typeof aiError === 'string' && aiError.includes('{')) {
        const errorObj = JSON.parse(aiError);
        if (errorObj.errors) {
          detailedErrors = errorObj.errors;
        }
        if (errorObj.fallback_reason) {
          fallbackReason = errorObj.fallback_reason;
        }
      }
    } catch (e) {
      // Not a JSON string, use as is
    }

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)', border: '2px solid #ff9800', marginTop: '20px' }}>
        <h3 style={{ color: '#e65100' }}>⚠️ AI Suggestions Failed</h3>
        <p style={{ marginBottom: '12px', color: '#e65100' }}>{fallbackReason || aiError}</p>

        {/* Show detailed provider errors if available */}
        {detailedErrors && Object.keys(detailedErrors).length > 0 && (
          <div style={{ background: 'white', padding: '12px', borderRadius: '6px', marginTop: '12px', marginBottom: '12px' }}>
            <strong>🔍 Detailed Error Information:</strong>
            <div style={{ marginTop: '8px' }}>
              {Object.entries(detailedErrors).map(([provider, error]) => (
                <div key={provider} style={{
                  padding: '8px',
                  margin: '6px 0',
                  background: '#ffebee',
                  borderRadius: '4px',
                  borderLeft: '3px solid #f44336'
                }}>
                  <strong>{provider.toUpperCase()}:</strong>
                  <code style={{ display: 'block', marginTop: '4px', fontSize: '12px', color: '#c62828', wordBreak: 'break-word' }}>
                    {error}
                  </code>
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ background: 'white', padding: '12px', borderRadius: '6px', marginTop: '12px' }}>
          <strong>💡 What this means:</strong>
          <p style={{ margin: '8px 0', color: '#333' }}>
            Financial data was successfully loaded, but AI-powered suggestions could not be generated.
            You can still proceed to view the retrieved data and manually enter your assumptions.
          </p>
          <strong>📋 Next Steps:</strong>
          <ol style={{ margin: '8px 0', paddingLeft: '20px', color: '#333' }}>
            <li>Click "View Retrieved Inputs" to see the loaded financial data</li>
            <li>Manually enter your assumptions for WACC, Terminal Growth, etc.</li>
            <li>Use historical trends and peer benchmarks to inform your inputs</li>
            <li>Optionally click "Refresh Data" to retry AI generation</li>
          </ol>
        </div>
      </div>
    );
  };

  return (
    <div className="step-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2>Step 5: Review Required Inputs</h2>
          <p style={{ color: '#666', marginTop: '8px' }}>Review the data points needed for {selectedModel} analysis. Click "Retrieve Data" to fetch from financial APIs.</p>
        </div>
        <button onClick={onBackToModelSelection} className="btn-secondary">
          ← Change Model
        </button>
      </div>

      {/* Render ALL required inputs from backend - comprehensive list */}
      {renderAllRequiredInputs()}

      {/* Show AI error warning if applicable */}
      {renderAiError()}

      <div style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
        {!hasRetrievedData ? (
          <button
            onClick={onRetrieveData}
            className="btn-primary"
            disabled={loading}
          >
            {loading ? 'Retrieving Data...' : '📥 Retrieve Data'}
          </button>
        ) : (
          <>
            <button
              onClick={onRetrieveData}
              className="btn-secondary"
              disabled={loading}
            >
              {loading ? '🔄 Refreshing Data...' : '🔄 Refresh Data'}
            </button>
            <button
              onClick={onShowInputs}
              className="btn-primary"
            >
              Continue to Review Data →
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default RequirementsStep;
