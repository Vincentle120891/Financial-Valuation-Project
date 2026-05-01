import React from 'react';
import { 
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, 
  Tooltip, Legend, ResponsiveContainer, AreaChart, Area, 
  ComposedChart, Scatter 
} from 'recharts';

/**
 * AssumptionsStep Component
 * Step 9: Review & Confirm Assumptions (Final confirmation before running valuation)
 * 
 * Features:
 * - Historical trends visualization
 * - Peer benchmarking summary
 * - AI suggestions with rationale
 * - Manual input override
 * - Interactive charts (Revenue, EBITDA, Growth)
 * - Health check and error validation
 * - Final confirmation of all assumptions
 * 
 * Props:
 * - onConfirmAssumptions: function - Callback to confirm and proceed to Run Valuation
 * - onBackToRequirements: function - Callback to go back to requirements step
 */
const AssumptionsStep = ({
  historicalData,
  peerData,
  aiData,
  aiError,
  confirmedValues,
  selectedModel,
  onManualInput,
  onUseAI,
  onConfirmAssumptions,
  loading,
  showReviewOnly = false,
  onContinueToForecastDrivers,
  onBackToRequirements
}) => {
  // ==================== HEALTH CHECK & ERROR VALIDATION ====================
  
  // Validate data integrity
  const validateDataHealth = () => {
    const issues = [];
    
    // Check historical data
    if (!historicalData) {
      issues.push({
        type: 'error',
        field: 'Historical Data',
        message: 'No historical financial data available'
      });
    } else {
      if (!historicalData.revenue || Object.keys(historicalData.revenue).length === 0) {
        issues.push({
          type: 'warning',
          field: 'Revenue',
          message: 'Revenue data is missing or empty'
        });
      }
      if (!historicalData.ebitda || Object.keys(historicalData.ebitda).length === 0) {
        issues.push({
          type: 'warning',
          field: 'EBITDA',
          message: 'EBITDA data is missing or empty'
        });
      }
    }
    
    // Check peer data
    if (!peerData || (Array.isArray(peerData) && peerData.length === 0)) {
      issues.push({
        type: 'warning',
        field: 'Peer Data',
        message: 'No peer comparison data available'
      });
    }
    
    // Check AI data for DCF model
    if (selectedModel === 'DCF' && (!aiData || Object.keys(aiData).length === 0)) {
      issues.push({
        type: 'error',
        field: 'AI Suggestions',
        message: 'AI suggestions not generated. Please retrieve data first.'
      });
    } else if (aiData && Object.keys(aiData).length > 0) {
      // Validate critical AI fields
      if (!aiData.wacc_percent?.value && !aiData.wacc) {
        issues.push({
          type: 'warning',
          field: 'WACC',
          message: 'WACC suggestion is missing'
        });
      }
      if (!aiData.terminal_growth_rate_percent?.value && !aiData.terminal_growth) {
        issues.push({
          type: 'warning',
          field: 'Terminal Growth',
          message: 'Terminal growth suggestion is missing'
        });
      }
    }
    
    return issues;
  };
  
  const dataHealthIssues = validateDataHealth();
  const hasCriticalErrors = dataHealthIssues.some(issue => issue.type === 'error');
  const hasWarnings = dataHealthIssues.some(issue => issue.type === 'warning');
  const hasAnyData = historicalData || (peerData && peerData.length > 0) || (aiData && Object.keys(aiData).length > 0);
  // Prepare historical chart data
  const prepareHistoricalChartData = () => {
    if (!historicalData?.revenue) return [];
    return Object.keys(historicalData.revenue).map(year => ({
      year,
      revenue: historicalData.revenue[year],
      ebitda: historicalData.ebitda?.[year] || 0
    }));
  };

  // Prepare forecast comparison data
  const prepareForecastComparisonData = () => {
    if (!aiData?.revenue_growth_forecast || !historicalData?.revenue) return [];
    const lastYearRevenue = Object.values(historicalData.revenue).pop() || 0;
    return aiData.revenue_growth_forecast.map((growth, idx) => {
      const projectedRevenue = lastYearRevenue * Math.pow(1 + growth, idx + 1);
      return {
        period: `Period ${idx + 1}`,
        growthRate: (growth * 100).toFixed(1),
        projectedRevenue: Math.round(projectedRevenue),
        formattedRevenue: `$${(projectedRevenue / 1000).toFixed(1)}B`
      };
    });
  };

  // Prepare EBITDA trend data
  const prepareEbitdaTrendData = () => {
    const data = [];
    
    // Add historical EBITDA margins
    if (historicalData?.ebitda_margin) {
      Object.entries(historicalData.ebitda_margin).forEach(([year, margin]) => {
        data.push({
          period: year,
          margin: (margin * 100).toFixed(1),
          isHistorical: true
        });
      });
    }
    
    // Add forecast EBITDA margins
    if (aiData?.ebitda_margin_forecast) {
      aiData.ebitda_margin_forecast.forEach((margin, idx) => {
        data.push({
          period: `F${idx + 1}`,
          margin: (margin * 100).toFixed(1),
          isHistorical: false
        });
      });
    }
    
    return data;
  };

  const historicalChartData = prepareHistoricalChartData();
  const forecastComparisonData = prepareForecastComparisonData();
  const ebitdaTrendData = prepareEbitdaTrendData();

  return (
    <div className="step-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>{showReviewOnly ? 'Step 6: View Retrieved Inputs' : 'Step 8: Review & Confirm Assumptions'}</h2>
        {onBackToRequirements && (
          <button onClick={onBackToRequirements} className="btn-secondary">
            ← Back to Requirements
          </button>
        )}
      </div>
      
      {/* ==================== HEALTH CHECK DISPLAY ==================== */}
      {!hasAnyData && (
        <div className="summary-box" style={{ background: 'linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%)', border: '2px solid #f44336' }}>
          <h3 style={{ color: '#c62828' }}>🚨 Critical: No Data Loaded</h3>
          <p style={{ marginBottom: '16px' }}>The system has not retrieved any data yet. Please follow these steps:</p>
          <ol style={{ color: '#c62828', lineHeight: '1.8' }}>
            <li>Click "Back to Requirements" button above</li>
            <li>Click "Retrieve Data" in Step 5</li>
            <li>Wait for data to load successfully</li>
            <li>Click "View Retrieved Inputs" to return here</li>
          </ol>
          {onBackToRequirements && (
            <button onClick={onBackToRequirements} className="btn-primary" style={{ marginTop: '16px' }}>
              Go to Step 5 →
            </button>
          )}
        </div>
      )}
      
      {/* AI Error Display - Show when financial data exists but AI failed */}
      {hasAnyData && aiError && (
        <div className="summary-box" style={{ background: 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)', border: '2px solid #ff9800' }}>
          <h3 style={{ color: '#e65100' }}>⚠️ AI Suggestions Unavailable</h3>
          <p style={{ marginBottom: '12px', color: '#e65100' }}>{aiError}</p>
          <div style={{ background: 'white', padding: '16px', borderRadius: '6px', marginTop: '12px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>📋 Next Steps:</h4>
            <ol style={{ color: '#333', lineHeight: '1.8', marginLeft: '20px' }}>
              <li><strong>Review Retrieved Data:</strong> Scroll down to view the historical financials and peer data that were successfully loaded.</li>
              <li><strong>Manual Input:</strong> Use the input fields below to manually enter your assumptions for WACC, Terminal Growth, and other forecast parameters.</li>
              <li><strong>Use Historical Trends:</strong> Refer to the historical charts and peer benchmarks shown below to inform your manual inputs.</li>
              <li><strong>Retry AI (Optional):</strong> Go back to Step 5 and click "Refresh Data" to attempt AI generation again.</li>
            </ol>
          </div>
          {!showReviewOnly && onBackToRequirements && (
            <button onClick={onBackToRequirements} className="btn-secondary" style={{ marginTop: '16px' }}>
              ← Back to Step 5 to Refresh Data
            </button>
          )}
        </div>
      )}
      
      {/* Health Issues Summary */}
      {hasAnyData && dataHealthIssues.length > 0 && (
        <div className="summary-box" style={{ 
          background: hasCriticalErrors 
            ? 'linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%)' 
            : 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)',
          border: hasCriticalErrors ? '2px solid #f44336' : '2px solid #ff9800'
        }}>
          <h3 style={{ color: hasCriticalErrors ? '#c62828' : '#e65100' }}>
            {hasCriticalErrors ? '🚨 Data Integrity Issues Detected' : '⚠ Data Quality Warnings'}
          </h3>
          <p style={{ marginBottom: '12px' }}>
            {hasCriticalErrors 
              ? 'Critical issues must be resolved before proceeding. Please go back and retrieve data again.' 
              : 'Some data fields are missing or incomplete. You may proceed with caution.'}
          </p>
          <ul style={{ marginBottom: '16px' }}>
            {dataHealthIssues.map((issue, idx) => (
              <li key={idx} style={{ 
                color: issue.type === 'error' ? '#c62828' : '#e65100',
                marginBottom: '6px'
              }}>
                <strong>{issue.field}:</strong> {issue.message}
              </li>
            ))}
          </ul>
          {hasCriticalErrors && onBackToRequirements && (
            <button onClick={onBackToRequirements} className="btn-primary">
              Go Back to Fix Issues →
            </button>
          )}
        </div>
      )}
      
      {/* Benchmark Summary */}
      {historicalData && (
        <div className="summary-box">
          <h3>Historical Trends (Last 3 Years)</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
            <div>
              <strong>Revenue CAGR:</strong>
              <p>{historicalData.revenue_cagr ? (historicalData.revenue_cagr * 100).toFixed(1) + '%' : 'N/A'}</p>
            </div>
            <div>
              <strong>Avg EBITDA Margin:</strong>
              <p>{historicalData.avg_ebitda_margin ? (historicalData.avg_ebitda_margin * 100).toFixed(1) + '%' : 'N/A'}</p>
            </div>
            <div>
              <strong>Avg ROE:</strong>
              <p>{historicalData.avg_roe ? (historicalData.avg_roe * 100).toFixed(1) + '%' : 'N/A'}</p>
            </div>
          </div>
          
          {/* Historical Revenue Chart */}
          {historicalChartData.length > 0 && (
            <div style={{ marginTop: '24px' }}>
              <h4 style={{ marginBottom: '12px', color: '#333' }}>Revenue Trend</h4>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={historicalChartData}>
                  <defs>
                    <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#667eea" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#667eea" stopOpacity={0.1}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                  <XAxis dataKey="year" stroke="#666" />
                  <YAxis stroke="#666" tickFormatter={(value) => `$${(value/1000).toFixed(0)}B`} />
                  <Tooltip 
                    formatter={(value) => [`$${(value/1000).toFixed(1)}B`, 'Revenue']}
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                  />
                  <Area type="monotone" dataKey="revenue" stroke="#667eea" fillOpacity={1} fill="url(#colorRevenue)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
      
      {/* Peer Benchmarking */}
      {peerData && Array.isArray(peerData) && peerData.length > 0 && (
        <div className="summary-box">
          <h3>Peer Benchmarking</h3>
          <p><strong>Peers Analyzed:</strong> {peerData.length} companies</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginTop: '12px' }}>
            <div>
              <strong>Median EV/EBITDA:</strong>
              <p>{peerData[0]?.ev_ebitda_ltm ? peerData[0].ev_ebitda_ltm.toFixed(1) + 'x' : 'N/A'}</p>
            </div>
            <div>
              <strong>Median P/E:</strong>
              <p>{peerData[0]?.pe_ltm ? peerData[0].pe_ltm.toFixed(1) + 'x' : 'N/A'}</p>
            </div>
            <div>
              <strong>Peer Count:</strong>
              <p>{peerData.length}</p>
            </div>
          </div>
        </div>
      )}
      
      {/* AI Suggestions Table */}
      {aiData && Object.keys(aiData).length > 0 && (
        <div className="summary-box" style={{ 
          background: aiData._metadata?.used_fallback 
            ? 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)' 
            : 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ color: '#667eea' }}>
              {aiData._metadata?.used_fallback ? '⚠️ AI Fallback Mode - Deterministic Assumptions' : '🤖 AI Suggestions with Rationale'}
            </h3>
            {aiData._metadata && (
              <span style={{ fontSize: '12px', padding: '4px 8px', background: aiData._metadata.used_fallback ? '#ff9800' : '#4caf50', color: 'white', borderRadius: '4px' }}>
                {aiData._metadata.used_fallback ? 'Fallback Used' : 'AI Generated'}
              </span>
            )}
          </div>
          <p style={{ marginBottom: '20px', color: '#666' }}>
            {aiData._metadata?.used_fallback 
              ? 'AI providers were unavailable. Using deterministic fallback rules based on CAPM formula and historical averages. You can still manually adjust these assumptions.'
              : 'AI analyzes historical trends, peer benchmarks, and market conditions to provide data-driven recommendations'
            }
          </p>
          {aiData._metadata?.provider_status && (
            <div style={{ marginBottom: '16px', padding: '12px', background: 'rgba(255,255,255,0.5)', borderRadius: '6px', fontSize: '13px' }}>
              <strong>Provider Status:</strong>{' '}
              {Object.entries(aiData._metadata.provider_status).map(([provider, status]) => (
                <span key={provider} style={{ 
                  marginRight: '12px', 
                  color: status === 'configured' ? '#4caf50' : '#f44336' 
                }}>
                  {provider.toUpperCase()}: {status === 'configured' ? '✓' : '✗'}
                </span>
              ))}
            </div>
          )}
          
          <table className="assumptions-table">
            <thead>
              <tr>
                <th>Field</th>
                <th>AI Suggestion</th>
                <th>Rationale & Sources</th>
                <th>Your Input</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {/* DCF Fields */}
              {(selectedModel === 'DCF' || !selectedModel) && (
                <>
                  <tr>
                    <td>WACC</td>
                    <td>{aiData.wacc_percent ? (aiData.wacc_percent.value / 100).toFixed(2) + '%' : aiData.wacc ? (aiData.wacc * 100).toFixed(2) + '%' : 'N/A'}</td>
                    <td className="rationale-cell">
                      {aiData.wacc_percent?.rationale ? (
                        <div className="rationale-content">
                          <p><strong>Why:</strong> {aiData.wacc_percent.rationale}</p>
                          <p><strong>Sources:</strong> {aiData.wacc_percent.sources || 'CAPM Formula'}</p>
                        </div>
                      ) : aiData.wacc_rationale ? (
                        <div className="rationale-content">
                          <p><strong>Why:</strong> {aiData.wacc_rationale}</p>
                          <p><strong>Sources:</strong> {aiData.wacc_sources || 'CAPM Formula'}</p>
                        </div>
                      ) : 'AI explanation will appear here'}
                    </td>
                    <td>
                      <input 
                        type="number" 
                        step="0.001" 
                        placeholder="Enter WACC (e.g., 0.085)" 
                        onChange={(e) => onManualInput('wacc', e.target.value)} 
                        className="manual-input" 
                      />
                    </td>
                    <td>
                      {!confirmedValues.wacc ? (
                        <button onClick={() => onUseAI('wacc', aiData.wacc_percent ? aiData.wacc_percent.value / 100 : aiData.wacc)} className="btn-small">Use AI</button>
                      ) : (
                        <span className="positive">✓ Confirmed</span>
                      )}
                    </td>
                  </tr>
                  <tr>
                    <td>Terminal Growth Rate</td>
                    <td>{aiData.terminal_growth_rate_percent ? (aiData.terminal_growth_rate_percent.value / 100).toFixed(2) + '%' : aiData.terminal_growth ? (aiData.terminal_growth * 100).toFixed(2) + '%' : 'N/A'}</td>
                    <td className="rationale-cell">
                      {aiData.terminal_growth_rate_percent?.rationale ? (
                        <div className="rationale-content">
                          <p><strong>Why:</strong> {aiData.terminal_growth_rate_percent.rationale}</p>
                          <p><strong>Sources:</strong> {aiData.terminal_growth_rate_percent.sources || 'Historical GDP'}</p>
                        </div>
                      ) : aiData.terminal_growth_rationale ? (
                        <div className="rationale-content">
                          <p><strong>Why:</strong> {aiData.terminal_growth_rationale}</p>
                          <p><strong>Sources:</strong> {aiData.terminal_growth_sources || 'Historical GDP'}</p>
                        </div>
                      ) : 'AI explanation will appear here'}
                    </td>
                    <td>
                      <input 
                        type="number" 
                        step="0.001" 
                        placeholder="Enter terminal growth (e.g., 0.02)" 
                        onChange={(e) => onManualInput('terminal_growth', e.target.value)} 
                        className="manual-input" 
                      />
                    </td>
                    <td>
                      {!confirmedValues.terminal_growth ? (
                        <button onClick={() => onUseAI('terminal_growth', aiData.terminal_growth_rate_percent ? aiData.terminal_growth_rate_percent.value / 100 : aiData.terminal_growth)} className="btn-small">Use AI</button>
                      ) : (
                        <span className="positive">✓ Confirmed</span>
                      )}
                    </td>
                  </tr>
                  <tr>
                    <td>Revenue Growth Forecast</td>
                    <td>
                      {aiData.revenue_growth_forecast 
                        ? (Array.isArray(aiData.revenue_growth_forecast) 
                            ? aiData.revenue_growth_forecast.map(g => typeof g === 'object' ? (g.value / 100).toFixed(1) + '%' : (g * 100).toFixed(1) + '%').join(', ')
                            : 'N/A')
                        : 'N/A'}
                    </td>
                    <td className="rationale-cell">
                      {aiData.revenue_growth_rationale ? (
                        <div className="rationale-content">
                          <p><strong>Why:</strong> {aiData.revenue_growth_rationale}</p>
                          <p><strong>Sources:</strong> {aiData.revenue_growth_sources || 'Historical Trend'}</p>
                        </div>
                      ) : aiData.revenue_growth_forecast?.[0]?.rationale ? (
                        <div className="rationale-content">
                          <p><strong>Why:</strong> {aiData.revenue_growth_forecast[0].rationale}</p>
                          <p><strong>Sources:</strong> {aiData.revenue_growth_forecast[0].sources || 'Historical Trend'}</p>
                        </div>
                      ) : 'AI explanation will appear here'}
                    </td>
                    <td>
                      <input 
                        type="text" 
                        placeholder="e.g., 0.08, 0.06, 0.05, 0.04, 0.03, 0.02" 
                        onChange={(e) => onManualInput('revenue_growth_forecast', e.target.value)} 
                        className="manual-input" 
                      />
                    </td>
                    <td>
                      {!confirmedValues.revenue_growth_forecast ? (
                        <button onClick={() => onUseAI('revenue_growth_forecast', aiData.revenue_growth_forecast?.map(g => typeof g === 'object' ? g.value / 100 : g))} className="btn-small">Use AI</button>
                      ) : (
                        <span className="positive">✓ Confirmed</span>
                      )}
                    </td>
                  </tr>
                </>
              )}
            </tbody>
          </table>
          
          <div style={{ marginTop: '20px' }}>
            {showReviewOnly ? (
              <button 
                onClick={onContinueToForecastDrivers} 
                className="btn-primary btn-large"
              >
                Continue to Modify Forecast Drivers →
              </button>
            ) : (
              <button 
                onClick={onConfirmAssumptions} 
                disabled={loading} 
                className="btn-primary btn-large"
              >
                Confirm Assumptions & Proceed
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AssumptionsStep;
