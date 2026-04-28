import React from 'react';

/**
 * RequirementsStep Component
 * Step 5: Review Data Requirements
 * 
 * Features:
 * - Model-specific data requirements display
 * - Historical vs forecast period breakdown
 * - Back navigation to model selection
 */
const RequirementsStep = ({ selectedModel, onBackToModelSelection }) => {
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
    </div>
  );
};

export default RequirementsStep;
