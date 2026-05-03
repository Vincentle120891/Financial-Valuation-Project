import React from 'react';

/**
 * ApiDataStep Component
 * Step 6: Review Data Retrieved from APIs
 * 
 * Features:
 * - Display historical financials retrieved from API with detailed numbers
 * - Show forecast drivers from API with period-by-period values
 * - Display peer comparison data with individual company metrics
 * - Show DCF inputs (WACC, terminal growth) from API
 * - Display DuPont analysis results with detailed ratios
 * - Show Comps analysis results with all multiples
 * - Navigate to Step 7 (AI Assumptions) or back to Step 5
 */
const ApiDataStep = ({ 
  historicalData,
  forecastDrivers,
  peerData,
  dcfInputs,
  dupontResults,
  compsResults,
  onBackToRequirements,
  onContinueToAiAssumptions,
  loading
}) => {
  // Check if data has been retrieved
  const hasRetrievedData = historicalData || peerData || dcfInputs || dupontResults || compsResults;

  // Helper function to format numbers
  const formatNumber = (num, decimals = 2) => {
    if (num === null || num === undefined) return 'N/A';
    return Number(num).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  };

  const formatCurrency = (num) => {
    if (num === null || num === undefined) return 'N/A';
    const absNum = Math.abs(num);
    if (absNum >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
    if (absNum >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
    if (absNum >= 1e3) return `$${(num / 1e3).toFixed(2)}K`;
    return `$${num.toFixed(2)}`;
  };

  const formatPercent = (num) => {
    if (num === null || num === undefined) return 'N/A';
    return `${(num * 100).toFixed(2)}%`;
  };

  // Render historical financials with detailed numbers
  const renderHistoricalData = () => {
    if (!historicalData) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)', marginBottom: '20px' }}>
        <h3>📊 Historical Financials (from API)</h3>
        
        {/* Revenue Table */}
        {historicalData.revenue && Object.keys(historicalData.revenue).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Revenue</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(historicalData.revenue).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#1976d2', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* EBITDA Table */}
        {historicalData.ebitda && Object.keys(historicalData.ebitda).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>EBITDA</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(historicalData.ebitda).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: value >= 0 ? '#4caf50' : '#f44336', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Net Income Table */}
        {historicalData.net_income && Object.keys(historicalData.net_income).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Net Income</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(historicalData.net_income).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: value >= 0 ? '#4caf50' : '#f44336', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Operating Expenses Table */}
        {historicalData.operating_expenses && Object.keys(historicalData.operating_expenses).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Operating Expenses</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(historicalData.operating_expenses).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#ff9800', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CapEx Table */}
        {historicalData.capex && Object.keys(historicalData.capex).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Capital Expenditure (CapEx)</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(historicalData.capex).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#9c27b0', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Depreciation & Amortization Table */}
        {historicalData.depreciation && Object.keys(historicalData.depreciation).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Depreciation & Amortization</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(historicalData.depreciation).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#00bcd4', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Total Assets Table */}
        {historicalData.total_assets && Object.keys(historicalData.total_assets).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Total Assets</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(historicalData.total_assets).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#3f51b5', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Total Debt Table */}
        {historicalData.total_debt && Object.keys(historicalData.total_debt).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Total Debt</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(historicalData.total_debt).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#f44336', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Free Cash Flow Table */}
        {historicalData.free_cash_flow && Object.keys(historicalData.free_cash_flow).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Free Cash Flow</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(historicalData.free_cash_flow).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: value >= 0 ? '#4caf50' : '#f44336', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Cash & Equivalents Table */}
        {historicalData.cash_and_equivalents && Object.keys(historicalData.cash_and_equivalents).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Cash & Cash Equivalents</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(historicalData.cash_and_equivalents).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#009688', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Inventory Table */}
        {historicalData.inventory && Object.keys(historicalData.inventory).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Inventory</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(historicalData.inventory).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#ff5722', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Accounts Receivable Table */}
        {historicalData.accounts_receivable && Object.keys(historicalData.accounts_receivable).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Accounts Receivable</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(historicalData.accounts_receivable).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#673ab7', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Accounts Payable Table */}
        {historicalData.accounts_payable && Object.keys(historicalData.accounts_payable).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Accounts Payable</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(historicalData.accounts_payable).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#e91e63', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Shareholders Equity Table */}
        {historicalData.shareholders_equity && Object.keys(historicalData.shareholders_equity).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Shareholders Equity</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(historicalData.shareholders_equity).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#00bcd4', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Summary Metrics */}
        <div style={{ marginTop: '20px', padding: '16px', background: 'white', borderRadius: '8px' }}>
          <h4 style={{ color: '#1565c0', marginBottom: '12px' }}>📊 Key Financial Metrics</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
            {historicalData.revenue_cagr !== undefined && (
              <div>
                <strong>Revenue CAGR:</strong>
                <p style={{ margin: '4px 0 0 0', color: '#2e7d32', fontWeight: 600 }}>
                  {(historicalData.revenue_cagr * 100).toFixed(2)}%
                </p>
              </div>
            )}
            {historicalData.avg_ebitda_margin !== undefined && (
              <div>
                <strong>Avg EBITDA Margin:</strong>
                <p style={{ margin: '4px 0 0 0', color: '#1976d2', fontWeight: 600 }}>
                  {(historicalData.avg_ebitda_margin * 100).toFixed(2)}%
                </p>
              </div>
            )}
            {historicalData.avg_roe !== undefined && (
              <div>
                <strong>Avg ROE:</strong>
                <p style={{ margin: '4px 0 0 0', color: '#7b1fa2', fontWeight: 600 }}>
                  {(historicalData.avg_roe * 100).toFixed(2)}%
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // Render forecast drivers with detailed period values
  const renderForecastDrivers = () => {
    if (!forecastDrivers) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)', marginBottom: '20px' }}>
        <h3>📈 Forecast Drivers (from API)</h3>
        
        {['base_case', 'best_case', 'worst_case'].map(scenario => {
          const scenarioData = forecastDrivers[scenario];
          if (!scenarioData) return null;
          
          return (
            <div key={scenario} style={{ marginTop: '16px', paddingBottom: '16px', borderBottom: scenario === 'worst_case' ? 'none' : '1px solid #a5d6a7' }}>
              <h4 style={{ color: '#2e7d32', marginBottom: '12px', textTransform: 'capitalize' }}>
                {scenario.replace('_', ' ')} Scenario
              </h4>
              
              {/* Sales Volume Growth */}
              {scenarioData.sales_volume_growth && scenarioData.sales_volume_growth.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>Sales Volume Growth:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.sales_volume_growth.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatPercent(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Inflation Rate */}
              {scenarioData.inflation_rate && scenarioData.inflation_rate.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>Inflation Rate:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.inflation_rate.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatPercent(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* OpEx Growth */}
              {scenarioData.opex_growth && scenarioData.opex_growth.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>OpEx Growth:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.opex_growth.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatPercent(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Capital Expenditure */}
              {scenarioData.capital_expenditure && scenarioData.capital_expenditure.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>Capital Expenditure (% of Revenue):</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.capital_expenditure.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatPercent(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* AR Days */}
              {scenarioData.ar_days && scenarioData.ar_days.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>Accounts Receivable Days:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.ar_days.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatNumber(value, 0)} days</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Inventory Days */}
              {scenarioData.inv_days && scenarioData.inv_days.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>Inventory Days:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.inv_days.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatNumber(value, 0)} days</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* AP Days */}
              {scenarioData.ap_days && scenarioData.ap_days.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>Accounts Payable Days:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.ap_days.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatNumber(value, 0)} days</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Tax Rate */}
              {scenarioData.tax_rate && scenarioData.tax_rate.length > 0 && (
                <div>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>Tax Rate:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.tax_rate.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatPercent(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  // Render peer data with detailed company information
  const renderPeerData = () => {
    if (!peerData || (Array.isArray(peerData) && peerData.length === 0)) return null;

    const companies = peerData.companies || (Array.isArray(peerData) ? peerData : []);

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)', marginBottom: '20px' }}>
        <h3>🏢 Peer Comparison Data (from API)</h3>
        
        {/* Summary Statistics */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '20px' }}>
          <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
            <strong>Peers Found:</strong>
            <p style={{ margin: '4px 0 0 0', color: '#666' }}>
              {companies.length} companies ✓
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
          {peerData.median_ev_revenue && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Median EV/Revenue:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {peerData.median_ev_revenue.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {peerData.median_pb && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Median P/B:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {peerData.median_pb.toFixed(1)}x ✓
              </p>
            </div>
          )}
        </div>

        {/* Individual Company Details */}
        {companies.length > 0 && (
          <div>
            <h4 style={{ color: '#e65100', marginBottom: '12px' }}>Individual Peer Companies</h4>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ background: '#fff8e1', borderBottom: '2px solid #ff9800' }}>
                    <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ffe0b2' }}>Ticker</th>
                    <th style={{ padding: '10px', textAlign: 'right', border: '1px solid #ffe0b2' }}>Market Cap</th>
                    <th style={{ padding: '10px', textAlign: 'right', border: '1px solid #ffe0b2' }}>EV/EBITDA</th>
                    <th style={{ padding: '10px', textAlign: 'right', border: '1px solid #ffe0b2' }}>P/E</th>
                    <th style={{ padding: '10px', textAlign: 'right', border: '1px solid #ffe0b2' }}>EV/Revenue</th>
                    <th style={{ padding: '10px', textAlign: 'right', border: '1px solid #ffe0b2' }}>P/B</th>
                  </tr>
                </thead>
                <tbody>
                  {companies.map((company, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #ffe0b2', background: idx % 2 === 0 ? 'white' : '#fff8e1' }}>
                      <td style={{ padding: '10px', fontWeight: 600, color: '#333', border: '1px solid #ffe0b2' }}>
                        {company.ticker || company.symbol || 'N/A'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', color: '#666', border: '1px solid #ffe0b2' }}>
                        {company.market_cap ? formatCurrency(company.market_cap) : 'N/A'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', color: '#666', border: '1px solid #ffe0b2' }}>
                        {company.ev_ebitda ? company.ev_ebitda.toFixed(1) + 'x' : 'N/A'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', color: '#666', border: '1px solid #ffe0b2' }}>
                        {company.pe_ratio ? company.pe_ratio.toFixed(1) + 'x' : 'N/A'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', color: '#666', border: '1px solid #ffe0b2' }}>
                        {company.ev_revenue ? company.ev_revenue.toFixed(1) + 'x' : 'N/A'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', color: '#666', border: '1px solid #ffe0b2' }}>
                        {company.pb_ratio ? company.pb_ratio.toFixed(1) + 'x' : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    );
  };

  // Render DCF inputs with all components
  const renderDcfInputs = () => {
    if (!dcfInputs) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%)', marginBottom: '20px' }}>
        <h3>💰 DCF Model Inputs (from API)</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          {dcfInputs.risk_free_rate !== undefined && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Risk-Free Rate:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {(dcfInputs.risk_free_rate * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dcfInputs.equity_risk_premium !== undefined && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Equity Risk Premium:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {(dcfInputs.equity_risk_premium * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dcfInputs.beta !== undefined && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Beta:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {dcfInputs.beta.toFixed(2)} ✓
              </p>
            </div>
          )}
          {dcfInputs.cost_of_debt !== undefined && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Cost of Debt:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {(dcfInputs.cost_of_debt * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dcfInputs.wacc && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px', borderLeft: '4px solid #9c27b0' }}>
              <strong>WACC (Calculated):</strong>
              <p style={{ margin: '4px 0 0 0', color: '#9c27b0', fontWeight: 600 }}>
                {(dcfInputs.wacc * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dcfInputs.terminal_growth_rate && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Terminal Growth Rate:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {(dcfInputs.terminal_growth_rate * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dcfInputs.terminal_ebitda_multiple && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Terminal EBITDA Multiple:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {dcfInputs.terminal_ebitda_multiple.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {dcfInputs.useful_life_existing && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Useful Life (Existing Assets):</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {dcfInputs.useful_life_existing} years ✓
              </p>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Render DuPont results with detailed ratios
  const renderDupontResults = () => {
    if (!dupontResults) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #fce4ec 0%, #f8bbd9 100%)', marginBottom: '20px' }}>
        <h3>📊 DuPont Analysis Results (from API)</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          {dupontResults.net_profit_margin && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Net Profit Margin:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {(dupontResults.net_profit_margin * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dupontResults.asset_turnover && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Asset Turnover:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {dupontResults.asset_turnover.toFixed(2)}x ✓
              </p>
            </div>
          )}
          {dupontResults.equity_multiplier && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Equity Multiplier:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {dupontResults.equity_multiplier.toFixed(2)}x ✓
              </p>
            </div>
          )}
          {dupontResults.roe && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px', borderLeft: '4px solid #e91e63' }}>
              <strong>ROE (Calculated):</strong>
              <p style={{ margin: '4px 0 0 0', color: '#e91e63', fontWeight: 600 }}>
                {(dupontResults.roe * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Render Comps results with all multiples
  const renderCompsResults = () => {
    if (!compsResults) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 100%)', marginBottom: '20px' }}>
        <h3>📈 Comps Analysis Results (from API)</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          {compsResults.ev_ebitda && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>EV/EBITDA:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {compsResults.ev_ebitda.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {compsResults.pe_ratio && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>P/E Ratio:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {compsResults.pe_ratio.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {compsResults.ev_revenue && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>EV/Revenue:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {compsResults.ev_revenue.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {compsResults.pb_ratio && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>P/B Ratio:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {compsResults.pb_ratio.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {compsResults.peg_ratio && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>PEG Ratio:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {compsResults.peg_ratio.toFixed(2)}x ✓
              </p>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="step-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Step 6: API Data Review</h2>
        <button onClick={onBackToRequirements} className="btn-secondary">
          ← Back to Requirements
        </button>
      </div>
      
      <div style={{ marginBottom: '20px', padding: '16px', background: '#e3f2fd', borderRadius: '8px' }}>
        <p style={{ margin: 0, color: '#1565c0' }}>
          <strong>ℹ️ About this step:</strong> This screen shows all financial data retrieved automatically from external APIs. 
          Review the data below before proceeding to AI-generated assumptions.
        </p>
      </div>

      {!hasRetrievedData ? (
        <div className="summary-box" style={{ background: 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)' }}>
          <h3 style={{ color: '#e65100' }}>⚠ No Data Retrieved</h3>
          <p>Please go back to Step 5 and click "Retrieve Data" first.</p>
        </div>
      ) : (
        <>
          {renderHistoricalData()}
          {renderForecastDrivers()}
          {renderPeerData()}
          {renderDcfInputs()}
          {renderDupontResults()}
          {renderCompsResults()}
          
          <div style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
            <button 
              onClick={onContinueToAiAssumptions} 
              className="btn-primary"
              disabled={loading}
            >
              Continue to AI Assumptions →
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default ApiDataStep;
