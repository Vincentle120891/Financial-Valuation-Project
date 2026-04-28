import React from 'react';

/**
 * RunValuationStep Component
 * Step 9: Run Valuation
 * 
 * Features:
 * - Configuration summary display
 * - Back navigation to model selection
 * - Run valuation trigger
 */
const RunValuationStep = ({ 
  selectedCompany, 
  selectedModel, 
  selectedScenario, 
  confirmedValues,
  loading,
  onBackToModelSelection,
  onRunValuation 
}) => {
  const getModelName = () => {
    switch (selectedModel) {
      case 'DCF': return 'Discounted Cash Flow';
      case 'DuPont': return 'DuPont Analysis';
      case 'COMPS': return 'Trading Comps';
      default: return 'Unknown';
    }
  };

  return (
    <div className="step-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Step 9: Run Valuation</h2>
        <button onClick={onBackToModelSelection} className="btn-secondary">
          ← Change Model
        </button>
      </div>
      
      <div className="summary-box">
        <h3>Configuration Summary</h3>
        <p><strong>Company:</strong> {selectedCompany?.name} ({selectedCompany?.symbol})</p>
        <p><strong>Model:</strong> {getModelName()}</p>
        <p><strong>Scenario:</strong> {selectedScenario.replace('_', ' ').toUpperCase()}</p>
        <p><strong>Confirmed Inputs:</strong> {Object.keys(confirmedValues).length} fields</p>
      </div>
      
      <button 
        onClick={onRunValuation} 
        disabled={loading} 
        className="btn-primary btn-large"
      >
        {loading ? 'Calculating...' : 'Run Valuation'}
      </button>
    </div>
  );
};

export default RunValuationStep;
