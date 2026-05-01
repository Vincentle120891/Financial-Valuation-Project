import React from 'react';

/**
 * AiAssumptionsStep Component
 * Step 7: Review AI-Generated Assumptions
 * 
 * Features:
 * - Display AI-generated assumptions with confidence scores
 * - Show AI rationale for each assumption
 * - Allow manual override of AI suggestions
 * - Display warnings when AI generation failed/timed out
 * - Navigate to Step 8 (Forecast Drivers) or back to Step 6
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

  // Render WACC assumption
  const renderWaccAssumption = () => {
    const aiValue = aiData?.wacc || aiData?.wacc_percent?.value;
    const confirmedValue = confirmedValues?.wacc?.value;
    const displayValue = confirmedValue !== undefined ? confirmedValue : aiValue;

    return (
      <div style={{ background: 'white', padding: '16px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #ddd' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h4 style={{ margin: 0, color: '#1976d2' }}>WACC (Weighted Average Cost of Capital)</h4>
          {aiData?.wacc && (
            <span style={{ fontSize: '12px', padding: '4px 8px', background: '#e3f2fd', borderRadius: '4px', color: '#1565c0' }}>
              🤖 AI Suggested
            </span>
          )}
        </div>
        
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input
            type="number"
            step="0.01"
            value={displayValue !== undefined ? (displayValue > 1 ? displayValue / 100 : displayValue) * 100 : ''}
            onChange={(e) => handleManualInputChange('wacc', parseFloat(e.target.value) / 100)}
            placeholder="Enter WACC %"
            style={{ flex: 1, padding: '10px', borderRadius: '6px', border: '1px solid #ccc', fontSize: '14px' }}
          />
          <span style={{ fontWeight: 600, color: '#333' }}>%</span>
          
          {aiData?.wacc && (
            <button
              onClick={() => handleUseAiSuggestion('wacc', aiData.wacc)}
              style={{
                padding: '10px 16px',
                background: confirmedValues?.wacc?.source === 'ai' ? '#4caf50' : '#2196f3',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              {confirmedValues?.wacc?.source === 'ai' ? '✓ Using AI' : 'Use AI'}
            </button>
          )}
        </div>
        
        {aiData?.wacc_rationale && (
          <p style={{ marginTop: '8px', fontSize: '13px', color: '#666', fontStyle: 'italic' }}>
            <strong>Rationale:</strong> {aiData.wacc_rationale}
          </p>
        )}
      </div>
    );
  };

  // Render Terminal Growth assumption
  const renderTerminalGrowthAssumption = () => {
    const aiValue = aiData?.terminal_growth || aiData?.terminal_growth_rate_percent?.value;
    const confirmedValue = confirmedValues?.terminal_growth?.value;
    const displayValue = confirmedValue !== undefined ? confirmedValue : aiValue;

    return (
      <div style={{ background: 'white', padding: '16px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #ddd' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h4 style={{ margin: 0, color: '#1976d2' }}>Terminal Growth Rate</h4>
          {aiData?.terminal_growth && (
            <span style={{ fontSize: '12px', padding: '4px 8px', background: '#e3f2fd', borderRadius: '4px', color: '#1565c0' }}>
              🤖 AI Suggested
            </span>
          )}
        </div>
        
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input
            type="number"
            step="0.01"
            value={displayValue !== undefined ? (displayValue > 1 ? displayValue / 100 : displayValue) * 100 : ''}
            onChange={(e) => handleManualInputChange('terminal_growth', parseFloat(e.target.value) / 100)}
            placeholder="Enter Terminal Growth %"
            style={{ flex: 1, padding: '10px', borderRadius: '6px', border: '1px solid #ccc', fontSize: '14px' }}
          />
          <span style={{ fontWeight: 600, color: '#333' }}>%</span>
          
          {aiData?.terminal_growth && (
            <button
              onClick={() => handleUseAiSuggestion('terminal_growth', aiData.terminal_growth)}
              style={{
                padding: '10px 16px',
                background: confirmedValues?.terminal_growth?.source === 'ai' ? '#4caf50' : '#2196f3',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              {confirmedValues?.terminal_growth?.source === 'ai' ? '✓ Using AI' : 'Use AI'}
            </button>
          )}
        </div>
        
        {aiData?.terminal_growth_rationale && (
          <p style={{ marginTop: '8px', fontSize: '13px', color: '#666', fontStyle: 'italic' }}>
            <strong>Rationale:</strong> {aiData.terminal_growth_rationale}
          </p>
        )}
      </div>
    );
  };

  // Render Revenue Growth Forecast
  const renderRevenueGrowthForecast = () => {
    const aiForecast = aiData?.revenue_growth_forecast;
    
    if (!aiForecast) return null;

    return (
      <div style={{ background: 'white', padding: '16px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #ddd' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h4 style={{ margin: 0, color: '#1976d2' }}>Revenue Growth Forecast</h4>
          <span style={{ fontSize: '12px', padding: '4px 8px', background: '#e3f2fd', borderRadius: '4px', color: '#1565c0' }}>
            🤖 AI Generated
          </span>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: '8px' }}>
          {aiForecast.map((growth, idx) => (
            <div key={idx} style={{ textAlign: 'center', padding: '8px', background: '#f5f5f5', borderRadius: '4px' }}>
              <div style={{ fontSize: '12px', color: '#666' }}>Year {idx + 1}</div>
              <div style={{ fontWeight: 600, color: '#1976d2' }}>{(growth * 100).toFixed(1)}%</div>
            </div>
          ))}
        </div>
        
        {aiData?.revenue_growth_rationale && (
          <p style={{ marginTop: '8px', fontSize: '13px', color: '#666', fontStyle: 'italic' }}>
            <strong>Rationale:</strong> {aiData.revenue_growth_rationale}
          </p>
        )}
      </div>
    );
  };

  // Render EBITDA Margin Forecast
  const renderEbitdaMarginForecast = () => {
    const aiForecast = aiData?.ebitda_margin_forecast;
    
    if (!aiForecast) return null;

    return (
      <div style={{ background: 'white', padding: '16px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #ddd' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h4 style={{ margin: 0, color: '#1976d2' }}>EBITDA Margin Forecast</h4>
          <span style={{ fontSize: '12px', padding: '4px 8px', background: '#e3f2fd', borderRadius: '4px', color: '#1565c0' }}>
            🤖 AI Generated
          </span>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: '8px' }}>
          {aiForecast.map((margin, idx) => (
            <div key={idx} style={{ textAlign: 'center', padding: '8px', background: '#f5f5f5', borderRadius: '4px' }}>
              <div style={{ fontSize: '12px', color: '#666' }}>Year {idx + 1}</div>
              <div style={{ fontWeight: 600, color: '#1976d2' }}>{(margin * 100).toFixed(1)}%</div>
            </div>
          ))}
        </div>
        
        {aiData?.ebitda_margin_rationale && (
          <p style={{ marginTop: '8px', fontSize: '13px', color: '#666', fontStyle: 'italic' }}>
            <strong>Rationale:</strong> {aiData.ebitda_margin_rationale}
          </p>
        )}
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
          <strong>ℹ️ About this step:</strong> Review AI-generated assumptions for your valuation model. 
          You can accept AI suggestions or manually override them with your own inputs.
        </p>
      </div>

      {renderAiError()}

      {selectedModel === 'DCF' && (
        <>
          {renderWaccAssumption()}
          {renderTerminalGrowthAssumption()}
          {renderRevenueGrowthForecast()}
          {renderEbitdaMarginForecast()}
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
