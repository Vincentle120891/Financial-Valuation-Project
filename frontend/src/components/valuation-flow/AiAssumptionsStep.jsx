import React from 'react';

/**
 * AiAssumptionsStep Component
 * Step 7: Historical Data Extraction Results (3 Valuation Methods × 2 Markets)
 *
 * CORRECTED LOGIC:
 * - Step 7 uses AI to extract HISTORICAL financial data that APIs cannot provide
 * - Displays extracted historical data gaps, sources, and completeness score
 * - NO forward-looking assumptions are generated here (that's Step 8)
 * - Works for ALL 3 valuation models (DCF, DuPont, Comps) and BOTH markets
 *
 * Workflow:
 * 1. Compare model requirements vs. apiData from Step 6
 * 2. Identify GAPS (missing historical inputs)
 * 3. Display gaps to user with "Generate AI Suggestions" button
 * 4. AI searches public reports/filings to fill gaps
 * 5. Show extraction results with confidence scores and sources
 */
const AiAssumptionsStep = ({
  aiData,
  aiError,
  confirmedValues,
  selectedModel,
  market = 'international',
  historicalData,
  apiData,
  onManualInput,
  onUseAI,
  onBackToApiData,
  onContinueToForecastDrivers,
  onRetryAiExtraction,
  loading
}) => {
  // Handle using AI suggestion for historical data
  const handleUseAiSuggestion = (field, value) => {
    if (onUseAI) {
      onUseAI(field, value);
    }
  };

  // Handle manual input for historical data
  const handleManualInputChange = (field, value) => {
    if (onManualInput) {
      onManualInput(field, value);
    }
  };

  // Render AI error/warning message for historical data extraction
  const renderAiError = () => {
    if (!aiError) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)', border: '2px solid #ff9800', marginBottom: '20px' }}>
        <h3 style={{ color: '#e65100' }}>⚠️ Historical Data Extraction Issue</h3>
        <p style={{ marginBottom: '12px', color: '#e65100' }}>{aiError}</p>
        <div style={{ background: 'white', padding: '12px', borderRadius: '6px', marginTop: '12px' }}>
          <strong>💡 What this means:</strong>
          <p style={{ margin: '8px 0', color: '#333' }}>
            AI-powered historical data extraction encountered an issue. You can still proceed with the available API data.
          </p>
          <strong>📋 Next Steps:</strong>
          <ol style={{ margin: '8px 0', paddingLeft: '20px', color: '#333' }}>
            <li>Review the extracted historical data below</li>
            <li>Click "Retry AI Extraction" to attempt again</li>
            <li>Proceed to Step 8 for assumption generation</li>
          </ol>
        </div>
      </div>
    );
  };

  // Render "No Historical Gaps" message when all data is complete
  const renderNoGapsMessage = () => {
    const modelText = selectedModel === 'DCF'
      ? 'DCF requires 5 years of historical income statement, balance sheet, and cash flow data.'
      : selectedModel === 'DuPont'
        ? 'DuPont Analysis requires 5 years of Net Income, Revenue, Assets, and Equity.'
        : 'Trading Comps requires current peer company multiples and financial metrics.';

    return (
      <div style={{ background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)', border: '2px solid #4caf50', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
        <h3 style={{ color: '#2e7d32', margin: '0 0 12px 0' }}>✅ All Historical Data Retrieved</h3>
        <p style={{ margin: '0 0 12px 0', color: '#1b5e20', lineHeight: '1.6' }}>
          API data retrieval was 100% successful. No AI extraction was needed for the {selectedModel} model.
        </p>
        <div style={{ background: 'white', padding: '12px', borderRadius: '6px', marginTop: '12px' }}>
          <strong>📊 Data Requirements Met:</strong>
          <p style={{ margin: '8px 0', color: '#333', fontSize: '14px' }}>{modelText}</p>
          <strong>✓ Next Step:</strong>
          <p style={{ margin: '8px 0 0 0', color: '#333', fontSize: '14px' }}>
            Proceed to Step 8 to generate forward-looking assumptions (DCF) or run calculations directly (DuPont/Comps).
          </p>
        </div>
      </div>
    );
  };

  // Render historical data gaps table - PRIMARY DISPLAY for Step 7
  const renderHistoricalDataGaps = () => {
    // Check if we have historical gaps filled data
    const hasGaps = aiData && aiData.historical_gaps_filled && aiData.historical_gaps_filled.length > 0;
    const completeness = aiData?.data_completeness_score || 1.0;
    const sourcesUsed = aiData?.sources_used || [];
    const totalGapsFound = aiData?.total_gaps_found || 0;
    const totalGapsFilled = aiData?.total_gaps_filled || 0;

    // No gaps case - all data retrieved successfully
    if (!hasGaps && completeness === 1.0) {
      return renderNoGapsMessage();
    }

    // Gaps exist - show extraction results
    const gaps = aiData?.historical_gaps_filled || [];

    return (
      <>
        {/* Completeness Summary */}
        <div style={{
          background: completeness >= 0.8
            ? 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)'
            : 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)',
          border: completeness >= 0.8 ? '2px solid #4caf50' : '2px solid #ff9800',
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <h3 style={{ color: completeness >= 0.8 ? '#2e7d32' : '#e65100', margin: '0 0 12px 0' }}>
            {completeness >= 0.8 ? '✅ Historical Data Extraction Complete' : '⚠️ Partial Historical Data Extraction'}
          </h3>
          <p style={{ margin: '0 0 12px 0', color: completeness >= 0.8 ? '#1b5e20' : '#e65100', lineHeight: '1.6' }}>
            <strong>Completeness Score:</strong> {(completeness * 100).toFixed(0)}% |
            <strong> Gaps Filled:</strong> {totalGapsFilled} / {totalGapsFound}
          </p>
          {sourcesUsed.length > 0 && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px', marginTop: '12px' }}>
              <strong>📚 Sources Used:</strong>
              <ul style={{ margin: '8px 0', paddingLeft: '20px', color: '#333', fontSize: '14px' }}>
                {sourcesUsed.map((source, idx) => (
                  <li key={idx}>{source}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Historical Data Gaps Table */}
        {gaps.length > 0 && (
          <div style={{ background: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px', border: '1px solid #ddd' }}>
            <h3 style={{ color: '#1976d2', margin: '0 0 16px 0' }}>📊 Extracted Historical Data</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
              <thead>
                <tr style={{ background: '#f5f5f5', borderBottom: '2px solid #ddd' }}>
                  <th style={{ padding: '12px', textAlign: 'left', color: '#333' }}>Metric</th>
                  <th style={{ padding: '12px', textAlign: 'center', color: '#333' }}>Fiscal Year</th>
                  <th style={{ padding: '12px', textAlign: 'right', color: '#333' }}>Extracted Value</th>
                  <th style={{ padding: '12px', textAlign: 'left', color: '#333' }}>Source</th>
                  <th style={{ padding: '12px', textAlign: 'center', color: '#333' }}>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {gaps.map((gap, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '12px', color: '#333', fontWeight: 500 }}>{gap.metric}</td>
                    <td style={{ padding: '12px', textAlign: 'center', color: '#666' }}>{gap.fiscal_year}</td>
                    <td style={{ padding: '12px', textAlign: 'right', color: '#1976d2', fontWeight: 600 }}>
                      {gap.extracted_value !== null ? gap.extracted_value.toLocaleString() : 'N/A'}
                    </td>
                    <td style={{ padding: '12px', color: '#666', fontSize: '13px' }}>{gap.data_source}</td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      <span style={{
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        background: gap.confidence_score >= 0.8 ? '#e8f5e9' : gap.confidence_score >= 0.6 ? '#fff3e0' : '#ffebee',
                        color: gap.confidence_score >= 0.8 ? '#2e7d32' : gap.confidence_score >= 0.6 ? '#e65100' : '#c62828',
                        fontWeight: 600
                      }}>
                        {(gap.confidence_score * 100).toFixed(0)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Extraction Methodology */}
        {aiData?.extraction_methodology && (
          <div style={{ background: '#f5f5f5', padding: '16px', borderRadius: '8px', marginBottom: '20px', border: '1px solid #ddd' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#333' }}>🔍 Extraction Methodology</h4>
            <p style={{ margin: 0, fontSize: '14px', lineHeight: '1.6', color: '#555' }}>{aiData.extraction_methodology}</p>
          </div>
        )}

        {/* Retry Button */}
        {completeness < 1.0 && onRetryAiExtraction && (
          <button
            onClick={onRetryAiExtraction}
            className="btn-secondary"
            disabled={loading}
            style={{ marginTop: '10px' }}
          >
            🔄 Retry AI Extraction
          </button>
        )}
      </>
    );
  };

  // Determine rendering based on model type and market
  // ALL models use this step for historical gap filling
  const isVietnamMarket = market === 'vietnamese' || market === 'Vietnam';

  return (
    <div className="step-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2>Step 7: Historical Data Extraction Results</h2>
          <p style={{ color: '#666', marginTop: '8px' }}>
            Review AI-extracted historical financial data that APIs could not retrieve.
            AI searched public filings, annual reports, and financial statements to fill data gaps.
          </p>
        </div>
        <button onClick={onBackToApiData} className="btn-secondary" disabled={loading}>
          ← Back to API Data
        </button>
      </div>

      {/* Model-specific info banner */}
      <div style={{
        marginBottom: '20px',
        padding: '16px',
        borderRadius: '8px',
        background: isVietnamMarket
          ? 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)'
          : 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)',
        border: isVietnamMarket
          ? '2px solid #ff9800'
          : '2px solid #2196f3'
      }}>
        <p style={{ margin: 0, color: isVietnamMarket ? '#e65100' : '#1565c0' }}>
          <strong>📋 What happened:</strong> Step 6 retrieved data from APIs. This step shows any missing historical data that AI extracted from public documents.
          {selectedModel === 'DCF' && ' DCF requires 5 years of historical financials for accurate projections.'}
          {selectedModel === 'DuPont' && ' DuPont Analysis needs 5 years of balance sheet and income statement data.'}
          {selectedModel === 'COMPS' && ' Trading Comps requires current peer multiples and financial metrics.'}
        </p>
      </div>

      {renderAiError()}

      {/* PRIMARY DISPLAY: Historical Data Gaps (works for all 3×2 matrix) */}
      {renderHistoricalDataGaps()}

      {/* No data extracted warning */}
      {(!aiData || Object.keys(aiData).length === 0) && !aiError && (
        <div className="summary-box" style={{ background: 'linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%)', marginBottom: '20px' }}>
          <h3>⚠️ No AI Extraction Performed</h3>
          <p>AI extraction has not been triggered yet. Click the button below to search for missing historical data.</p>
          {onRetryAiExtraction && (
            <button
              onClick={onRetryAiExtraction}
              className="btn-primary"
              disabled={loading}
              style={{ marginTop: '10px' }}
            >
              🔍 Generate AI Suggestions
            </button>
          )}
        </div>
      )}

      <div style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
        <button
          onClick={onContinueToForecastDrivers}
          className="btn-primary"
          disabled={loading}
        >
          Continue to Step 8: Forecast Drivers →
        </button>
      </div>
    </div>
  );
};

export default AiAssumptionsStep;