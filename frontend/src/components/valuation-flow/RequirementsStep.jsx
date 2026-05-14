import React from 'react';
import DataFieldDisplay from './DataFieldDisplay';

/**
 * RequirementsStep Component
 * Step 5: Review Data Requirements & Retrieved Data
 *
 * Features:
 * - Model-specific data requirements display
 * - Historical vs forecast period breakdown
 * - Display retrieved data with success/failure status
 * - Back navigation to model selection
 * - Continue button after data retrieval
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

  // Status mapping function to convert backend statuses to frontend formats
  const mapStatus = (backendStatus) => {
    if (!backendStatus) return 'missing';
    const statusMap = {
      'RETRIEVED': 'fetched',
      'CALCULATED': 'calculated',
      'AI_GENERATED': 'ai_generated',
      'MANUAL': 'manual',
      'ESTIMATED': 'estimated',
      'MISSING': 'missing'
    };
    return statusMap[backendStatus] || 'missing';
  };

  // Group required fields by category - REMOVED: Not used anymore, using inline grouping in renderAllRequiredInputs
  // const getGroupedRequiredFields = () => {...};

  // Get data status from unified schema - REMOVED: Not used in Step 5 (only used after data fetch in later steps)
  // const getDataStatus = (categoryKey, fieldKey) => {...};

  // Render all required inputs from backend using DataFieldDisplay
  const renderAllRequiredInputs = () => {
    if (!requiredFields || requiredFields.length === 0) {
      return <div className="text-center py-8 text-gray-500">Loading requirements...</div>;
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
        {Object.entries(groupedFields).map(([categoryName, fields], catIdx) => (
          <div key={catIdx} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-800">{categoryName}</h3>
              <p className="text-sm text-gray-600">Required data points for this category</p>
            </div>
            <div className="divide-y divide-gray-100">
              {fields.map((field, fieldIdx) => {
                // At Step 5, we don't have valuationData yet - only requiredFields from prepareAssumptions
                // Use the status from requiredFields directly
                const status = field.status || 'MISSING';
                const mappedStatus = mapStatus(status);

                // Construct DataField object for consistent rendering
                const dataFieldObj = {
                  label: field.name || field.fieldName,
                  value: field.value,
                  status: status,
                  source: mappedStatus === 'fetched' ? 'yfinance' : 'manual_required',
                  confidence: mappedStatus === 'fetched' ? 0.95 : 0,
                  periods: []
                };

                return (
                  <div key={fieldIdx} className="p-4 hover:bg-gray-50 transition-colors">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900">{field.name || field.fieldName}</h4>
                        <p className="text-sm text-gray-600 mt-1">Field: {field.fieldName}</p>
                      </div>
                      <div className="ml-4 flex-shrink-0">
                        {mappedStatus === 'fetched' || mappedStatus === 'retrieved' ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            ✓ Auto-Fetched
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                            ⚠ User Input Required
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Render Data Field */}
                    <div className="mt-2">
                      {mappedStatus === 'fetched' || mappedStatus === 'retrieved' ? (
                        <DataFieldDisplay
                          data={dataFieldObj}
                          compact={true}
                        />
                      ) : (
                        <div className="text-sm text-red-600 flex items-center">
                          <span className="mr-1">⚠</span> MISSING - No data available
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    );
  };

  // Check if data has been retrieved
  const hasRetrievedData = historicalData || peerData || dcfInputs || dupontResults || compsResults || (aiData && Object.keys(aiData).length > 0);

  // Helper function to extract values from unified schema format
  // Backend returns: { historical_financials: { revenue: DataField, ebitda: DataField, ... } }
  // Extracts period values from DataField objects
  const getFieldValues = (data, fieldName) => {
    if (!data || !data.historical_financials) return {};

    const fieldData = data.historical_financials[fieldName];
    if (!fieldData) return {};

    // Handle DataField with array of period values
    if (fieldData.value && Array.isArray(fieldData.value)) {
      const result = {};
      fieldData.value.forEach(periodValue => {
        if (periodValue.period && periodValue.value !== undefined) {
          result[periodValue.period] = periodValue.value;
        }
      });
      return result;
    }

    // Handle single value case
    if (fieldData.value !== undefined) {
      return { value: fieldData.value };
    }

    return {};
  };

  // Render retrieved data summary
  const renderRetrievedData = () => {
    if (!hasRetrievedData) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)', marginTop: '20px' }}>
        <h3>✓ Retrieved Data Summary</h3>

        {/* Historical Data */}
        {historicalData && (
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ color: '#2e7d32', marginBottom: '8px' }}>Historical Financials</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
              {/* Unified schema format: historical_financials.{field}.value */}
              {(historicalData.historical_financials?.revenue || getFieldValues(historicalData, 'revenue')) && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>Revenue:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {Object.keys(historicalData.historical_financials?.revenue || getFieldValues(historicalData, 'revenue')).length} years ✓
                  </p>
                </div>
              )}
              {(historicalData.historical_financials?.ebitda || getFieldValues(historicalData, 'ebitda')) && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>EBITDA:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {Object.keys(historicalData.historical_financials?.ebitda || getFieldValues(historicalData, 'ebitda')).length} years ✓
                  </p>
                </div>
              )}
              {(historicalData.historical_financials?.net_income || getFieldValues(historicalData, 'net_income')) && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>Net Income:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {Object.keys(historicalData.historical_financials?.net_income || getFieldValues(historicalData, 'net_income')).length} years ✓
                  </p>
                </div>
              )}
              {(historicalData.historical_financials?.operating_expenses || getFieldValues(historicalData, 'operating_expenses')) && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>OpEx:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {Object.keys(historicalData.historical_financials?.operating_expenses || getFieldValues(historicalData, 'operating_expenses')).length} years ✓
                  </p>
                </div>
              )}
              {(historicalData.historical_financials?.capex || getFieldValues(historicalData, 'capex')) && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>CapEx:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {Object.keys(historicalData.historical_financials?.capex || getFieldValues(historicalData, 'capex')).length} years ✓
                  </p>
                </div>
              )}
              {(historicalData.historical_financials?.depreciation || getFieldValues(historicalData, 'depreciation')) && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>D&A:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {Object.keys(historicalData.historical_financials?.depreciation || getFieldValues(historicalData, 'depreciation')).length} years ✓
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Forecast Drivers */}
        {forecastDrivers && (
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ color: '#2e7d32', marginBottom: '8px' }}>Forecast Drivers</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
              {forecastDrivers.base_case && (
                <>
                  {forecastDrivers.base_case.sales_volume_growth && (
                    <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                      <strong>Sales Growth:</strong>
                      <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                        {forecastDrivers.base_case.sales_volume_growth.length} periods ✓
                      </p>
                    </div>
                  )}
                  {forecastDrivers.base_case.inflation_rate && (
                    <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                      <strong>Inflation:</strong>
                      <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                        {forecastDrivers.base_case.inflation_rate.length} periods ✓
                      </p>
                    </div>
                  )}
                  {forecastDrivers.base_case.opex_growth && (
                    <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                      <strong>OpEx Growth:</strong>
                      <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                        {forecastDrivers.base_case.opex_growth.length} periods ✓
                      </p>
                    </div>
                  )}
                  {forecastDrivers.base_case.capital_expenditure && (
                    <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                      <strong>CapEx:</strong>
                      <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                        {forecastDrivers.base_case.capital_expenditure.length} periods ✓
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}

        {/* Peer Data */}
        {peerData && peerData.length > 0 && (
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ color: '#2e7d32', marginBottom: '8px' }}>Peer Comparison Data</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
              <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                <strong>Peers Found:</strong>
                <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                  {peerData.companies ? peerData.companies.length : peerData.length} companies ✓
                </p>
              </div>
              {peerData.median_ev_ebitda && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>Median EV/EBITDA:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {peerData.median_ev_ebitda.toFixed(1)}x ✓
                  </p>
                </div>
              )}
              {peerData.median_pe && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>Median P/E:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {peerData.median_pe.toFixed(1)}x ✓
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* DCF Inputs */}
        {dcfInputs && (
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ color: '#2e7d32', marginBottom: '8px' }}>DCF Model Inputs</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
              {dcfInputs.wacc && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>WACC:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {(dcfInputs.wacc * 100).toFixed(2)}% ✓
                  </p>
                </div>
              )}
              {dcfInputs.terminal_growth_rate && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>Terminal Growth:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {(dcfInputs.terminal_growth_rate * 100).toFixed(2)}% ✓
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* DuPont Results */}
        {dupontResults && (
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ color: '#2e7d32', marginBottom: '8px' }}>DuPont Analysis Data</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
              <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                <strong>ROE Components:</strong>
                <p style={{ margin: '4px 0 0 0', color: '#666' }}>Ready ✓</p>
              </div>
            </div>
          </div>
        )}

        {/* Comps Results */}
        {compsResults && (
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ color: '#2e7d32', marginBottom: '8px' }}>Comps Analysis Data</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
              <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                <strong>Valuation Multiples:</strong>
                <p style={{ margin: '4px 0 0 0', color: '#666' }}>Ready ✓</p>
              </div>
            </div>
          </div>
        )}

        {/* AI Suggestions Status */}
        {aiData && Object.keys(aiData).length > 0 && (
          <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #a5d6a7' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>🤖 AI Suggestions Generated</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
              {aiData.wacc && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px', borderLeft: '4px solid #1565c0' }}>
                  <strong>WACC:</strong> {(aiData.wacc * 100).toFixed(2)}%
                </div>
              )}
              {aiData.terminal_growth && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px', borderLeft: '4px solid #1565c0' }}>
                  <strong>Terminal Growth:</strong> {(aiData.terminal_growth * 100).toFixed(2)}%
                </div>
              )}
              {aiData.revenue_growth_forecast && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px', borderLeft: '4px solid #1565c0' }}>
                  <strong>Revenue Growth:</strong> {aiData.revenue_growth_forecast.length} periods
                </div>
              )}
              {aiData.ebitda_margin_forecast && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px', borderLeft: '4px solid #1565c0' }}>
                  <strong>EBITDA Margin:</strong> {aiData.ebitda_margin_forecast.length} periods
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  // Render missing data warning
  const renderMissingData = () => {
    const missingItems = [];

    if (selectedModel === 'DCF' && !historicalData) {
      missingItems.push('Historical Financials');
    }
    if (selectedModel === 'DCF' && !forecastDrivers?.base_case) {
      missingItems.push('Forecast Drivers');
    }
    if (selectedModel === 'COMPS' && !peerData) {
      missingItems.push('Peer Comparison Data');
    }

    if (missingItems.length > 0 && hasRetrievedData) {
      return (
        <div className="summary-box" style={{ background: 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)', marginTop: '20px' }}>
          <h3 style={{ color: '#e65100' }}>⚠ Partial Data Retrieved</h3>
          <p>The following data could not be retrieved automatically and may need manual input:</p>
          <ul style={{ color: '#e65100' }}>
            {missingItems.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </div>
      );
    }
    return null;
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

      {/* Show retrieved data if available */}
      {renderRetrievedData()}

      {/* Show missing data warning if applicable */}
      {renderMissingData()}

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