import React, { useState } from 'react';

/**
 * ForecastDriversStep Component
 * Step 7: Modify Forecast Drivers and DCF Inputs
 * 
 * Features:
 * - Edit all forecast driver assumptions (Revenue Growth, Volume vs Price, Inflation, etc.)
 * - Edit DCF model inputs (Risk-Free Rate, Beta, WACC, Terminal Growth, etc.)
 * - Support for multiple scenarios (Best Case, Base Case, Worst Case)
 * - Real-time validation and feedback
 */
const ForecastDriversStep = ({
  forecastDrivers: initialForecastDrivers,
  dcfInputs: initialDcfInputs,
  onManualInput,
  onConfirmDrivers,
  onBackToRequirements,
  onContinueToAssumptions,
  loading
}) => {
  // Initialize local state for forecast drivers
  const [localForecastDrivers, setLocalForecastDrivers] = useState(
    initialForecastDrivers || {
      best_case: { 
        sales_volume_growth: [], 
        inflation_rate: [], 
        opex_growth: [], 
        capital_expenditure: [], 
        ar_days: [], 
        inv_days: [], 
        ap_days: [], 
        tax_rate: [] 
      },
      base_case: { 
        sales_volume_growth: [], 
        inflation_rate: [], 
        opex_growth: [], 
        capital_expenditure: [], 
        ar_days: [], 
        inv_days: [], 
        ap_days: [], 
        tax_rate: [] 
      },
      worst_case: { 
        sales_volume_growth: [], 
        inflation_rate: [], 
        opex_growth: [], 
        capital_expenditure: [], 
        ar_days: [], 
        inv_days: [], 
        ap_days: [], 
        tax_rate: [] 
      }
    }
  );

  // Initialize local state for DCF inputs
  const [localDcfInputs, setLocalDcfInputs] = useState(
    initialDcfInputs || {
      risk_free_rate: 0.045,
      equity_risk_premium: 0.06,
      beta: 1.0,
      cost_of_debt: 0.05,
      wacc: 0.085,
      terminal_growth_rate: 0.02,
      terminal_ebitda_multiple: 10.0,
      useful_life_existing: 10,
      useful_life_new: 10
    }
  );

  const [activeScenario, setActiveScenario] = useState('base_case');
  const [editMode, setEditMode] = useState({
    forecastDrivers: false,
    dcfInputs: false
  });

  // Handle forecast driver input change
  const handleForecastDriverChange = (scenario, field, yearIndex, value) => {
    const numValue = parseFloat(value) || 0;
    
    setLocalForecastDrivers(prev => ({
      ...prev,
      [scenario]: {
        ...prev[scenario],
        [field]: prev[scenario][field].map((v, idx) => idx === yearIndex ? numValue : v)
      }
    }));

    // Notify parent component
    if (onManualInput) {
      onManualInput(`forecast_${scenario}_${field}_${yearIndex}`, numValue);
    }
  };

  // Handle DCF input change
  const handleDcfInputChange = (field, value) => {
    const numValue = parseFloat(value) || 0;
    
    setLocalDcfInputs(prev => ({
      ...prev,
      [field]: numValue
    }));

    // Notify parent component
    if (onManualInput) {
      onManualInput(`dcf_${field}`, numValue);
    }
  };

  // Generate array of years for forecast (5-10 years)
  const forecastYears = Array.from({ length: 5 }, (_, i) => `Year ${i + 1}`);

  // Render forecast driver input row with AI suggestions
  const renderForecastDriverRow = (scenario, field, label, step = 0.01, isPercentage = true) => {
    const values = localForecastDrivers[scenario]?.[field] || [];
    
    return (
      <div key={`${scenario}_${field}`} className="driver-row" style={{ marginBottom: '16px', padding: '12px', background: '#f9f9f9', borderRadius: '6px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <label style={{ fontWeight: 'bold', color: '#333' }}>
            {label} {isPercentage && '(%)'}
          </label>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
          {forecastYears.map((year, idx) => {
            const aiSuggestion = values[idx];
            const displayValue = aiSuggestion !== undefined ? (isPercentage ? (aiSuggestion * 100).toFixed(2) : aiSuggestion.toFixed(2)) : '';
            
            return (
              <div key={idx}>
                <label style={{ fontSize: '12px', color: '#666', display: 'block', marginBottom: '4px' }}>{year}</label>
                <input
                  type="number"
                  step={step}
                  value={displayValue}
                  onChange={(e) => handleForecastDriverChange(scenario, field, idx, isPercentage ? parseFloat(e.target.value) / 100 : parseFloat(e.target.value))}
                  disabled={!editMode.forecastDrivers}
                  style={{
                    width: '100%',
                    padding: '6px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '13px'
                  }}
                />
                {aiSuggestion?.rationale && (
                  <div style={{ fontSize: '10px', color: '#667eea', marginTop: '4px', fontStyle: 'italic' }}>
                    💡 {aiSuggestion.rationale}
                  </div>
                )}
                {aiSuggestion?.sources && (
                  <div style={{ fontSize: '9px', color: '#999', marginTop: '2px' }}>
                    Source: {aiSuggestion.sources}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // Render DCF input field with AI suggestions
  const renderDcfInputField = (field, label, step = 0.001, isPercentage = true, min = 0, max = 1) => {
    const valueObj = localDcfInputs[field];
    const value = typeof valueObj === 'object' && valueObj !== null ? valueObj.value : valueObj;
    const displayValue = isPercentage ? (value * 100).toFixed(2) : value.toFixed(2);
    
    return (
      <div key={field} className="dcf-input-row" style={{ marginBottom: '12px' }}>
        <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '6px', color: '#333' }}>
          {label} {isPercentage && '(%)'}
        </label>
        <input
          type="number"
          step={step}
          min={min}
          max={max}
          value={displayValue}
          onChange={(e) => handleDcfInputChange(field, isPercentage ? parseFloat(e.target.value) / 100 : parseFloat(e.target.value))}
          disabled={!editMode.dcfInputs}
          style={{
            width: '100%',
            padding: '8px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            fontSize: '14px'
          }}
        />
        {typeof valueObj === 'object' && valueObj !== null && valueObj.rationale && (
          <div style={{ fontSize: '11px', color: '#667eea', marginTop: '6px', fontStyle: 'italic' }}>
            💡 {valueObj.rationale}
          </div>
        )}
        {typeof valueObj === 'object' && valueObj !== null && valueObj.sources && (
          <div style={{ fontSize: '10px', color: '#999', marginTop: '3px' }}>
            Source: {valueObj.sources}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="step-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Step 7: Modify Forecast Drivers & DCF Inputs</h2>
        <button onClick={onBackToRequirements} className="btn-secondary">
          ← Back to Requirements
        </button>
      </div>

      {/* Scenario Selector */}
      <div className="summary-box" style={{ marginBottom: '24px' }}>
        <h3>Select Scenario</h3>
        <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
          {['best_case', 'base_case', 'worst_case'].map(scenario => (
            <button
              key={scenario}
              onClick={() => setActiveScenario(scenario)}
              style={{
                padding: '10px 20px',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 'bold',
                background: activeScenario === scenario ? '#667eea' : '#e0e0e0',
                color: activeScenario === scenario ? 'white' : '#333'
              }}
            >
              {scenario.replace('_', ' ').toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Forecast Drivers Section */}
      <div className="summary-box" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3>📊 Forecast Drivers (5-Year Projection)</h3>
          <button
            onClick={() => setEditMode(prev => ({ ...prev, forecastDrivers: !prev.forecastDrivers }))}
            className="btn-small"
            style={{
              background: editMode.forecastDrivers ? '#4caf50' : '#ff9800',
              color: 'white'
            }}
          >
            {editMode.forecastDrivers ? '✓ Editing' : '✏️ Edit'}
          </button>
        </div>
        
        {renderForecastDriverRow(activeScenario, 'sales_volume_growth', 'Volume Growth', 0.01, true)}
        {renderForecastDriverRow(activeScenario, 'inflation_rate', 'Inflation Rate', 0.001, true)}
        {renderForecastDriverRow(activeScenario, 'opex_growth', 'OpEx Growth', 0.01, true)}
        {renderForecastDriverRow(activeScenario, 'capital_expenditure', 'CapEx (% of Revenue)', 0.01, true)}
        {renderForecastDriverRow(activeScenario, 'ar_days', 'AR Days', 1, false)}
        {renderForecastDriverRow(activeScenario, 'inv_days', 'Inventory Days', 1, false)}
        {renderForecastDriverRow(activeScenario, 'ap_days', 'AP Days', 1, false)}
        {renderForecastDriverRow(activeScenario, 'tax_rate', 'Tax Rate', 0.01, true)}
      </div>

      {/* DCF Model Inputs Section */}
      <div className="summary-box" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3>💰 DCF Model Inputs</h3>
          <button
            onClick={() => setEditMode(prev => ({ ...prev, dcfInputs: !prev.dcfInputs }))}
            className="btn-small"
            style={{
              background: editMode.dcfInputs ? '#4caf50' : '#ff9800',
              color: 'white'
            }}
          >
            {editMode.dcfInputs ? '✓ Editing' : '✏️ Edit'}
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            {renderDcfInputField('risk_free_rate', 'Risk-Free Rate', 0.001, true, 0, 0.2)}
            {renderDcfInputField('equity_risk_premium', 'Equity Risk Premium', 0.001, true, 0, 0.2)}
            {renderDcfInputField('beta', 'Beta', 0.01, false, 0, 3)}
            {renderDcfInputField('cost_of_debt', 'Cost of Debt', 0.001, true, 0, 0.2)}
          </div>
          <div>
            {renderDcfInputField('wacc', 'WACC', 0.001, true, 0, 0.2)}
            {renderDcfInputField('terminal_growth_rate', 'Terminal Growth Rate', 0.001, true, 0, 0.1)}
            {renderDcfInputField('terminal_ebitda_multiple', 'Terminal EBITDA Multiple', 0.1, false, 1, 50)}
            {renderDcfInputField('useful_life_existing', 'Useful Life (Existing Assets)', 1, false, 1, 50, 'years')}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', marginTop: '24px' }}>
        <button
          onClick={onBackToRequirements}
          className="btn-secondary btn-large"
          disabled={loading}
        >
          ← Back to Requirements
        </button>
        <button
          onClick={onContinueToAssumptions}
          className="btn-primary btn-large"
          disabled={loading}
        >
          Continue to Confirm Assumptions →
        </button>
      </div>
    </div>
  );
};

export default ForecastDriversStep;
