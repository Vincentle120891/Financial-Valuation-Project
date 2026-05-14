import React, { useState } from 'react';
import DataFieldDisplay from './DataFieldDisplay';
import { 
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, 
  Tooltip, Legend, ResponsiveContainer 
} from 'recharts';

/**
 * ResultsStep Component
 * Step 11: View Valuation Results
 * 
 * Features:
 * - Multi-method results display (DCF, DuPont, COMPS) simultaneously
 * - Comparison table across all valuation methods
 * - Interactive charts for each method
 * - Key metrics highlights
 * - Upside/downside analysis
 * - Export and reset actions
 * 
 * REFACTORED: Now supports valuationMatrix[market][method] structure
 */
const ResultsStep = ({ 
  valuationMatrix,
  selectedMarket,
  selectedModels,
  onBackToModelSelection,
  onReset 
}) => {
  // Normalize inputs to work with both new matrix and legacy formats
  const getResultsForMethod = (method) => {
    if (valuationMatrix?.[selectedMarket]?.[method]) {
      return valuationMatrix[selectedMarket][method];
    }
    return null;
  };

  const hasAnyResults = selectedModels?.some(model => getResultsForMethod(model.toLowerCase()));

  if (!hasAnyResults) {
    return (
      <div className="step-container">
        <h2>Step 11: Valuation Results & Analysis</h2>
        <p style={{ color: '#666', textAlign: 'center', padding: '40px' }}>
          No valuation results available. Please complete the valuation process first.
        </p>
        <button onClick={onBackToModelSelection} className="btn-secondary" style={{ marginTop: '20px' }}>
          ← Back to Model Selection
        </button>
      </div>
    );
  }

  // Prepare FCF projection data for DCF charts
  const prepareFcfChartData = (dcfOutputs) => {
    if (!dcfOutputs?.free_cash_flows) return [];
    const fcfArray = dcfOutputs.free_cash_flows;
    return fcfArray.map((fcf, idx) => ({
      period: idx === fcfArray.length - 1 ? 'Terminal' : `Year ${idx + 1}`,
      fcf: Math.round(fcf),
      pv: Math.round(dcfOutputs.present_values?.[idx] || 0)
    }));
  };

  // Prepare DuPont trend data
  const prepareDupontTrendData = (dupontOutputs) => {
    if (!dupontOutputs?.roe_history) return [];
    const roeHistory = dupontOutputs.roe_history;
    const netMarginHistory = dupontOutputs.net_margin_history;
    
    return Object.entries(roeHistory).map(([year, roe]) => ({
      year,
      roe: (roe * 100).toFixed(1),
      netMargin: netMarginHistory?.[year] 
        ? (netMarginHistory[year] * 100).toFixed(1) 
        : 'N/A'
    }));
  };

  return (
    <div className="step-container">
      <h2>Step 11: Valuation Results & Analysis</h2>
      <p style={{ marginBottom: '24px', color: '#666' }}>
        Comprehensive valuation output for {selectedModels?.join(', ')} methods.
        Compare intrinsic value estimates, sensitivity analysis, and comparative metrics across all selected models.
      </p>
      
      {/* Multi-Method Summary Dashboard */}
      {selectedModels?.length > 1 && (
        <div className="summary-box" style={{ marginBottom: '32px', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
          <h3 style={{ color: 'white', marginBottom: '20px' }}>📊 Multi-Method Valuation Summary</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', color: 'white' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid rgba(255,255,255,0.3)' }}>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Metric</th>
                  {selectedModels.map(model => (
                    <th key={model} style={{ padding: '12px', textAlign: 'center' }}>{model}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.2)' }}>
                  <td style={{ padding: '12px', fontWeight: 'bold' }}>Implied Share Price</td>
                  {selectedModels.map(model => {
                    const results = getResultsForMethod(model.toLowerCase());
                    let price = 'N/A';
                    if (model === 'DCF' && results?.dcf_outputs?.implied_share_price) {
                      price = `$${results.dcf_outputs.implied_share_price.toFixed(2)}`;
                    } else if (model === 'DuPont') {
                      price = 'N/A (ROE Focus)';
                    } else if (model === 'COMPS' && results?.comps_outputs?.implied_share_price_median) {
                      price = `$${results.comps_outputs.implied_share_price_median.toFixed(2)}`;
                    }
                    return (
                      <td key={model} style={{ padding: '12px', textAlign: 'center' }}>
                        {model === 'DCF' && results?.dcf_outputs?.implied_share_price ? (
                          <DataFieldDisplay 
                            dataField={{
                              key: `${model}_share_price`,
                              value: results.dcf_outputs.implied_share_price,
                              status: 'CALCULATED',
                              source: 'DCF Model',
                              confidence_score: 0.90
                            }}
                            showMetadata={false}
                            compact={true}
                          />
                        ) : model === 'COMPS' && results?.comps_outputs?.implied_share_price_median ? (
                          <DataFieldDisplay 
                            dataField={{
                              key: `${model}_share_price`,
                              value: results.comps_outputs.implied_share_price_median,
                              status: 'CALCULATED',
                              source: 'Trading Comps',
                              confidence_score: 0.85
                            }}
                            showMetadata={false}
                            compact={true}
                          />
                        ) : (
                          price
                        )}
                      </td>
                    );
                  })}
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.2)' }}>
                  <td style={{ padding: '12px', fontWeight: 'bold' }}>Upside/(Downside)</td>
                  {selectedModels.map(model => {
                    const results = getResultsForMethod(model.toLowerCase());
                    let upside = 'N/A';
                    if (model === 'DCF' && results?.dcf_outputs?.upside_downside !== undefined) {
                      upside = `${results.dcf_outputs.upside_downside.toFixed(1)}%`;
                    } else if (model === 'COMPS' && results?.comps_outputs?.upside_downside_pct !== undefined) {
                      upside = `${results.comps_outputs.upside_downside_pct.toFixed(1)}%`;
                    }
                    return (
                      <td key={model} style={{ padding: '12px', textAlign: 'center' }}>
                        {(model === 'DCF' && results?.dcf_outputs?.upside_downside !== undefined) || 
                         (model === 'COMPS' && results?.comps_outputs?.upside_downside_pct !== undefined) ? (
                          <DataFieldDisplay 
                            dataField={{
                              key: `${model}_upside`,
                              value: model === 'DCF' ? results.dcf_outputs.upside_downside / 100 : results.comps_outputs.upside_downside_pct / 100,
                              status: 'CALCULATED',
                              source: model === 'DCF' ? 'DCF Model' : 'Trading Comps',
                              confidence_score: 0.85
                            }}
                            showMetadata={false}
                            compact={true}
                            formatAsPercentage={true}
                          />
                        ) : (
                          upside
                        )}
                      </td>
                    );
                  })}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Render results for each selected method */}
      {selectedModels?.map((model) => {
        const methodKey = model.toLowerCase();
        const results = getResultsForMethod(methodKey);
        
        if (!results) return null;

        return (
          <div key={model} className="results-dashboard" style={{ marginBottom: '32px', paddingBottom: '32px', borderBottom: selectedModels.indexOf(model) < selectedModels.length - 1 ? '2px solid #e0e0e0' : 'none' }}>
            <h3 style={{ color: '#667eea', marginBottom: '20px' }}>
              {model === 'DCF' && '📈 DCF Valuation'}
              {model === 'DuPont' && '🔍 DuPont Analysis'}
              {model === 'COMPS' && '🏢 Trading Comps'}
            </h3>

            {/* DCF Results */}
            {model === 'DCF' && results.dcf_outputs && (
              <>
                <div className="primary-result">
                  <div className="result-highlight">
                    <span className="label">Enterprise Value</span>
                    <span className="value">${(results.dcf_outputs.enterprise_value / 1000000).toFixed(1)}M</span>
                  </div>
                  <div className="result-highlight">
                    <span className="label">Equity Value</span>
                    <span className="value">${(results.dcf_outputs.equity_value / 1000000).toFixed(1)}M</span>
                  </div>
                  <div className="result-highlight">
                    <span className="label">Implied Share Price</span>
                    <span className="value">${results.dcf_outputs.implied_share_price?.toFixed(2)}</span>
                  </div>
                  <div className={`result-highlight ${results.dcf_outputs.upside_downside >= 0 ? 'positive' : 'negative'}`}>
                    <span className="label">Upside/(Downside)</span>
                    <span className="value">{results.dcf_outputs.upside_downside?.toFixed(1)}%</span>
                  </div>
                </div>
                
                {/* FCF Projection Chart */}
                {(() => {
                  const fcfChartData = prepareFcfChartData(results.dcf_outputs);
                  if (fcfChartData.length === 0) return null;
                  return (
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
                  );
                })()}
              </>
            )}

            {/* DuPont Results */}
            {model === 'DuPont' && (results.dupont_outputs || results.roe_history) && (
              <>
                <div className="primary-result">
                  <div className="result-highlight">
                    <span className="label">ROE (Latest Year)</span>
                    <span className="value">{((results.dupont_outputs?.roe_latest || results.roe_latest || 0) * 100).toFixed(1)}%</span>
                  </div>
                  <div className="result-highlight">
                    <span className="label">Net Profit Margin</span>
                    <span className="value">{((results.dupont_outputs?.net_margin_latest || results.net_margin_latest || 0) * 100).toFixed(1)}%</span>
                  </div>
                  <div className="result-highlight">
                    <span className="label">Asset Turnover</span>
                    <span className="value">{(results.dupont_outputs?.asset_turnover_latest || results.asset_turnover_latest || 0).toFixed(2)}x</span>
                  </div>
                  <div className="result-highlight">
                    <span className="label">Equity Multiplier</span>
                    <span className="value">{(results.dupont_outputs?.equity_multiplier_latest || results.equity_multiplier_latest || 0).toFixed(2)}x</span>
                  </div>
                </div>
                
                {/* ROE Trend Chart */}
                {(() => {
                  const dupontTrendData = prepareDupontTrendData(results.dupont_outputs || results);
                  if (dupontTrendData.length === 0) return null;
                  return (
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
                  );
                })()}
              </>
            )}

            {/* COMPS Results */}
            {model === 'COMPS' && results.comps_outputs && (
              <>
                <div className="primary-result">
                  <div className="result-highlight">
                    <span className="label">Implied Share Price (Median)</span>
                    <span className="value">${results.comps_outputs.implied_share_price_median?.toFixed(2)}</span>
                  </div>
                  <div className="result-highlight">
                    <span className="label">Current Share Price</span>
                    <span className="value">${results.comps_outputs.current_share_price?.toFixed(2)}</span>
                  </div>
                  <div className={`result-highlight ${results.comps_outputs.upside_downside_pct >= 0 ? 'positive' : 'negative'}`}>
                    <span className="label">Implied Upside/(Downside)</span>
                    <span className="value">{results.comps_outputs.upside_downside_pct?.toFixed(1)}%</span>
                  </div>
                  <div className="result-highlight">
                    <span className="label">Peers Analyzed</span>
                    <span className="value">{results.comps_outputs.peer_count}</span>
                  </div>
                </div>
                
                {/* Peer Multiples */}
                {results.comps_outputs.peer_statistics && (
                  <div className="summary-box" style={{ marginTop: '24px' }}>
                    <h3>Peer Multiples Statistics</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                      <div>
                        <strong>EV/EBITDA Median</strong>
                        <p>{results.comps_outputs.peer_statistics.ev_ebitda?.median?.toFixed(1)}x</p>
                      </div>
                      <div>
                        <strong>P/E Median</strong>
                        <p>{results.comps_outputs.peer_statistics.pe?.median?.toFixed(1)}x</p>
                      </div>
                      <div>
                        <strong>EV/Sales Median</strong>
                        <p>{results.comps_outputs.peer_statistics.ev_sales?.median?.toFixed(1)}x</p>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        );
      })}
      
      {/* Action Buttons */}
      <div style={{ marginTop: '24px', display: 'flex', gap: '12px' }}>
        <button onClick={onBackToModelSelection} className="btn-secondary">
          ← Change Models
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
