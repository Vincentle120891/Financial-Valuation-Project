import React, { useState, useRef } from 'react';

/**
 * HistoricalDataExtractionStep Component
 * Step 7: Historical Data Extraction Results (3 Valuation Methods × 2 Markets)
 *
 * CORRECTED LOGIC:
 * - Step 7 uses AI to extract HISTORICAL financial data that APIs cannot provide
 * - Displays extracted historical data gaps, sources, and completeness score
 * - NO forward-looking assumptions are generated here (that's Step 8)
 * - Works for ALL 3 valuation models (DCF, DuPont, Comps) and BOTH markets
 * - NEW: Supports PDF upload for manual document submission
 *
 * Workflow:
 * 1. Compare model requirements vs. apiData from Step 6
 * 2. Identify GAPS (missing historical inputs)
 * 3. Display gaps to user with "Generate AI Suggestions" button
 * 4. AI searches public reports/filings to fill gaps
 * 5. Show extraction results with confidence scores and sources
 * 6. NEW: Users can upload PDF reports directly for extraction
 */
const HistoricalDataExtractionStep = ({
  historicalGapsData,
  aiError,
  confirmedValues,
  selectedModel,
  market = 'international',
  historicalData,
  apiData,
  sessionId,
  onManualInput,
  onUseAI,
  onBackToApiData,
  onContinueToForecastDrivers,
  onRetryAiExtraction,
  loading
}) => {
  // FIX Issue #5: Backward compatibility layer for legacy aiData prop name
  const data = historicalGapsData || aiData;
  
  // PDF Upload state
  const [uploadingPdf, setUploadingPdf] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);

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

  // PDF Upload handler
  const handlePdfUpload = async (event) => {
    const file = event.target.files[0];
    if (!file || !sessionId) return;

    setUploadingPdf(true);
    setUploadError(null);
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('session_id', sessionId);
      formData.append('method', selectedModel || 'DCF');
      formData.append('market', market);

      const response = await fetch('/api/step-7-upload-pdf', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const result = await response.json();
      setUploadResult(result);
      
      // Notify parent component of successful upload
      if (onRetryAiExtraction) {
        // Trigger a refresh of the historical data
        onRetryAiExtraction();
      }
    } catch (error) {
      setUploadError(error.message);
    } finally {
      setUploadingPdf(false);
    }
  };

  // Trigger file input click
  const triggerFileUpload = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
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
    // Check if we have historical gaps filled data (using renamed 'data' variable)
    const hasGaps = data && data.historical_gaps_filled && data.historical_gaps_filled.length > 0;
    const completeness = data?.data_completeness_score || 1.0;
    const sourcesUsed = data?.sources_used || [];
    const totalGapsFound = data?.total_gaps_found || 0;
    const totalGapsFilled = data?.total_gaps_filled || 0;

    // No gaps case - all data retrieved successfully
    if (!hasGaps && completeness === 1.0) {
      return renderNoGapsMessage();
    }

    // Gaps exist - show extraction results
    const gaps = data?.historical_gaps_filled || [];

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
        {data?.extraction_methodology && (
          <div style={{ background: '#f5f5f5', padding: '16px', borderRadius: '8px', marginBottom: '20px', border: '1px solid #ddd' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#333' }}>🔍 Extraction Methodology</h4>
            <p style={{ margin: 0, fontSize: '14px', lineHeight: '1.6', color: '#555' }}>{data.extraction_methodology}</p>
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

      {/* Options Banner - Clear guidance for users */}
      <div style={{
        marginBottom: '20px',
        padding: '20px',
        borderRadius: '8px',
        background: 'linear-gradient(135deg, #f0f4ff 0%, #e8eaf6 100%)',
        border: '2px solid #7986cb'
      }}>
        <h3 style={{ color: '#3949ab', margin: '0 0 16px 0', fontSize: '18px' }}>
          🎯 How to Retrieve Historical Data
        </h3>
        <p style={{ margin: '0 0 16px 0', color: '#5c6bc0', fontSize: '14px', lineHeight: '1.6' }}>
          To ensure accurate valuation, you need precise historical financial data. 
          Since automatic API data can be incomplete, please choose one of these options:
        </p>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
          {/* Option 1 */}
          <div style={{
            background: 'white',
            padding: '16px',
            borderRadius: '6px',
            border: '2px solid #9c27b0'
          }}>
            <h4 style={{ color: '#7b1fa2', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '20px' }}>📤</span> Option 1: Upload PDF Reports
            </h4>
            <p style={{ margin: '0 0 12px 0', fontSize: '13px', color: '#666', lineHeight: '1.5' }}>
              Upload the company's annual reports (10-K, Annual Report, or Financial Statements). 
              Our AI will automatically extract and normalize the data.
            </p>
            <ul style={{ margin: '0', paddingLeft: '20px', fontSize: '12px', color: '#757575', lineHeight: '1.8' }}>
              <li><strong>Best for:</strong> Precise line items (NWC, CapEx, D&A)</li>
              <li><strong>Formats:</strong> PDF only</li>
              <li><strong>Standards:</strong> US GAAP, IFRS, Vietnamese</li>
            </ul>
          </div>

          {/* Option 2 */}
          <div style={{
            background: 'white',
            padding: '16px',
            borderRadius: '6px',
            border: '2px solid #2196f3'
          }}>
            <h4 style={{ color: '#1976d2', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '20px' }}>🤖</span> Option 2: Use External AI Tools
            </h4>
            <p style={{ margin: '0 0 12px 0', fontSize: '13px', color: '#666', lineHeight: '1.5' }}>
              Use AI tools like ChatGPT, Claude, or Perplexity to search and extract historical data online.
              Then manually input the metrics in Step 8.
            </p>
            <ul style={{ margin: '0', paddingLeft: '20px', fontSize: '12px', color: '#757575', lineHeight: '1.8' }}>
              <li><strong>Prompt:</strong> "Extract 5-year revenue, net income, EBITDA for [TICKER]"</li>
              <li><strong>Best for:</strong> Quick estimates when PDFs unavailable</li>
              <li><strong>Tip:</strong> Cross-verify with multiple sources</li>
            </ul>
          </div>
        </div>

        {/* Important Note */}
        <div style={{
          marginTop: '16px',
          padding: '12px',
          background: '#fff8e1',
          border: '1px solid #ffc107',
          borderRadius: '6px',
          fontSize: '13px',
          color: '#f57f17'
        }}>
          <strong>⚠️ Note:</strong> Automatic document fetching is currently disabled. For the most accurate results, 
          we strongly recommend uploading official PDF reports using Option 1 above.
        </div>
      </div>

      {renderAiError()}

      {/* PDF Upload Section */}
      <div style={{ 
        background: 'linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%)', 
        border: '2px solid #9c27b0', 
        padding: '20px', 
        borderRadius: '8px', 
        marginBottom: '20px' 
      }}>
        <h3 style={{ color: '#7b1fa2', margin: '0 0 12px 0' }}>📄 Upload Financial Report (PDF)</h3>
        <p style={{ margin: '0 0 16px 0', color: '#4a148c', fontSize: '14px' }}>
          Upload annual reports, 10-K filings, or financial statements to extract missing historical data.
          AI will automatically extract key metrics and fill gaps in your valuation model.
        </p>
        
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handlePdfUpload}
          style={{ display: 'none' }}
        />
        
        {/* Upload button and status */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button
            onClick={triggerFileUpload}
            disabled={uploadingPdf || loading}
            className="btn-secondary"
            style={{ 
              background: uploadingPdf ? '#e0e0e0' : '#9c27b0', 
              color: 'white',
              border: 'none'
            }}
          >
            {uploadingPdf ? '⏳ Uploading & Extracting...' : '📎 Upload PDF Report'}
          </button>
          
          {uploadResult && (
            <span style={{ color: '#2e7d32', fontWeight: 600 }}>
              ✓ Extracted {Object.keys(uploadResult.extracted_metrics || {}).length} metrics from {uploadResult.fiscal_year}
            </span>
          )}
        </div>
        
        {/* Upload error */}
        {uploadError && (
          <div style={{ 
            marginTop: '12px', 
            padding: '12px', 
            background: '#ffebee', 
            border: '1px solid #ef5350', 
            borderRadius: '6px',
            color: '#c62828'
          }}>
            ❌ Upload failed: {uploadError}
          </div>
        )}
        
        {/* Upload success details */}
        {uploadResult && uploadResult.extracted_metrics && (
          <div style={{ 
            marginTop: '16px', 
            padding: '12px', 
            background: 'white', 
            borderRadius: '6px',
            border: '1px solid #a5d6a7'
          }}>
            <strong style={{ color: '#1b5e20' }}>Extracted Metrics:</strong>
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', 
              gap: '8px', 
              marginTop: '8px' 
            }}>
              {Object.entries(uploadResult.extracted_metrics).map(([key, value]) => (
                <div key={key} style={{ 
                  padding: '8px', 
                  background: '#e8f5e9', 
                  borderRadius: '4px',
                  fontSize: '13px'
                }}>
                  <strong>{key}:</strong> {typeof value === 'number' ? value.toLocaleString() : value}
                </div>
              ))}
            </div>
            {uploadResult.confidence_score && (
              <p style={{ marginTop: '8px', fontSize: '13px', color: '#666' }}>
                <strong>Confidence:</strong> {(uploadResult.confidence_score * 100).toFixed(0)}% | 
                <strong> Method:</strong> {uploadResult.extraction_method}
              </p>
            )}
          </div>
        )}
      </div>

      {/* PRIMARY DISPLAY: Historical Data Gaps (works for all 3×2 matrix) */}
      {renderHistoricalDataGaps()}

      {/* No data extracted warning */}
      {(!data || Object.keys(data).length === 0) && !aiError && (
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

export default HistoricalDataExtractionStep;