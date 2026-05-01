import React from 'react';

/**
 * AiAssumptionsStep Component
 * Step 7: Review AI-Generated Assumptions
 * 
 * AI ONLY generates 4 inputs that cannot be fetched from APIs:
 * 1. Equity Risk Premium (ERP)
 * 2. Country Risk Premium (CRP)
 * 3. Terminal Growth Rate
 * 4. Terminal EBITDA Multiple
 * 
 * All other inputs (Risk-Free Rate, Beta, Cost of Debt, WACC, Forecast Drivers)
 * are calculated from API data or user-provided scenario drivers.
 */
const AiAssumptionsStep = ({
  aiData,
  aiError,
  confirmedValues,
  selectedModel,
  onManualInput,
  onUseAI,
  onBackToApiData,
  onContinueToForecastDrivers,
  loading
}) => {
  // Handle using AI suggestion
  const handleUseAiSuggestion = (field, value) => {
    if (onUseAI) {
      onUseAI(field, value);
    }
  };

  // Handle manual input
  const handleManualInputChange = (field, value) => {
    if (onManualInput) {
      onManualInput(field, value);
    }
  };

  // Render AI error/warning message
  const renderAiError = () => {
    if (!aiError) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)', border: '2px solid #ff9800', marginBottom: '20px' }}>
        <h3 style={{ color: '#e65100' }}>⚠️ AI Generation Issue</h3>
        <p style={{ marginBottom: '12px', color: '#e65100' }}>{aiError}</p>
        <div style={{ background: 'white', padding: '12px', borderRadius: '6px', marginTop: '12px' }}>
          <strong>💡 What this means:</strong>
          <p style={{ margin: '8px 0', color: '#333' }}>
            AI-powered suggestions could not be generated. You can still proceed by manually entering your assumptions.
          </p>
          <strong>📋 Next Steps:</strong>
          <ol style={{ margin: '8px 0', paddingLeft: '20px', color: '#333' }}>
            <li>Enter your assumptions manually in the fields below</li>
            <li>Use historical trends and peer benchmarks to inform your inputs</li>
            <li>Optionally go back and retry AI generation</li>
          </ol>
        </div>
      </div>
    );
  };

  // Helper to extract value from AI data structure
  const getAiValue = (field) => {
    // Check multiple possible field names
    const possibleKeys = [
      field,
      `${field}_value`,
      `${field}_percent`,
      `${field}_rate`
    ];
    
    for (const key of possibleKeys) {
      if (aiData?.[key]) {
        const item = aiData[key];
        if (typeof item === 'object' && 'value' in item) {
          return item.value;
        }
        return item;
      }
    }
    return undefined;
  };

  // Helper to extract rationale from AI data structure
  const getAiRationale = (field) => {
    const item = aiData?.[field];
    if (item && typeof item === 'object' && 'rationale' in item) {
      return item.rationale;
    }
    return aiData?.[`${field}_rationale`];
  };

  // Render single assumption field
  const renderAssumptionField = ({ 
    fieldKey, 
    label, 
    step = 0.01, 
    isPercentage = true,
    min,
    max,
    description
  }) => {
    const aiValue = getAiValue(fieldKey);
    const confirmedValue = confirmedValues?.[fieldKey]?.value;
    const displayValue = confirmedValue !== undefined ? confirmedValue : aiValue;
    const rationale = getAiRationale(fieldKey);

    // Convert to percentage for display if needed
    const displayPercent = displayValue !== undefined 
      ? (displayValue > 1 ? displayValue / 100 : displayValue) * 100 
      : '';

    return (
      <div style={{ background: 'white', padding: '16px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #ddd' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <h4 style={{ margin: 0, color: '#1976d2' }}>{label}</h4>
          {aiValue !== undefined && (
            <span style={{ fontSize: '12px', padding: '4px 8px', background: '#e3f2fd', borderRadius: '4px', color: '#1565c0' }}>
              🤖 AI Suggested
            </span>
          )}
        </div>
        
        {description && (
          <p style={{ fontSize: '13px', color: '#666', marginBottom: '12px' }}>{description}</p>
        )}
        
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input
            type="number"
            step={step}
            min={min}
            max={max}
            value={displayPercent || ''}
            onChange={(e) => {
              const val = parseFloat(e.target.value);
              const rawValue = isPercentage ? val / 100 : val;
              handleManualInputChange(fieldKey, rawValue);
            }}
            placeholder={`Enter ${label}`}
            style={{ flex: 1, padding: '10px', borderRadius: '6px', border: '1px solid #ccc', fontSize: '14px' }}
          />
          {isPercentage && <span style={{ fontWeight: 600, color: '#333' }}>%</span>}
          
          {aiValue !== undefined && (
            <button
              onClick={() => handleUseAiSuggestion(fieldKey, aiValue)}
              style={{
                padding: '10px 16px',
                background: confirmedValues?.[fieldKey]?.source === 'ai' ? '#4caf50' : '#2196f3',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              {confirmedValues?.[fieldKey]?.source === 'ai' ? '✓ Using AI' : 'Use AI'}
            </button>
          )}
        </div>
        
        {rationale && (
          <p style={{ marginTop: '8px', fontSize: '13px', color: '#666', fontStyle: 'italic' }}>
            <strong>Rationale:</strong> {rationale}
          </p>
        )}
      </div>
    );
  };

  // Render the 4 AI-only inputs
  const renderAiOnlyInputs = () => {
    return (
      <>
        {renderAssumptionField({
          fieldKey: 'equity_risk_premium',
          label: 'Equity Risk Premium (ERP)',
          description: 'Expected excess return of the market over the risk-free rate. Typical range: 4.5% - 6.5% for developed markets.',
          min: 0,
          max: 15
        })}
        
        {renderAssumptionField({
          fieldKey: 'country_risk_premium',
          label: 'Country Risk Premium (CRP)',
          description: 'Additional risk premium for the company\'s primary operating country. 0% for stable developed markets like US.',
          min: 0,
          max: 10
        })}
        
        {renderAssumptionField({
          fieldKey: 'terminal_growth_rate',
          label: 'Terminal Growth Rate',
          description: 'Perpetual growth rate for terminal value calculation. Should not exceed long-term GDP growth (typically 2-3%).',
          min: 0,
          max: 5
        })}
        
        {renderAssumptionField({
          fieldKey: 'terminal_ebitda_multiple',
          label: 'Terminal EBITDA Multiple',
          description: 'Expected exit multiple at end of forecast period. Varies by sector: Tech (10-15x), Consumer (10-14x), Industrials (8-12x).',
          isPercentage: false,
          step: 0.5,
          min: 0,
          max: 30
        })}
      </>
    );
  };

  // Render AI rationale summary
  const renderAiRationaleSummary = () => {
    const rationale = aiData?.ai_rationale?.value || aiData?.rationale;
    if (!rationale) return null;

    return (
      <div style={{ background: '#f5f5f5', padding: '16px', borderRadius: '8px', marginBottom: '20px', border: '1px solid #ddd' }}>
        <h4 style={{ margin: '0 0 8px 0', color: '#333' }}>🤖 AI Analysis Summary</h4>
        <p style={{ margin: 0, fontSize: '14px', lineHeight: '1.6', color: '#555' }}>{rationale}</p>
      </div>
    );
  };

  return (
    <div className="step-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Step 7: AI Assumptions</h2>
        <button onClick={onBackToApiData} className="btn-secondary">
          ← Back to API Data
        </button>
      </div>
      
      <div style={{ marginBottom: '20px', padding: '16px', background: '#e3f2fd', borderRadius: '8px' }}>
        <p style={{ margin: 0, color: '#1565c0' }}>
          <strong>ℹ️ About this step:</strong> AI generates ONLY 4 forward-looking assumptions that cannot be fetched from financial APIs.
          All other inputs (Risk-Free Rate, Beta, Cost of Debt, WACC, Forecast Drivers) are calculated from API data or provided in Scenario Drivers.
        </p>
      </div>

      {renderAiError()}

      {selectedModel === 'DCF' && (
        <>
          {renderAiOnlyInputs()}
          {renderAiRationaleSummary()}
        </>
      )}

      {!aiData || Object.keys(aiData).length === 0 ? (
        <div className="summary-box" style={{ background: 'linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%)' }}>
          <h3>⚠️ No AI Suggestions Available</h3>
          <p>Please enter your assumptions manually or go back to retry AI generation.</p>
        </div>
      ) : null}

      <div style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
        <button 
          onClick={onContinueToForecastDrivers} 
          className="btn-primary"
          disabled={loading}
        >
          Continue to Forecast Drivers →
        </button>
      </div>
    </div>
  );
};

export default AiAssumptionsStep;
