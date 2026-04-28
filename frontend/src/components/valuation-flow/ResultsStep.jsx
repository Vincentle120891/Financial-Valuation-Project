import React from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, 
  Tooltip, Legend, ResponsiveContainer 
} from 'recharts';

/**
 * ResultsStep Component
 * Step 10: View Valuation Results
 * 
 * Features:
 * - Model-specific results display (DCF, DuPont, COMPS)
 * - Interactive charts for FCF projections and ROE trends
 * - Key metrics highlights
 * - Upside/downside analysis
 * - Export and reset actions
 */
const ResultsStep = ({ 
  valuationResults, 
  selectedModel,
  dupontResults,
  compsResults,
  onBackToModelSelection,
  onReset 
}) => {
  if (!valuationResults) return null;

  // Prepare FCF projection data for DCF charts
  const prepareFcfChartData = () => {
    if (!valuationResults.dcf_outputs?.free_cash_flows) return [];
    const fcfArray = valuationResults.dcf_outputs.free_cash_flows;
    return fcfArray.map((fcf, idx) => ({
      period: idx === fcfArray.length - 1 ? 'Terminal' : `Year ${idx + 1}`,
      fcf: Math.round(fcf),
      pv: Math.round(valuationResults.dcf_outputs.present_values?.[idx] || 0)
    }));
  };

  // Prepare DuPont trend data
  const prepareDupontTrendData = () => {
    if (!dupontResults?.roe_history) return [];
    return Object.entries(dupontResults.roe_history).map(([year, roe]) => ({
      year,
      roe: (roe * 100).toFixed(1),
      netMargin: dupontResults.net_margin_history?.[year] 
        ? (dupontResults.net_margin_history[year] * 100).toFixed(1) 
        : 'N/A'
    }));
  };

  const fcfChartData = prepareFcfChartData();
  const dupontTrendData = prepareDupontTrendData();

  return (
    <div className="step-container">
      <h2>Step 10: Valuation Results</h2>
      
      {/* DCF Results */}
      {selectedModel === 'DCF' && valuationResults.dcf_outputs && (
        <div className="results-dashboard">
          <div className="primary-result">
            <h3>DCF Valuation Summary</h3>
            <div className="result-highlight">
              <span className="label">Enterprise Value</span>
              <span className="value">
                ${(valuationResults.dcf_outputs.enterprise_value / 1000000).toFixed(1)}M
              </span>
            </div>
            <div className="result-highlight">
              <span className="label">Equity Value</span>
              <span className="value">
                ${(valuationResults.dcf_outputs.equity_value / 1000000).toFixed(1)}M
              </span>
            </div>
            <div className="result-highlight">
              <span className="label">Implied Share Price</span>
              <span className="value">
                ${valuationResults.dcf_outputs.implied_share_price?.toFixed(2)}
              </span>
            </div>
            <div className={`result-highlight ${valuationResults.dcf_outputs.upside_downside >= 0 ? 'positive' : 'negative'}`}>
              <span className="label">Upside/(Downside)</span>
              <span className="value">
                {valuationResults.dcf_outputs.upside_downside?.toFixed(1)}%
              </span>
            </div>
          </div>
          
          {/* FCF Projection Chart */}
          {fcfChartData.length > 0 && (
            <div className="summary-box" style={{ marginTop: '24px' }}>
              <h3>Free Cash Flow Projections</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={fcfChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                  <XAxis dataKey="period" stroke="#666" />
                  <YAxis stroke="#666" />
                  <Tooltip 
                    formatter={(value) => [`$${(value/1000).toFixed(1)}M`, 'Value']}
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                  />
                  <Legend />
                  <Bar dataKey="fcf" fill="#667eea" name="Free Cash Flow" />
                  <Bar dataKey="pv" fill="#28a745" name="Present Value" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
      
      {/* DuPont Results */}
      {selectedModel === 'DuPont' && valuationResults.dupont_outputs && (
        <div className="results-dashboard">
          <div className="primary-result">
            <h3>DuPont Analysis Summary</h3>
            <div className="result-highlight">
              <span className="label">ROE (Latest Year)</span>
              <span className="value">
                {(valuationResults.dupont_outputs.roe_latest * 100).toFixed(1)}%
              </span>
            </div>
            <div className="result-highlight">
              <span className="label">Net Profit Margin</span>
              <span className="value">
                {(valuationResults.dupont_outputs.net_margin_latest * 100).toFixed(1)}%
              </span>
            </div>
            <div className="result-highlight">
              <span className="label">Asset Turnover</span>
              <span className="value">
                {valuationResults.dupont_outputs.asset_turnover_latest.toFixed(2)}x
              </span>
            </div>
            <div className="result-highlight">
              <span className="label">Equity Multiplier</span>
              <span className="value">
                {valuationResults.dupont_outputs.equity_multiplier_latest.toFixed(2)}x
              </span>
            </div>
          </div>
          
          {/* ROE Trend Chart */}
          {dupontTrendData.length > 0 && (
            <div className="summary-box" style={{ marginTop: '24px' }}>
              <h3 style={{ marginBottom: '16px' }}>📈 5-Year ROE Decomposition Trend</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={dupontTrendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                  <XAxis dataKey="year" stroke="#666" />
                  <YAxis stroke="#666" label={{ value: 'ROE (%)', angle: -90, position: 'insideLeft' }} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="roe" stroke="#667eea" strokeWidth={3} name="ROE %" dot={{ r: 5 }} />
                  <Line type="monotone" dataKey="netMargin" stroke="#28a745" strokeWidth={2} name="Net Margin %" strokeDasharray="5 5" />
                </LineChart>
              </ResponsiveContainer>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginTop: '20px' }}>
                <div style={{ padding: '12px', background: 'white', borderRadius: '8px' }}>
                  <strong style={{ color: '#666', fontSize: '12px' }}>Avg ROE</strong>
                  <p style={{ fontSize: '20px', fontWeight: 'bold', color: '#667eea' }}>
                    {(dupontTrendData.reduce((sum, d) => sum + parseFloat(d.roe), 0) / dupontTrendData.length).toFixed(1)}%
                  </p>
                </div>
                <div style={{ padding: '12px', background: 'white', borderRadius: '8px' }}>
                  <strong style={{ color: '#666', fontSize: '12px' }}>ROE Trend</strong>
                  <p style={{ fontSize: '20px', fontWeight: 'bold', color: parseFloat(dupontTrendData[dupontTrendData.length - 1]?.roe) > parseFloat(dupontTrendData[0]?.roe) ? '#28a745' : '#dc3545' }}>
                    {parseFloat(dupontTrendData[dupontTrendData.length - 1]?.roe) > parseFloat(dupontTrendData[0]?.roe) ? '📈 Improving' : '📉 Declining'}
                  </p>
                </div>
                <div style={{ padding: '12px', background: 'white', borderRadius: '8px' }}>
                  <strong style={{ color: '#666', fontSize: '12px' }}>Latest ROE</strong>
                  <p style={{ fontSize: '20px', fontWeight: 'bold', color: '#764ba2' }}>{dupontTrendData[dupontTrendData.length - 1]?.roe}%</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Trading Comps Results */}
      {selectedModel === 'COMPS' && valuationResults.comps_outputs && (
        <div className="results-dashboard">
          <div className="primary-result">
            <h3>Trading Comps Summary</h3>
            <div className="result-highlight">
              <span className="label">Implied Share Price (Median)</span>
              <span className="value">
                ${valuationResults.comps_outputs.implied_share_price_median?.toFixed(2)}
              </span>
            </div>
            <div className="result-highlight">
              <span className="label">Current Share Price</span>
              <span className="value">
                ${valuationResults.comps_outputs.current_share_price?.toFixed(2)}
              </span>
            </div>
            <div className={`result-highlight ${valuationResults.comps_outputs.upside_downside_pct >= 0 ? 'positive' : 'negative'}`}>
              <span className="label">Implied Upside/(Downside)</span>
              <span className="value">
                {valuationResults.comps_outputs.upside_downside_pct?.toFixed(1)}%
              </span>
            </div>
            <div className="result-highlight">
              <span className="label">Peers Analyzed</span>
              <span className="value">{valuationResults.comps_outputs.peer_count}</span>
            </div>
          </div>
          
          {/* Peer Multiples */}
          {valuationResults.comps_outputs.peer_statistics && (
            <div className="summary-box" style={{ marginTop: '24px' }}>
              <h3>Peer Multiples Statistics</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                <div>
                  <strong>EV/EBITDA Median</strong>
                  <p>{valuationResults.comps_outputs.peer_statistics.ev_ebitda?.median?.toFixed(1)}x</p>
                </div>
                <div>
                  <strong>P/E Median</strong>
                  <p>{valuationResults.comps_outputs.peer_statistics.pe?.median?.toFixed(1)}x</p>
                </div>
                <div>
                  <strong>EV/Sales Median</strong>
                  <p>{valuationResults.comps_outputs.peer_statistics.ev_sales?.median?.toFixed(1)}x</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Action Buttons */}
      <div style={{ marginTop: '24px', display: 'flex', gap: '12px' }}>
        <button onClick={onBackToModelSelection} className="btn-secondary">
          ← Change Model
        </button>
        <button onClick={onReset} className="btn-secondary">
          Start New Valuation
        </button>
        <button className="btn-primary">Export Report</button>
      </div>
    </div>
  );
};

export default ResultsStep;
