import React from 'react';

/**
 * ApiDataStep Component
 * Step 6: Review Data Retrieved from APIs
 * 
 * Features:
 * - Display historical financials retrieved from API
 * - Show forecast drivers from API
 * - Display peer comparison data
 * - Show DCF inputs (WACC, terminal growth) from API
 * - Display DuPont analysis results
 * - Show Comps analysis results
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

  // Render historical financials
  const renderHistoricalData = () => {
    if (!historicalData) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)', marginBottom: '20px' }}>
        <h3>📊 Historical Financials (from API)</h3>
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
    );
  };

  // Render forecast drivers
  const renderForecastDrivers = () => {
    if (!forecastDrivers) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)', marginBottom: '20px' }}>
        <h3>📈 Forecast Drivers (from API)</h3>
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
    );
  };

  // Render peer data
  const renderPeerData = () => {
    if (!peerData || (Array.isArray(peerData) && peerData.length === 0)) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)', marginBottom: '20px' }}>
        <h3>🏢 Peer Comparison Data (from API)</h3>
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
    );
  };

  // Render DCF inputs
  const renderDcfInputs = () => {
    if (!dcfInputs) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%)', marginBottom: '20px' }}>
        <h3>💰 DCF Model Inputs (from API)</h3>
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
    );
  };

  // Render DuPont results
  const renderDupontResults = () => {
    if (!dupontResults) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #fce4ec 0%, #f8bbd9 100%)', marginBottom: '20px' }}>
        <h3>📊 DuPont Analysis Results (from API)</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
          <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
            <strong>ROE Components:</strong>
            <p style={{ margin: '4px 0 0 0', color: '#666' }}>Ready ✓</p>
          </div>
        </div>
      </div>
    );
  };

  // Render Comps results
  const renderCompsResults = () => {
    if (!compsResults) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 100%)', marginBottom: '20px' }}>
        <h3>📈 Comps Analysis Results (from API)</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
          <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
            <strong>Valuation Multiples:</strong>
            <p style={{ margin: '4px 0 0 0', color: '#666' }}>Ready ✓</p>
          </div>
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
