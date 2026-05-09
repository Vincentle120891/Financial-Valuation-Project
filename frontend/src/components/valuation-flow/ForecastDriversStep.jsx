import React, { useState } from 'react';
import { generateAISuggestion } from '../../services/api';

/**
 * ForecastDriversStep Component
 * Step 8: Modify Forecast Drivers and DCF Inputs with AI Suggestions
 * 
 * Features:
 * - Edit all forecast driver assumptions (Revenue Growth, Volume vs Price, Inflation, etc.)
 * - Edit DCF model inputs (Risk-Free Rate, Beta, WACC, Terminal Growth, etc.)
 * - Generate AI suggestions for each category
 * - Support for multiple scenarios (Best Case, Base Case, Worst Case)
 * - Real-time validation and feedback
 */
const ForecastDriversStep = ({
  sessionId,
  forecastDrivers: initialForecastDrivers,
  dcfInputs: initialDcfInputs,
  step6Data,
  step7Data,
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
  const [aiLoading, setAiLoading] = useState({});
  const [aiSuggestions, setAiSuggestions] = useState({});

  // Generate AI suggestion for a specific category
  const handleGenerateAISuggestion = async (category) => {
    if (!sessionId) {
      alert('Session ID not available. Please go back and restart the valuation.');
      return;
    }

    setAiLoading(prev => ({ ...prev, [category]: true }));
    try {
      const response = await generateAISuggestion(sessionId, category);
      if (response.status === 'success' && response.suggestion) {
        setAiSuggestions(prev => ({ ...prev, [category]: response.suggestion }));
        
        // Auto-apply the suggestion to the current state
        const suggestion = response.suggestion;
        if (category === 'revenue_drivers') {
          // Apply volume growth and price increase to forecast drivers
          if (suggestion.volume_growth !== undefined) {
            setLocalForecastDrivers(prev => ({
              ...prev,
              [activeScenario]: {
                ...prev[activeScenario],
                sales_volume_growth: prev[activeScenario].sales_volume_growth.map(() => suggestion.volume_growth)
              }
            }));
          }
          if (suggestion.price_increase !== undefined) {
            // Price increase would affect inflation_rate or could be a separate field
            setLocalForecastDrivers(prev => ({
              ...prev,
              [activeScenario]: {
                ...prev[activeScenario],
                inflation_rate: prev[activeScenario].inflation_rate.map(() => suggestion.price_increase)
              }
            }));
          }
        } else if (category === 'cost_margins') {
          if (suggestion.cogs_percent !== undefined) {
            // COGS % affects gross margin
          }
          if (suggestion.sgna_percent !== undefined) {
            // SG&A % affects opex
            setLocalForecastDrivers(prev => ({
              ...prev,
              [activeScenario]: {
                ...prev[activeScenario],
                opex_growth: prev[activeScenario].opex_growth.map(() => suggestion.sgna_percent)
              }
            }));
          }
          if (suggestion.tax_rate !== undefined) {
            setLocalForecastDrivers(prev => ({
              ...prev,
              [activeScenario]: {
                ...prev[activeScenario],
                tax_rate: prev[activeScenario].tax_rate.map(() => suggestion.tax_rate)
              }
            }));
          }
        } else if (category === 'working_capital') {
          if (suggestion.ar_days !== undefined) {
            setLocalForecastDrivers(prev => ({
              ...prev,
              [activeScenario]: {
                ...prev[activeScenario],
                ar_days: prev[activeScenario].ar_days.map(() => suggestion.ar_days)
              }
            }));
          }
          if (suggestion.inventory_days !== undefined) {
            setLocalForecastDrivers(prev => ({
              ...prev,
              [activeScenario]: {
                ...prev[activeScenario],
                inv_days: prev[activeScenario].inv_days.map(() => suggestion.inventory_days)
              }
            }));
          }
          if (suggestion.ap_days !== undefined) {
            setLocalForecastDrivers(prev => ({
              ...prev,
              [activeScenario]: {
                ...prev[activeScenario],
                ap_days: prev[activeScenario].ap_days.map(() => suggestion.ap_days)
              }
            }));
          }
        } else if (category === 'wacc_components') {
          if (suggestion.risk_free_rate !== undefined) {
            setLocalDcfInputs(prev => ({ ...prev, risk_free_rate: suggestion.risk_free_rate }));
          }
          if (suggestion.market_risk_premium !== undefined) {
            setLocalDcfInputs(prev => ({ ...prev, equity_risk_premium: suggestion.market_risk_premium }));
          }
          if (suggestion.country_risk_premium !== undefined) {
            // CRP would need to be added to DCF inputs
          }
          if (suggestion.cost_of_debt !== undefined) {
            setLocalDcfInputs(prev => ({ ...prev, cost_of_debt: suggestion.cost_of_debt }));
          }
          if (suggestion.de_equity_ratio !== undefined) {
            // D/E ratio affects WACC calculation
          }
        } else if (category === 'terminal_value') {
          if (suggestion.terminal_growth_rate !== undefined) {
            setLocalDcfInputs(prev => ({ ...prev, terminal_growth_rate: suggestion.terminal_growth_rate }));
          }
          if (suggestion.terminal_ebitda_multiple !== undefined) {
            setLocalDcfInputs(prev => ({ ...prev, terminal_ebitda_multiple: suggestion.terminal_ebitda_multiple }));
          }
        }
      }
    } catch (error) {
      console.error('Failed to generate AI suggestion:', error);
      alert(`Failed to generate AI suggestion: ${error.message}`);
    } finally {
      setAiLoading(prev => ({ ...prev, [category]: false }));
    }
  };

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
        <div>
          <h2>Step 8: Modify Forecast Drivers & DCF Inputs</h2>
          <p style={{ color: '#666', marginTop: '8px' }}>Fine-tune revenue growth rates, margins, and other forecast drivers. Adjust assumptions for Bull/Base/Bear scenarios.</p>
        </div>
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

      {/* AI Suggestion Studio Section */}
      <div className="summary-box" style={{ marginBottom: '24px', background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3>🤖 AI Assumption Studio</h3>
          <span style={{ fontSize: '13px', color: '#666' }}>Generate AI-powered suggestions for each category</span>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          {/* Revenue Drivers */}
          <div style={{ background: 'white', padding: '16px', borderRadius: '8px', border: '1px solid #ddd' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#1976d2' }}>📈 Revenue Drivers</h4>
            <p style={{ fontSize: '13px', color: '#666', marginBottom: '12px' }}>Volume Growth & Price Increase assumptions based on historical trends and market analysis</p>
            <button
              onClick={() => handleGenerateAISuggestion('revenue_drivers')}
              disabled={aiLoading.revenue_drivers}
              style={{
                width: '100%',
                padding: '10px',
                background: aiLoading.revenue_drivers ? '#ccc' : '#2196f3',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: aiLoading.revenue_drivers ? 'not-allowed' : 'pointer',
                fontWeight: 'bold'
              }}
            >
              {aiLoading.revenue_drivers ? '⏳ Generating...' : '✨ Generate AI Suggestion'}
            </button>
            {aiSuggestions.revenue_drivers && (
              <div style={{ marginTop: '12px', padding: '8px', background: '#e3f2fd', borderRadius: '4px', fontSize: '12px' }}>
                <strong>✓ Applied:</strong>
                {aiSuggestions.revenue_drivers.volume_growth && (
                  <div>Volume Growth: {(aiSuggestions.revenue_drivers.volume_growth * 100).toFixed(1)}%</div>
                )}
                {aiSuggestions.revenue_drivers.price_increase && (
                  <div>Price Increase: {(aiSuggestions.revenue_drivers.price_increase * 100).toFixed(1)}%</div>
                )}
              </div>
            )}
          </div>

          {/* Cost & Margins */}
          <div style={{ background: 'white', padding: '16px', borderRadius: '8px', border: '1px solid #ddd' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#1976d2' }}>💰 Cost & Margins</h4>
            <p style={{ fontSize: '13px', color: '#666', marginBottom: '12px' }}>COGS %, SG&A %, and Tax Rate based on historical margins and peer benchmarks</p>
            <button
              onClick={() => handleGenerateAISuggestion('cost_margins')}
              disabled={aiLoading.cost_margins}
              style={{
                width: '100%',
                padding: '10px',
                background: aiLoading.cost_margins ? '#ccc' : '#2196f3',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: aiLoading.cost_margins ? 'not-allowed' : 'pointer',
                fontWeight: 'bold'
              }}
            >
              {aiLoading.cost_margins ? '⏳ Generating...' : '✨ Generate AI Suggestion'}
            </button>
            {aiSuggestions.cost_margins && (
              <div style={{ marginTop: '12px', padding: '8px', background: '#e3f2fd', borderRadius: '4px', fontSize: '12px' }}>
                <strong>✓ Applied:</strong>
                {aiSuggestions.cost_margins.sgna_percent && (
                  <div>SG&A %: {(aiSuggestions.cost_margins.sgna_percent * 100).toFixed(1)}%</div>
                )}
                {aiSuggestions.cost_margins.tax_rate && (
                  <div>Tax Rate: {(aiSuggestions.cost_margins.tax_rate * 100).toFixed(1)}%</div>
                )}
              </div>
            )}
          </div>

          {/* Working Capital */}
          <div style={{ background: 'white', padding: '16px', borderRadius: '8px', border: '1px solid #ddd' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#1976d2' }}>🔄 Working Capital</h4>
            <p style={{ fontSize: '13px', color: '#666', marginBottom: '12px' }}>AR Days, Inventory Days, AP Days based on historical efficiency metrics</p>
            <button
              onClick={() => handleGenerateAISuggestion('working_capital')}
              disabled={aiLoading.working_capital}
              style={{
                width: '100%',
                padding: '10px',
                background: aiLoading.working_capital ? '#ccc' : '#2196f3',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: aiLoading.working_capital ? 'not-allowed' : 'pointer',
                fontWeight: 'bold'
              }}
            >
              {aiLoading.working_capital ? '⏳ Generating...' : '✨ Generate AI Suggestion'}
            </button>
            {aiSuggestions.working_capital && (
              <div style={{ marginTop: '12px', padding: '8px', background: '#e3f2fd', borderRadius: '4px', fontSize: '12px' }}>
                <strong>✓ Applied:</strong>
                {aiSuggestions.working_capital.ar_days && (
                  <div>AR Days: {aiSuggestions.working_capital.ar_days.toFixed(0)}</div>
                )}
                {aiSuggestions.working_capital.inventory_days && (
                  <div>Inventory Days: {aiSuggestions.working_capital.inventory_days.toFixed(0)}</div>
                )}
                {aiSuggestions.working_capital.ap_days && (
                  <div>AP Days: {aiSuggestions.working_capital.ap_days.toFixed(0)}</div>
                )}
              </div>
            )}
          </div>

          {/* WACC Components */}
          <div style={{ background: 'white', padding: '16px', borderRadius: '8px', border: '1px solid #ddd' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#1976d2' }}>📊 WACC Components</h4>
            <p style={{ fontSize: '13px', color: '#666', marginBottom: '12px' }}>Risk-Free Rate, Market Risk Premium, Country Risk Premium, Cost of Debt, D/E Ratio</p>
            <button
              onClick={() => handleGenerateAISuggestion('wacc_components')}
              disabled={aiLoading.wacc_components}
              style={{
                width: '100%',
                padding: '10px',
                background: aiLoading.wacc_components ? '#ccc' : '#2196f3',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: aiLoading.wacc_components ? 'not-allowed' : 'pointer',
                fontWeight: 'bold'
              }}
            >
              {aiLoading.wacc_components ? '⏳ Generating...' : '✨ Generate AI Suggestion'}
            </button>
            {aiSuggestions.wacc_components && (
              <div style={{ marginTop: '12px', padding: '8px', background: '#e3f2fd', borderRadius: '4px', fontSize: '12px' }}>
                <strong>✓ Applied:</strong>
                {aiSuggestions.wacc_components.risk_free_rate && (
                  <div>Risk-Free Rate: {(aiSuggestions.wacc_components.risk_free_rate * 100).toFixed(2)}%</div>
                )}
                {aiSuggestions.wacc_components.market_risk_premium && (
                  <div>Market Risk Premium: {(aiSuggestions.wacc_components.market_risk_premium * 100).toFixed(2)}%</div>
                )}
                {aiSuggestions.wacc_components.cost_of_debt && (
                  <div>Cost of Debt: {(aiSuggestions.wacc_components.cost_of_debt * 100).toFixed(2)}%</div>
                )}
              </div>
            )}
          </div>

          {/* Terminal Value */}
          <div style={{ background: 'white', padding: '16px', borderRadius: '8px', border: '1px solid #ddd' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#1976d2' }}>🎯 Terminal Value</h4>
            <p style={{ fontSize: '13px', color: '#666', marginBottom: '12px' }}>Terminal Growth Rate and EBITDA Multiple based on industry standards and peer medians</p>
            <button
              onClick={() => handleGenerateAISuggestion('terminal_value')}
              disabled={aiLoading.terminal_value}
              style={{
                width: '100%',
                padding: '10px',
                background: aiLoading.terminal_value ? '#ccc' : '#2196f3',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: aiLoading.terminal_value ? 'not-allowed' : 'pointer',
                fontWeight: 'bold'
              }}
            >
              {aiLoading.terminal_value ? '⏳ Generating...' : '✨ Generate AI Suggestion'}
            </button>
            {aiSuggestions.terminal_value && (
              <div style={{ marginTop: '12px', padding: '8px', background: '#e3f2fd', borderRadius: '4px', fontSize: '12px' }}>
                <strong>✓ Applied:</strong>
                {aiSuggestions.terminal_value.terminal_growth_rate && (
                  <div>Terminal Growth: {(aiSuggestions.terminal_value.terminal_growth_rate * 100).toFixed(1)}%</div>
                )}
                {aiSuggestions.terminal_value.terminal_ebitda_multiple && (
                  <div>EBITDA Multiple: {aiSuggestions.terminal_value.terminal_ebitda_multiple.toFixed(1)}x</div>
                )}
              </div>
            )}
          </div>
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
