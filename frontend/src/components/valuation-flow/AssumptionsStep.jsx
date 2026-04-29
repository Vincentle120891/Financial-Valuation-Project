import React from 'react';
import { 
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, 
  Tooltip, Legend, ResponsiveContainer, AreaChart, Area, 
  ComposedChart, Scatter 
} from 'recharts';

/**
 * AssumptionsStep Component
 * Steps 6 & 8: View Retrieved Inputs / Review & Confirm Assumptions
 * 
 * Features:
 * - Historical trends visualization
 * - Peer benchmarking summary
 * - AI suggestions with rationale
 * - Manual input override (Step 8 only)
 * - Interactive charts (Revenue, EBITDA, Growth)
 * 
 * Props:
 * - showReviewOnly: boolean (default: false) - If true, shows read-only view for Step 6
 * - onContinueToConfirm: function - Callback to navigate from Step 6 to Step 8
 */
const AssumptionsStep = ({
  historicalData,
  peerData,
  aiData,
  confirmedValues,
  selectedModel,
  onManualInput,
  onUseAI,
  onConfirmAssumptions,
  loading,
  showReviewOnly = false,
  onContinueToConfirm
}) => {
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
      <h2>{showReviewOnly ? 'Step 6: View Retrieved Inputs' : 'Step 8: Review & Confirm Assumptions'}</h2>
      
      {/* Show message if no data available */}
      {!historicalData && (!peerData || Object.keys(peerData).length === 0) && (!aiData || Object.keys(aiData).length === 0) && (
        <div className="summary-box" style={{ background: 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)' }}>
          <h3 style={{ color: '#e65100' }}>⚠ No Data Available</h3>
          <p>Please go back to Step 5 and click "Retrieve Data" first to load the input values.</p>
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
      {peerData && Object.keys(peerData).length > 0 && (
        <div className="summary-box">
          <h3>Peer Benchmarking</h3>
          <p><strong>Peers Analyzed:</strong> {Array.isArray(peerData) ? peerData.length : 'N/A'} companies</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginTop: '12px' }}>
            <div>
              <strong>Median EV/EBITDA:</strong>
              <p>{peerData.median_ev_ebitda ? peerData.median_ev_ebitda.toFixed(1) + 'x' : 'N/A'}</p>
            </div>
            <div>
              <strong>Median P/E:</strong>
              <p>{peerData.median_pe ? peerData.median_pe.toFixed(1) + 'x' : 'N/A'}</p>
            </div>
            <div>
              <strong>Peer Growth Avg:</strong>
              <p>{peerData.avg_revenue_growth ? (peerData.avg_revenue_growth * 100).toFixed(1) + '%' : 'N/A'}</p>
            </div>
          </div>
        </div>
      )}
      
      {/* AI Suggestions Table */}
      {aiData && Object.keys(aiData).length > 0 && (
        <div className="summary-box" style={{ background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)' }}>
          <h3 style={{ color: '#667eea' }}>🤖 AI Suggestions with Rationale</h3>
          <p style={{ marginBottom: '20px', color: '#666' }}>
            AI analyzes historical trends, peer benchmarks, and market conditions to provide data-driven recommendations
          </p>
          
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
                    <td>{aiData.wacc ? (aiData.wacc * 100).toFixed(2) + '%' : 'N/A'}</td>
                    <td className="rationale-cell">
                      {aiData.wacc_rationale ? (
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
                        <button onClick={() => onUseAI('wacc', aiData.wacc)} className="btn-small">Use AI</button>
                      ) : (
                        <span className="positive">✓ Confirmed</span>
                      )}
                    </td>
                  </tr>
                  <tr>
                    <td>Terminal Growth Rate</td>
                    <td>{aiData.terminal_growth ? (aiData.terminal_growth * 100).toFixed(2) + '%' : 'N/A'}</td>
                    <td className="rationale-cell">
                      {aiData.terminal_growth_rationale ? (
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
                        <button onClick={() => onUseAI('terminal_growth', aiData.terminal_growth)} className="btn-small">Use AI</button>
                      ) : (
                        <span className="positive">✓ Confirmed</span>
                      )}
                    </td>
                  </tr>
                  <tr>
                    <td>Revenue Growth Forecast</td>
                    <td>
                      {aiData.revenue_growth_forecast 
                        ? aiData.revenue_growth_forecast.map(g => (g * 100).toFixed(1) + '%').join(', ') 
                        : 'N/A'}
                    </td>
                    <td className="rationale-cell">
                      {aiData.revenue_growth_rationale ? (
                        <div className="rationale-content">
                          <p><strong>Why:</strong> {aiData.revenue_growth_rationale}</p>
                          <p><strong>Sources:</strong> {aiData.revenue_growth_sources || 'Historical Trend'}</p>
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
                        <button onClick={() => onUseAI('revenue_growth_forecast', aiData.revenue_growth_forecast)} className="btn-small">Use AI</button>
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
                onClick={onContinueToConfirm} 
                className="btn-primary btn-large"
              >
                Continue to Confirm Assumptions →
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
