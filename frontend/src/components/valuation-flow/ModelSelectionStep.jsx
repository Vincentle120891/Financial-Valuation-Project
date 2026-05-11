import React from 'react';

/**
 * ModelSelectionStep Component
 * Step 4: Select Valuation Model(s)
 * 
 * FIXED: Now uses Radio Buttons instead of checkboxes.
 * Per documentation: "MUST use Radio Buttons. Multi-select is forbidden."
 * This prevents AI context hallucination from multiple simultaneous model selections.
 */
const ModelSelectionStep = ({ onSelectModel, selectedModels }) => {
  const models = [
    { 
      id: 'DCF', 
      name: 'Discounted Cash Flow', 
      desc: 'Intrinsic value based on projected free cash flows. Requires 3-year historical data + 6-period forecast.' 
    },
    { 
      id: 'DuPont', 
      name: 'DuPont Analysis', 
      desc: 'ROE decomposition into margins, turnover, and leverage. Analyzes 3-5 years of trends.' 
    },
    { 
      id: 'COMPS', 
      name: 'Trading Comps', 
      desc: 'Relative valuation using peer multiples. Automatically fetches 5+ comparable companies.' 
    }
  ];

  // GAP 2 FIX: Use single selection (radio button behavior) instead of array-based multi-select
  const handleSelectModel = (modelId) => {
    // Single selection - just pass the model ID directly (not an array)
    onSelectModel(modelId);
  };

  const isSelected = (modelId) => {
    // Single selection - selectedModels is now a string (not array)
    return selectedModels === modelId;
  };

  return (
    <div className="step-container">
      <h2>Step 4: Select Valuation Model</h2>
      <p style={{ marginBottom: '20px', color: '#666' }}>
        Choose one valuation methodology to apply.
        <strong style={{ color: '#667eea' }}> Single selection ensures accurate AI context for the chosen method.</strong>
      </p>
      <div className="model-options">
        {models.map((model) => (
          <div 
            key={model.id} 
            className={`model-card ${isSelected(model.id) ? 'selected' : ''}`}
            onClick={() => handleSelectModel(model.id)}
            style={{
              cursor: 'pointer',
              border: isSelected(model.id) ? '2px solid #667eea' : '2px solid #e0e0e0',
              background: isSelected(model.id) ? '#f8f9ff' : 'white',
              position: 'relative'
            }}
          >
            {/* GAP 2 FIX: Radio button instead of checkbox */}
            <div style={{ 
              position: 'absolute', 
              top: '10px', 
              right: '10px',
              width: '20px',
              height: '20px',
              borderRadius: '50%',  // Circle for radio button
              border: '2px solid #667eea',
              background: isSelected(model.id) ? '#667eea' : 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: '14px'
            }}>
              {isSelected(model.id) && '●'}  // Filled circle for selected radio
            </div>
            <h3>{model.name}</h3>
            <p>{model.desc}</p>
          </div>
        ))}
      </div>
      <div style={{ marginTop: '20px', textAlign: 'center' }}>
        <p style={{ color: '#666', fontSize: '14px' }}>
          {!selectedModels
            ? 'Select one model to continue'
            : `1 model selected: ${selectedModels}`}
        </p>
      </div>
    </div>
  );
};

export default ModelSelectionStep;
