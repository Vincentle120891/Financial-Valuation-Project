import React from 'react';

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
  aiData,
  onContinueToAssumptions
}) => {
  const getModelRequirements = () => {
    switch (selectedModel) {
      case 'DCF':
        return (
          <>
            <p><strong>Historical:</strong> 3 most recent fiscal years (FY-3, FY-2, FY-1)</p>
            <ul>
              <li>Revenue, COGS, Operating Expenses</li>
              <li>Depreciation & Amortization</li>
              <li>Working Capital items (AR, Inventory, AP)</li>
              <li>Capital Expenditures</li>
            </ul>
            <p><strong>Forecast:</strong> 6 periods (monthly/quarterly/annual)</p>
            <ul>
              <li>Revenue growth assumptions</li>
              <li>EBITDA margins</li>
              <li>WACC and Terminal Growth Rate</li>
            </ul>
          </>
        );
      case 'DuPont':
        return (
          <>
            <p><strong>Historical:</strong> 3-5 years of annual data</p>
            <ul>
              <li>Net Income</li>
              <li>Revenue</li>
              <li>Total Assets</li>
              <li>Shareholders' Equity</li>
            </ul>
            <p><strong>Output:</strong> ROE decomposition trends</p>
          </>
        );
      case 'COMPS':
        return (
          <>
            <p><strong>Target Company:</strong> Latest financial metrics</p>
            <ul>
              <li>Market Cap, Enterprise Value</li>
              <li>EBITDA, Net Income, Revenue</li>
              <li>Shares Outstanding</li>
            </ul>
            <p><strong>Peer Group:</strong> 5+ comparable companies</p>
            <ul>
              <li>Same industry/sector</li>
              <li>Similar size and growth profile</li>
              <li>Trading multiples (P/E, EV/EBITDA, EV/Sales)</li>
            </ul>
          </>
        );
      default:
        return <p>Please select a model first.</p>;
    }
  };

  // Check if data has been retrieved
  const hasRetrievedData = historicalData || peerData || dcfInputs || dupontResults || compsResults;

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
              {historicalData.revenue && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>Revenue:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {Object.keys(historicalData.revenue).length} years ✓
                  </p>
                </div>
              )}
              {historicalData.ebitda && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>EBITDA:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {Object.keys(historicalData.ebitda).length} years ✓
                  </p>
                </div>
              )}
              {historicalData.net_income && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>Net Income:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {Object.keys(historicalData.net_income).length} years ✓
                  </p>
                </div>
              )}
              {historicalData.operating_expenses && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>OpEx:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {Object.keys(historicalData.operating_expenses).length} years ✓
                  </p>
                </div>
              )}
              {historicalData.capex && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>CapEx:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {Object.keys(historicalData.capex).length} years ✓
                  </p>
                </div>
              )}
              {historicalData.depreciation && (
                <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                  <strong>D&A:</strong>
                  <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {Object.keys(historicalData.depreciation).length} years ✓
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

  return (
    <div className="step-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Step 5: Required Inputs</h2>
        <button onClick={onBackToModelSelection} className="btn-secondary">
          ← Change Model
        </button>
      </div>
      
      <div className="summary-box">
        <h3>Data Requirements by Model</h3>
        {getModelRequirements()}
      </div>

      {/* Show retrieved data if available */}
      {renderRetrievedData()}
      
      {/* Show missing data warning if applicable */}
      {renderMissingData()}

      <div style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
        {!hasRetrievedData ? (
          <button 
            onClick={onRetrieveData} 
            className="btn-primary"
            disabled={loading}
          >
            {loading ? 'Retrieving Data...' : 'Retrieve Data'}
          </button>
        ) : (
          <>
            <button 
              onClick={onRetrieveData} 
              className="btn-secondary"
              disabled={loading}
            >
              {loading ? 'Refreshing...' : '↻ Refresh Data'}
            </button>
            <button 
              onClick={onContinueToAssumptions} 
              className="btn-primary"
            >
              Review Assumptions →
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default RequirementsStep;
